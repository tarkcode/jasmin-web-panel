"""Clients area.

A *client* is a customer who binds INTO our SMPP server (port 2775) to SEND SMS.
In Jasmin that means: a User (login) + a Group, their source IP whitelisted, and
an MT route sending their traffic OUT through a provider connector (e.g. AETELCO).
This is the opposite of a provider (an outbound smppccm connector we dial).

This page creates and lists clients end-to-end so the two roles never get mixed
up again — it never creates an smppccm connector.
"""
import re

from django.conf import settings
from django.db import connection
from django.utils.translation import gettext as _
from django.shortcuts import render
from django.http import JsonResponse
from django.contrib.auth.decorators import login_required

from main.core.smpp import Groups, Users, Filters, MTRouter, SMPPCCM
from main.core.models import UsersModel, GroupsModel
from main.core.tools import require_post_ajax
from main.web.views.content.smpp_access import _read_ips, _write_ips, _valid_ip

OUR_SMPP_HOST = getattr(settings, "PANEL_SMPP_PUBLIC_HOST", "161.97.156.97")
OUR_SMPP_PORT = str(getattr(settings, "PANEL_SMPP_PUBLIC_PORT", "2775"))

_UID_RE = re.compile(r"uid=([^)\s>]+)")
_CID_RE = re.compile(r"smppc\(([^)]+)\)")


def _nested(u, *keys):
    cur = u
    for k in keys:
        if not isinstance(cur, dict):
            return ""
        cur = cur.get(k)
        if cur is None:
            return ""
    return cur


def _route_map():
    """uid -> {connector, rate, order} from static MT routes; plus the default connector."""
    out, default_conn = {}, None
    try:
        routes = MTRouter()._list()
    except Exception:
        routes = []
    for r in routes:
        cid = None
        for c in (r.get("connectors") or []):
            m = _CID_RE.search(c or "")
            if m:
                cid = m.group(1)
                break
        if r.get("type") == "DefaultRoute":
            default_conn = cid
            continue
        for f in (r.get("filters") or []):
            m = _UID_RE.search(f or "")
            if m:
                out[m.group(1)] = {"connector": cid, "rate": (r.get("rate") or "0").strip(), "order": r.get("order")}
    return out, default_conn


def _traffic_today():
    counts = {}
    try:
        with connection.cursor() as cur:
            cur.execute("SELECT uid, count(*) FROM submit_log WHERE created_at::date = CURRENT_DATE GROUP BY uid")
            for uid, n in cur.fetchall():
                counts[uid] = n
    except Exception:
        pass
    return counts


def _clients_list():
    rmap, default_conn = _route_map()
    ip_by_label = {}
    for row in _read_ips():
        ip_by_label.setdefault((row.get("label") or "").strip(), []).append(row["ip"])
    creds = {u.uid: (u.username, u.password) for u in UsersModel.objects.all()}
    traffic = _traffic_today()
    try:
        users = Users().list().get("users", [])
    except Exception:
        users = []
    clients = []
    for u in users:
        uid = u.get("uid")
        if not uid:
            continue
        uname, pw = creds.get(uid, (u.get("username", ""), ""))
        route = rmap.get(uid)
        clients.append({
            "uid": uid,
            "gid": u.get("gid", ""),
            "username": u.get("username", "") or uname,
            "has_password": bool(pw),
            "status": u.get("status", ""),
            "balance": _nested(u, "mt_messaging_cred", "quota", "balance") or "ND",
            "throughput": _nested(u, "mt_messaging_cred", "quota", "smpps_throughput") or "ND",
            "ips": ip_by_label.get(uid, []),
            "provider": (route["connector"] if route else (default_conn or "—")),
            "via_default": route is None,
            "rate": (route["rate"] if route else "0"),
            "today": traffic.get(uid, 0),
        })
    return clients


def _providers():
    """Connectors we can route clients OUT through (the real providers)."""
    try:
        return [c.get("cid") for c in SMPPCCM().list().get("connectors", []) if c.get("cid")]
    except Exception:
        return []


@login_required
def clients_view(request):
    return render(request, "web/content/clients.html", {
        "our_smpp_host": OUR_SMPP_HOST,
        "our_smpp_port": OUR_SMPP_PORT,
    })


def _clients_meta():
    try:
        groups = [g["name"] for g in Groups().list().get("groups", [])]
    except Exception:
        groups = []
    provs = _providers()
    _rmap, default_conn = _route_map()
    return JsonResponse({"groups": groups, "providers": provs,
                         "default_provider": default_conn or (provs[0] if provs else ""),
                         "status": 200})


def _clients_create(request):
    steps = []

    def ok(step, detail=""):
        steps.append({"step": step, "ok": True, "detail": detail})

    def warn(step, detail):
        steps.append({"step": step, "ok": False, "detail": str(detail)})

    def fail(step, msg):
        msg = str(msg)
        steps.append({"step": step, "ok": False, "detail": msg})
        return JsonResponse({"steps": steps, "message": msg, "status": 400}, status=400)

    P = request.POST.get
    uid = (P("uid") or "").strip()
    username = (P("username") or "").strip()
    password = P("password") or ""
    group_mode = P("group_mode") or "existing"
    gid = (P("gid") or "").strip()
    provider = (P("provider") or "").strip()
    rate = (P("rate") or "0").strip()
    ips_raw = (P("ips") or "").strip()
    balance = (P("balance") or "").strip()
    throughput = (P("throughput") or "").strip()

    if not uid or " " in uid:
        return fail("Client", _("Client ID is required and cannot contain spaces."))
    if not username:
        return fail("Client", _("Username (their SMPP login) is required."))
    if len(username) > 15:
        return fail("Client", _("Username is too long (max 15 characters)."))
    if not password:
        return fail("Client", _("Password is required."))
    if len(password) > 8:
        return fail("Client", _("Password is too long. SMPP passwords are limited to 8 characters."))
    if not provider:
        return fail("Route", _("Choose a provider connector to route this client's traffic through."))
    try:
        rate_val = float(rate or "0")
    except ValueError:
        return fail("Route", _("Rate must be a number."))
    ip_list = [x.strip() for x in re.split(r"[\s,]+", ips_raw) if x.strip()]
    for ip in ip_list:
        if not _valid_ip(ip):
            return fail("Whitelist", _("Invalid IP / CIDR: %(ip)s") % {"ip": ip})

    # 1) group
    try:
        existing_groups = [g["name"] for g in Groups().list().get("groups", [])]
    except Exception as e:
        return fail("Group", _("Could not read groups: ") + str(e))
    if group_mode == "new":
        if not gid or " " in gid:
            return fail("Group", _("New group id is required and cannot contain spaces."))
        if gid not in existing_groups:
            Groups().create(data=dict(gid=gid))
            if gid not in [g["name"] for g in Groups().list().get("groups", [])]:
                return fail("Group", _("Failed to create group '%(g)s'.") % {"g": gid})
            ok("Group", _("Created group %(g)s") % {"g": gid})
        else:
            ok("Group", _("Using existing group %(g)s") % {"g": gid})
    else:
        if not gid:
            return fail("Group", _("Select a group for this client."))
        if gid not in existing_groups:
            return fail("Group", _("Selected group '%(g)s' does not exist.") % {"g": gid})
        ok("Group", _("Using group %(g)s") % {"g": gid})

    # 2) user (login)
    if Users().get_user(uid, silent=True):
        return fail("Client", _("A client with ID '%(u)s' already exists.") % {"u": uid})
    try:
        Users().create(data=dict(uid=uid, gid=gid, username=username, password=password))
    except Exception as e:
        return fail("Client", _("Failed to create client login: ") + str(e))
    try:
        gm, _c = GroupsModel.objects.get_or_create(gid=gid)
        UsersModel.objects.update_or_create(
            uid=uid, defaults={"gid": gm, "username": username, "password": password,
                               "parameters": "", "user": request.user})
    except Exception:
        pass
    ok("Client", _("Created client login %(u)s (username %(n)s)") % {"u": uid, "n": username})

    # 3) credit / throughput (optional)
    updates = []
    if balance != "":
        updates.append(["mt_messaging_cred", "quota", "balance", balance])
    if throughput != "":
        updates.append(["mt_messaging_cred", "quota", "smpps_throughput", throughput])
    if updates:
        try:
            Users().partial_update(updates, uid=uid)
            ok("Credit", _("Set ") + ", ".join("%s=%s" % (u[-2], u[-1]) for u in updates))
        except Exception as e:
            warn("Credit", _("Could not set credit/throughput (set it later): ") + str(e))

    # 4) whitelist their source IP(s)
    if ip_list:
        rows = _read_ips()
        existing = {r["ip"] for r in rows}
        for ip in ip_list:
            if ip not in existing:
                rows.append({"ip": ip, "label": uid})
        try:
            _write_ips(rows)
            ok("Whitelist", _("Whitelisted %(ips)s (firewall updates in a few seconds)") % {"ips": ", ".join(ip_list)})
        except OSError as e:
            warn("Whitelist", _("Could not write whitelist: ") + str(e))
    else:
        warn("Whitelist", _("No source IP given — the client can't bind in until you whitelist their IP (SMPP Access)."))

    # 5) filter + MT route -> provider
    fid = "uf_" + uid
    try:
        existing_filters = [f["fid"] for f in Filters().list().get("filters", [])]
    except Exception as e:
        return fail("Route", _("Could not read filters: ") + str(e))
    if fid not in existing_filters:
        try:
            Filters().create(data=dict(type="userfilter", fid=fid, parameter=uid))
        except Exception as e:
            return fail("Route", _("Failed to create filter: ") + str(e))
        if fid not in [f["fid"] for f in Filters().list().get("filters", [])]:
            return fail("Route", _("Failed to create filter %(f)s.") % {"f": fid})
    try:
        orders = [int(r["order"]) for r in MTRouter()._list() if str(r["order"]).isdigit()]
        next_order = (max(orders) + 1) if orders else 1
        MTRouter().create(data=dict(type="StaticMTRoute", order=str(next_order),
                                    rate=str(rate_val), smppconnectors=provider, filters=fid))
        ok("Route", _("Routing %(u)s → %(p)s @ %(r)s") % {"u": uid, "p": provider, "r": rate_val})
    except Exception as e:
        return fail("Route", _("Client login created, but routing to the provider failed: ") + str(e))

    handoff = {
        "uid": uid, "host": OUR_SMPP_HOST, "port": OUR_SMPP_PORT,
        "system_id": username, "password": password, "bind": "transceiver",
        "ips": ip_list, "provider": provider,
    }
    return JsonResponse({"steps": steps, "handoff": handoff,
                         "message": str(_("Client %(u)s is set up.")) % {"u": uid}, "status": 200})


def _clients_delete(request):
    uid = (request.POST.get("uid") or "").strip()
    if not uid:
        return JsonResponse({"message": str(_("Client id required.")), "status": 400}, status=400)
    removed = []
    # routes for this uid
    try:
        for r in MTRouter()._list():
            if not str(r.get("order", "")).isdigit():
                continue
            if any(_UID_RE.search(f or "") and _UID_RE.search(f).group(1) == uid for f in (r.get("filters") or [])):
                try:
                    MTRouter().destroy(order=r["order"])
                    removed.append("route %s" % r["order"])
                except Exception:
                    pass
    except Exception:
        pass
    # filter
    try:
        Filters().destroy(fid="uf_" + uid)
        removed.append("filter")
    except Exception:
        pass
    # login
    try:
        Users().destroy(uid=uid)
        removed.append("login")
    except Exception:
        pass
    # whitelist entries labelled with this uid
    try:
        rows = [r for r in _read_ips() if (r.get("label") or "").strip() != uid]
        _write_ips(rows)
        removed.append("whitelist")
    except Exception:
        pass
    try:
        UsersModel.objects.filter(uid=uid).delete()
    except Exception:
        pass
    return JsonResponse({"message": str(_("Client %(u)s removed (%(x)s).")) % {"u": uid, "x": ", ".join(removed) or "nothing"},
                         "status": 200})


@require_post_ajax
def clients_view_manage(request):
    s = request.POST.get("s")
    if s == "list":
        return JsonResponse({"clients": _clients_list(), "status": 200})
    if s == "meta":
        return _clients_meta()
    if s == "create":
        return _clients_create(request)
    if s == "delete":
        return _clients_delete(request)
    return JsonResponse({"message": str(_("Sorry, Command does not matched.")), "status": 400}, status=400)
