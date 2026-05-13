"""
Celery tasks for the campaigns module.

Two tasks of interest:
- run_campaign(campaign_id): drains pending recipients at the configured throttle,
  honoring pause/cancel by re-checking campaign.status each batch.
- sync_campaign_dlrs(campaign_id=None): correlates submit_log entries back to
  CampaignRecipient.msgid to update delivery status. If no campaign_id is given
  it runs across every live campaign.

The worker is intentionally simple: a single celery worker drains one campaign
at a time. Multiple campaigns can run in parallel by virtue of celery's
prefetch — each call to run_campaign holds one slot.
"""
import logging
import time

from celery import shared_task
from django.db import transaction
from django.db.models import F
from django.utils import timezone

from main.campaigns.models import Campaign, CampaignRecipient
from main.campaigns.services import render_template
from main.web.helpers import send_smpp, send_http

logger = logging.getLogger(__name__)

BATCH_SIZE = 50
HEARTBEAT_EVERY = 25  # check campaign.status from DB this often
DLR_LOOKUP_LIMIT = 5000  # per sync run

# Status maps from submit_log to recipient
DELIVERED_STATUSES = {"DELIVRD"}
FAILED_STATUSES = {"UNDELIV", "REJECTD", "EXPIRED", "DELETED",
                   "ESME_RDELIVERYFAILURE", "ESME_RSYSERR", "ESME_RINVDFTMSGID"}


def _resolve_user_credentials(user_uid: str):
    """Look up Jasmin user creds from the local mirror table. Returns (username, password) or (None, None)."""
    if not user_uid:
        return None, None
    try:
        from main.core.models import UsersModel
        u = UsersModel.objects.filter(uid=user_uid).first()
        if u:
            return u.username, u.password
    except Exception as exc:
        logger.warning(f"Could not resolve user_uid={user_uid}: {exc}")
    return None, None


def _send_one(campaign: Campaign, recipient: CampaignRecipient):
    """Render template, send via configured method, return (ok, msgid, error)."""
    text = render_template(campaign.message_template, recipient.variables, msisdn=recipient.msisdn)
    username, password = _resolve_user_credentials(campaign.user_uid)

    try:
        validity_seconds = int(campaign.message_validity) if campaign.message_validity else 0
    except (ValueError, TypeError):
        validity_seconds = 0

    common_kwargs = dict(
        encoding=campaign.encoding or "auto",
        validity_seconds=validity_seconds,
    )

    try:
        if campaign.send_method == Campaign.SEND_METHOD_HTTP:
            code, body, msgid = send_http(campaign.sender_id, recipient.msisdn, text,
                                          username=username, password=password, **common_kwargs)
        else:
            code, body, msgid = send_smpp(campaign.sender_id, recipient.msisdn, text,
                                          system_id=username, password=password, **common_kwargs)
    except Exception as exc:
        return False, "", f"send error: {exc}"

    if 200 <= code < 300:
        return True, msgid, ""
    return False, "", (body or f"HTTP {code}")[:500]


@shared_task(bind=True, name="campaigns.run_campaign")
def run_campaign(self, campaign_id: int):
    try:
        campaign = Campaign.objects.get(pk=campaign_id)
    except Campaign.DoesNotExist:
        logger.warning(f"Campaign #{campaign_id} not found")
        return

    if campaign.status not in (Campaign.STATUS_QUEUED, Campaign.STATUS_PAUSED, Campaign.STATUS_RUNNING):
        logger.info(f"Campaign #{campaign_id} status={campaign.status}, skipping")
        return

    Campaign.objects.filter(pk=campaign_id).update(
        status=Campaign.STATUS_RUNNING,
        started_at=campaign.started_at or timezone.now(),
    )

    # Token-bucket-ish throttle: sleep `interval` between sends.
    interval = 1.0 / max(1, campaign.throttle_mps)
    processed_since_heartbeat = 0

    logger.info(f"Campaign #{campaign_id} draining at {campaign.throttle_mps} mps")

    while True:
        # heartbeat: check if we got paused / cancelled
        if processed_since_heartbeat >= HEARTBEAT_EVERY:
            processed_since_heartbeat = 0
        if processed_since_heartbeat == 0:
            campaign.refresh_from_db(fields=["status"])
            if campaign.status in (Campaign.STATUS_PAUSED, Campaign.STATUS_CANCELLED, Campaign.STATUS_FAILED):
                logger.info(f"Campaign #{campaign_id} stopping (status={campaign.status})")
                return

        # Claim a batch atomically.
        with transaction.atomic():
            batch = list(
                CampaignRecipient.objects.select_for_update(skip_locked=True)
                .filter(campaign_id=campaign_id, status=CampaignRecipient.STATUS_PENDING)
                .order_by("id")[:BATCH_SIZE]
            )
            if not batch:
                # Nothing left → mark completed.
                Campaign.objects.filter(pk=campaign_id).update(
                    status=Campaign.STATUS_COMPLETED,
                    finished_at=timezone.now(),
                )
                logger.info(f"Campaign #{campaign_id} completed")
                return
            ids = [r.id for r in batch]
            CampaignRecipient.objects.filter(id__in=ids).update(status=CampaignRecipient.STATUS_SENDING)

        for r in batch:
            ok, msgid, error = _send_one(campaign, r)
            now = timezone.now()
            if ok:
                CampaignRecipient.objects.filter(pk=r.pk).update(
                    status=CampaignRecipient.STATUS_SENT,
                    msgid=msgid or "",
                    sent_at=now,
                    error_message="",
                )
                Campaign.objects.filter(pk=campaign_id).update(sent_count=F("sent_count") + 1)
            else:
                CampaignRecipient.objects.filter(pk=r.pk).update(
                    status=CampaignRecipient.STATUS_FAILED,
                    error_message=error,
                    sent_at=now,
                )
                Campaign.objects.filter(pk=campaign_id).update(failed_count=F("failed_count") + 1)
            processed_since_heartbeat += 1
            time.sleep(interval)


@shared_task(bind=True, name="campaigns.sync_campaign_dlrs")
def sync_campaign_dlrs(self, campaign_id: int = None):
    """
    Correlate CampaignRecipient.msgid → SubmitLog.status. Updates recipient.status
    and bumps delivered_count / failed_count on the parent campaign.

    If campaign_id is None, scans every live campaign — useful as a periodic task.
    """
    from main.core.models import SubmitLog

    qs = CampaignRecipient.objects.exclude(msgid="").filter(
        status__in=[CampaignRecipient.STATUS_SENT, CampaignRecipient.STATUS_SENDING]
    )
    if campaign_id is not None:
        qs = qs.filter(campaign_id=campaign_id)
    else:
        qs = qs.filter(campaign__status__in=Campaign.LIVE_STATUSES)
    qs = qs[:DLR_LOOKUP_LIMIT]

    updated = 0
    for r in qs:
        log = SubmitLog.objects.filter(msgid=r.msgid).order_by("-status_at").first()
        if not log:
            continue
        if log.status in DELIVERED_STATUSES:
            CampaignRecipient.objects.filter(pk=r.pk).update(
                status=CampaignRecipient.STATUS_DELIVERED,
                delivered_at=log.status_at,
            )
            Campaign.objects.filter(pk=r.campaign_id).update(delivered_count=F("delivered_count") + 1)
            updated += 1
        elif log.status in FAILED_STATUSES:
            # Only count if previously sent — we already counted failures-at-submit elsewhere.
            CampaignRecipient.objects.filter(pk=r.pk).update(
                status=CampaignRecipient.STATUS_UNDELIVERED,
                error_message=log.status,
            )
            updated += 1
    return {"updated": updated}
