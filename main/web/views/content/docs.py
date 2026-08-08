from django.shortcuts import render
from django.contrib.auth.decorators import login_required


@login_required
def docs_view(request):
    """Static, self-contained user guide for the web panel.

    Pure template render — no Jasmin/telnet calls, no AJAX endpoint. The page
    explains how the pieces (connectors, users, groups, filters, routes) fit
    together and the common end-to-end workflows (send a single SMS, send a
    bulk campaign, read the logs)."""
    return render(request, "web/content/docs.html")
