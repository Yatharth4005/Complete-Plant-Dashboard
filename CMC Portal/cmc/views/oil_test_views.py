import json
from datetime import date
from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from tpm.models import Department
from cmc.models import Equipment, OilTestLog, SAPNotification
from cmc.forms.oil_test_forms import OilTestLogForm
from portal.utils.decorators import module_access_required

@login_required
@module_access_required('CMC')
def log_list(request, dept_id):
    department = get_object_or_404(Department, id=dept_id)
    logs = OilTestLog.objects.filter(equipment__department=department).order_by('-date')
    
    search_q = request.GET.get('q', '').strip()
    status_filter = request.GET.get('status', '').strip()
    
    if search_q:
        logs = logs.filter(equipment__name__icontains=search_q)
    if status_filter:
        logs = logs.filter(status=status_filter)
        
    context = {
        'department': department,
        'logs': logs,
        'search_q': search_q,
        'status_filter': status_filter,
        'active_tab': 'oil',
    }
    return render(request, 'cmc/oil_test/log_list.html', context)


@login_required
@module_access_required('CMC')
def log_entry(request, dept_id):
    department = get_object_or_404(Department, id=dept_id)
    
    if request.method == 'POST':
        form = OilTestLogForm(request.POST)
        if form.is_valid():
            log = form.save(commit=False)
            log.entered_by = request.user
            log.save()
            
            # If status is NOT OK, propagate to SAP notifications tracker
            if log.status == OilTestLog.OilStatus.NOT_OK:
                SAPNotification.objects.get_or_create(
                    notification_no=log.notification_no or f"OIL-{log.id}",
                    equipment=log.equipment,
                    defaults={
                        'raised_by': log.login_by or request.user.username[:10],
                        'raised_date': log.sent_date or date.today(),
                        'description': f"Oil Test abnormal viscosity/moisture on {log.date}: {log.remarks}",
                        'status': SAPNotification.NotifStatus.OPEN,
                        'oil_test': log
                    }
                )
                
            return redirect('cmc:oil_list', dept_id=department.id)
    else:
        form = OilTestLogForm(initial={'date': date.today()})
        
    context = {
        'department': department,
        'form': form,
        'active_tab': 'oil',
    }
    return render(request, 'cmc/oil_test/log_entry.html', context)


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
    viscosity_trend = []
    
    if selected_equip:
        # Fetch last 12 tests
        logs = OilTestLog.objects.filter(equipment=selected_equip).order_by('date')[:12]
        chart_dates = [log.date.strftime('%d %b') for log in logs]
        viscosity_trend = [log.viscosity for log in logs]
        
    # Pie chart distribution for OK vs NOT OK
    total_tests = OilTestLog.objects.filter(equipment__department=department)
    ok_count = total_tests.filter(status=OilTestLog.OilStatus.OK).count()
    not_ok_count = total_tests.filter(status=OilTestLog.OilStatus.NOT_OK).count()

    context = {
        'department': department,
        'equipments': equipments,
        'selected_equip': selected_equip,
        'chart_dates_json': json.dumps(chart_dates),
        'viscosity_trend_json': json.dumps(viscosity_trend),
        'ok_count': ok_count,
        'not_ok_count': not_ok_count,
        'active_tab': 'oil',
    }
    return render(request, 'cmc/oil_test/analytics.html', context)
