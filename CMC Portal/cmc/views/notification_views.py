from datetime import date
from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.views.decorators.http import require_POST
from tpm.models import Department
from cmc.models import SAPNotification
from portal.utils.decorators import module_access_required

@login_required
@module_access_required('CMC')
def tracker(request, dept_id):
    department = get_object_or_404(Department, id=dept_id)
    notifications = SAPNotification.objects.filter(equipment__department=department)
    
    open_notifs = notifications.filter(status=SAPNotification.NotifStatus.OPEN).order_by('raised_date')
    closed_notifs = notifications.filter(status=SAPNotification.NotifStatus.CLOSED).order_by('-closed_date')
    
    # Calculate days open for open notifications
    open_notif_data = []
    for notif in open_notifs:
        days_open = (date.today() - notif.raised_date).days
        
        # Color coding severity based on days open
        if days_open > 30:
            severity = 'danger'
        elif days_open > 15:
            severity = 'warning'
        else:
            severity = 'success'
            
        open_notif_data.append({
            'notif': notif,
            'days_open': days_open,
            'severity': severity
        })
        
    context = {
        'department': department,
        'open_notifs': open_notif_data,
        'closed_notifs': closed_notifs,
        'active_tab': 'notif',
    }
    return render(request, 'cmc/notifications/tracker.html', context)


@login_required
@module_access_required('CMC')
@require_POST
def close_notif(request, dept_id, notif_id):
    department = get_object_or_404(Department, id=dept_id)
    notif = get_object_or_404(SAPNotification, id=notif_id, equipment__department=department)
    
    action_taken = request.POST.get('action_taken', '').strip()
    
    notif.status = SAPNotification.NotifStatus.CLOSED
    notif.closed_date = date.today()
    notif.action_taken = action_taken
    notif.save()
    
    return redirect('cmc:notification_tracker', dept_id=department.id)
