import time

from django.utils.translation import gettext as _
from django.shortcuts import render
from django.http import JsonResponse
from django.contrib.auth.decorators import login_required

from main.core.smpp import SMPPCCM
from main.core.tools import require_post_ajax
from main.core.exceptions import JasminSyntaxError, JasminError, UnknownError


@login_required
def smppccm_view(request):
    return render(request, "web/content/smppccm.html")


@require_post_ajax
def smppccm_view_manage(request):
    response = {}
    s = request.POST.get("s")
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
        existing = smppccm.get_smppccm(cid, silent=True)
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
