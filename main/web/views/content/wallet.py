from decimal import Decimal, InvalidOperation

from django.utils.translation import gettext as _
from django.http import JsonResponse
from django.shortcuts import render
from django.contrib.auth.decorators import login_required

from main.core.tools import require_post_ajax
from main.core.models import Wallet, WalletTransaction, SubmitLog
from main.core.smpp import Users

MANUAL_TYPES = {"credit", "debit", "refund", "adjustment"}
SYNC_CAP = 20000  # max SMS charges mirrored per sync run


def _dec(v):
    try:
        return Decimal(str(v if v not in (None, "") else "0"))
    except (InvalidOperation, ValueError, TypeError):
        return None


def _jasmin_balance(uid, users_client=None):
    """Live balance from Jasmin (the authority). Returns Decimal or None if the
    user has no defined quota ('ND' = unlimited/undefined)."""
    client = users_client or Users()
    u = client.get_user(uid, silent=True) or {}
    bal = (((u.get("mt_messaging_cred") or {}).get("quota") or {}).get("balance"))
    return _dec(bal) if bal not in (None, "ND", "None") else None


@login_required
def wallet_view(request):
    return render(request, "web/content/wallet.html")


def _signed_delta(txn_type, amount):
    if txn_type in ("credit", "refund"):
        return abs(amount)
    if txn_type == "debit":
        return -abs(amount)
    return amount  # adjustment: signed as entered


@require_post_ajax
def wallet_view_manage(request):
    s = request.POST.get("s")
    response = {}

    if s == "list":
        wallets = list(Wallet.objects.all())
        # one jcli call for all live balances
        live = {}
        try:
            uc = Users()
            for u in uc.list().get("users", []):
                uid = u.get("uid")
                if uid:
                    bal = (((u.get("mt_messaging_cred") or {}).get("quota") or {}).get("balance"))
                    live[uid] = None if bal in (None, "ND", "None") else str(bal)
        except Exception:
            pass
        rows = []
        for w in wallets:
            rows.append({
                "id": w.id, "uid": w.uid, "currency": w.currency,
                "jasmin_balance": live.get(w.uid, None),
                "txn_count": w.transactions.count(),
            })
        response["wallets"] = rows

    elif s == "users":
        try:
            response["users"] = [u.get("uid") for u in Users().list().get("users", []) if u.get("uid")]
        except Exception:
            response["users"] = []

    elif s == "txn":
        uid = (request.POST.get("uid") or "").strip()
        txn_type = request.POST.get("txn_type")
        amount = _dec(request.POST.get("amount"))
        currency = (request.POST.get("currency") or "USD").strip() or "USD"
        description = (request.POST.get("description") or "").strip()
        if not uid:
            return JsonResponse({"message": str(_("Select a user.")), "status": 400}, status=400)
        if txn_type not in MANUAL_TYPES:
            return JsonResponse({"message": str(_("Invalid transaction type.")), "status": 400}, status=400)
        if amount is None or (txn_type != "adjustment" and amount <= 0):
            return JsonResponse({"message": str(_("Amount must be a positive number.")), "status": 400}, status=400)

        uc = Users()
        if not uc.get_user(uid, silent=True):
            return JsonResponse({"message": str(_("User '%(u)s' does not exist in Jasmin.")) % {"u": uid}, "status": 400}, status=400)
        wallet, _created = Wallet.objects.get_or_create(uid=uid, defaults={"currency": currency})
        if _created is False and currency and wallet.currency != currency:
            pass  # keep the wallet's original currency

        delta = _signed_delta(txn_type, amount)
        current = _jasmin_balance(uid, uc)
        current = current if current is not None else Decimal(0)  # ND -> start from 0
        new_balance = current + delta
        try:
            Users().partial_update(
                data=[["mt_messaging_cred", "quota", "balance", format(new_balance, 'f')]], uid=uid)
        except Exception as e:
            return JsonResponse({"message": str(_("Could not update Jasmin balance: ")) + str(e), "status": 400}, status=400)

        WalletTransaction.objects.create(
            wallet=wallet, txn_type=txn_type, amount=delta, balance_after=new_balance,
            description=description, created_by=getattr(request.user, "username", ""))
        response["message"] = str(_("%(t)s applied. New balance: %(b)s %(c)s")) % {
            "t": txn_type.capitalize(), "b": format(new_balance, 'f'), "c": wallet.currency}

    elif s == "history":
        uid = (request.POST.get("uid") or "").strip()
        try:
            wallet = Wallet.objects.get(uid=uid)
        except Wallet.DoesNotExist:
            return JsonResponse({"transactions": [], "status": 200})
        txns = wallet.transactions.all()[:500]
        response["transactions"] = [t.get_dict() for t in txns]

    elif s == "sync_sms":
        wallets = {w.uid: w for w in Wallet.objects.all()}
        if not wallets:
            return JsonResponse({"message": str(_("No wallets to sync.")), "synced": 0, "status": 200})
        seen = set(WalletTransaction.objects.filter(txn_type="sms_charge").values_list("reference", flat=True))
        qs = (SubmitLog.objects.filter(uid__in=list(wallets.keys()), status="ESME_ROK")
              .exclude(charge__isnull=True).exclude(charge=0).order_by("created_at")
              .values("msgid", "uid", "charge")[:SYNC_CAP])
        new_txns = []
        for row in qs:
            if row["msgid"] in seen:
                continue
            seen.add(row["msgid"])
            new_txns.append(WalletTransaction(
                wallet=wallets[row["uid"]], txn_type="sms_charge",
                amount=-Decimal(str(row["charge"])), balance_after=None,
                description="SMS charge", reference=row["msgid"], created_by="system"))
        WalletTransaction.objects.bulk_create(new_txns, batch_size=500)
        capped = " (capped, run again for more)" if len(new_txns) >= SYNC_CAP else ""
        response["message"] = str(_("Mirrored %(n)s SMS charge(s)%(c)s.")) % {"n": len(new_txns), "c": capped}
        response["synced"] = len(new_txns)

    else:
        return JsonResponse({"message": str(_("Sorry, Command does not matched.")), "status": 400}, status=400)

    response["status"] = 200
    return JsonResponse(response, status=200)
