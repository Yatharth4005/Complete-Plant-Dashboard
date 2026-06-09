import json
from datetime import date
from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse, HttpResponse
from django.db.models import Max
from tpm.models import Department
from cmc.models import Equipment, EquipmentBearingPoint, VibrationLog, VibrationReading, PMScheduleEntry
from cmc.forms.vibration_forms import VibrationLogForm
from portal.utils.decorators import module_access_required

@login_required
@module_access_required('CMC')
def log_list(request, dept_id):
    department = get_object_or_404(Department, id=dept_id)
    logs = VibrationLog.objects.filter(equipment__department=department).order_by('-date')
    
    # Filter parameters
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
        'active_tab': 'vibration',
    }
    return render(request, 'cmc/vibration/log_list.html', context)


@login_required
@module_access_required('CMC')
def log_entry(request, dept_id):
    department = get_object_or_404(Department, id=dept_id)
    
    if request.method == 'POST':
        form = VibrationLogForm(request.POST)
        if form.is_valid():
            log = form.save(commit=False)
            log.entered_by = request.user
            
            # Link to PM schedule if exists for this day/equipment
            sched_entry = PMScheduleEntry.objects.filter(
                equipment=log.equipment,
                scheduled_date=log.date,
            ).first()
            if sched_entry:
                log.schedule_entry = sched_entry
                sched_entry.status = PMScheduleEntry.VisitStatus.DONE
                sched_entry.actual_date = log.date
                sched_entry.done_by = request.user
                sched_entry.save()
                
            log.save()
            
            # Save bearing readings
            bearing_ids = request.POST.getlist('bearing_point_id')
            labels = request.POST.getlist('bearing_label')
            numbers = request.POST.getlist('bearing_no')
            h_readings = request.POST.getlist('horizontal_r1')
            v_readings = request.POST.getlist('vertical_r2')
            a_readings = request.POST.getlist('axial')
            
            for idx in range(len(labels)):
                lbl = labels[idx].strip()
                if not lbl:
                    continue
                    
                b_id = bearing_ids[idx] if idx < len(bearing_ids) else None
                bp = None
                if b_id and not b_id.startswith('new_'):
                    try:
                        bp = EquipmentBearingPoint.objects.get(id=b_id)
                    except EquipmentBearingPoint.DoesNotExist:
                        pass
                
                h_val = float(h_readings[idx]) if idx < len(h_readings) and h_readings[idx] else None
                v_val = float(v_readings[idx]) if idx < len(v_readings) and v_readings[idx] else None
                a_val = float(a_readings[idx]) if idx < len(a_readings) and a_readings[idx] else None
                
                VibrationReading.objects.create(
                    vibration_log=log,
                    bearing_point=bp,
                    bearing_label=lbl,
                    bearing_no=numbers[idx] if idx < len(numbers) else '',
                    horizontal_r1=h_val,
                    vertical_r2=v_val,
                    axial=a_val,
                )
                
            # If status is NOT OK, trigger warning notification stub or save it
            if log.status == VibrationLog.VibrationStatus.NOT_OK:
                from cmc.models import SAPNotification
                SAPNotification.objects.get_or_create(
                    notification_no=f"VIB-{log.id}",
                    equipment=log.equipment,
                    defaults={
                        'raised_by': request.user.username[:10],
                        'raised_date': date.today(),
                        'description': f"Vibration abnormal findings on {log.date}: {log.remarks}",
                        'status': SAPNotification.NotifStatus.OPEN,
                        'vibration_log': log
                    }
                )
            
            return redirect('cmc:vibration_list', dept_id=department.id)
    else:
        form = VibrationLogForm(initial={'date': date.today()})
        
    context = {
        'department': department,
        'form': form,
        'active_tab': 'vibration',
    }
    return render(request, 'cmc/vibration/log_entry.html', context)


@login_required
@module_access_required('CMC')
def log_detail(request, dept_id, log_id):
    department = get_object_or_404(Department, id=dept_id)
    log = get_object_or_404(VibrationLog, id=log_id, equipment__department=department)
    readings = log.readings.all()
    
    context = {
        'department': department,
        'log': log,
        'readings': readings,
        'active_tab': 'vibration',
    }
    return render(request, 'cmc/vibration/log_detail.html', context)


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
    bearing_trends = {}
    
    if selected_equip:
        # Fetch last 12 readings for selected equipment
        logs = VibrationLog.objects.filter(equipment=selected_equip).order_by('date')[:12]
        chart_dates = [log.date.strftime('%d %b') for log in logs]
        
        # Structure bearing data trends
        for log in logs:
            for rd in log.readings.all():
                if rd.bearing_label not in bearing_trends:
                    bearing_trends[rd.bearing_label] = {
                        'horizontal': [],
                        'vertical': [],
                        'axial': []
                    }
                bearing_trends[rd.bearing_label]['horizontal'].append(rd.horizontal_r1)
                bearing_trends[rd.bearing_label]['vertical'].append(rd.vertical_r2)
                bearing_trends[rd.bearing_label]['axial'].append(rd.axial)

    context = {
        'department': department,
        'equipments': equipments,
        'selected_equip': selected_equip,
        'chart_dates_json': json.dumps(chart_dates),
        'bearing_trends_json': json.dumps(bearing_trends),
        'active_tab': 'vibration',
    }
    return render(request, 'cmc/vibration/analytics.html', context)


@login_required
@module_access_required('CMC')
def get_bearing_points(request):
    equipment_id = request.GET.get('equipment_id')
    if not equipment_id:
        return JsonResponse({'bearing_points': []})
        
    bp_list = EquipmentBearingPoint.objects.filter(equipment_id=equipment_id)
    data = []
    for bp in bp_list:
        data.append({
            'id': bp.id,
            'label': bp.label,
            'bearing_no': bp.bearing_no,
            'horizontal_r1': '',
            'vertical_r2': '',
            'axial': '',
        })
    return JsonResponse({'bearing_points': data})
