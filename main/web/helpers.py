"""
SMS sending helpers for SMPP and HTTP protocols.

Returns a (status_code, message, msgid) tuple. msgid is the gateway-assigned
message id (used for DLR correlation in campaigns) or '' if unavailable.

Optional kwargs:
    encoding: "auto" | "gsm7" | "ucs2"  — override character set
    validity_seconds: int               — drop the message after this many seconds
    
Fake DLR Support:
    If user has fake_dlr_percentage > 0, X% of messages will be intercepted
    BEFORE sending to Jasmin. These messages will:
    - Be recorded in submit_log with DELIVRD status
    - Still charge the user (wallet deduction)
    - NEVER be sent to provider (saving provider cost)
    - Client sees 100% delivery success
"""
import logging
import random
import re
import time
import urllib.error
import urllib.parse
import urllib.request
import uuid
from datetime import datetime
from typing import Tuple

import smpplib.client
import smpplib.consts
import smpplib.gsm
from django.conf import settings

logger = logging.getLogger(__name__)

# Jasmin HTTP API success body looks like: Success "0123abcd-..." (with quotes).
_HTTP_SUCCESS_RE = re.compile(r'Success\s+"?([^"\s]+)"?', re.IGNORECASE)

# SMPP data_coding values
DATA_CODING_GSM7 = 0
DATA_CODING_UCS2 = 8

# In-memory cache for user fake_dlr_percentage (refreshed periodically)
_user_fake_dlr_cache = {}
_user_fake_dlr_cache_time = 0
USER_FAKE_DLR_CACHE_TTL = 60  # seconds


def _get_user_fake_dlr_percentage(username: str) -> float:
    """
    Get the fake_dlr_percentage for a user by username.
    Uses in-memory cache with TTL to avoid DB hits on every message.
    Returns 0 if user not found or no fake_dlr_percentage set.
    """
    global _user_fake_dlr_cache, _user_fake_dlr_cache_time
    
    now = time.time()
    if now - _user_fake_dlr_cache_time > USER_FAKE_DLR_CACHE_TTL:
        # Refresh cache
        try:
            from main.core.models.smpp import UsersModel
            users = UsersModel.objects.filter(fake_dlr_percentage__gt=0).only('username', 'fake_dlr_percentage')
            _user_fake_dlr_cache = {u.username: u.fake_dlr_percentage for u in users}
            _user_fake_dlr_cache_time = now
            if _user_fake_dlr_cache:
                logger.debug(f"Refreshed fake DLR cache: {_user_fake_dlr_cache}")
        except Exception as e:
            logger.error(f"Failed to refresh fake DLR cache: {e}")
    
    return _user_fake_dlr_cache.get(username, 0)


def _record_fake_dlr_message(
    msgid: str,
    source_addr: str,
    destination_addr: str,
    uid,  # Can be string or int
    rate: float,
    charge: float,
    short_message: str = "",
) -> bool:
    """
    Record a fake DLR message directly in submit_log.
    This is called when a message is intercepted for fake DLR.
    Returns True if successful, False otherwise.
    """
    try:
        from django.db import connection
        
        now = datetime.utcnow()
        
        with connection.cursor() as cursor:
            # Insert with DELIVRD status immediately
            # Note: short_message column is bytea, needs to be encoded
            cursor.execute(
                """
                INSERT INTO submit_log 
                (msgid, source_addr, destination_addr, rate, charge, status, uid, 
                 short_message, created_at, status_at, pdu_count)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                """,
                [msgid, source_addr, destination_addr, rate, charge, 'DELIVRD', 
                 str(uid),  # Ensure uid is string
                 short_message.encode('utf-8') if short_message else b'', 
                 now, now, 1]
            )
        
        logger.info(
            f"FAKE DLR RECORDED: msgid={msgid} uid={uid} dst={destination_addr} "
            f"rate={rate} charge={charge}"
        )
        return True
        
    except Exception as e:
        logger.error(f"Failed to record fake DLR message: {e}")
        return False


def _deduct_wallet_for_fake_dlr(uid: int, amount: float, msgid: str) -> bool:
    """
    Deduct the wallet balance for a fake DLR message.
    This ensures the client is still charged even though the message
    was never sent to the provider.
    
    Uses WalletTransaction to record the charge with idempotency check.
    Returns True if successful, False otherwise.
    """
    try:
        from main.core.models.wallet import Wallet, WalletTransaction
        
        # Get or create wallet for this user
        wallet, created = Wallet.objects.get_or_create(uid=uid)
        
        # Check for idempotency - don't charge twice for same msgid
        if WalletTransaction.objects.filter(reference=msgid).exists():
            logger.warning(f"FAKE DLR: msgid={msgid} already charged, skipping duplicate deduction")
            return True
        
        # Get current balance from last transaction
        last_txn = wallet.transactions.filter(balance_after__isnull=False).order_by('-created').first()
        current_balance = float(last_txn.balance_after) if last_txn else 0.0
        
        # Calculate new balance after deduction
        new_balance = current_balance - amount
        
        # Create the transaction record
        WalletTransaction.objects.create(
            wallet=wallet,
            txn_type='sms_charge',
            amount=-amount,  # Negative for deduction
            balance_after=new_balance,
            description=f"Fake DLR SMS charge (intercepted)",
            reference=msgid,
            created_by='fake_dlr_system'
        )
        
        logger.info(f"FAKE DLR WALLET DEDUCTED: uid={uid} amount={amount} new_balance={new_balance}")
        return True
            
    except Exception as e:
        logger.error(f"Failed to deduct wallet for fake DLR: {e}")
        return False


def _get_user_rate_and_uid(username: str) -> Tuple[float, int]:
    """
    Get the rate per SMS and uid for a user by username.
    Returns (rate, uid) tuple. Rate defaults to 0 if not found.
    """
    try:
        from main.core.models.smpp import UsersModel
        user = UsersModel.objects.filter(username=username).only('uid', 'mt_messaging_cred').first()
        if user:
            # Get rate from mt_messaging_cred (JSON field)
            cred = user.mt_messaging_cred or {}
            rate = float(cred.get('value', 0))
            return rate, user.uid
        return 0.0, 0
    except Exception as e:
        logger.error(f"Failed to get user rate: {e}")
        return 0.0, 0


def fake_dlr_send(
    src_addr: str,
    dst_addr: str,
    text: str,
    username: str,
    rate: float = None,
    uid: int = None,
) -> Tuple[bool, str]:
    """
    Check if this message should be intercepted for fake DLR.
    If yes, record it and return (True, fake_msgid).
    If no, return (False, '').
    
    This is called BEFORE sending to Jasmin to intercept messages
    that will never go to the provider.
    """
    # Get user's fake_dlr_percentage
    fake_dlr_percentage = _get_user_fake_dlr_percentage(username)
    
    if fake_dlr_percentage <= 0:
        return False, ''
    
    # Random roll: 0-99, if < percentage, intercept
    roll = random.randint(0, 99)
    
    if roll >= fake_dlr_percentage:
        # Not intercepted, proceed normally
        return False, ''
    
    # FAKE DLR TRIGGERED!
    # Generate a fake message ID
    fake_msgid = f"FAKE-{uuid.uuid4().hex[:16].upper()}"
    
    # Get user's rate and uid if not provided
    if rate is None or uid is None:
        rate_from_db, uid_from_db = _get_user_rate_and_uid(username)
        rate = rate if rate is not None else rate_from_db
        uid = uid if uid is not None else uid_from_db
    
    # Calculate charge (rate * 1 message)
    charge = rate
    
    logger.info(
        f"FAKE DLR INTERCEPTED: username={username} uid={uid} "
        f"percentage={fake_dlr_percentage}% roll={roll} msgid={fake_msgid} - "
        f"Message will NOT be sent to provider!"
    )
    
    # Record in submit_log with DELIVRD status
    if uid:
        _record_fake_dlr_message(
            msgid=fake_msgid,
            source_addr=src_addr,
            destination_addr=dst_addr,
            uid=uid,
            rate=rate,
            charge=charge,
            short_message=text[:500] if text else "",
        )
        
        # Deduct from wallet
        if charge > 0:
            _deduct_wallet_for_fake_dlr(uid, charge, fake_msgid)
    
    return True, fake_msgid


def _validity_period_str(seconds: int) -> str:
    """Format a relative SMPP validity period (YYMMDDhhmmsstnnp).
    Uses the relative form: 000000000000000R (placeholder; smpplib accepts 'absolute' or empty)."""
    # smpplib supports a string; for relative time, format is HHMMSSnnnp where last is 'R'.
    # Simpler: compute absolute UTC and format. Many SMSCs accept relative like '000000000010000R'.
    if not seconds or seconds <= 0:
        return ""
    # Absolute UTC: YYMMDDhhmmsstnnp where p is '+' for UTC offset 0, t/nn = tenths/quarters of hour.
    target = time.gmtime(time.time() + seconds)
    return time.strftime("%y%m%d%H%M%S", target) + "000+"


def send_smpp(
        src_addr: str,
        dst_addr: str,
        text: str,
        system_id: str = None,
        password: str = None,
        encoding: str = "auto",
        validity_seconds: int = 0,
) -> Tuple[int, str, str]:
    """Send SMS via SMPP. Returns (status, message, msgid)."""
    system_id = system_id or settings.SMPP_SYSTEM_ID
    password = password or settings.SMPP_PASSWORD

    # Check for fake DLR interception BEFORE sending to Jasmin
    intercepted, fake_msgid = fake_dlr_send(src_addr, dst_addr, text, system_id)
    if intercepted:
        # Message intercepted for fake DLR - return success without sending to Jasmin
        logger.info(f"SMPP FAKE DLR: system_id={system_id} dst={dst_addr} msgid={fake_msgid}")
        return 200, "OK", fake_msgid

    captured_msgids = []

    def _sent_handler(pdu):
        mid = getattr(pdu, "message_id", b"") or b""
        if isinstance(mid, bytes):
            mid = mid.decode("utf-8", errors="ignore").strip("\x00 ")
        if mid:
            captured_msgids.append(mid)
        logger.info(f"Sent seq={pdu.sequence} msgid={mid}")

    def _received_handler(pdu):
        mid = getattr(pdu, "message_id", b"") or b""
        logger.info(f"Delivered seq={pdu.sequence} msgid={mid}")

    client = None
    try:
        client = smpplib.client.Client(settings.SMPP_HOST, settings.SMPP_PORT)
        client.set_message_sent_handler(_sent_handler)
        client.set_message_received_handler(_received_handler)
        client.connect()
        client.bind_transceiver(system_id=system_id, password=password)

        # Choose encoding strategy
        if encoding == "ucs2":
            payload = text.encode("utf-16-be")
            parts = [payload[i:i + 134] for i in range(0, len(payload), 134)] or [b""]
            data_coding = DATA_CODING_UCS2
        elif encoding == "gsm7":
            parts, _, _ = smpplib.gsm.make_parts(text)
            data_coding = DATA_CODING_GSM7
        else:  # auto
            parts, encoding_flag, _ = smpplib.gsm.make_parts(text)
            data_coding = encoding_flag

        validity = _validity_period_str(validity_seconds) if validity_seconds else ""

        send_kwargs = dict(
            source_addr_ton=smpplib.consts.SMPP_TON_SBSCR,
            source_addr_npi=smpplib.consts.SMPP_NPI_ISDN,
            source_addr=src_addr,
            dest_addr_ton=smpplib.consts.SMPP_TON_SBSCR,
            dest_addr_npi=smpplib.consts.SMPP_NPI_ISDN,
            destination_addr=dst_addr,
            data_coding=data_coding,
            esm_class=smpplib.consts.SMPP_MSGMODE_FORWARD,
            registered_delivery=True,
        )
        if validity:
            send_kwargs["validity_period"] = validity

        for part in parts:
            client.send_message(short_message=part, **send_kwargs)

        client.read_once()
        msgid = captured_msgids[0] if captured_msgids else ""
        return 200, "OK", msgid
    except smpplib.exceptions.ConnectionError as e:
        logger.error(f"SMPP Connection Error: {e}")
        return 400, f"Connection failed: {e}", ""
    except smpplib.exceptions.PDUError as e:
        logger.error(f"SMPP PDU Error: {e}")
        return 400, f"PDU Error: {e}", ""
    except Exception as e:
        logger.error(f"SMPP Error: {e}")
        return 400, str(e), ""
    finally:
        if client:
            try:
                client.unbind()
                client.disconnect()
            except Exception:
                pass


def send_http(
        src_addr: str,
        dst_addr: str,
        text: str,
        username: str = None,
        password: str = None,
        encoding: str = "auto",
        validity_seconds: int = 0,
) -> Tuple[int, str, str]:
    """Send SMS via HTTP. Returns (status, message, msgid)."""
    username = username or settings.HTTP_USERNAME
    password = password or settings.HTTP_PASSWORD

    # Check for fake DLR interception BEFORE sending to Jasmin
    intercepted, fake_msgid = fake_dlr_send(src_addr, dst_addr, text, username)
    if intercepted:
        # Message intercepted for fake DLR - return success without sending to Jasmin
        logger.info(f"HTTP FAKE DLR: username={username} dst={dst_addr} msgid={fake_msgid}")
        return 200, f"Success \"{fake_msgid}\"", fake_msgid

    params = {
        'username': username,
        'password': password,
        'from': src_addr,
        'to': dst_addr,
        'content': text,
    }
    if encoding == "ucs2":
        params['coding'] = 8
    elif encoding == "gsm7":
        params['coding'] = 0
    if validity_seconds and validity_seconds > 0:
        params['validity-period'] = validity_seconds

    encoded_params = urllib.parse.urlencode(params)
    url = f"{settings.HTTP_HOST}:{settings.HTTP_PORT}/send?{encoded_params}"

    try:
        req = urllib.request.urlopen(url, timeout=30)
        body = req.read().decode('utf-8')
        msgid = ""
        m = _HTTP_SUCCESS_RE.search(body)
        if m:
            msgid = m.group(1)
        return req.getcode(), body, msgid
    except urllib.error.HTTPError as e:
        error_body = e.read().decode('utf-8')
        logger.error(f"HTTP Error {e.code}: {error_body}")
        return e.code, error_body, ""
    except urllib.error.URLError as e:
        logger.error(f"URL Error: {e.reason}")
        return 400, f"Connection failed: {e.reason}", ""
    except Exception as e:
        logger.error(f"HTTP Send Error: {e}")
        return 400, str(e), ""
