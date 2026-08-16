from decimal import Decimal, InvalidOperation

from django.utils.translation import gettext as _
from django.shortcuts import render
from django.http import JsonResponse
from django.contrib.auth.decorators import login_required

from main.core.tools import require_post_ajax
from main.core.models import RouteDetail

VALID_TYPES = {"transactional", "promotional", "otp", "other"}
VALID_STATUS = {"active", "inactive", "testing"}


def _to_decimal(v):
    try:
        return Decimal(str(v if v not in (None, "") else "0"))
    except (InvalidOperation, ValueError, TypeError):
        return None


def _to_int(v, default=0):
    try:
        return int(v)
    except (ValueError, TypeError):
        return default


@login_required
def route_details_view(request):
    return render(request, "web/content/route_details.html")


def _apply_fields(route, request):
    """Read + validate the shared form fields onto a RouteDetail instance.
    Returns an error JsonResponse on invalid input, else None."""
    name = (request.POST.get("name") or "").strip()
    connector = (request.POST.get("smpp_connector") or "").strip()
    if not name:
        return JsonResponse({"message": str(_("Route name is required.")), "status": 400}, status=400)
    if not connector:
        return JsonResponse({"message": str(_("An SMPP connector / provider is required.")), "status": 400}, status=400)
    buy_price = _to_decimal(request.POST.get("buy_price"))
    if buy_price is None:
        return JsonResponse({"message": str(_("Buy price must be a number.")), "status": 400}, status=400)
    route_type = request.POST.get("route_type") or "transactional"
    status = request.POST.get("status") or "active"
    route.name = name
    route.country = (request.POST.get("country") or "").strip()
    route.route_type = route_type if route_type in VALID_TYPES else "transactional"
    route.smpp_connector = connector
    route.buy_price = buy_price
    route.currency = (request.POST.get("currency") or "USD").strip() or "USD"
    route.tps = _to_int(request.POST.get("tps"), 0)
    route.status = status if status in VALID_STATUS else "active"
    return None


@require_post_ajax
def route_details_view_manage(request):
    s = request.POST.get("s")
    response = {}
    if s == "list":
        response["routes"] = [r.get_dict() for r in RouteDetail.objects.all()]
    elif s == "add":
        route = RouteDetail()
        err = _apply_fields(route, request)
        if err:
            return err
        route.save()
        response["message"] = str(_("Route added successfully!"))
    elif s == "edit":
        try:
            route = RouteDetail.objects.get(id=request.POST.get("id"))
        except (RouteDetail.DoesNotExist, ValueError):
            return JsonResponse({"message": str(_("Route not found.")), "status": 404}, status=404)
        err = _apply_fields(route, request)
        if err:
            return err
        route.save()
        response["message"] = str(_("Route updated successfully!"))
    elif s == "toggle":
        try:
            route = RouteDetail.objects.get(id=request.POST.get("id"))
        except (RouteDetail.DoesNotExist, ValueError):
            return JsonResponse({"message": str(_("Route not found.")), "status": 404}, status=404)
        route.status = "inactive" if route.status == "active" else "active"
        route.save(update_fields=["status", "modified"])
        response["message"] = str(_("Status changed to %(s)s.")) % {"s": route.get_status_display()}
    elif s == "delete":
        try:
            route = RouteDetail.objects.get(id=request.POST.get("id"))
        except (RouteDetail.DoesNotExist, ValueError):
            return JsonResponse({"message": str(_("Route not found.")), "status": 404}, status=404)
        route.delete()
        response["message"] = str(_("Route deleted successfully!"))
    else:
        return JsonResponse({"message": str(_("Sorry, Command does not matched.")), "status": 400}, status=400)
    response["status"] = 200
    return JsonResponse(response, status=200)
