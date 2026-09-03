import os
import re
import socket
import time
from concurrent.futures import ThreadPoolExecutor, as_completed

from django.utils.translation import gettext as _
from django.shortcuts import render
from django.http import JsonResponse
from django.contrib.auth.decorators import login_required

from main.core.smpp import SMPPCCM
from main.core.tools import require_post_ajax
from main.core.exceptions import JasminSyntaxError, JasminError, UnknownError

# Jasmin writes one log per connector here (mounted read-only into this container).
LOG_DIR = "/var/log/jasmin"
# cids are alphanumeric/underscore/dash — this also blocks path traversal.
_CID_RE = re.compile(r"^[A-Za-z0-9_\-]{1,60}$")


def _tail_lines(path, n):
    """Return the last `n` non-empty lines of a (possibly large) log file."""
    try:
        with open(path, "rb") as f:
            f.seek(0, os.SEEK_END)
            remaining = f.tell()
            buf = b""
            while remaining > 0 and buf.count(b"\n") <= n:
                step = 8192 if remaining >= 8192 else remaining
                remaining -= step
                f.seek(remaining)
                buf = f.read(step) + buf
            text = buf.decode("utf-8", errors="replace")
    except OSError:
        return []
    lines = [ln.rstrip("\r") for ln in text.splitlines() if ln.strip()]
    return lines[-n:]


def _summarize_reason(lines):
    """Turn the most recent meaningful log event into a plain-English reason."""
    patterns = [
        ("ESME_RINVPASWD", _("Not connected — the provider rejected our password (Invalid Password). Verify the connector's password with the provider (max 8 characters).")),
        ("ESME_RINVSYSID", _("Not connected — the provider rejected our username / System ID (Invalid System ID). Verify the username with the provider.")),
        ("ESME_RINVSYSTYP", _("Not connected — the provider rejected the System Type. Verify the 'System Type' value with the provider.")),
        ("ESME_RBINDFAIL", _("Not connected — the provider refused the bind. The account may be disabled, or already bound from elsewhere.")),
        ("ESME_RINVBNDSTS", _("Not connected — invalid bind status. The account may already be bound elsewhere, or the bind type is wrong.")),
        ("Connection refused", _("Not connected — the provider's server refused the connection (wrong port, or their service is down).")),
        ("TimeoutError", _("Not connected — the provider's server is unreachable (connection timed out). Check host/port and ask the provider to whitelist our server IP.")),
        ("Connection failed", _("Not connected — could not reach the provider's server. Check host/port and ask the provider to whitelist our server IP.")),
    ]
    for ln in reversed(lines):
        for token, msg in patterns:
            if token in ln:
                return str(msg)
        # a fresh successful bind after any error clears the reason
        if "bound" in ln.lower() and "requesting" not in ln.lower():
            return str(_("Connected — bind established."))
    for ln in reversed(lines):
        m = re.search(r"ESME_\w+", ln)
        if m:
            return str(_("Not connected — the provider returned %(code)s.")) % {"code": m.group(0)}
    return str(_("No recent connection errors found in the log."))


def _tcp_probe(host, port, timeout=4.0):
    """Open a bare TCP connection to a provider's SMSC. This is the ONLY thing we
    can measure about 'their side' — whether their server answers us at all.
    Returns (reachable, latency_ms)."""
    try:
        start = time.time()
        with socket.create_connection((host, int(port)), timeout=timeout):
            return True, int((time.time() - start) * 1000)
    except Exception:
        return False, None


def _last_bind_reject(lines):
    """Scan recent log lines for the last SMPP BIND-layer rejection (not a
    connect-level timeout — reachability is measured live by _tcp_probe). A fresh
    successful bind supersedes any older rejection."""
    rejects = [
        ("ESME_RINVPASWD", _("provider rejected our password (Invalid Password)")),
        ("ESME_RINVSYSID", _("provider rejected our username (Invalid System ID)")),
        ("ESME_RINVSYSTYP", _("provider rejected our System Type")),
        ("ESME_RBINDFAIL", _("provider refused the bind (account disabled, or already bound elsewhere)")),
        ("ESME_RINVBNDSTS", _("invalid bind status (already bound elsewhere, or wrong bind type)")),
        ("Request timed out after", _("provider did not answer our bind request")),
    ]
    for ln in reversed(lines):
        low = ln.lower()
        if "bound" in low and "requesting" not in low:
            return None
        for token, msg in rejects:
            if token in ln:
                return str(msg)
    return None


def _provider_status_for(conn):
    """Compute the 'provider side' health of one connector, as seen from our
    server: a live TCP reachability probe combined with the last bind reply."""
    cid = conn.get("cid") or ""
    host = conn.get("host") or ""
    port = conn.get("port") or ""
    reachable, latency_ms = _tcp_probe(host, port)
    lines = _tail_lines(os.path.join(LOG_DIR, "default-%s.log" % cid), 60) if _CID_RE.match(cid) else []
    reject = _last_bind_reject(lines) if reachable else None
    if not reachable:
        state = "unreachable"
        reason = str(_("Provider server unreachable — it's down, the host/port is wrong, "
                       "or our server IP isn't whitelisted on their side."))
    elif reject:
        state = "refused"
        reason = str(_("Reachable, but %(why)s. Their server is up — the problem is the "
                       "account/login on their side.")) % {"why": reject}
    else:
        state = "ok"
        reason = str(_("Provider server reachable and accepting our connection")) + \
            ((" (%d ms)." % latency_ms) if latency_ms is not None else ".")
    return {"cid": cid, "state": state, "reachable": reachable,
            "latency_ms": latency_ms, "reason": reason}


def _provider_status(request):
    """Probe every connector's provider endpoint concurrently and return a
    cid -> {state, reason, ...} map for the 'Provider' status dots."""
    try:
        data = SMPPCCM().list()
    except (JasminSyntaxError, JasminError, UnknownError) as e:
        detail = getattr(e, "detail", str(e)) or str(e)
        return JsonResponse({"message": str(_("Could not read connectors")) + f": {detail}",
                             "status": 500}, status=500)
    conns = [c for c in (data.get("connectors") or []) if c.get("host") and c.get("port")]
    results = {}
    if conns:
        with ThreadPoolExecutor(max_workers=min(8, len(conns))) as ex:
            futures = [ex.submit(_provider_status_for, c) for c in conns]
            for fut in as_completed(futures):
                try:
                    r = fut.result()
                    results[r["cid"]] = r
                except Exception:
                    pass
    return JsonResponse({"providers": results, "status": 200})


def _connector_logs(request):
    """Return the tail of a connector's Jasmin log plus a plain-English reason."""
    cid = (request.POST.get("cid") or "").strip()
    if not _CID_RE.match(cid):
        return JsonResponse({"message": str(_("Invalid connector id.")), "status": 400}, status=400)
    try:
        max_lines = max(20, min(int(request.POST.get("lines", 250)), 1000))
    except (TypeError, ValueError):
        max_lines = 250
    errors_only = request.POST.get("errors_only") == "true"

    path = os.path.join(LOG_DIR, "default-%s.log" % cid)
    # Defence in depth: the resolved file must sit directly inside LOG_DIR.
    if os.path.dirname(os.path.realpath(path)) != os.path.realpath(LOG_DIR):
        return JsonResponse({"message": str(_("Invalid connector id.")), "status": 400}, status=400)

    if not os.path.isfile(path):
        return JsonResponse({
            "cid": cid, "lines": [], "available": False,
            "reason": str(_("No log file for this connector yet (it may never have started).")),
            "status": 200,
        })

    lines = _tail_lines(path, max_lines)
    reason = _summarize_reason(lines)
    if errors_only:
        lines = [ln for ln in lines if (" ERROR " in ln or " WARNING " in ln or "Bind failed" in ln or "ESME_" in ln)]
    return JsonResponse({
        "cid": cid, "lines": lines, "reason": reason, "available": True, "status": 200,
    })


@login_required
def smppccm_view(request):
    return render(request, "web/content/smppccm.html")


@require_post_ajax
def smppccm_view_manage(request):
    response = {}
    s = request.POST.get("s")
    if s == "logs":
        # Reading a log file needs no telnet session — handle before opening one.
        return _connector_logs(request)
    if s == "provider_status":
        # Live per-provider reachability probe (their side, as seen from us).
        return _provider_status(request)
    smppccm = SMPPCCM()
    if s == "list":
        response = smppccm.list()
    elif s == "add":
        cid = request.POST.get("cid", "").strip()
        if not cid or ' ' in cid:
            return JsonResponse({
                "message": str(_("CID cannot be empty or contain spaces. Use underscores instead.")),
                "status": 400
            }, status=400)
        # Reject a duplicate CID up-front with a clear message. Otherwise Jasmin
        # fails the 'ok' commit and the panel only shows an opaque
        # "Failed to create connector" with no reason.
        # NOTE: get_smppccm() returns {} (not None) for an unknown cid because
        # jcli's "Unknown connector:" line still matches its generic branch, so
        # we test for a real connector by the presence of a parsed 'cid' key.
        # Use a FRESH session for this check so the `smppccm` create session below
        # stays pristine — reusing a session before create() makes create()'s
        # telnet result parsing misfire and falsely report failure.
        existing = SMPPCCM().get_smppccm(cid, silent=True)
        if existing and existing.get("cid"):
            return JsonResponse({
                "message": str(_("A connector with this CID already exists.")) + f" ('{cid}')",
                "status": 400
            }, status=400)
        username = request.POST.get("username", "")
        if len(username) > 15:
            return JsonResponse({
                "message": str(_("Username is too long. Jasmin only allows up to 15 characters.")) +
                           f" ('{username}' is {len(username)} chars)",
                "status": 400
            }, status=400)
        password = request.POST.get("password", "")
        # SMPP passwords are a COctetString capped at 9 octets (8 usable chars);
        # anything longer silently breaks the bind. Never echo the value back.
        if len(password) > 8:
            return JsonResponse({
                "message": str(_("Password is too long. SMPP passwords are limited to 8 characters.")) +
                           f" (got {len(password)})",
                "status": 400
            }, status=400)
        try:
            smppccm.create(data=dict(
                cid=cid,
                host=request.POST.get("host"),
                port=request.POST.get("port"),
                username=username,
                password=password,
            ))
        except (JasminSyntaxError, JasminError, UnknownError) as e:
            detail = getattr(e, 'detail', str(e)) or str(e)
            return JsonResponse({
                "message": str(_("Failed to create connector")) + f": {detail}",
                "status": 400
            }, status=400)
        response["message"] = str(_("SMPPCCM added successfully!"))
    elif s == "edit":
        # Guard the SMPP 8-char password limit before touching the connector.
        password = request.POST.get("password", "")
        if len(password) > 8:
            return JsonResponse({
                "message": str(_("Password is too long. SMPP passwords are limited to 8 characters.")) +
                           f" (got {len(password)})",
                "status": 400
            }, status=400)
        try:
            smppccm.partial_update(data=dict(
                cid=request.POST.get("cid"),
                logfile=request.POST.get("logfile"),
                logrotate=request.POST.get("logrotate"),
                loglevel=request.POST.get("loglevel"),
                host=request.POST.get("host"),
                port=request.POST.get("port"),
                ssl=request.POST.get("ssl"),
                username=request.POST.get("username"),
                password=request.POST.get("password"),
                bind=request.POST.get("bind"),
                bind_to=request.POST.get("bind_to"),
                trx_to=request.POST.get("trx_to"),
                res_to=request.POST.get("res_to"),
                pdu_red_to=request.POST.get("pdu_red_to"),
                con_loss_retry=request.POST.get("con_loss_retry"),
                con_loss_delay=request.POST.get("con_loss_delay"),
                con_fail_retry=request.POST.get("con_fail_retry"),
                con_fail_delay=request.POST.get("con_fail_delay"),
                src_addr=request.POST.get("src_addr"),
                src_ton=request.POST.get("src_ton"),
                src_npi=request.POST.get("src_npi"),
                dst_ton=request.POST.get("dst_ton"),
                dst_npi=request.POST.get("dst_npi"),
                bind_ton=request.POST.get("bind_ton"),
                bind_npi=request.POST.get("bind_npi"),
                validity=request.POST.get("validity"),
                priority=request.POST.get("priority"),
                requeue_delay=request.POST.get("requeue_delay"),
                addr_range=request.POST.get("addr_range"),
                systype=request.POST.get("systype"),
                dlr_expiry=request.POST.get("dlr_expiry"),
                submit_throughput=request.POST.get("submit_throughput"),
                proto_id=request.POST.get("proto_id"),
                coding=request.POST.get("coding"),
                elink_interval=request.POST.get("elink_interval"),
                def_msg_id=request.POST.get("def_msg_id"),
                ripf=request.POST.get("ripf"),
                dlr_msgid=request.POST.get("dlr_msgid"),
            ), cid=request.POST.get("cid"))
        except (JasminSyntaxError, JasminError, UnknownError) as e:
            detail = getattr(e, 'detail', str(e)) or str(e)
            return JsonResponse({
                "message": str(_("Failed to update connector")) + f": {detail}",
                "status": 400
            }, status=400)
        response["message"] = str(_("SMPPCCM updated successfully!"))
    elif s == "delete":
        response = smppccm.destroy(cid=request.POST.get("cid"))
        response["message"] = str(_("SMPPCCM deleted successfully!"))
    elif s == "start":
        response = smppccm.start(cid=request.POST.get("cid"))
        response["message"] = str(_("SMPPCCM started successfully!"))
    elif s == "stop":
        response = smppccm.stop(cid=request.POST.get("cid"))
        response["message"] = str(_("SMPPCCM stoped successfully!"))
    elif s == "restart":
        smppccm.stop(cid=request.POST.get("cid"))
        time.sleep(6)
        response = smppccm.start(cid=request.POST.get("cid"))
        response["message"] = str(_("SMPPCCM restarted successfully!"))
    else:
        return JsonResponse({"message": str(_("Sorry, Command does not matched.")), "status": 400}, status=400)
    response["status"] = 200
    return JsonResponse(response)
