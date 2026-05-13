from django.conf import settings
from django.db import models
from django.utils.translation import gettext_lazy as _

from main.core.models.timestamped import TimeStampedModel


class Campaign(TimeStampedModel):
    STATUS_DRAFT = "draft"
    STATUS_SCHEDULED = "scheduled"
    STATUS_QUEUED = "queued"
    STATUS_RUNNING = "running"
    STATUS_PAUSED = "paused"
    STATUS_COMPLETED = "completed"
    STATUS_CANCELLED = "cancelled"
    STATUS_FAILED = "failed"

    STATUS_CHOICES = (
        (STATUS_DRAFT, _("Draft")),
        (STATUS_SCHEDULED, _("Scheduled")),
        (STATUS_QUEUED, _("Queued")),
        (STATUS_RUNNING, _("Running")),
        (STATUS_PAUSED, _("Paused")),
        (STATUS_COMPLETED, _("Completed")),
        (STATUS_CANCELLED, _("Cancelled")),
        (STATUS_FAILED, _("Failed")),
    )

    SEND_METHOD_SMPP = "smpp"
    SEND_METHOD_HTTP = "http"
    SEND_METHOD_CHOICES = (
        (SEND_METHOD_SMPP, "SMPP"),
        (SEND_METHOD_HTTP, "HTTP"),
    )

    SMS_TYPE_CHOICES = (
        ("transactional", _("Transactional")),
        ("promotional", _("Promotional")),
        ("otp", _("OTP")),
        ("marketing", _("Marketing")),
    )

    ENCODING_AUTO = "auto"
    ENCODING_GSM7 = "gsm7"
    ENCODING_UCS2 = "ucs2"
    ENCODING_CHOICES = (
        (ENCODING_AUTO, "Auto-detect"),
        (ENCODING_GSM7, "GSM 7-bit"),
        (ENCODING_UCS2, "UCS-2 (Unicode)"),
    )

    AUDIENCE_CSV = "csv"
    AUDIENCE_QUICK_LIST = "quick_list"
    AUDIENCE_CHOICES = (
        (AUDIENCE_CSV, _("CSV upload")),
        (AUDIENCE_QUICK_LIST, _("Quick number list")),
    )

    VALIDITY_UNLIMITED = ""
    VALIDITY_CHOICES = (
        (VALIDITY_UNLIMITED, _("Unlimited")),
        ("3600", _("1 hour")),
        ("21600", _("6 hours")),
        ("43200", _("12 hours")),
        ("86400", _("24 hours")),
        ("172800", _("48 hours")),
    )

    LIVE_STATUSES = (STATUS_QUEUED, STATUS_RUNNING, STATUS_PAUSED, STATUS_SCHEDULED)
    TERMINAL_STATUSES = (STATUS_COMPLETED, STATUS_CANCELLED, STATUS_FAILED)

    name = models.CharField(_("Name"), max_length=120)
    description = models.TextField(_("Description"), blank=True, default="")
    sms_type = models.CharField(_("SMS type"), max_length=16, choices=SMS_TYPE_CHOICES, default="transactional")
    message_template = models.TextField(_("Message template"))
    sender_id = models.CharField(_("Sender ID"), max_length=24)
    send_method = models.CharField(_("Send method"), max_length=8, choices=SEND_METHOD_CHOICES, default=SEND_METHOD_SMPP)
    user_uid = models.CharField(_("Jasmin user UID"), max_length=24, blank=True, default="")
    encoding = models.CharField(_("Encoding"), max_length=8, choices=ENCODING_CHOICES, default=ENCODING_AUTO)
    is_rtl = models.BooleanField(_("Right-to-left"), default=False)
    message_validity = models.CharField(_("Message validity (seconds)"), max_length=12, choices=VALIDITY_CHOICES, blank=True, default=VALIDITY_UNLIMITED)
    audience_source = models.CharField(_("Audience source"), max_length=16, choices=AUDIENCE_CHOICES, default=AUDIENCE_CSV)

    status = models.CharField(_("Status"), max_length=12, choices=STATUS_CHOICES, default=STATUS_DRAFT, db_index=True)
    scheduled_at = models.DateTimeField(_("Scheduled at"), null=True, blank=True)
    started_at = models.DateTimeField(_("Started at"), null=True, blank=True)
    finished_at = models.DateTimeField(_("Finished at"), null=True, blank=True)

    throttle_mps = models.PositiveIntegerField(_("Throttle (msgs/sec)"), default=10)

    total_recipients = models.PositiveIntegerField(default=0)
    sent_count = models.PositiveIntegerField(default=0)
    delivered_count = models.PositiveIntegerField(default=0)
    failed_count = models.PositiveIntegerField(default=0)

    last_error = models.TextField(blank=True, default="")
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL,
                                   null=True, blank=True, related_name="campaigns_created")

    class Meta:
        db_table = "campaigns_campaign"
        verbose_name = _("Campaign")
        verbose_name_plural = _("Campaigns")
        ordering = ("-created",)

    def __str__(self):
        return f"{self.name} (#{self.pk})"

    @property
    def is_live(self):
        return self.status in self.LIVE_STATUSES

    @property
    def is_terminal(self):
        return self.status in self.TERMINAL_STATUSES

    @property
    def progress_pct(self):
        if not self.total_recipients:
            return 0
        completed = self.sent_count + self.failed_count
        return int(round((completed / self.total_recipients) * 100))

    @property
    def pending_count(self):
        return max(0, self.total_recipients - self.sent_count - self.failed_count)


class CampaignRecipient(models.Model):
    STATUS_PENDING = "pending"
    STATUS_SENDING = "sending"
    STATUS_SENT = "sent"
    STATUS_DELIVERED = "delivered"
    STATUS_FAILED = "failed"
    STATUS_UNDELIVERED = "undelivered"
    STATUS_SKIPPED = "skipped"

    STATUS_CHOICES = (
        (STATUS_PENDING, _("Pending")),
        (STATUS_SENDING, _("Sending")),
        (STATUS_SENT, _("Sent")),
        (STATUS_DELIVERED, _("Delivered")),
        (STATUS_FAILED, _("Failed")),
        (STATUS_UNDELIVERED, _("Undelivered")),
        (STATUS_SKIPPED, _("Skipped")),
    )

    campaign = models.ForeignKey(Campaign, on_delete=models.CASCADE, related_name="recipients")
    msisdn = models.CharField(_("Phone number"), max_length=24, db_index=True)
    variables = models.JSONField(_("Template variables"), default=dict, blank=True)

    msgid = models.CharField(_("Jasmin message ID"), max_length=64, blank=True, default="", db_index=True)
    status = models.CharField(_("Status"), max_length=12, choices=STATUS_CHOICES, default=STATUS_PENDING, db_index=True)
    error_message = models.TextField(_("Error"), blank=True, default="")

    sent_at = models.DateTimeField(_("Sent at"), null=True, blank=True)
    delivered_at = models.DateTimeField(_("Delivered at"), null=True, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "campaigns_recipient"
        verbose_name = _("Campaign recipient")
        verbose_name_plural = _("Campaign recipients")
        indexes = [
            models.Index(fields=["campaign", "status"]),
            models.Index(fields=["campaign", "msgid"]),
        ]

    def __str__(self):
        return f"{self.msisdn} ({self.status})"
