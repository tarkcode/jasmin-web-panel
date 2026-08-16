from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from django.db.models import Count, Q
from django.utils import timezone

from main.core.smpp import Users
from main.core.models import SubmitLog, RouteAssignment, UsersModel, Wallet

# submit_log statuses are mutually exclusive per row (updated in place by DLRs)
_FAILED = ['UNDELIV', 'EXPIRED', 'REJECTD', 'ESME_RDELIVERYFAILURE']


def _agg(qs):
    return qs.aggregate(
        total=Count('id'),
        delivered=Count('id', filter=Q(status='DELIVRD')),
        failed=Count('id', filter=Q(status__in=_FAILED)),
        pending=Count('id', filter=Q(status='ESME_ROK')),
        rejected=Count('id', filter=Q(status__startswith='ESME_R') & ~Q(status__in=['ESME_ROK', 'ESME_RDELIVERYFAILURE'])),
    )


@login_required
def user_profile_view(request, uid):
    u = Users().get_user(uid, silent=True)
    info = None
    if u:
        quota = ((u.get('mt_messaging_cred') or {}).get('quota') or {})
        info = {
            'uid': u.get('uid', uid),
            'gid': u.get('gid', ''),
            'username': u.get('username', ''),
            'status': u.get('status', ''),
            'balance': quota.get('balance', 'ND'),
            'smpps_throughput': quota.get('smpps_throughput', 'ND'),
            'http_throughput': quota.get('http_throughput', 'ND'),
        }

    base = SubmitLog.objects.filter(uid=uid)
    now = timezone.localtime()
    today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
    month_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    stats = {
        'all': _agg(base),
        'today': _agg(base.filter(created_at__gte=today_start)),
        'month': _agg(base.filter(created_at__gte=month_start)),
    }
    for period in stats.values():
        t = period.get('total') or 0
        period['delivery_rate'] = round((period.get('delivered') or 0) / t * 100, 1) if t else 0.0

    last_activity = base.order_by('-created_at').values_list('created_at', flat=True).first()
    mirror = UsersModel.objects.filter(uid=uid).first()
    assignments = [a.get_dict() for a in RouteAssignment.objects.filter(uid=uid).select_related('route')]
    connectors = sorted({a['connector'] for a in assignments if a.get('connector')})
    wallet = Wallet.objects.filter(uid=uid).first()

    context = {
        'uid': uid,
        'info': info,
        'not_found': u is None,
        'stats': stats,
        'last_activity': last_activity,
        'created': mirror.created if mirror else None,
        'assignments': assignments,
        'connectors': connectors,
        'wallet_exists': wallet is not None,
    }
    return render(request, 'web/content/user_profile.html', context)
