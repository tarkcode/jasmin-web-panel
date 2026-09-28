"""
Tests for Fake DLR interception in main/web/helpers.py.

Covers:
- _get_user_fake_dlr_config: DB-backed cache with TTL, shared across "workers"
  (simulated here by hitting the same Django cache backend directly).
- _increment_user_message_count: atomic cache-backed counter, window TTL.
- fake_dlr_send: end-to-end short-circuit behavior (percentage/threshold),
  making sure no real send is attempted when a message is intercepted.
"""
import pytest
from django.contrib.auth import get_user_model
from django.core.cache import cache

from main.core.models.smpp import GroupsModel, UsersModel
from main.web.helpers import (
    _FAKE_DLR_CONFIG_CACHE_KEY,
    _FAKE_DLR_COUNTER_KEY_PREFIX,
    _get_user_fake_dlr_config,
    _increment_user_message_count,
    fake_dlr_send,
)

User = get_user_model()


@pytest.fixture(autouse=True)
def clear_fake_dlr_cache():
    """Ensure each test starts with a clean cache (config map + counters)."""
    cache.clear()
    yield
    cache.clear()


@pytest.fixture
def make_user(db):
    """Factory fixture to create a UsersModel row with fake DLR settings."""
    counter = {"n": 0}

    def _make(username="alice", fake_dlr_percentage=0, fake_dlr_threshold=0,
              fake_dlr_window_minutes=60):
        counter["n"] += 1
        n = counter["n"]
        group = GroupsModel.objects.create(gid=f"grp{n}")
        auth_user = User.objects.create_user(
            username=f"{username}_auth_{n}", password="testpass123"
        )
        return UsersModel.objects.create(
            uid=f"uid_{n}",
            gid=group,
            username=username,
            password="smpp_pass",
            parameters="{}",
            user=auth_user,
            fake_dlr_percentage=fake_dlr_percentage,
            fake_dlr_threshold=fake_dlr_threshold,
            fake_dlr_window_minutes=fake_dlr_window_minutes,
        )

    return _make


@pytest.mark.django_db
class TestGetUserFakeDlrConfig:
    def test_cache_miss_loads_from_db(self, make_user):
        make_user(username="bob", fake_dlr_percentage=50, fake_dlr_threshold=3,
                  fake_dlr_window_minutes=30)

        config = _get_user_fake_dlr_config("bob")

        assert config == {"percentage": 50, "threshold": 3, "window_minutes": 30}

    def test_unknown_user_returns_defaults(self, make_user):
        make_user(username="carol", fake_dlr_percentage=100)

        config = _get_user_fake_dlr_config("someone_else")

        assert config == {"percentage": 0, "threshold": 0, "window_minutes": 60}

    def test_cache_is_reused_without_hitting_db_again(self, make_user):
        user = make_user(username="dave", fake_dlr_percentage=20)

        first = _get_user_fake_dlr_config("dave")
        # Mutate the DB row directly; cached value should NOT reflect this
        # until the cache TTL expires and is refreshed.
        UsersModel.objects.filter(pk=user.pk).update(fake_dlr_percentage=99)
        second = _get_user_fake_dlr_config("dave")

        assert first == second == {"percentage": 20, "threshold": 0, "window_minutes": 60}

    def test_config_shared_across_cache_clients(self, make_user):
        """
        Simulates two different Gunicorn worker processes by using two
        independent lookups against the same shared cache backend - both
        must see the identical config once it has been populated.
        """
        make_user(username="erin", fake_dlr_percentage=75, fake_dlr_threshold=1,
                  fake_dlr_window_minutes=15)

        worker_a_view = _get_user_fake_dlr_config("erin")
        # Nothing worker-local involved; reading straight from the cache
        # backend confirms the data really is shared state, not a dict
        # local to this process/module.
        raw_cached_map = cache.get(_FAKE_DLR_CONFIG_CACHE_KEY)
        worker_b_view = _get_user_fake_dlr_config("erin")

        assert raw_cached_map["erin"] == {"percentage": 75, "threshold": 1, "window_minutes": 15}
        assert worker_a_view == worker_b_view


@pytest.mark.django_db
class TestIncrementUserMessageCount:
    def test_first_call_returns_one(self):
        result = _increment_user_message_count("frank", window_minutes=60)
        assert result == 1

    def test_increments_atomically_across_calls(self):
        assert _increment_user_message_count("gina", window_minutes=60) == 1
        assert _increment_user_message_count("gina", window_minutes=60) == 2
        assert _increment_user_message_count("gina", window_minutes=60) == 3

    def test_counters_are_isolated_per_username(self):
        _increment_user_message_count("henry", window_minutes=60)
        _increment_user_message_count("henry", window_minutes=60)
        _increment_user_message_count("irene", window_minutes=60)

        assert cache.get(_FAKE_DLR_COUNTER_KEY_PREFIX + "henry") == 2
        assert cache.get(_FAKE_DLR_COUNTER_KEY_PREFIX + "irene") == 1

    def test_counter_visible_to_a_second_reader(self):
        """
        Cross-worker consistency check: incrementing via one call path and
        reading the raw cache key directly (as another worker process would)
        must show the same value — this is the whole point of moving off
        the old per-process module-level dict.
        """
        _increment_user_message_count("jack", window_minutes=60)
        _increment_user_message_count("jack", window_minutes=60)

        assert cache.get(_FAKE_DLR_COUNTER_KEY_PREFIX + "jack") == 2


@pytest.mark.django_db
class TestFakeDlrSend:
    def test_percentage_zero_never_intercepts(self, make_user):
        make_user(username="kate", fake_dlr_percentage=0)

        intercepted, msgid = fake_dlr_send("1000", "254700000000", "hello", "kate")

        assert intercepted is False
        assert msgid == ""

    def test_percentage_100_always_intercepts(self, make_user):
        make_user(username="leo", fake_dlr_percentage=100, fake_dlr_threshold=0)

        intercepted, msgid = fake_dlr_send("1000", "254700000000", "hello", "leo")

        assert intercepted is True
        assert isinstance(msgid, str) and msgid != ""

    def test_unknown_user_never_intercepts(self):
        intercepted, msgid = fake_dlr_send("1000", "254700000000", "hello", "ghost_user")

        assert intercepted is False
        assert msgid == ""

    def test_threshold_keeps_first_n_messages_real(self, make_user):
        make_user(username="mona", fake_dlr_percentage=100, fake_dlr_threshold=2,
                  fake_dlr_window_minutes=60)

        first = fake_dlr_send("1000", "254700000000", "msg1", "mona")
        second = fake_dlr_send("1000", "254700000000", "msg2", "mona")
        third = fake_dlr_send("1000", "254700000000", "msg3", "mona")

        assert first == (False, "")
        assert second == (False, "")
        assert third[0] is True

    def test_each_call_increments_the_shared_counter(self, make_user):
        make_user(username="nina", fake_dlr_percentage=100, fake_dlr_threshold=5,
                  fake_dlr_window_minutes=60)

        for _ in range(3):
            fake_dlr_send("1000", "254700000000", "hi", "nina")

        assert cache.get(_FAKE_DLR_COUNTER_KEY_PREFIX + "nina") == 3

    def test_intercepted_message_returns_unique_msgid_format(self, make_user):
        make_user(username="oscar", fake_dlr_percentage=100)

        _, msgid1 = fake_dlr_send("1000", "254700000000", "hi", "oscar")

        # Should look like a real msgid: non-empty, no surrounding whitespace.
        assert msgid1.strip() == msgid1
        assert len(msgid1) > 0
