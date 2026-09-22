"""
HTTP Send API with Fake DLR interception.

This endpoint proxies SMS send requests to Jasmin, but intercepts messages
for users with fake_dlr_percentage > 0 BEFORE they reach Jasmin.

Usage:
    POST /api/send/
    or
    GET /api/send/?username=X&password=X&from=X&to=X&content=X

Parameters:
    username: SMPP username
    password: SMPP password  
    from: Source address (sender ID)
    to: Destination address (phone number)
    content: Message content
    coding: (optional) Data coding - 0=GSM7, 8=UCS2
    validity-period: (optional) Validity period in seconds

Returns:
    Success: "Success \"MESSAGE_ID\""
    Error: "Error \"error message\""
"""
import logging
import urllib.parse
import urllib.request
import urllib.error

from django.http import HttpResponse
from django.conf import settings
from django.views.decorators.csrf import csrf_exempt

from main.web.helpers import fake_dlr_send, _get_user_rate_and_uid

logger = logging.getLogger(__name__)


@csrf_exempt
def send_sms(request):
    """
    Send SMS via HTTP API with fake DLR interception.
    
    This endpoint mimics Jasmin's HTTP API but intercepts messages
    for users with fake_dlr_percentage configured.
    """
    # Get parameters from GET or POST
    if request.method == 'POST':
        params = request.POST
    else:
        params = request.GET
    
    username = params.get('username')
    password = params.get('password')
    src_addr = params.get('from')
    dst_addr = params.get('to')
    text = params.get('content', '')
    
    # Validate required parameters
    if not all([username, password, src_addr, dst_addr]):
        return HttpResponse('Error "Missing required parameters"', content_type='text/plain', status=400)
    
    # Check for fake DLR interception BEFORE sending to Jasmin
    intercepted, fake_msgid = fake_dlr_send(src_addr, dst_addr, text, username)
    if intercepted:
        # Message intercepted for fake DLR - return success without sending to Jasmin
        logger.info(f"HTTP API FAKE DLR: username={username} dst={dst_addr} msgid={fake_msgid}")
        return HttpResponse(f'Success "{fake_msgid}"', content_type='text/plain')
    
    # Not intercepted - forward to Jasmin HTTP API
    try:
        # Build Jasmin API URL
        jasmin_url = f"{settings.HTTP_HOST}:{settings.HTTP_PORT}/send"
        
        # Forward all parameters to Jasmin
        forward_params = {
            'username': username,
            'password': password,
            'from': src_addr,
            'to': dst_addr,
            'content': text,
        }
        
        # Forward optional parameters
        if params.get('coding'):
            forward_params['coding'] = params.get('coding')
        if params.get('validity-period'):
            forward_params['validity-period'] = params.get('validity-period')
        
        encoded_params = urllib.parse.urlencode(forward_params)
        url = f"{jasmin_url}?{encoded_params}"
        
        # Make request to Jasmin
        req = urllib.request.urlopen(url, timeout=30)
        body = req.read().decode('utf-8')
        
        return HttpResponse(body, content_type='text/plain', status=req.getcode())
        
    except urllib.error.HTTPError as e:
        error_body = e.read().decode('utf-8')
        logger.error(f"HTTP Error {e.code}: {error_body}")
        return HttpResponse(error_body, content_type='text/plain', status=e.code)
    except urllib.error.URLError as e:
        logger.error(f"URL Error: {e.reason}")
        return HttpResponse(f'Error "Connection failed: {e.reason}"', content_type='text/plain', status=400)
    except Exception as e:
        logger.error(f"HTTP Send Error: {e}")
        return HttpResponse(f'Error "{e}"', content_type='text/plain', status=400)
