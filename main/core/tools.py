from django.conf import settings
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.views.decorators.http import require_http_methods

from functools import wraps
from .exceptions import (CanNotModifyError, JasminSyntaxError, UnknownError)

STANDARD_PROMPT = settings.STANDARD_PROMPT
INTERACTIVE_PROMPT = settings.INTERACTIVE_PROMPT


def _match_text(match_group):
    "Coerce a pexpect match group (bytes in the default spawn mode, or str) to stripped text."
    if isinstance(match_group, bytes):
        match_group = match_group.decode(errors="replace")
    return match_group.strip()


def set_ikeys(telnet, keys2vals):
    "set multiple keys for interactive command"
    for key, val in keys2vals.items():
        # print(key, val)
        telnet.sendline("%s %s" % (key, val))
        matched_index = telnet.expect([
            r'.*(Unknown .*)' + INTERACTIVE_PROMPT,
            r'(.*) can not be modified.*' + INTERACTIVE_PROMPT,
            r'(.*)' + INTERACTIVE_PROMPT
        ])
        result = _match_text(telnet.match.group(1))
        if matched_index == 0:
            raise UnknownError(result)
        if matched_index == 1:
            raise CanNotModifyError(result)
    telnet.sendline('ok')
    ok_index = telnet.expect([
        r'ok(.* syntax is invalid).*' + INTERACTIVE_PROMPT,
        # Jasmin refuses to save when required options are missing/empty, e.g.
        # "You must set these options before saving: fid, type, gid". Without this
        # branch we sit at the interactive prompt until the telnet timeout fires.
        r'.*(You must set these options before saving[^\r\n]*).*' + INTERACTIVE_PROMPT,
        r'.*' + STANDARD_PROMPT,
    ])
    if ok_index == 0:
        # remove whitespace and return error
        raise JasminSyntaxError(" ".join(_match_text(telnet.match.group(1)).split()))
    if ok_index == 1:
        message = " ".join(_match_text(telnet.match.group(1)).split())
        # Leave the interactive session cleanly so the telnet connection is reusable.
        telnet.sendline('ko')
        try:
            telnet.expect(r'.*' + STANDARD_PROMPT)
        except Exception:
            pass
        raise JasminSyntaxError(message)


def split_cols(lines):
    "split columns into lists, skipping blank and non-data lines"
    parsed = []
    for line in lines:
        raw_split = line.split()
        fields = [s for s in raw_split if (s and raw_split[0][0] == '#')]
        parsed.append(fields)
    return parsed

def require_post_ajax(view_func):
    @wraps(view_func)
    @require_http_methods(["POST"])
    @login_required
    def _wrapped_view(request, *args, **kwargs):
        if request.headers.get('x-requested-with') != 'XMLHttpRequest':
            return JsonResponse({'message': 'This is an AJAX-only endpoint', 'status': 400}, status=400)
        return view_func(request, *args, **kwargs)
    return _wrapped_view

def require_get_ajax(view_func):
    @wraps(view_func)
    @require_http_methods(["GET"])
    @login_required
    def _wrapped_view(request, *args, **kwargs):
        if request.headers.get('x-requested-with') != 'XMLHttpRequest':
            return JsonResponse({'message': 'This is an AJAX-only endpoint', 'status': 400}, status=400)
        return view_func(request, *args, **kwargs)
    return _wrapped_view
