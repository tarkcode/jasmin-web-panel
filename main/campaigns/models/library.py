"""Reusable assets used by campaigns: message templates and sender IDs."""
from django.conf import settings
from django.db import models
from django.utils.translation import gettext_lazy as _

from main.core.models.timestamped import TimeStampedModel


class MessageTemplate(TimeStampedModel):
    SMS_TYPE_CHOICES = (
        ("transactional", _("Transactional")),
        ("promotional", _("Promotional")),
        ("otp", _("OTP")),
        ("marketing", _("Marketing")),
    )

    name = models.CharField(_("Name"), max_length=120, unique=True)
    body = models.TextField(_("Message body"))
    sms_type = models.CharField(_("SMS type"), max_length=16, choices=SMS_TYPE_CHOICES, default="transactional")
    is_active = models.BooleanField(_("Active"), default=True)
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL,
                                   null=True, blank=True, related_name="campaign_templates")

    class Meta:
        db_table = "campaigns_messagetemplate"
        verbose_name = _("Message template")
        verbose_name_plural = _("Message templates")
        ordering = ("name",)

    def __str__(self):
        return self.name


class SenderId(TimeStampedModel):
    """Pre-approved sender IDs the operator can pick from when creating a campaign."""
    value = models.CharField(_("Value"), max_length=24, unique=True,
                             help_text=_("The sender ID as it appears on the handset, e.g. JASMIN, ACME-TX."))
    label = models.CharField(_("Label"), max_length=120, blank=True, default="",
                             help_text=_("Friendly description shown in the picker."))
    sms_type = models.CharField(_("Allowed SMS type"), max_length=16, blank=True, default="",
                                help_text=_("Restrict to a specific SMS type, or leave blank for any."))
    is_active = models.BooleanField(_("Active"), default=True)

    class Meta:
        db_table = "campaigns_senderid"
        verbose_name = _("Sender ID")
        verbose_name_plural = _("Sender IDs")
        ordering = ("value",)

    def __str__(self):
        return self.value
