from django.shortcuts import render
from django.http import JsonResponse
from django.contrib.auth.decorators import login_required
from django.conf import settings
from django.db.models import Count, Q
from django.db.models.functions import TruncDate, TruncWeek, TruncMonth, TruncYear
from datetime import datetime, timedelta
import json

from main.core.utils import get_client_ip, is_online
from main.core.tools import require_get_ajax
from main.core.models import SubmitLog


@login_required
def dashboard_view(request):
    ip_address = get_client_ip(request)

    # Get submit log statistics
    submit_stats = SubmitLog.objects.aggregate(
        total=Count('id'),
        success=Count('id', filter=Q(status__in=['ESME_ROK', 'ESME_RINVNUMDESTS'])),
        failed=Count('id', filter=Q(status='ESME_RDELIVERYFAILURE')),
        unknown=Count('id', filter=~Q(status__in=['ESME_ROK', 'ESME_RINVNUMDESTS', 'ESME_RDELIVERYFAILURE']))
    )

    # Get last 30 days data for initial timeline chart (daily)
    end_date = datetime.now()
    start_date = end_date - timedelta(days=30)

    daily_data = SubmitLog.objects.filter(
        created_at__gte=start_date,
        created_at__lte=end_date
    ).annotate(
        date=TruncDate('created_at')
    ).values('date').annotate(
        success=Count('id', filter=Q(status__in=['ESME_ROK', 'ESME_RINVNUMDESTS'])),
        failed=Count('id', filter=Q(status='ESME_RDELIVERYFAILURE'))
    ).order_by('date')

    # Format data for Chart.js
    timeline_labels = []
    timeline_success = []
    timeline_failed = []

    for entry in daily_data:
        timeline_labels.append(entry['date'].strftime('%Y-%m-%d'))
        timeline_success.append(entry['success'])
        timeline_failed.append(entry['failed'])

    context = {
        'ip_address': ip_address,
        'submit_stats': submit_stats,
        'timeline_labels': json.dumps(timeline_labels),
        'timeline_success': json.dumps(timeline_success),
        'timeline_failed': json.dumps(timeline_failed),
    }

    return render(request, "web/dashboard.html", context)


@require_get_ajax
def global_manage(request):
    response = {}
    s = request.GET.get("s")
    if s == "gw_state":
        # CHECK GATEWAY BINDING OK
        response["status"], response["message"] = is_online(
            host=settings.TELNET_HOST, port=settings.TELNET_PORT)
    elif s == "submit_log_timeline":
        # Get timeline data based on grouping
        grouping = request.GET.get('grouping', 'daily')

        # Determine date range based on grouping
        end_date = datetime.now()
        if grouping == 'daily':
            start_date = end_date - timedelta(days=30)
            trunc_func = TruncDate
            date_format = '%Y-%m-%d'
        elif grouping == 'weekly':
            start_date = end_date - timedelta(weeks=12)
            trunc_func = TruncWeek
            date_format = '%Y-W%W'
        elif grouping == 'monthly':
            start_date = end_date - timedelta(days=365)
            trunc_func = TruncMonth
            date_format = '%Y-%m'
        else:  # yearly
            start_date = end_date - timedelta(days=365*3)
            trunc_func = TruncYear
            date_format = '%Y'

        data = SubmitLog.objects.filter(
            created_at__gte=start_date,
            created_at__lte=end_date
        ).annotate(
            period=trunc_func('created_at')
        ).values('period').annotate(
            success=Count('id', filter=Q(status__in=['ESME_ROK', 'ESME_RINVNUMDESTS'])),
            failed=Count('id', filter=Q(status='ESME_RDELIVERYFAILURE'))
        ).order_by('period')

        labels = []
        success_data = []
        failed_data = []

        for entry in data:
            if entry['period']:
                labels.append(entry['period'].strftime(date_format))
                success_data.append(entry['success'])
                failed_data.append(entry['failed'])

        response['labels'] = labels
        response['success'] = success_data
        response['failed'] = failed_data
        response['status'] = 'success'

    elif s == "business_overview":
        from django.utils import timezone
        from main.core.smpp import SMPPCCM, Users
        from main.core.models import RouteDetail, RouteAssignment

        # Connectors: bound (both sides up) vs not
        active = down = 0
        try:
            for c in SMPPCCM().list().get("connectors", []):
                if c.get("status") == "started" and str(c.get("session", "")).startswith("BOUND"):
                    active += 1
                else:
                    down += 1
        except Exception:
            pass
        try:
            users_count = len(Users().list().get("users", []))
        except Exception:
            users_count = 0

        # Today's traffic
        now = timezone.localtime()
        start = now.replace(hour=0, minute=0, second=0, microsecond=0)
        todays = SubmitLog.objects.filter(created_at__gte=start)
        total_today = todays.count()
        ok_statuses = ['ESME_ROK', 'ESME_RINVNUMDESTS', 'DELIVRD']
        delivered_today = todays.filter(status__in=ok_statuses).count()
        delivered_pct = round(delivered_today / total_today * 100, 1) if total_today else 0.0

        # Revenue / cost / margin today = today's messages x configured prices
        buy = {rd.smpp_connector: float(rd.buy_price) for rd in RouteDetail.objects.filter(status='active')}
        sell = {}
        currency = "USD"
        for a in RouteAssignment.objects.filter(status='active').select_related('route'):
            sell[(a.uid, a.route.smpp_connector)] = float(a.sell_price)
            if a.route.currency:
                currency = a.route.currency
        cost = revenue = 0.0
        for row in todays.values('uid', 'routed_cid').annotate(n=Count('id')):
            n, uid, cid = row['n'], row['uid'], row['routed_cid']
            if cid in buy:
                cost += n * buy[cid]
            if (uid, cid) in sell:
                revenue += n * sell[(uid, cid)]
        margin = revenue - cost
        margin_pct = round(margin / cost * 100, 1) if cost else None

        response.update({
            "connections_active": active,
            "connections_down": down,
            "users_count": users_count,
            "messages_today": total_today,
            "delivered_pct": delivered_pct,
            "routes_count": RouteDetail.objects.count(),
            "assignments_count": RouteAssignment.objects.count(),
            "cost_today": round(cost, 4),
            "revenue_today": round(revenue, 4),
            "margin_today": round(margin, 4),
            "margin_pct": margin_pct,
            "currency": currency,
            "status": "success",
        })

    return JsonResponse(response, status=200)
