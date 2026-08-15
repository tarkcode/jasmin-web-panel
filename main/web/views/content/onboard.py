from django.utils.translation import gettext as _
from django.shortcuts import render
from django.http import JsonResponse
from django.contrib.auth.decorators import login_required

from main.core.smpp import Groups, Users, Filters, MTRouter
from main.core.models import UsersModel, GroupsModel
from main.core.tools import require_post_ajax


@login_required
def onboard_view(request):
    """Guided 'onboard a customer' wizard.

    Creates, in one flow, everything a customer needs to start sending:
    Group -> User -> UserFilter -> MT Route (to a chosen SMPP connector, with a
    rate). Pure template render; the work happens in onboard_view_manage."""
    return render(request, "web/content/onboard.html")


def _onboard_create(request):
    """Orchestrate Group -> User -> Filter -> MT Route, reporting each step.

    No auto-rollback: if a later step fails we return the steps completed so far
    plus the error, so the operator can see exactly where it stopped."""
    steps = []

    def ok(step, detail=""):
        steps.append({"step": step, "ok": True, "detail": detail})

    def fail(step, msg):
        msg = str(msg)
        steps.append({"step": step, "ok": False, "detail": msg})
        return JsonResponse({"steps": steps, "message": msg, "status": 400}, status=400)

    group_mode = request.POST.get("group_mode", "existing")
    gid = (request.POST.get("gid") or "").strip()
    uid = (request.POST.get("uid") or "").strip()
    username = (request.POST.get("username") or "").strip()
    password = request.POST.get("password") or ""
    connector = (request.POST.get("connector") or "").strip()
    rate = (request.POST.get("rate") or "0").strip()
    balance = (request.POST.get("balance") or "").strip()
    smpps_tp = (request.POST.get("smpps_throughput") or "").strip()
    http_tp = (request.POST.get("http_throughput") or "").strip()

    # ---- validation ----
    if not gid:
        return fail("Group", _("Group is required."))
    if not uid or " " in uid:
        return fail("User", _("User ID is required and cannot contain spaces."))
    if not username:
        return fail("User", _("Username is required."))
    if len(username) > 15:
        return fail("User", _("Username is too long (max 15 characters)."))
    if not password:
        return fail("User", _("Password is required."))
    if len(password) > 8:
        return fail("User", _("Password is too long. SMPP passwords are limited to 8 characters."))
    if " " in gid:
        return fail("Group", _("Group id cannot contain spaces."))
    if not connector:
        return fail("Route", _("An SMPP connector is required."))
    try:
        rate_val = float(rate or "0")
    except ValueError:
        return fail("Route", _("Rate must be a number."))

    # ---- 1. Group ----
    try:
        existing_groups = [g["name"] for g in Groups().list().get("groups", [])]
    except Exception as e:
        return fail("Group", _("Could not read groups: ") + str(e))
    if group_mode == "new":
        if gid in existing_groups:
            return fail("Group", _("Group '%(g)s' already exists — choose it from existing groups instead.") % {"g": gid})
        Groups().create(data=dict(gid=gid))
        # Groups.create()'s return is unreliable (regex-parsed); the group is
        # actually created either way, so confirm success by re-listing.
        if gid not in [g["name"] for g in Groups().list().get("groups", [])]:
            return fail("Group", _("Failed to create group '%(g)s'.") % {"g": gid})
        ok("Group", _("Created group %(g)s") % {"g": gid})
    else:
        if gid not in existing_groups:
            return fail("Group", _("Selected group '%(g)s' does not exist.") % {"g": gid})
        ok("Group", _("Using existing group %(g)s") % {"g": gid})

    # ---- 2. User ----
    if Users().get_user(uid, silent=True):
        return fail("User", _("A user with ID '%(u)s' already exists.") % {"u": uid})
    try:
        Users().create(data=dict(uid=uid, gid=gid, username=username, password=password))
    except Exception as e:
        return fail("User", _("Failed to create user: ") + str(e))
    # Mirror credentials into the Django models (used by the Send SMS feature).
    try:
        group_model, _created = GroupsModel.objects.get_or_create(gid=gid)
        UsersModel.objects.update_or_create(
            uid=uid,
            defaults={"gid": group_model, "username": username, "password": password,
                      "parameters": "", "user": request.user},
        )
    except Exception:
        pass
    ok("User", _("Created user %(u)s") % {"u": uid})

    # ---- optional balance / throughput ----
    updates = []
    if balance:
        updates.append(["mt_messaging_cred", "quota", "balance", balance])
    if smpps_tp:
        updates.append(["mt_messaging_cred", "quota", "smpps_throughput", smpps_tp])
    if http_tp:
        updates.append(["mt_messaging_cred", "quota", "http_throughput", http_tp])
    if updates:
        try:
            Users().partial_update(data=updates, uid=uid)
            ok("Quota", _("Applied balance / throughput"))
        except Exception as e:
            steps.append({"step": "Quota", "ok": False,
                          "detail": str(_("User created, but balance/throughput could not be applied: ")) + str(e)})

    # ---- 3. Filter (UserFilter) ----
    fid = "uf_" + uid
    try:
        existing_filters = [f["fid"] for f in Filters().list().get("filters", [])]
    except Exception as e:
        return fail("Filter", _("Could not read filters: ") + str(e))
    if fid in existing_filters:
        ok("Filter", _("Using existing filter %(f)s") % {"f": fid})
    else:
        try:
            Filters().create(data=dict(type="userfilter", fid=fid, parameter=uid))
        except Exception as e:
            return fail("Filter", _("Failed to create filter: ") + str(e))
        # Filters.create() returns {'filter': None} on failure without raising; verify.
        if fid not in [f["fid"] for f in Filters().list().get("filters", [])]:
            return fail("Filter", _("Failed to create filter %(f)s.") % {"f": fid})
        ok("Filter", _("Created filter %(f)s") % {"f": fid})

    # ---- 4. MT Route ----
    try:
        orders = [int(r["order"]) for r in MTRouter()._list() if str(r["order"]).isdigit()]
        next_order = (max(orders) + 1) if orders else 1
        MTRouter().create(data=dict(
            type="StaticMTRoute", order=str(next_order), rate=str(rate_val),
            smppconnectors=connector, filters=fid,
        ))
        ok("Route", _("Created MT route #%(o)s → %(c)s @ %(r)s") % {"o": next_order, "c": connector, "r": rate_val})
    except Exception as e:
        return fail("Route", _("Group, user and filter were created, but the MT route failed: ") + str(e))

    return JsonResponse({"steps": steps, "message": str(_("Customer onboarded successfully!")), "status": 200})


@require_post_ajax
def onboard_view_manage(request):
    if request.POST.get("s") == "create":
        return _onboard_create(request)
    return JsonResponse({"message": str(_("Sorry, Command does not matched.")), "status": 400}, status=400)
