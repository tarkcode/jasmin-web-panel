"""
Jasmin MT Interceptor: fake_dlr_interceptor.py

NOTE: This interceptor approach requires Jasmin's interceptord service to be running.
See the alternative approach in main/web/helpers.py:fake_dlr_send() which intercepts
at the Django submission layer before messages reach Jasmin.

This file is kept for reference and can be used if you want to configure
Jasmin's interceptor service. See Jasmin documentation for setup:

1. Start jasmin-interceptord service inside the Jasmin container
2. Enable interceptor-client in jasmind startup with --enable-interceptor-client
3. Configure MT interceptor via jCli: mtinterceptor -a

Author: Jasmin Web Panel
"""

# This file is a placeholder for the Jasmin interceptor approach.
# The actual implementation is in main/web/helpers.py using fake_dlr_send()
# which intercepts messages at the Django layer BEFORE they reach Jasmin.
pass
