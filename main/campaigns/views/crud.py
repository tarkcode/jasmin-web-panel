"""
Campaign views: list, create (CSV/quick-list + template + encoding + scheduling),
detail, manage (start/pause/resume/cancel), recipients JSON for live polling, CSV export,
and helpers for the create form (preview, normalise, save template, list templates).
"""
import csv
import json

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.db.models import Count, Q
from django.http import JsonResponse, HttpResponse
from django.shortcuts import render, redirect, get_object_or_404
from django.urls import reverse
from django.utils import timezone
from django.utils.dateparse import parse_datetime
from django.views.decorators.http import require_http_methods, require_POST

from main.campaigns.models import Campaign, CampaignRecipient, MessageTemplate, SenderId
from main.campaigns.services import (
    CSVIngestError, parse_csv, parse_quick_list, render_template,
    extract_placeholders, normalise_to_gsm,
)
from main.campaigns.tasks import run_campaign, sync_campaign_dlrs
from main.core.utils import paginate


# ───────────────────────────────────────────────────────────────────────
# List
# ───────────────────────────────────────────────────────────────────────
@login_required
def campaign_list(request):
    qs = Campaign.objects.all().order_by("-created")

    status_filter = request.GET.get("status", "").strip()
    if status_filter:
        qs = qs.filter(status=status_filter)

    search = request.GET.get("search", "").strip()
    if search:
        qs = qs.filter(Q(name__icontains=search) | Q(sender_id__icontains=search))

    summary = Campaign.objects.aggregate(
        total=Count("id"),
        running=Count("id", filter=Q(status=Campaign.STATUS_RUNNING)),
        scheduled=Count("id", filter=Q(status=Campaign.STATUS_SCHEDULED)),
        completed=Count("id", filter=Q(status=Campaign.STATUS_COMPLETED)),
        failed=Count("id", filter=Q(status=Campaign.STATUS_FAILED)),
    )

    page = paginate(qs, per_page=20, page=request.GET.get("page"))
    return render(request, "campaigns/list.html", {
        "campaigns": page,
        "summary": summary,
        "status_filter": status_filter,
        "search": search,
    })


# ───────────────────────────────────────────────────────────────────────
# Create — extended form: SMS Type, Sender ID picker, template library,
# encoding control, audience (CSV vs quick list), validity, RTL, scheduling.
# ───────────────────────────────────────────────────────────────────────
@login_required
@require_http_methods(["GET", "POST"])
def campaign_create(request):
    from main.core.models import UsersModel
    users_for_picker = list(UsersModel.objects.values("uid", "username")[:200])
    sender_ids = list(SenderId.objects.filter(is_active=True).order_by("value"))
    templates = list(MessageTemplate.objects.filter(is_active=True).order_by("name"))

    if request.method == "GET":
        return render(request, "campaigns/new.html", {
            "users_for_picker": users_for_picker,
            "sender_ids": sender_ids,
            "templates": templates,
            "default_throttle": 10,
            "form": {},
            "audience_default": Campaign.AUDIENCE_CSV,
            "sms_type_choices": Campaign.SMS_TYPE_CHOICES,
            "encoding_choices": Campaign.ENCODING_CHOICES,
            "audience_choices": Campaign.AUDIENCE_CHOICES,
            "validity_choices": Campaign.VALIDITY_CHOICES,
        })

    name = (request.POST.get("name") or "").strip()
    description = (request.POST.get("description") or "").strip()
    template = (request.POST.get("message_template") or "").strip()
    sender_id = (request.POST.get("sender_id") or "").strip()
    send_method = (request.POST.get("send_method") or "smpp").strip()
    user_uid = (request.POST.get("user_uid") or "").strip()
    sms_type = (request.POST.get("sms_type") or "transactional").strip()
    encoding = (request.POST.get("encoding") or Campaign.ENCODING_AUTO).strip()
    is_rtl = request.POST.get("is_rtl") == "1"
    validity = (request.POST.get("message_validity") or "").strip()
    audience_source = (request.POST.get("audience_source") or Campaign.AUDIENCE_CSV).strip()
    quick_list_raw = (request.POST.get("quick_list") or "").strip()
    throttle = int(request.POST.get("throttle_mps") or 10)
    is_scheduled = request.POST.get("is_scheduled") == "yes"
    schedule_raw = (request.POST.get("scheduled_at") or "").strip() if is_scheduled else ""
    action = (request.POST.get("action") or "save").strip()  # save | start

    errors = []
    if not name:
        errors.append("Campaign name is required")
    if not template:
        errors.append("Text message is required")
    if not sender_id:
        errors.append("Sender ID is required")
    if send_method not in ("smpp", "http"):
        errors.append("Send method must be SMPP or HTTP")
    if encoding not in dict(Campaign.ENCODING_CHOICES):
        errors.append("Invalid encoding")
    if validity and validity not in dict(Campaign.VALIDITY_CHOICES):
        errors.append("Invalid message validity")
    if sms_type not in dict(Campaign.SMS_TYPE_CHOICES):
        errors.append("Invalid SMS type")
    if audience_source not in dict(Campaign.AUDIENCE_CHOICES):
        errors.append("Invalid audience source")
    if throttle < 1 or throttle > 1000:
        errors.append("Throttle must be between 1 and 1000 msgs/sec")

    scheduled_at = None
    if schedule_raw:
        scheduled_at = parse_datetime(schedule_raw)
        if scheduled_at is None:
            errors.append("Invalid scheduled time")
        elif timezone.is_naive(scheduled_at):
            scheduled_at = timezone.make_aware(scheduled_at)

    rows, csv_errors = [], []
    if audience_source == Campaign.AUDIENCE_QUICK_LIST:
        if not quick_list_raw:
            errors.append("Quick number list is required when audience is set to Quick number list")
        else:
            rows, csv_errors = parse_quick_list(quick_list_raw)
            if not rows:
                errors.append("Quick number list produced 0 valid recipients")
    else:
        file_obj = request.FILES.get("recipients_csv")
        if not file_obj:
            errors.append("Recipients CSV is required")
        else:
            try:
                phone_column_choice = (request.POST.get("phone_column") or "").strip() or None
                rows, _, csv_errors, _ = parse_csv(file_obj.read(), phone_column_choice)
                if not rows:
                    errors.append("CSV produced 0 valid recipients")
            except CSVIngestError as e:
                errors.append(str(e))

    if errors:
        for e in errors:
            messages.error(request, e)
        return render(request, "campaigns/new.html", {
            "users_for_picker": users_for_picker,
            "sender_ids": sender_ids,
            "templates": templates,
            "default_throttle": throttle,
            "form": request.POST,
            "audience_default": audience_source,
            "sms_type_choices": Campaign.SMS_TYPE_CHOICES,
            "encoding_choices": Campaign.ENCODING_CHOICES,
            "audience_choices": Campaign.AUDIENCE_CHOICES,
            "validity_choices": Campaign.VALIDITY_CHOICES,
        })

    with transaction.atomic():
        campaign = Campaign.objects.create(
            name=name,
            description=description,
            sms_type=sms_type,
            message_template=template,
            sender_id=sender_id,
            send_method=send_method,
            user_uid=user_uid,
            encoding=encoding,
            is_rtl=is_rtl,
            message_validity=validity,
            audience_source=audience_source,
            throttle_mps=throttle,
            status=Campaign.STATUS_DRAFT,
            scheduled_at=scheduled_at,
            total_recipients=len(rows),
            created_by=request.user if request.user.is_authenticated else None,
        )
        CampaignRecipient.objects.bulk_create([
            CampaignRecipient(
                campaign=campaign,
                msisdn=row["msisdn"],
                variables=row["variables"],
            )
            for row in rows
        ], batch_size=2000)

    if csv_errors:
        messages.warning(
            request,
            f"{len(rows)} recipients added; {len(csv_errors)} rows skipped (invalid phones / duplicates).",
        )
    else:
        messages.success(request, f"Campaign created with {len(rows)} recipients.")

    if action == "start":
        if scheduled_at and scheduled_at > timezone.now():
            campaign.status = Campaign.STATUS_SCHEDULED
            campaign.save(update_fields=["status"])
            messages.info(request, f"Scheduled for {scheduled_at:%Y-%m-%d %H:%M}.")
        else:
            campaign.status = Campaign.STATUS_QUEUED
            campaign.save(update_fields=["status"])
            run_campaign.delay(campaign.pk)
            messages.success(request, "Campaign queued — sending will begin shortly.")
    return redirect(reverse("campaigns:detail", args=[campaign.pk]))


# ───────────────────────────────────────────────────────────────────────
# Detail
# ───────────────────────────────────────────────────────────────────────
@login_required
def campaign_detail(request, pk):
    campaign = get_object_or_404(Campaign, pk=pk)

    if campaign.is_live and campaign.sent_count > 0:
        try:
            sync_campaign_dlrs.delay(campaign.pk)
        except Exception:
            pass

    recipient_qs = campaign.recipients.all().order_by("id")
    rstatus = request.GET.get("rstatus", "").strip()
    if rstatus:
        recipient_qs = recipient_qs.filter(status=rstatus)
    rsearch = request.GET.get("rsearch", "").strip()
    if rsearch:
        recipient_qs = recipient_qs.filter(Q(msisdn__icontains=rsearch) | Q(msgid__icontains=rsearch))
    recipients = paginate(recipient_qs, per_page=25, page=request.GET.get("page"))

    breakdown = campaign.recipients.values("status").annotate(n=Count("id"))
    by_status = {row["status"]: row["n"] for row in breakdown}

    return render(request, "campaigns/detail.html", {
        "campaign": campaign,
        "recipients": recipients,
        "rstatus": rstatus,
        "rsearch": rsearch,
        "by_status": by_status,
    })


@login_required
def campaign_recipients_json(request, pk):
    """Light JSON used by the detail page to live-update progress without full reload."""
    campaign = get_object_or_404(Campaign, pk=pk)
    breakdown = list(campaign.recipients.values("status").annotate(n=Count("id")))
    return JsonResponse({
        "status": campaign.status,
        "total": campaign.total_recipients,
        "sent": campaign.sent_count,
        "delivered": campaign.delivered_count,
        "failed": campaign.failed_count,
        "pending": campaign.pending_count,
        "progress": campaign.progress_pct,
        "started_at": campaign.started_at.isoformat() if campaign.started_at else None,
        "finished_at": campaign.finished_at.isoformat() if campaign.finished_at else None,
        "breakdown": {row["status"]: row["n"] for row in breakdown},
    })


# ───────────────────────────────────────────────────────────────────────
# Lifecycle: start / pause / resume / cancel
# ───────────────────────────────────────────────────────────────────────
@login_required
@require_POST
def campaign_manage(request, pk):
    campaign = get_object_or_404(Campaign, pk=pk)
    action = (request.POST.get("action") or "").strip()

    out = {"status": "ok", "action": action, "new_status": campaign.status}

    if action == "start":
        if campaign.status not in (Campaign.STATUS_DRAFT, Campaign.STATUS_SCHEDULED, Campaign.STATUS_PAUSED):
            return JsonResponse({"status": "error", "message": f"Cannot start from {campaign.status}"}, status=400)
        Campaign.objects.filter(pk=pk).update(status=Campaign.STATUS_QUEUED)
        run_campaign.delay(pk)
        out["new_status"] = Campaign.STATUS_QUEUED

    elif action == "pause":
        if campaign.status != Campaign.STATUS_RUNNING:
            return JsonResponse({"status": "error", "message": f"Cannot pause from {campaign.status}"}, status=400)
        Campaign.objects.filter(pk=pk).update(status=Campaign.STATUS_PAUSED)
        out["new_status"] = Campaign.STATUS_PAUSED

    elif action == "resume":
        if campaign.status != Campaign.STATUS_PAUSED:
            return JsonResponse({"status": "error", "message": f"Cannot resume from {campaign.status}"}, status=400)
        Campaign.objects.filter(pk=pk).update(status=Campaign.STATUS_QUEUED)
        run_campaign.delay(pk)
        out["new_status"] = Campaign.STATUS_QUEUED

    elif action == "cancel":
        if campaign.is_terminal:
            return JsonResponse({"status": "error", "message": f"Cannot cancel from {campaign.status}"}, status=400)
        Campaign.objects.filter(pk=pk).update(status=Campaign.STATUS_CANCELLED, finished_at=timezone.now())
        out["new_status"] = Campaign.STATUS_CANCELLED

    elif action == "sync_dlr":
        sync_campaign_dlrs.delay(pk)
        out["queued"] = True

    else:
        return JsonResponse({"status": "error", "message": f"Unknown action: {action}"}, status=400)

    return JsonResponse(out)


@login_required
@require_POST
def campaign_delete(request, pk):
    campaign = get_object_or_404(Campaign, pk=pk)
    if campaign.is_live:
        return JsonResponse({"status": "error", "message": "Cancel the campaign before deleting it."}, status=400)
    campaign.delete()
    return JsonResponse({"status": "ok"})


# ───────────────────────────────────────────────────────────────────────
# Export recipients as CSV
# ───────────────────────────────────────────────────────────────────────
@login_required
def campaign_recipients_export(request, pk):
    campaign = get_object_or_404(Campaign, pk=pk)
    response = HttpResponse(content_type="text/csv")
    response["Content-Disposition"] = (
        f'attachment; filename="campaign-{campaign.pk}-recipients.csv"'
    )
    writer = csv.writer(response)
    writer.writerow(["id", "msisdn", "status", "msgid", "sent_at", "delivered_at", "error_message", "variables"])
    for r in campaign.recipients.all().iterator(chunk_size=2000):
        writer.writerow([
            r.pk,
            r.msisdn,
            r.status,
            r.msgid,
            r.sent_at.isoformat() if r.sent_at else "",
            r.delivered_at.isoformat() if r.delivered_at else "",
            r.error_message,
            json.dumps(r.variables) if r.variables else "",
        ])
    return response


# ───────────────────────────────────────────────────────────────────────
# AJAX helpers used by the create form: preview, normalise, save/use template
# ───────────────────────────────────────────────────────────────────────
@login_required
@require_POST
def template_preview(request):
    body = (request.POST.get("body") or "").strip()
    sample_phone = (request.POST.get("sample_phone") or "+91XXXXXXXXXX").strip()
    sample_vars_raw = (request.POST.get("sample_vars") or "{}").strip()
    try:
        sample_vars = json.loads(sample_vars_raw) if sample_vars_raw else {}
        if not isinstance(sample_vars, dict):
            sample_vars = {}
    except json.JSONDecodeError:
        sample_vars = {}

    rendered = render_template(body, sample_vars, msisdn=sample_phone)
    return JsonResponse({
        "status": "ok",
        "preview": rendered,
        "placeholders": extract_placeholders(body),
    })


@login_required
@require_POST
def template_normalise(request):
    body = request.POST.get("body") or ""
    return JsonResponse({"status": "ok", "normalised": normalise_to_gsm(body)})


@login_required
@require_POST
def template_save(request):
    name = (request.POST.get("name") or "").strip()
    body = (request.POST.get("body") or "").strip()
    sms_type = (request.POST.get("sms_type") or "transactional").strip()
    if not name:
        return JsonResponse({"status": "error", "message": "Template name is required"}, status=400)
    if not body:
        return JsonResponse({"status": "error", "message": "Template body is required"}, status=400)

    tpl, created = MessageTemplate.objects.update_or_create(
        name=name,
        defaults={"body": body, "sms_type": sms_type, "is_active": True,
                  "created_by": request.user if request.user.is_authenticated else None},
    )
    return JsonResponse({"status": "ok", "id": tpl.id, "name": tpl.name, "created": created})


@login_required
def template_get(request, pk):
    tpl = get_object_or_404(MessageTemplate, pk=pk, is_active=True)
    return JsonResponse({"status": "ok", "id": tpl.id, "name": tpl.name,
                         "body": tpl.body, "sms_type": tpl.sms_type})
