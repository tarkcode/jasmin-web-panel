"""
Pure helpers for the campaigns module — CSV ingestion, phone validation,
and template substitution. No Django ORM imports here so this file is
import-cheap and easy to unit-test.
"""
import csv
import io
import re
from typing import Iterable, Tuple

# Reserved column names that we treat specially; everything else becomes a {placeholder}.
PHONE_COLUMN_CANDIDATES = ("msisdn", "phone", "phone_number", "mobile", "number", "to", "destination")
PLACEHOLDER_RE = re.compile(r"\{([a-zA-Z_][a-zA-Z0-9_]*)\}")
# Permissive E.164-ish: optional +, 7–15 digits.
PHONE_RE = re.compile(r"^\+?\d{7,15}$")
MAX_RECIPIENTS = 200_000


class CSVIngestError(ValueError):
    """Raised when an uploaded CSV cannot be parsed at all."""


def detect_phone_column(headers: Iterable[str]) -> str:
    """
    Pick the column most likely to hold phone numbers.
    Falls back to the first column if no candidate matches.
    """
    headers = [h.strip() for h in headers]
    lowered = {h.lower(): h for h in headers}
    for candidate in PHONE_COLUMN_CANDIDATES:
        if candidate in lowered:
            return lowered[candidate]
    return headers[0] if headers else ""


def normalise_phone(raw: str) -> str:
    """Strip whitespace, parens, dashes. Leave + and digits alone."""
    if raw is None:
        return ""
    cleaned = re.sub(r"[\s\-\(\)\.]", "", str(raw))
    return cleaned


def is_valid_phone(s: str) -> bool:
    return bool(PHONE_RE.match(s))


def parse_csv(file_bytes: bytes, phone_column: str = None) -> Tuple[list, list, list, str]:
    """
    Parse a CSV blob and return (rows, headers, errors, phone_column).
    `rows` is a list of dicts {msisdn: ..., variables: {col: val, ...}}.
    `errors` is a list of {line, msisdn, reason} for invalid rows (skipped, not raised).
    """
    if not file_bytes:
        raise CSVIngestError("File is empty")

    # Best-effort decoding; many SMS CSVs come from Excel as cp1252.
    for encoding in ("utf-8-sig", "utf-8", "cp1252", "latin-1"):
        try:
            text = file_bytes.decode(encoding)
            break
        except UnicodeDecodeError:
            continue
    else:
        raise CSVIngestError("Could not decode CSV — please save as UTF-8")

    # Sniff delimiter, fall back to comma.
    sample = text[:4096]
    try:
        dialect = csv.Sniffer().sniff(sample, delimiters=",;\t|")
    except csv.Error:
        dialect = csv.excel

    reader = csv.DictReader(io.StringIO(text), dialect=dialect)
    headers = [h.strip() for h in (reader.fieldnames or [])]
    if not headers:
        raise CSVIngestError("CSV has no header row")

    if phone_column is None:
        phone_column = detect_phone_column(headers)
    if phone_column not in headers:
        raise CSVIngestError(f"Phone column '{phone_column}' not found in headers: {headers}")

    rows = []
    errors = []
    seen = set()

    for line_no, raw in enumerate(reader, start=2):  # header is line 1
        if len(rows) >= MAX_RECIPIENTS:
            errors.append({"line": line_no, "msisdn": "", "reason": f"truncated at {MAX_RECIPIENTS} rows"})
            break

        msisdn = normalise_phone(raw.get(phone_column, ""))
        if not msisdn:
            errors.append({"line": line_no, "msisdn": "", "reason": "missing phone"})
            continue
        if not is_valid_phone(msisdn):
            errors.append({"line": line_no, "msisdn": msisdn, "reason": "invalid phone format"})
            continue
        if msisdn in seen:
            errors.append({"line": line_no, "msisdn": msisdn, "reason": "duplicate (skipped)"})
            continue

        seen.add(msisdn)
        variables = {k.strip(): (v or "").strip() for k, v in raw.items() if k and k.strip() != phone_column}
        rows.append({"msisdn": msisdn, "variables": variables})

    return rows, headers, errors, phone_column


def render_template(template: str, variables: dict, msisdn: str = "") -> str:
    """
    Replace {placeholder} occurrences using the variables dict.
    Missing keys render as empty strings rather than raising — bulk sends
    should never explode mid-batch on a single bad row.
    Reserved key 'msisdn' is always available.
    """
    ctx = dict(variables or {})
    ctx.setdefault("msisdn", msisdn)

    def sub(match):
        key = match.group(1)
        return str(ctx.get(key, ""))

    return PLACEHOLDER_RE.sub(sub, template or "")


def extract_placeholders(template: str) -> list:
    """Return ordered, deduplicated list of placeholder names in a template."""
    seen = set()
    out = []
    for match in PLACEHOLDER_RE.finditer(template or ""):
        name = match.group(1)
        if name not in seen:
            seen.add(name)
            out.append(name)
    return out


def parse_quick_list(raw: str) -> Tuple[list, list]:
    """
    Parse a textarea-pasted list of phone numbers (newline / comma / semicolon
    separated). Returns (rows, errors). rows have empty variables dict — no
    placeholder substitution from a quick list.
    """
    if not raw:
        return [], []

    tokens = re.split(r"[\s,;]+", raw.strip())
    rows = []
    errors = []
    seen = set()
    for token in tokens:
        if not token:
            continue
        msisdn = normalise_phone(token)
        if not msisdn:
            errors.append({"line": 0, "msisdn": token, "reason": "empty"})
            continue
        if not is_valid_phone(msisdn):
            errors.append({"line": 0, "msisdn": msisdn, "reason": "invalid format"})
            continue
        if msisdn in seen:
            errors.append({"line": 0, "msisdn": msisdn, "reason": "duplicate"})
            continue
        seen.add(msisdn)
        rows.append({"msisdn": msisdn, "variables": {}})
        if len(rows) >= MAX_RECIPIENTS:
            break
    return rows, errors


# Common non-GSM characters that have a sensible GSM-7 equivalent.
_GSM_NORMALIZE_MAP = {
    "‘": "'", "’": "'", "‚": "'", "‛": "'",  # curly single quotes
    "“": '"', "”": '"', "„": '"', "‟": '"',  # curly double quotes
    "–": "-", "—": "-", "―": "-",                  # en/em/horizontal dash
    "…": "...",                                              # ellipsis
    " ": " ",                                                # non-breaking space
    "·": ".",                                                # middle dot
    "•": "*",                                                # bullet
    "™": "TM", "®": "(R)", "©": "(C)",
    "€": "EUR", "£": "GBP", "¥": "JPY",
}


def normalise_to_gsm(text: str) -> str:
    """Replace common Unicode look-alikes with their GSM-7 equivalents.
    The output is not guaranteed to be 100% GSM-7 — just much closer."""
    if not text:
        return ""
    out = []
    for ch in text:
        out.append(_GSM_NORMALIZE_MAP.get(ch, ch))
    return "".join(out)


def gsm7_chars_remaining(text: str) -> Tuple[int, int]:
    """
    Approximate part count and chars remaining for a GSM-7 message.
    UCS-2 detection is left to the SMPP layer; this is a UI affordance only.
    """
    if not text:
        return 0, 160
    is_unicode = any(ord(c) > 127 for c in text)
    limit_single = 70 if is_unicode else 160
    limit_multi = 67 if is_unicode else 153
    n = len(text)
    if n <= limit_single:
        return 1, limit_single - n
    parts = -(-n // limit_multi)  # ceil
    return parts, parts * limit_multi - n
