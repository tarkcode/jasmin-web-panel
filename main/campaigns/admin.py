from django.contrib import admin

from .models import Campaign, CampaignRecipient, MessageTemplate, SenderId


@admin.register(Campaign)
class CampaignAdmin(admin.ModelAdmin):
    list_display = ("id", "name", "sms_type", "status", "send_method", "throttle_mps",
                    "total_recipients", "sent_count", "delivered_count", "failed_count",
                    "scheduled_at", "started_at", "finished_at")
    list_filter = ("status", "send_method", "sms_type", "encoding")
    search_fields = ("name", "sender_id", "user_uid")
    readonly_fields = ("started_at", "finished_at", "total_recipients",
                       "sent_count", "delivered_count", "failed_count")


@admin.register(CampaignRecipient)
class CampaignRecipientAdmin(admin.ModelAdmin):
    list_display = ("id", "campaign", "msisdn", "status", "msgid", "sent_at", "delivered_at")
    list_filter = ("status", "campaign")
    search_fields = ("msisdn", "msgid")


@admin.register(MessageTemplate)
class MessageTemplateAdmin(admin.ModelAdmin):
    list_display = ("name", "sms_type", "is_active", "modified")
    list_filter = ("sms_type", "is_active")
    search_fields = ("name", "body")


@admin.register(SenderId)
class SenderIdAdmin(admin.ModelAdmin):
    list_display = ("value", "label", "sms_type", "is_active", "modified")
    list_filter = ("sms_type", "is_active")
    search_fields = ("value", "label")
