from django.utils.translation import gettext as _
from django.shortcuts import render
from django.http import JsonResponse
from django.contrib.auth.decorators import login_required

from main.core.tools import require_post_ajax
from main.core.models import FakeDLRConnectorModel


@login_required
def fake_dlr_view(request):
    return render(request, "web/content/fake_dlr.html")


@require_post_ajax
def fake_dlr_view_manage(request):
    s = request.POST.get("s")
    response = {}

    if s == "list":
        configs = FakeDLRConnectorModel.objects.all().order_by('cid')
        response["configs"] = [{
            "id": c.id,
            "cid": c.cid,
            "name": c.name,
            "enabled": c.enabled,
            "success_rate": c.success_rate,
            "min_delay": c.min_delay,
            "max_delay": c.max_delay,
            "instant_response": c.instant_response,
            "total_messages": c.total_messages,
            "delivered_count": c.delivered_count,
            "failed_count": c.failed_count,
            "delivery_rate": round(c.delivery_rate, 1),
        } for c in configs]
    elif s == "add":
        cid = request.POST.get("cid", "").strip()
        name = request.POST.get("name", "").strip() or cid
        if not cid:
            return JsonResponse({"message": str(_("Connector ID is required.")), "status": 400}, status=400)
        if FakeDLRConnectorModel.objects.filter(cid=cid).exists():
            return JsonResponse({"message": str(_("Config for this connector already exists.")), "status": 400}, status=400)
        FakeDLRConnectorModel.objects.create(
            cid=cid,
            name=name,
            enabled=request.POST.get("enabled") == "true",
            success_rate=int(request.POST.get("success_rate", 100)),
            min_delay=int(request.POST.get("min_delay", 3)),
            max_delay=int(request.POST.get("max_delay", 10)),
            instant_response=request.POST.get("instant_response") == "true",
        )
        response["message"] = str(_("Fake DLR config created successfully!"))
    elif s == "edit":
        config_id = request.POST.get("id")
        try:
            config = FakeDLRConnectorModel.objects.get(id=config_id)
        except FakeDLRConnectorModel.DoesNotExist:
            return JsonResponse({"message": str(_("Config not found.")), "status": 404}, status=404)
        config.name = request.POST.get("name", config.name)
        config.enabled = request.POST.get("enabled") == "true"
        config.success_rate = int(request.POST.get("success_rate", config.success_rate))
        config.min_delay = int(request.POST.get("min_delay", config.min_delay))
        config.max_delay = int(request.POST.get("max_delay", config.max_delay))
        config.instant_response = request.POST.get("instant_response") == "true"
        config.save()
        response["message"] = str(_("Fake DLR config updated successfully!"))
    elif s == "toggle":
        config_id = request.POST.get("id")
        try:
            config = FakeDLRConnectorModel.objects.get(id=config_id)
        except FakeDLRConnectorModel.DoesNotExist:
            return JsonResponse({"message": str(_("Config not found.")), "status": 404}, status=404)
        config.enabled = not config.enabled
        config.save(update_fields=["enabled"])
        response["message"] = str(_("Toggled successfully!"))
    elif s == "delete":
        config_id = request.POST.get("id")
        try:
            config = FakeDLRConnectorModel.objects.get(id=config_id)
        except FakeDLRConnectorModel.DoesNotExist:
            return JsonResponse({"message": str(_("Config not found.")), "status": 404}, status=404)
        config.delete()
        response["message"] = str(_("Fake DLR config deleted successfully!"))
    elif s == "reset_stats":
        config_id = request.POST.get("id")
        try:
            config = FakeDLRConnectorModel.objects.get(id=config_id)
        except FakeDLRConnectorModel.DoesNotExist:
            return JsonResponse({"message": str(_("Config not found.")), "status": 404}, status=404)
        config.total_messages = 0
        config.delivered_count = 0
        config.failed_count = 0
        config.save(update_fields=["total_messages", "delivered_count", "failed_count"])
        response["message"] = str(_("Stats reset successfully!"))
    else:
        return JsonResponse({"message": str(_("Unknown command.")), "status": 400}, status=400)

    response["status"] = 200
    return JsonResponse(response, status=200)
