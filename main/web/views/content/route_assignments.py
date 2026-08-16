from decimal import Decimal, InvalidOperation

from django.utils.translation import gettext as _
from django.shortcuts import render
from django.http import JsonResponse
from django.contrib.auth.decorators import login_required

from main.core.tools import require_post_ajax
from main.core.models import RouteDetail, RouteAssignment
from main.core.smpp import Users

VALID_STATUS = {"active", "inactive"}


def _to_decimal(v):
    try:
        return Decimal(str(v if v not in (None, "") else "0"))
    except (InvalidOperation, ValueError, TypeError):
        return None


@login_required
def route_assignments_view(request):
    return render(request, "web/content/route_assignments.html")


def _meta():
    """Buy-routes (with price/currency for live margin) + Jasmin users for the pickers."""
    routes = [{
        "id": r.id, "name": r.name, "connector": r.smpp_connector, "country": r.country,
        "buy_price": str(r.buy_price), "currency": r.currency, "status": r.status,
    } for r in RouteDetail.objects.all()]
    try:
        users = [u.get("uid") for u in Users().list().get("users", []) if u.get("uid")]
    except Exception:
        users = []
    return JsonResponse({"routes": routes, "users": users, "status": 200})


@require_post_ajax
def route_assignments_view_manage(request):
    s = request.POST.get("s")
    response = {}
    if s == "meta":
        return _meta()
    if s == "list":
        response["assignments"] = [a.get_dict() for a in
                                   RouteAssignment.objects.select_related("route").all()]
    elif s in ("add", "edit"):
        if s == "add":
            assignment = RouteAssignment()
        else:
            try:
                assignment = RouteAssignment.objects.get(id=request.POST.get("id"))
            except (RouteAssignment.DoesNotExist, ValueError):
                return JsonResponse({"message": str(_("Assignment not found.")), "status": 404}, status=404)
        try:
            route = RouteDetail.objects.get(id=request.POST.get("route_id"))
        except (RouteDetail.DoesNotExist, ValueError):
            return JsonResponse({"message": str(_("Select a valid route.")), "status": 400}, status=400)
        uid = (request.POST.get("uid") or "").strip()
        if not uid:
            return JsonResponse({"message": str(_("Select a customer (user).")), "status": 400}, status=400)
        sell_price = _to_decimal(request.POST.get("sell_price"))
        if sell_price is None:
            return JsonResponse({"message": str(_("Sell price must be a number.")), "status": 400}, status=400)
        # one assignment per (route, user)
        dupe = RouteAssignment.objects.filter(route=route, uid=uid)
        if s == "edit":
            dupe = dupe.exclude(id=assignment.id)
        if dupe.exists():
            return JsonResponse({
                "message": str(_("This route is already assigned to '%(u)s'. Edit that assignment instead.")) % {"u": uid},
                "status": 400}, status=400)
        status = request.POST.get("status") or "active"
        assignment.route = route
        assignment.uid = uid
        assignment.sell_price = sell_price
        assignment.status = status if status in VALID_STATUS else "active"
        assignment.notes = (request.POST.get("notes") or "").strip()
        assignment.save()
        response["message"] = str(_("Assignment saved successfully!"))
    elif s == "toggle":
        try:
            assignment = RouteAssignment.objects.get(id=request.POST.get("id"))
        except (RouteAssignment.DoesNotExist, ValueError):
            return JsonResponse({"message": str(_("Assignment not found.")), "status": 404}, status=404)
        assignment.status = "inactive" if assignment.status == "active" else "active"
        assignment.save(update_fields=["status", "modified"])
        response["message"] = str(_("Status changed to %(s)s.")) % {"s": assignment.get_status_display()}
    elif s == "delete":
        try:
            assignment = RouteAssignment.objects.get(id=request.POST.get("id"))
        except (RouteAssignment.DoesNotExist, ValueError):
            return JsonResponse({"message": str(_("Assignment not found.")), "status": 404}, status=404)
        assignment.delete()
        response["message"] = str(_("Assignment deleted successfully!"))
    else:
        return JsonResponse({"message": str(_("Sorry, Command does not matched.")), "status": 400}, status=400)
    response["status"] = 200
    return JsonResponse(response, status=200)
