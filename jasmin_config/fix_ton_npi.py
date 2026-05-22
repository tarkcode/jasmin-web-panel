"""
Jasmin MT Interceptor: fix_ton_npi.py
Fixes source and destination TON/NPI before forwarding to the upstream SMPP provider.

Problem: The vendor/web panel sends submit_sm with wrong TON/NPI values.
The upstream (168.144.0.33:5757) returns ESME_RINVSRCTON because:
  - Alphanumeric sender (e.g. CMMCSS, SIXCOM) sent with TON=4 instead of TON=5
  - NPI=1 (ISDN) instead of NPI=0 (Unknown) for alphanumeric

This interceptor reads the source_addr, determines if it is numeric or
alphanumeric, and sets the correct TON/NPI values accordingly.
"""

import re

try:
    src = routable.pdu.params.get('source_addr', b'')
    if isinstance(src, bytes):
        src_str = src.decode('utf-8', errors='replace').strip()
    else:
        src_str = str(src).strip()

    # Numeric sender (e.g. +911234567890) -> International/ISDN
    if re.match(r'^\+?\d+$', src_str):
        routable.pdu.params['source_addr_ton'] = 1  # International
        routable.pdu.params['source_addr_npi'] = 1  # ISDN
    else:
        # Alphanumeric sender (e.g. CMMCSS, SIXCOM, JasminSMS)
        routable.pdu.params['source_addr_ton'] = 5  # Alphanumeric
        routable.pdu.params['source_addr_npi'] = 0  # Unknown

    # Fix destination: always International/ISDN for +91 numbers
    routable.pdu.params['dest_addr_ton'] = 1  # International
    routable.pdu.params['dest_addr_npi'] = 1  # ISDN

except Exception as e:
    pass
