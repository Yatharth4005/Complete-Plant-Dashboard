import json
from datetime import date
from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from tpm.models import Department
from cmc.models import Equipment, WDALog, SAPNotification
from cmc.forms.wda_forms import WDALogForm
from portal.utils.decorators import module_access_required

@login_required
@module_access_required('CMC')
def log_list(request, dept_id):
    department = get_object_or_404(Department, id=dept_id)
    logs = WDALog.objects.filter(equipment__department=department).order_by('-date')
    
    search_q = request.GET.get('q', '').strip()
    status_filter = request.GET.get('status', '').strip()
    
    if search_q:
        logs = logs.filter(equipment__name__icontains=search_q)
    if status_filter:
        logs = logs.filter(final_status=status_filter)
        
    context = {
        'department': department,
        'logs': logs,
        'search_q': search_q,
        'status_filter': status_filter,
        'active_tab': 'wda',
    }
    return render(request, 'cmc/wda/log_list.html', context)


@login_required
@module_access_required('CMC')
def log_entry(request, dept_id):
    department = get_object_or_404(Department, id=dept_id)
    
    if request.method == 'POST':
        form = WDALogForm(request.POST)
        if form.is_valid():
            log = form.save(commit=False)
            log.entered_by = request.user
            log.save()
            
            # If final status is NOT OK, propagate to SAP notifications tracker
            if log.final_status in (WDALog.WDAStatus.NOT_OK, WDALog.WDAStatus.NEED_ATTENTION):
                SAPNotification.objects.get_or_create(
                    notification_no=log.notification_no or f"WDA-{log.id}",
                    equipment=log.equipment,
                    defaults={
                        'raised_by': log.sent_login or request.user.username[:10],
                        'raised_date': log.sent_date or date.today(),
                        'description': f"WDA abnormal readings (WPC: {log.wpc}) on {log.date}: {log.remarks}",
                        'status': SAPNotification.NotifStatus.OPEN,
                        'wda_log': log
                    }
                )
                
            return redirect('cmc:wda_list', dept_id=department.id)
    else:
        form = WDALogForm(initial={'date': date.today()})
        
    context = {
        'department': department,
        'form': form,
        'active_tab': 'wda',
    }
    return render(request, 'cmc/wda/log_entry.html', context)


@login_required
@module_access_required('CMC')
def analytics(request, dept_id):
    department = get_object_or_404(Department, id=dept_id)
    equipments = Equipment.objects.filter(department=department, is_active=True)
    
    selected_equip_id = request.GET.get('equipment_id')
    selected_equip = None
    if selected_equip_id:
        selected_equip = equipments.filter(id=selected_equip_id).first()
    if not selected_equip and equipments.exists():
        selected_equip = equipments.first()
        
    chart_dates = []
    wpc_trend = []
    dl_trend = []
    ds_trend = []
    
    if selected_equip:
        # Fetch last 12 tests
        logs = WDALog.objects.filter(equipment=selected_equip).order_by('date')[:12]
        chart_dates = [log.date.strftime('%d %b') for log in logs]
        wpc_trend = [log.wpc for log in logs]
        dl_trend = [log.dl for log in logs]
        ds_trend = [log.ds for log in logs]
        
    # Pie chart distribution for final status
    total_wda = WDALog.objects.filter(equipment__department=department)
    ok_count = total_wda.filter(final_status=WDALog.WDAStatus.OK).count()
    attention_count = total_wda.filter(final_status=WDALog.WDAStatus.NEED_ATTENTION).count()
    not_ok_count = total_wda.filter(final_status=WDALog.WDAStatus.NOT_OK).count()

    context = {
        'department': department,
        'equipments': equipments,
        'selected_equip': selected_equip,
        'chart_dates_json': json.dumps(chart_dates),
        'wpc_trend_json': json.dumps(wpc_trend),
        'dl_trend_json': json.dumps(dl_trend),
        'ds_trend_json': json.dumps(ds_trend),
        'ok_count': ok_count,
        'attention_count': attention_count,
        'not_ok_count': not_ok_count,
        'active_tab': 'wda',
    }
    return render(request, 'cmc/wda/analytics.html', context)
