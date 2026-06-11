import json
import os
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import HttpResponse, JsonResponse
from django.db import models
from django.db.models import Q, Sum, Avg
from django.utils import timezone
from tpm.models import Department
from delays.models import DelayUpload, DelayRecord
from delays.forms import DelayRecordForm
from delays.utils.parser import parse_excel_file
from portal.utils.access import user_can_access_module, user_can_edit_module

@login_required
def dept_overview(request, dept_id):
    """
    Main overview and dashboard for department delays.
    Displays metrics, charts, upload features, and logs tables.
    """
    department = get_object_or_404(Department, id=dept_id)
    
    # Check SSO Access
    if not user_can_access_module(request.user, department, 'Delays'):
        messages.error(request, "You do not have permission to access the Delays module.")
        return redirect('portal:dept_hub', dept_id=dept_id)
        
    can_edit = user_can_edit_module(request.user, department, 'Delays')
    
    # Active departments for switching
    departments = Department.objects.all().order_by('name')
    
    # Fetch all records
    records = DelayRecord.objects.filter(department=department)
    
    # Metrics
    total_mins = records.aggregate(Sum('duration_mins'))['duration_mins__sum'] or 0.0
    total_hrs = total_mins / 60.0
    total_events = records.count()
    
    # Top agency
    agency_breakdown = records.values('agency').annotate(total=Sum('duration_mins')).order_by('-total')
    top_agency = agency_breakdown[0]['agency'] if agency_breakdown else "N/A"
    top_agency_mins = agency_breakdown[0]['total'] if agency_breakdown else 0.0
    
    avg_duration = records.aggregate(Avg('duration_mins'))['duration_mins__avg'] or 0.0
    
    # Chart 1: Agency Distribution (Top 8)
    agency_labels = [x['agency'] for x in agency_breakdown[:8]]
    agency_data = [round(x['total'], 1) for x in agency_breakdown[:8]]
    
    # Chart 2: Daily Trend (Last 30 active days)
    daily_breakdown = list(records.values('date').annotate(total=Sum('duration_mins')).order_by('date'))
    daily_labels = [x['date'].strftime('%d-%b-%Y') for x in daily_breakdown[-30:]]
    daily_data = [round(x['total'], 1) for x in daily_breakdown[-30:]]
    
    # Chart 3: Top bottleneck equipment
    equip_breakdown = records.exclude(
        Q(equipment__isnull=True) | Q(equipment='') | Q(equipment='-') | Q(equipment='NA')
    ).values('equipment').annotate(total=Sum('duration_mins')).order_by('-total')[:5]
    
    equip_labels = [x['equipment'] for x in equip_breakdown]
    equip_data = [round(x['total'], 1) for x in equip_breakdown]
    
    # List of sheets parsed
    sheets_parsed = list(records.order_by('sheet_name').values_list('sheet_name', flat=True).distinct())
    
    # Upload history
    uploads = DelayUpload.objects.filter(department=department).order_by('-uploaded_at')
    
    # Form autocompletes
    agencies = list(records.order_by('agency').values_list('agency', flat=True).distinct().exclude(agency=''))
    sub_agencies = list(records.order_by('sub_agency').values_list('sub_agency', flat=True).distinct().exclude(sub_agency=''))
    sections = list(records.order_by('section').values_list('section', flat=True).distinct().exclude(section=''))
    equipments = list(records.order_by('equipment').values_list('equipment', flat=True).distinct().exclude(equipment=''))
    incharges = list(records.order_by('shift_incharge').values_list('shift_incharge', flat=True).distinct().exclude(shift_incharge=''))

    # Pareto Calculation by Agency
    agency_pareto = []
    running_mins = 0
    for idx, ab in enumerate(agency_breakdown):
        running_mins += ab['total']
        cum_percent = (running_mins / total_mins * 100) if total_mins > 0 else 0.0
        agency_pareto.append({
            'agency': ab['agency'] or "N/A",
            'mins': round(ab['total'], 1),
            'percent': round((ab['total'] / total_mins * 100) if total_mins > 0 else 0.0, 1),
            'cum_percent': round(cum_percent, 1),
            'rank': idx + 1,
            'is_vital': cum_percent <= 85.0 or idx == 0
        })

    # Pareto Calculation by Equipment
    all_equip_breakdown = records.exclude(
        Q(equipment__isnull=True) | Q(equipment='') | Q(equipment='-') | Q(equipment='NA')
    ).values('equipment').annotate(total=Sum('duration_mins')).order_by('-total')
    
    total_equip_mins = sum(x['total'] for x in all_equip_breakdown)
    equip_pareto = []
    running_equip_mins = 0
    for idx, eb in enumerate(all_equip_breakdown):
        running_equip_mins += eb['total']
        cum_percent = (running_equip_mins / total_equip_mins * 100) if total_equip_mins > 0 else 0.0
        equip_pareto.append({
            'equipment': eb['equipment'] or "N/A",
            'mins': round(eb['total'], 1),
            'percent': round((eb['total'] / total_equip_mins * 100) if total_equip_mins > 0 else 0.0, 1),
            'cum_percent': round(cum_percent, 1),
            'rank': idx + 1,
            'is_vital': cum_percent <= 85.0 or idx == 0
        })

    # Mitigation recommendations & keyword frequency
    keyword_counts = {
        'Motor / Drive Issues': 0,
        'Sensor / Electrical Faults': 0,
        'Bearing Overheating/Wear': 0,
        'Belt Tear / Slip': 0,
        'Hydraulic / Oil Leaks': 0,
        'Mechanical Coupling / Gearbox': 0,
        'Process Operations / Crane Delay': 0
    }
    
    keywords_map = {
        'motor': 'Motor / Drive Issues',
        'drive': 'Motor / Drive Issues',
        'trip': 'Motor / Drive Issues',
        'sensor': 'Sensor / Electrical Faults',
        'limit': 'Sensor / Electrical Faults',
        'proximity': 'Sensor / Electrical Faults',
        'cable': 'Sensor / Electrical Faults',
        'electrical': 'Sensor / Electrical Faults',
        'bearing': 'Bearing Overheating/Wear',
        'grease': 'Bearing Overheating/Wear',
        'vibration': 'Bearing Overheating/Wear',
        'belt': 'Belt Tear / Slip',
        'conveyor': 'Belt Tear / Slip',
        'hydraulic': 'Hydraulic / Oil Leaks',
        'leak': 'Hydraulic / Oil Leaks',
        'oil': 'Hydraulic / Oil Leaks',
        'seal': 'Hydraulic / Oil Leaks',
        'coupling': 'Mechanical Coupling / Gearbox',
        'gear': 'Mechanical Coupling / Gearbox',
        'gearbox': 'Mechanical Coupling / Gearbox',
        'spindle': 'Mechanical Coupling / Gearbox',
        'crane': 'Process Operations / Crane Delay',
        'guide': 'Process Operations / Crane Delay',
        'roll': 'Process Operations / Crane Delay',
        'operations': 'Process Operations / Crane Delay',
    }
    
    for r in records:
        desc = (r.description or '').lower()
        why = (r.why or '').lower()
        matched = set()
        for kw, category in keywords_map.items():
            if kw in desc or kw in why:
                matched.add(category)
        for category in matched:
            keyword_counts[category] += 1
            
    sorted_keywords = []
    for cat, count in keyword_counts.items():
        percent = (count / total_events * 100) if total_events > 0 else 0.0
        sorted_keywords.append({
            'category': cat,
            'count': count,
            'percent': round(percent, 1)
        })
    sorted_keywords.sort(key=lambda x: x['count'], reverse=True)

    # HTMX request for tabular logs partial
    if request.headers.get('HX-Request') and 'records-tab' in request.GET:
        # Return log table partial
        return render(request, 'delays/partials/_records_table.html', {
            'records': records[:100],
            'department': department,
            'can_edit': can_edit,
            'agencies': agencies,
            'equipments': equipments,
        })

    context = {
        'department': department,
        'departments': departments,
        'can_edit': can_edit,
        'total_mins': round(total_mins, 1),
        'total_hrs': round(total_hrs, 1),
        'total_events': total_events,
        'top_agency': top_agency,
        'top_agency_mins': round(top_agency_mins, 1),
        'avg_duration': round(avg_duration, 1),
        
        # Charts (serialize to JSON safely)
        'agency_labels_json': json.dumps(agency_labels),
        'agency_data_json': json.dumps(agency_data),
        'daily_labels_json': json.dumps(daily_labels),
        'daily_data_json': json.dumps(daily_data),
        'equip_labels_json': json.dumps(equip_labels),
        'equip_data_json': json.dumps(equip_data),
        
        # Pareto JSONs
        'pareto_labels_json': json.dumps([x['agency'] for x in agency_pareto]),
        'pareto_mins_json': json.dumps([x['mins'] for x in agency_pareto]),
        'pareto_cum_json': json.dumps([x['cum_percent'] for x in agency_pareto]),
        
        # Lists
        'records': records[:100], # Limit initially
        'sheets_parsed': sheets_parsed,
        'uploads': uploads,
        
        # Pareto Context Lists
        'agency_pareto': agency_pareto,
        'equip_pareto': equip_pareto[:10], # Top 10 for display
        
        # Mitigation
        'mitigation_categories': sorted_keywords,
        'top_mitigation_category': sorted_keywords[0]['category'] if sorted_keywords and sorted_keywords[0]['count'] > 0 else "N/A",
        
        # Autocomplete
        'agencies': agencies,
        'sub_agencies': sub_agencies,
        'sections': sections,
        'equipments': equipments,
        'incharges': incharges,
        
        # Sidebar/Layout settings
        'active_dept_id': department.id,
        'active_module': 'Delays',
        'active_section': 'department_module',
    }
    return render(request, 'delays/dashboard.html', context)


@login_required
def upload_file(request, dept_id):
    """
    POST view to upload delay reports and trigger parsing.
    """
    department = get_object_or_404(Department, id=dept_id)
    
    # Check access
    if not user_can_edit_module(request.user, department, 'Delays'):
        messages.error(request, "You do not have editing access to upload files.")
        return redirect('delays:dept_overview', dept_id=dept_id)
        
    if request.method == 'POST' and request.FILES.get('delay_file'):
        excel_file = request.FILES['delay_file']
        
        # Create upload registry
        upload = DelayUpload.objects.create(
            department=department,
            file=excel_file,
            filename=excel_file.name,
            uploaded_by=request.user,
            status='FAILED' # Default until parsed
        )
        
        try:
            success = parse_excel_file(upload)
            if success:
                messages.success(request, f"File successfully uploaded! {upload.error_message}")
            else:
                messages.error(request, f"Upload parsing failed: {upload.error_message}")
        except Exception as e:
            messages.error(request, f"System error occurred during parsing: {str(e)}")
            
    return redirect('delays:dept_overview', dept_id=dept_id)


@login_required
def delete_upload(request, dept_id, upload_id):
    """
    Deletes an uploaded file registry along with all parsed records.
    """
    department = get_object_or_404(Department, id=dept_id)
    
    if not user_can_edit_module(request.user, department, 'Delays'):
        messages.error(request, "You do not have permission to delete uploads.")
        return redirect('delays:dept_overview', dept_id=dept_id)
        
    upload = get_object_or_404(DelayUpload, id=upload_id, department=department)
    filename = upload.filename
    
    # Delete file path if exists
    if upload.file and os.path.exists(upload.file.path):
        try:
            os.remove(upload.file.path)
        except Exception:
            pass
            
    upload.delete() # Cascade deletes associated DelayRecords
    messages.success(request, f"Downtime logs and upload registry for '{filename}' deleted successfully.")
    return redirect('delays:dept_overview', dept_id=dept_id)


@login_required
def records_table(request, dept_id):
    """
    Search and filter endpoint for the delay logs table.
    """
    department = get_object_or_404(Department, id=dept_id)
    can_edit = user_can_edit_module(request.user, department, 'Delays')
    
    query = request.GET.get('q', '').strip()
    agency_filter = request.GET.get('agency', '').strip()
    sheet_filter = request.GET.get('sheet', '').strip()
    date_start = request.GET.get('date_start', '').strip()
    date_end = request.GET.get('date_end', '').strip()
    
    records = DelayRecord.objects.filter(department=department)
    
    if query:
        records = records.filter(
            Q(description__icontains=query) |
            Q(equipment__icontains=query) |
            Q(sub_equipment__icontains=query) |
            Q(shift_incharge__icontains=query) |
            Q(why__icontains=query)
        )
        
    if agency_filter:
        records = records.filter(agency=agency_filter)
        
    if sheet_filter:
        records = records.filter(sheet_name=sheet_filter)
        
    if date_start:
        records = records.filter(date__gte=date_start)
        
    if date_end:
        records = records.filter(date__lte=date_end)
        
    all_records = DelayRecord.objects.filter(department=department)
    agencies = list(all_records.order_by('agency').values_list('agency', flat=True).distinct().exclude(agency=''))
    equipments = list(all_records.order_by('equipment').values_list('equipment', flat=True).distinct().exclude(equipment=''))
    if not agencies:
        agencies = ['Mechanical', 'Electrical', 'Planned', 'Operations', 'Instrumentation']

    return render(request, 'delays/partials/_records_table.html', {
        'records': records[:150], # Limit query size for performance
        'department': department,
        'can_edit': can_edit,
        'agencies': agencies,
        'equipments': equipments,
    })


@login_required
def new_record(request, dept_id):
    """
    Create a new manual delay record entry.
    """
    department = get_object_or_404(Department, id=dept_id)
    
    if not user_can_edit_module(request.user, department, 'Delays'):
        messages.error(request, "You do not have editing permissions to log manual entries.")
        return redirect('delays:dept_overview', dept_id=dept_id)
        
    if request.method == 'POST':
        form = DelayRecordForm(request.POST, department=department)
        if form.is_valid():
            record = form.save(commit=False)
            record.department = department
            record.sheet_name = 'Manual Entry'
            record.save()
            messages.success(request, f"Manual delay entry on {record.date} successfully logged.")
            return redirect('delays:dept_overview', dept_id=dept_id)
    else:
        form = DelayRecordForm(department=department)
        
    # Fetch autocompletes
    records = DelayRecord.objects.filter(department=department)
    agencies = list(records.order_by('agency').values_list('agency', flat=True).distinct().exclude(agency=''))
    sub_agencies = list(records.order_by('sub_agency').values_list('sub_agency', flat=True).distinct().exclude(sub_agency=''))
    sections = list(records.order_by('section').values_list('section', flat=True).distinct().exclude(section=''))
    equipments = list(records.order_by('equipment').values_list('equipment', flat=True).distinct().exclude(equipment=''))
    incharges = list(records.order_by('shift_incharge').values_list('shift_incharge', flat=True).distinct().exclude(shift_incharge=''))
    
    context = {
        'form': form,
        'department': department,
        'is_edit': False,
        'agencies': agencies,
        'sub_agencies': sub_agencies,
        'sections': sections,
        'equipments': equipments,
        'incharges': incharges,
        
        # Sidebar
        'active_dept_id': department.id,
        'active_module': 'Delays',
        'active_section': 'department_module',
    }
    return render(request, 'delays/log_entry.html', context)


@login_required
def edit_record(request, dept_id, record_id):
    """
    Edit an existing delay record (parsed or manual).
    """
    department = get_object_or_404(Department, id=dept_id)
    record = get_object_or_404(DelayRecord, id=record_id, department=department)
    
    if not user_can_edit_module(request.user, department, 'Delays'):
        messages.error(request, "You do not have permissions to edit records.")
        return redirect('delays:dept_overview', dept_id=dept_id)
        
    if request.method == 'POST':
        form = DelayRecordForm(request.POST, instance=record, department=department)
        if form.is_valid():
            form.save()
            messages.success(request, "Delay record updated successfully.")
            return redirect('delays:dept_overview', dept_id=dept_id)
    else:
        form = DelayRecordForm(instance=record, department=department)
        
    # Fetch autocompletes
    records = DelayRecord.objects.filter(department=department)
    agencies = list(records.order_by('agency').values_list('agency', flat=True).distinct().exclude(agency=''))
    sub_agencies = list(records.order_by('sub_agency').values_list('sub_agency', flat=True).distinct().exclude(sub_agency=''))
    sections = list(records.order_by('section').values_list('section', flat=True).distinct().exclude(section=''))
    equipments = list(records.order_by('equipment').values_list('equipment', flat=True).distinct().exclude(equipment=''))
    incharges = list(records.order_by('shift_incharge').values_list('shift_incharge', flat=True).distinct().exclude(shift_incharge=''))
    
    context = {
        'form': form,
        'department': department,
        'record': record,
        'is_edit': True,
        'agencies': agencies,
        'sub_agencies': sub_agencies,
        'sections': sections,
        'equipments': equipments,
        'incharges': incharges,
        
        # Sidebar
        'active_dept_id': department.id,
        'active_module': 'Delays',
        'active_section': 'department_module',
    }
    return render(request, 'delays/log_entry.html', context)


@login_required
def delete_record(request, dept_id, record_id):
    """
    Deletes a specific delay record.
    """
    department = get_object_or_404(Department, id=dept_id)
    record = get_object_or_404(DelayRecord, id=record_id, department=department)
    
    if not user_can_edit_module(request.user, department, 'Delays'):
        if request.headers.get('HX-Request'):
            return HttpResponse('<div class="alert alert-danger">Access Denied</div>', status=403)
        messages.error(request, "You do not have permission to delete records.")
        return redirect('delays:dept_overview', dept_id=dept_id)
        
    record_info = f"{record.date} ({record.duration_mins}m - {record.agency})"
    record.delete()
    
    if request.headers.get('HX-Request'):
        # Return empty response to remove row via HTMX outer HTML swap
        return HttpResponse("", status=200)
        
    messages.success(request, f"Delay record on {record_info} deleted successfully.")
    return redirect('delays:dept_overview', dept_id=dept_id)


@login_required
def update_record_inline(request, dept_id, record_id):
    """
    Updates a specific delay record inline from the table row.
    """
    department = get_object_or_404(Department, id=dept_id)
    record = get_object_or_404(DelayRecord, id=record_id, department=department)
    
    if not user_can_edit_module(request.user, department, 'Delays'):
        return HttpResponse('<tr class="table-danger"><td colspan="6">Access Denied</td></tr>', status=403)
        
    if request.method == 'POST':
        # Retrieve values from POST parameters
        date_val = request.POST.get('date')
        duration_val = request.POST.get('duration_mins')
        agency_val = request.POST.get('agency')
        equipment_val = request.POST.get('equipment')
        why_val = request.POST.get('why')
        
        # Simple validation & update
        if date_val:
            record.date = date_val
        if duration_val:
            try:
                record.duration_mins = float(duration_val)
            except ValueError:
                pass
        if agency_val:
            record.agency = agency_val
        record.equipment = equipment_val
        record.why = why_val
        
        # Handle required description
        eq_name = record.equipment or "Unknown Equipment"
        record.description = f"Manual delay entry for {eq_name} ({record.agency})"
        
        record.save()
        
        # Render the updated single row back
        all_records = DelayRecord.objects.filter(department=department)
        agencies = list(all_records.order_by('agency').values_list('agency', flat=True).distinct().exclude(agency=''))
        equipments = list(all_records.order_by('equipment').values_list('equipment', flat=True).distinct().exclude(equipment=''))
        if not agencies:
            agencies = ['Mechanical', 'Electrical', 'Planned', 'Operations', 'Instrumentation']
            
        return render(request, 'delays/partials/_record_row.html', {
            'r': record,
            'department': department,
            'can_edit': True,
            'agencies': agencies,
            'equipments': equipments,
        })
        
    return HttpResponse('Method Not Allowed', status=405)


@login_required
def download_pdf_report(request, dept_id):
    """
    Generates and downloads the PDF analytics report for a department's delays.
    """
    department = get_object_or_404(Department, id=dept_id)
    
    # Check SSO Access
    if not user_can_access_module(request.user, department, 'Delays'):
        messages.error(request, "You do not have permission to access the Delays module.")
        return redirect('portal:dept_hub', dept_id=dept_id)
        
    from delays.utils.export import generate_delays_pdf
    pdf_content = generate_delays_pdf(department)
    
    response = HttpResponse(pdf_content, content_type='application/pdf')
    filename = f"{department.code.lower()}_delays_report_{timezone.now().strftime('%Y%m%d')}.pdf"
    response['Content-Disposition'] = f'attachment; filename="{filename}"'
    return response
