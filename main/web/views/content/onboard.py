from django.utils.translation import gettext as _
from django.shortcuts import render
from django.http import JsonResponse
from django.contrib.auth.decorators import login_required

from main.core.smpp import Groups, Users, Filters, MTRouter, SMPPCCM
from main.core.models import UsersModel, GroupsModel
from main.core.tools import require_post_ajax


@login_required
def onboard_view(request):
    """Connector-centric setup: always create a new SMPP connector, plus a user
    (new or existing) and group (new or existing), keeping the connector and user
    credentials in sync. Optionally wires a UserFilter + MT Route so the user can
    send through the connector immediately."""
    return render(request, "web/content/onboard.html")


def _onboard_meta():
    """Existing groups + users (with stored credentials) for the pickers.

    User passwords are only known for users created through the panel (mirrored
    into UsersModel); for others the password comes back empty and the operator
    must type it so the connector matches."""
    try:
        groups = [g["name"] for g in Groups().list().get("groups", [])]
    except Exception:
        groups = []
    creds_by_uid = {u.uid: (u.username, u.password) for u in UsersModel.objects.all()}
    users = []
    try:
        for u in Users().list().get("users", []):
            uid = u.get("uid")
            if not uid:
                continue
            uname, pw = creds_by_uid.get(uid, ("", ""))
            users.append({"uid": uid, "username": u.get("username", "") or uname, "password": pw})
    except Exception:
        pass
    return JsonResponse({"groups": groups, "users": users, "status": 200})


def _onboard_create(request):
    steps = []

    def ok(step, detail=""):
        steps.append({"step": step, "ok": True, "detail": detail})

    def fail(step, msg):
        msg = str(msg)
        steps.append({"step": step, "ok": False, "detail": msg})
        return JsonResponse({"steps": steps, "message": msg, "status": 400}, status=400)

    P = request.POST.get
    cid = (P("cid") or "").strip()
    host = (P("host") or "").strip()
    port = (P("port") or "").strip()
    username = (P("username") or "").strip()
    password = P("password") or ""
    user_mode = P("user_mode") or "new"
    uid_new = (P("uid") or "").strip()
    existing_uid = (P("existing_uid") or "").strip()
    group_mode = P("group_mode") or "existing"
    gid = (P("gid") or "").strip()
    make_route = (P("make_route") == "true")
    rate = (P("rate") or "0").strip()

    # ---- validate connector ----
    if not cid or " " in cid:
        return fail("Connector", _("Connector CID is required and cannot contain spaces."))
    if not host:
        return fail("Connector", _("Host is required."))
    if not port:
        return fail("Connector", _("Port is required."))
    if not username:
        return fail("Connector", _("Username is required."))
    if len(username) > 15:
        return fail("Connector", _("Username is too long (max 15 characters)."))
    if not password:
        return fail("Connector", _("Password is required."))
    if len(password) > 8:
        return fail("Connector", _("Password is too long. SMPP passwords are limited to 8 characters."))
    try:
        rate_val = float(rate or "0")
    except ValueError:
        return fail("Route", _("Rate must be a number."))

    target_uid = existing_uid if user_mode == "existing" else uid_new
    if user_mode == "existing" and not target_uid:
        return fail("User", _("Select an existing user."))
    if user_mode != "existing" and (not target_uid or " " in target_uid):
        return fail("User", _("User ID is required and cannot contain spaces."))

    # ---- 1. SMPP connector (always new) ----
    smpp = SMPPCCM()
    existing_conn = smpp.get_smppccm(cid, silent=True)
    if existing_conn and existing_conn.get("cid"):
        return fail("Connector", _("A connector with CID '%(c)s' already exists.") % {"c": cid})
    try:
        smpp.create(data=dict(cid=cid, host=host, port=port, username=username, password=password))
    except Exception as e:
        return fail("Connector", _("Failed to create connector: ") + str(e))
    ok("Connector", _("Created SMPP connector %(c)s") % {"c": cid})

    # ---- 2. User (existing or new) ----
    if user_mode == "existing":
        if not Users().get_user(target_uid, silent=True):
            return fail("User", _("Selected user '%(u)s' no longer exists.") % {"u": target_uid})
        ok("User", _("Linked existing user %(u)s") % {"u": target_uid})
    else:
        # resolve the group first
        try:
            existing_groups = [g["name"] for g in Groups().list().get("groups", [])]
        except Exception as e:
            return fail("Group", _("Could not read groups: ") + str(e))
        if group_mode == "new":
            if not gid or " " in gid:
                return fail("Group", _("New group id is required and cannot contain spaces."))
            if gid in existing_groups:
                ok("Group", _("Using existing group %(g)s") % {"g": gid})
            else:
                Groups().create(data=dict(gid=gid))
                # Groups.create()'s return is unreliable; confirm by re-listing.
                if gid not in [g["name"] for g in Groups().list().get("groups", [])]:
                    return fail("Group", _("Failed to create group '%(g)s'.") % {"g": gid})
                ok("Group", _("Created group %(g)s") % {"g": gid})
        else:
            if not gid:
                return fail("Group", _("Select a group for the new user."))
            if gid not in existing_groups:
                return fail("Group", _("Selected group '%(g)s' does not exist.") % {"g": gid})
            ok("Group", _("Using existing group %(g)s") % {"g": gid})

        if Users().get_user(target_uid, silent=True):
            return fail("User", _("A user with ID '%(u)s' already exists.") % {"u": target_uid})
        try:
            Users().create(data=dict(uid=target_uid, gid=gid, username=username, password=password))
        except Exception as e:
            return fail("User", _("Failed to create user: ") + str(e))
        try:
            group_model, _created = GroupsModel.objects.get_or_create(gid=gid)
            UsersModel.objects.update_or_create(
                uid=target_uid,
                defaults={"gid": group_model, "username": username, "password": password,
                          "parameters": "", "user": request.user},
            )
        except Exception:
            pass
        ok("User", _("Created user %(u)s with the same username/password as the connector") % {"u": target_uid})

    # ---- 3. Routing (optional) ----
    if make_route:
        fid = "uf_" + target_uid
        try:
            existing_filters = [f["fid"] for f in Filters().list().get("filters", [])]
        except Exception as e:
            return fail("Filter", _("Could not read filters: ") + str(e))
        if fid in existing_filters:
            ok("Filter", _("Using existing filter %(f)s") % {"f": fid})
        else:
            try:
                Filters().create(data=dict(type="userfilter", fid=fid, parameter=target_uid))
            except Exception as e:
                return fail("Filter", _("Failed to create filter: ") + str(e))
            if fid not in [f["fid"] for f in Filters().list().get("filters", [])]:
                return fail("Filter", _("Failed to create filter %(f)s.") % {"f": fid})
            ok("Filter", _("Created filter %(f)s") % {"f": fid})
        try:
            orders = [int(r["order"]) for r in MTRouter()._list() if str(r["order"]).isdigit()]
            next_order = (max(orders) + 1) if orders else 1
            MTRouter().create(data=dict(type="StaticMTRoute", order=str(next_order),
                                        rate=str(rate_val), smppconnectors=cid, filters=fid))
            ok("Route", _("Created MT route #%(o)s → %(c)s @ %(r)s") % {"o": next_order, "c": cid, "r": rate_val})
        except Exception as e:
            return fail("Route", _("Connector and user were created, but the MT route failed: ") + str(e))

    return JsonResponse({"steps": steps, "message": str(_("Done — connector and user are set up!")), "status": 200})


@require_post_ajax
def onboard_view_manage(request):
    s = request.POST.get("s")
    if s == "meta":
        return _onboard_meta()
    if s == "create":
        return _onboard_create(request)
    return JsonResponse({"message": str(_("Sorry, Command does not matched.")), "status": 400}, status=400)
