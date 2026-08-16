import os
from datetime import datetime

from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from django.db.models import Count, Q
from django.utils import timezone

from main.core.smpp import SMPPCCM
from main.core.models import SubmitLog
from main.web.views.content.smppccm import _tail_lines, _summarize_reason, LOG_DIR

_FAILED = ['UNDELIV', 'EXPIRED', 'REJECTD', 'ESME_RDELIVERYFAILURE']


def _agg(qs):
    return qs.aggregate(
        total=Count('id'),
        delivered=Count('id', filter=Q(status='DELIVRD')),
        failed=Count('id', filter=Q(status__in=_FAILED)),
        pending=Count('id', filter=Q(status='ESME_ROK')),
    )


def _parse_dt(s):
    try:
        return datetime.strptime(s, "%Y-%m-%d %H:%M:%S")
    except (ValueError, TypeError):
        return None


def _humanize(delta):
    if not delta:
        return None
    secs = int(delta.total_seconds())
    if secs < 0:
        return None
    d, rem = divmod(secs, 86400)
    h, rem = divmod(rem, 3600)
    m, _ = divmod(rem, 60)
    parts = []
    if d:
        parts.append("%dd" % d)
    if h:
        parts.append("%dh" % h)
    if m or not parts:
        parts.append("%dm" % m)
    return " ".join(parts)


@login_required
def connection_detail_view(request, cid):
    try:
        connector = SMPPCCM().retrieve(cid).get('connector')
    except Exception:
        connector = None
    try:
        stats = SMPPCCM().get_stats(cid)  # fresh session
    except Exception:
        stats = {}

    session = (connector or {}).get('session', '') if connector else ''
    is_bound = str(session).startswith('BOUND')

    def _sval(k):
        v = stats.get(k)
        return None if v in (None, 'ND', '') else v

    bound_at = _parse_dt(_sval('bound_at'))
    uptime_str = _humanize(datetime.now() - bound_at) if (is_bound and bound_at) else None

    base = SubmitLog.objects.filter(routed_cid=cid)
    now = timezone.localtime()
    today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
    traffic = {'all': _agg(base), 'today': _agg(base.filter(created_at__gte=today_start))}

    reason = None
    try:
        path = os.path.join(LOG_DIR, "default-%s.log" % cid)
        if os.path.isfile(path):
            reason = _summarize_reason(_tail_lines(path, 200))
    except Exception:
        reason = None

    context = {
        'cid': cid,
        'connector': connector,
        'not_found': connector is None,
        'stats': stats,
        'session': session,
        'is_bound': is_bound,
        'uptime': uptime_str,
        'connected_at': _sval('connected_at'),
        'disconnected_at': _sval('disconnected_at'),
        'bound_count': _sval('bound_count') or '0',
        'disconnected_count': _sval('disconnected_count') or '0',
        'last_pdu_at': _sval('last_received_pdu_at') or _sval('last_sent_pdu_at'),
        'submit_count': _sval('submit_sm_count') or '0',
        'deliver_count': _sval('deliver_sm_count') or '0',
        'throttling_errors': _sval('throttling_error_count') or '0',
        'other_errors': _sval('other_submit_error_count') or '0',
        'traffic': traffic,
        'reason': reason,
    }
    return render(request, 'web/content/connection_detail.html', context)
