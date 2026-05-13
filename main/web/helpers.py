"""
SMS sending helpers for SMPP and HTTP protocols.

Returns a (status_code, message, msgid) tuple. msgid is the gateway-assigned
message id (used for DLR correlation in campaigns) or '' if unavailable.

Optional kwargs:
    encoding: "auto" | "gsm7" | "ucs2"  — override character set
    validity_seconds: int               — drop the message after this many seconds
"""
import logging
import re
import time
import urllib.error
import urllib.parse
import urllib.request
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
