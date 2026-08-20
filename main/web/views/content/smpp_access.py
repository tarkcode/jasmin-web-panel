import ipaddress
import os

from django.utils.translation import gettext as _
from django.shortcuts import render
from django.http import JsonResponse
from django.contrib.auth.decorators import login_required

from main.core.tools import require_post_ajax

# Written by the panel, read by the host firewall watcher (jasmin-smpp-firewall.path).
IP_FILE = "/app/fw/allowed_ips.txt"


def _read_ips():
    rows = []
    try:
        with open(IP_FILE) as f:
            for line in f:
                line = line.rstrip("\n")
                if not line.strip() or line.lstrip().startswith("#"):
                    continue
                parts = line.split(None, 1)
                rows.append({"ip": parts[0], "label": parts[1].strip() if len(parts) > 1 else ""})
    except OSError:
        pass
    return rows


def _write_ips(rows):
    lines = [("%s %s" % (r["ip"], r.get("label", ""))).strip() for r in rows]
    # In-place write (file is world-writable); triggers the host path unit on close.
    with open(IP_FILE, "w") as f:
        f.write("\n".join(lines) + ("\n" if lines else ""))


def _valid_ip(ip):
    try:
        ipaddress.ip_network(ip, strict=False)  # accepts a bare IP or CIDR
        return True
    except ValueError:
        return False


@login_required
def smpp_access_view(request):
    return render(request, "web/content/smpp_access.html")


@require_post_ajax
def smpp_access_view_manage(request):
    s = request.POST.get("s")
    if s == "list":
        writable = os.access(IP_FILE, os.W_OK) if os.path.exists(IP_FILE) else False
        return JsonResponse({"ips": _read_ips(), "writable": writable, "status": 200})
    if s == "add":
        ip = (request.POST.get("ip") or "").strip()
        label = (request.POST.get("label") or "").replace("\n", " ").replace("\r", " ").strip()[:60]
        if not _valid_ip(ip):
            return JsonResponse({"message": str(_("Enter a valid IPv4 address or CIDR (e.g. 203.0.113.5 or 203.0.113.0/24).")), "status": 400}, status=400)
        rows = _read_ips()
        if any(r["ip"] == ip for r in rows):
            return JsonResponse({"message": str(_("That IP is already whitelisted.")), "status": 400}, status=400)
        rows.append({"ip": ip, "label": label})
        try:
            _write_ips(rows)
        except OSError as e:
            return JsonResponse({"message": str(_("Could not update the whitelist file: ")) + str(e), "status": 500}, status=500)
        return JsonResponse({"message": str(_("IP added — firewall updating (a few seconds).")), "status": 200})
    if s == "delete":
        ip = (request.POST.get("ip") or "").strip()
        rows = [r for r in _read_ips() if r["ip"] != ip]
        try:
            _write_ips(rows)
        except OSError as e:
            return JsonResponse({"message": str(_("Could not update the whitelist file: ")) + str(e), "status": 500}, status=500)
        return JsonResponse({"message": str(_("IP removed — firewall updating (a few seconds).")), "status": 200})
    return JsonResponse({"message": str(_("Sorry, Command does not matched.")), "status": 400}, status=400)
