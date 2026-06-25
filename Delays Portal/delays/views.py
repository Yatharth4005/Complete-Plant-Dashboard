import json
import os
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import HttpResponse, JsonResponse
from django.db import models
from django.db.models import Q, Sum, Avg
from django.utils import timezone
from datetime import date
from tpm.models import Department
from delays.models import DelayUpload, DelayRecord, DelayDropdownOption, DelayNotification
from delays.forms import DelayRecordForm
from delays.utils.parser import parse_excel_file
from portal.utils.access import user_can_access_module, user_can_edit_module

def get_department_autocompletes(department, records):
    if department.id == 0:
        custom_options = DelayDropdownOption.objects.none()
    else:
        custom_options = DelayDropdownOption.objects.filter(department=department)
    
    agencies_set = set(custom_options.filter(category__iexact='Agency').values_list('value', flat=True).distinct())
    if not agencies_set:
        agencies_set.update(['Mechanical', 'Electrical', 'Planned', 'Operations', 'Instrumentation'])
    agencies = sorted(list(agencies_set))
        
    sub_agencies_set = set(custom_options.filter(category__iexact='Sub-Agency').values_list('value', flat=True).distinct())
    sub_agencies_set.update(records.exclude(sub_agency__isnull=True).exclude(sub_agency='').values_list('sub_agency', flat=True).distinct())
    sub_agencies = sorted([x for x in sub_agencies_set if x])
    
    sections_set = set(records.order_by('section').values_list('section', flat=True).distinct().exclude(section=''))
    sections = sorted([x for x in sections_set if x])
    
    equipments_set = set(custom_options.filter(category__iexact='Equipment').values_list('value', flat=True).distinct())
    equipments_set.update(records.exclude(equipment__isnull=True).exclude(equipment='').exclude(equipment='NIL').values_list('equipment', flat=True).distinct())
    equipments = sorted([x for x in equipments_set if x])
    
    sub_equipments_set = set(custom_options.filter(category__iexact='Sub-Equipment').values_list('value', flat=True).distinct())
    sub_equipments_set.update(records.exclude(sub_equipment__isnull=True).exclude(sub_equipment='').values_list('sub_equipment', flat=True).distinct())
    sub_equipments = sorted([x for x in sub_equipments_set if x])
    
    incharges_set = set(records.order_by('shift_incharge').values_list('shift_incharge', flat=True).distinct().exclude(shift_incharge=''))
    incharges = sorted([x for x in incharges_set if x])
    
    return {
        'agencies': agencies,
        'sub_agencies': sub_agencies,
        'sections': sections,
        'equipments': equipments,
        'sub_equipments': sub_equipments,
        'incharges': incharges
    }

@login_required
def dept_overview(request, dept_id):
    """
    Main overview and dashboard for department delays.
    Displays metrics, charts, upload features, and logs tables.
    """
    date_start = request.GET.get('date_start', '').strip()
    date_end = request.GET.get('date_end', '').strip()

    if int(dept_id) == 0:
        class DummyDept:
            id = 0
            name = "Overall Plant"
            code = "Overall"
        department = DummyDept()
        can_edit = False
        is_admin = request.user.is_admin()
        all_records = DelayRecord.objects.all()
    else:
        department = get_object_or_404(Department, id=dept_id)
        
        # Check SSO Access
        if not user_can_access_module(request.user, department, 'Delays'):
            messages.error(request, "You do not have permission to access the Delays module.")
            return redirect('portal:dept_hub', dept_id=dept_id)
            
        can_edit = user_can_edit_module(request.user, department, 'Delays')
        is_admin = request.user.is_admin()
        all_records = DelayRecord.objects.filter(department=department)
    
    if date_start:
        all_records = all_records.filter(date__gte=date_start)
    if date_end:
        all_records = all_records.filter(date__lte=date_end)
    
    # Active departments for switching
    departments = Department.objects.all().order_by('name')
    
    # Metrics
    total_mins = all_records.aggregate(Sum('duration_mins'))['duration_mins__sum'] or 0.0
    total_hrs = total_mins / 60.0
    total_events = all_records.count()
    
    # Top agency (normalized)
    agency_totals = {}
    for r in all_records:
        ag = (r.agency or '').strip()
        if ag:
            agency_totals[ag] = agency_totals.get(ag, 0.0) + (r.duration_mins or 0.0)
            
    agency_breakdown_sorted = sorted(agency_totals.items(), key=lambda x: x[1], reverse=True)
    top_agency = agency_breakdown_sorted[0][0] if agency_breakdown_sorted else "N/A"
    top_agency_mins = agency_breakdown_sorted[0][1] if agency_breakdown_sorted else 0.0
    
    avg_duration = all_records.aggregate(Avg('duration_mins'))['duration_mins__avg'] or 0.0
    
    # Chart 1: Agency Distribution (Top 8) / Department-wise Distribution if Overall
    if department.id == 0:
        dept_breakdown = all_records.values('department__code').annotate(total=Sum('duration_mins')).order_by('-total')
        agency_labels = [x['department__code'] for x in dept_breakdown[:8]]
        agency_data = [round(x['total'], 1) for x in dept_breakdown[:8]]
    else:
        agency_labels = [x[0] for x in agency_breakdown_sorted[:8]]
        agency_data = [round(x[1], 1) for x in agency_breakdown_sorted[:8]]
    
    dept_trends = {}
    # Chart 2: Daily Trend / Department Comparison
    if department.id == 0:
        # For overall plant, we compare total downtime by department, stacked by agency
        dept_downtimes = all_records.values('department__code').annotate(total=Sum('duration_mins')).order_by('-total')
        daily_labels = [x['department__code'] for x in dept_downtimes if x['department__code']]
        
        raw_agencies = all_records.values_list('agency', flat=True).exclude(agency='')
        active_groups = sorted(list(set(a.strip() for a in raw_agencies if a)))
        if not active_groups:
            active_groups = ['Mechanical', 'Electrical', 'Planned', 'Operations', 'Instrumentation']
            
        downtime_by_dept_agency = all_records.values('department__code', 'agency').annotate(total=Sum('duration_mins'))
        downtime_map = {}
        for entry in downtime_by_dept_agency:
            dept = entry['department__code']
            agency = (entry['agency'] or '').strip()
            if not agency:
                continue
            downtime_map[(dept, agency)] = downtime_map.get((dept, agency), 0.0) + (entry['total'] or 0.0)
            
        daily_datasets = []
        for grp in active_groups:
            grp_data = []
            for dept_code in daily_labels:
                mins = downtime_map.get((dept_code, grp), 0.0)
                grp_data.append(round(mins, 1))
            daily_datasets.append({
                'label': grp or "N/A",
                'data': grp_data
            })

        # Calculate daily trend for each individual department to allow drill-down in overall plant dashboard
        all_depts = Department.objects.all().order_by('name')
        for d in all_depts:
            d_records = all_records.filter(department=d)
            if d_records.exists():
                d_daily_breakdown = list(d_records.values('date').annotate(total=Sum('duration_mins')).order_by('date'))
                d_daily_active_dates = [x['date'] for x in d_daily_breakdown[-30:]]
                d_daily_labels = [dt.strftime('%d-%b-%Y') for dt in d_daily_active_dates]
                
                d_last_30_records = d_records.filter(date__in=d_daily_active_dates)
                d_raw_agencies = d_last_30_records.values_list('agency', flat=True).exclude(agency='')
                d_active_groups = sorted(list(set(a.strip() for a in d_raw_agencies if a)))
                if not d_active_groups:
                    d_active_groups = ['Mechanical', 'Electrical', 'Planned', 'Operations', 'Instrumentation']
                
                d_downtime_by_date_group = d_last_30_records.values('date', 'agency').annotate(total=Sum('duration_mins'))
                d_downtime_map = {}
                for entry in d_downtime_by_date_group:
                    d_date = entry['date']
                    agency = (entry['agency'] or '').strip()
                    if not agency:
                        continue
                    d_downtime_map[(d_date, agency)] = d_downtime_map.get((d_date, agency), 0.0) + (entry['total'] or 0.0)
                
                d_daily_datasets = []
                for grp in d_active_groups:
                    grp_daily_data = []
                    for dt in d_daily_active_dates:
                        mins = d_downtime_map.get((dt, grp), 0.0)
                        grp_daily_data.append(round(mins, 1))
                    d_daily_datasets.append({
                        'label': grp or "N/A",
                        'data': grp_daily_data
                    })
                
                dept_trends[d.code] = {
                    'labels': d_daily_labels,
                    'datasets': d_daily_datasets,
                    'dept_name': d.name
                }
    else:
        # For a specific department
        if date_start or date_end:
            # If a date range is selected, show DAILY trend
            daily_breakdown = list(all_records.values('date').annotate(total=Sum('duration_mins')).order_by('date'))
            daily_active_dates = [x['date'] for x in daily_breakdown]
            daily_labels = [d.strftime('%d-%b-%Y') for d in daily_active_dates]
            
            raw_agencies = all_records.values_list('agency', flat=True).exclude(agency='')
            active_groups = sorted(list(set(a.strip() for a in raw_agencies if a)))
            if not active_groups:
                active_groups = ['Mechanical', 'Electrical', 'Planned', 'Operations', 'Instrumentation']
                
            downtime_by_date_group = all_records.values('date', 'agency').annotate(total=Sum('duration_mins'))
            downtime_map = {}
            for entry in downtime_by_date_group:
                d_date = entry['date']
                agency_name = (entry['agency'] or '').strip()
                if not agency_name:
                    continue
                downtime_map[(d_date, agency_name)] = downtime_map.get((d_date, agency_name), 0.0) + (entry['total'] or 0.0)
                
            daily_datasets = []
            for grp in active_groups:
                grp_daily_data = []
                for d in daily_active_dates:
                    mins = downtime_map.get((d, grp), 0.0)
                    grp_daily_data.append(round(mins, 1))
                daily_datasets.append({
                    'label': grp or "N/A",
                    'data': grp_daily_data
                })
        else:
            # If NO date range is selected, show MONTHLY trend
            months_set = set()
            for r in all_records:
                if r.date:
                    months_set.add(date(r.date.year, r.date.month, 1))
            sorted_months = sorted(list(months_set))
            
            daily_labels = [m.strftime('%b %Y') for m in sorted_months]
            
            raw_agencies = all_records.values_list('agency', flat=True).exclude(agency='')
            active_groups = sorted(list(set(a.strip() for a in raw_agencies if a)))
            if not active_groups:
                active_groups = ['Mechanical', 'Electrical', 'Planned', 'Operations', 'Instrumentation']
                
            downtime_map = {}
            for r in all_records:
                if r.date and r.agency:
                    m_date = date(r.date.year, r.date.month, 1)
                    ag = r.agency.strip()
                    downtime_map[(m_date, ag)] = downtime_map.get((m_date, ag), 0.0) + (r.duration_mins or 0.0)
                    
            daily_datasets = []
            for grp in active_groups:
                grp_monthly_data = []
                for m in sorted_months:
                    mins = downtime_map.get((m, grp), 0.0)
                    grp_monthly_data.append(round(mins, 1))
                daily_datasets.append({
                    'label': grp or "N/A",
                    'data': grp_monthly_data
                })
    
    # Chart 3: Top bottleneck equipment / Department
    if department.id == 0:
        dept_breakdown_bottleneck = all_records.values('department__code').annotate(total=Sum('duration_mins')).order_by('-total')[:5]
        equip_labels = [x['department__code'] for x in dept_breakdown_bottleneck]
        equip_data = [round(x['total'], 1) for x in dept_breakdown_bottleneck]
    else:
        equip_breakdown = all_records.exclude(
            Q(equipment__isnull=True) | Q(equipment='') | Q(equipment='-') | Q(equipment='NA')  # type: ignore
        ).values('equipment').annotate(total=Sum('duration_mins')).order_by('-total')[:5]
        equip_labels = [x['equipment'] for x in equip_breakdown]
        equip_data = [round(x['total'], 1) for x in equip_breakdown]
    
    # List of sheets parsed
    sheets_parsed = [s for s in all_records.order_by('sheet_name').values_list('sheet_name', flat=True).distinct() if s]
    
    # Upload history
    if department.id == 0:
        uploads = DelayUpload.objects.all().order_by('-uploaded_at')
    else:
        uploads = DelayUpload.objects.filter(department=department).order_by('-uploaded_at')
    
    # Form autocompletes
    autocompletes = get_department_autocompletes(department, all_records)
    agencies = autocompletes['agencies']
    sub_agencies = autocompletes['sub_agencies']
    sections = autocompletes['sections']
    equipments = autocompletes['equipments']
    sub_equipments = autocompletes['sub_equipments']
    incharges = autocompletes['incharges']
 
    # Pareto Calculation by Agency
    agency_pareto = []
    running_mins = 0
    for idx, (ag, total) in enumerate(agency_breakdown_sorted):
        running_mins += total
        cum_percent = (running_mins / total_mins * 100) if total_mins > 0 else 0.0
        agency_pareto.append({
            'agency': ag,
            'mins': round(total, 1),
            'percent': round((total / total_mins * 100) if total_mins > 0 else 0.0, 1),
            'cum_percent': round(cum_percent, 1),
            'rank': idx + 1,
            'is_vital': cum_percent <= 85.0 or idx == 0
        })
 
    # Pareto Calculation by Equipment
    all_equip_breakdown = all_records.exclude(
        Q(equipment__isnull=True) | Q(equipment='') | Q(equipment='-') | Q(equipment='NA')  # type: ignore
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
    
    for r in all_records:
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
 
    # Status filtering for logs table
    status_filter = request.GET.get('status', 'unlocked').strip()
    if status_filter == 'unlocked':
        table_records = all_records.filter(is_locked=False)
    elif status_filter == 'locked':
        table_records = all_records.filter(is_locked=True)
    else:
        table_records = all_records
        
    has_unlocked = all_records.filter(is_locked=False).exists()

    # Decorate records with equipment category and build equipment select options list
    equipment_opts = DelayDropdownOption.objects.filter(category__iexact='Equipment')
    if department.id != 0:
        equipment_opts = equipment_opts.filter(department=department)
    equip_cat_map = {opt.value.strip().lower(): opt.parent_value for opt in equipment_opts if opt.parent_value}
    
    records_list = list(table_records[:1000])
    for r in records_list:
        eq_key = (r.equipment or '').strip().lower()
        r.equipment_category = equip_cat_map.get(eq_key)

    equipments_list = []
    for eq in equipments:
        cat = equip_cat_map.get(eq.strip().lower())
        display = f"{eq} ({cat})" if cat else eq
        equipments_list.append({'value': eq, 'display': display})
 
    # HTMX request for tabular logs partial
    if request.headers.get('HX-Request') and 'records-tab' in request.GET:
        # Return log table partial
        return render(request, 'delays/partials/_records_table.html', {
            'records': records_list,
            'department': department,
            'can_edit': can_edit,
            'is_admin': is_admin,
            'status': status_filter,
            'has_unlocked': has_unlocked,
            'agencies': agencies,
            'equipments': equipments,
            'equipments_list': equipments_list,
            'sub_agencies': sub_agencies,
            'sub_equipments': sub_equipments,
        })
    
    dept_summaries = []
    if department.id == 0:
        all_depts = Department.objects.all().order_by('name')
        for d in all_depts:
            d_records = DelayRecord.objects.filter(department=d)
            d_count = d_records.count()
            if d_count > 0:
                d_mins = d_records.aggregate(Sum('duration_mins'))['duration_mins__sum'] or 0.0
                d_hrs = d_mins / 60.0
                d_avg = d_records.aggregate(Avg('duration_mins'))['duration_mins__avg'] or 0.0
                
                d_agency_breakdown = d_records.values('agency').annotate(total=Sum('duration_mins')).order_by('-total')
                d_top_agency = d_agency_breakdown[0]['agency'] if d_agency_breakdown else "N/A"
                
                dept_summaries.append({
                    'department': d,
                    'total_mins': round(d_mins, 1),
                    'total_hrs': round(d_hrs, 1),
                    'total_events': d_count,
                    'top_agency': d_top_agency,
                    'avg_duration': round(d_avg, 1),
                })

    # Fetch notifications
    if department.id == 0:
        notifications = DelayNotification.objects.all().order_by('-created_at')
        external_departments = Department.objects.all().order_by('name')
    else:
        notifications = DelayNotification.objects.filter(to_department=department).order_by('-created_at')
        external_departments = Department.objects.exclude(id=department.id).order_by('name')
    unread_notifications_count = notifications.filter(is_read=False).count()

    context = {
        'department': department,
        'departments': departments,
        'date_start': date_start,
        'date_end': date_end,
        'dept_summaries': dept_summaries,
        'can_edit': can_edit,
        'is_admin': is_admin,
        'status': status_filter,
        'has_unlocked': has_unlocked,
        'notifications': notifications,
        'unread_notifications_count': unread_notifications_count,
        'external_departments': external_departments,

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
        'daily_datasets_json': json.dumps(daily_datasets),
        'dept_trends_json': json.dumps(dept_trends),
        'equip_labels_json': json.dumps(equip_labels),
        'equip_data_json': json.dumps(equip_data),
        
        # Pareto JSONs
        'pareto_labels_json': json.dumps([x['agency'] for x in agency_pareto]),
        'pareto_mins_json': json.dumps([x['mins'] for x in agency_pareto]),
        'pareto_cum_json': json.dumps([x['cum_percent'] for x in agency_pareto]),
        
        # Lists
        'records': records_list, # Limit initially
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
        'table_agencies': sorted(list(set(agencies + list(Department.objects.all().values_list('name', flat=True))))),
        'sub_agencies': sub_agencies,
        'sections': sections,
        'equipments': equipments,
        'equipments_list': equipments_list,
        'sub_equipments': sub_equipments,
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
    if int(dept_id) == 0:
        class DummyDept:
            id = 0
            name = "Overall Plant"
            code = "Overall"
        department = DummyDept()
        can_edit = False
        records = DelayRecord.objects.all()
    else:
        department = get_object_or_404(Department, id=dept_id)
        can_edit = user_can_edit_module(request.user, department, 'Delays')
        records = DelayRecord.objects.filter(department=department)
        
    query = request.GET.get('q', '').strip()
    agency_type_filter = request.GET.get('agency_type', '').strip()
    agency_filter = request.GET.get('agency', '').strip()
    sub_agency_filter = request.GET.get('sub_agency', '').strip()
    equipment_filter = request.GET.get('equipment', '').strip()
    sub_equipment_filter = request.GET.get('sub_equipment', '').strip()
    sheet_filter = request.GET.get('sheet', '').strip()
    date_start = request.GET.get('date_start', '').strip()
    date_end = request.GET.get('date_end', '').strip()
    
    if query:
        records = records.filter(
            Q(description__icontains=query) |
            Q(equipment__icontains=query) |
            Q(sub_equipment__icontains=query) |
            Q(shift_incharge__icontains=query) |
            Q(why__icontains=query)  # type: ignore
        )
        
    if agency_type_filter:
        records = records.filter(agency_type=agency_type_filter)

    if agency_filter:
        records = records.filter(agency=agency_filter)

        
    if sub_agency_filter:
        records = records.filter(sub_agency=sub_agency_filter)
        
    if equipment_filter:
        records = records.filter(equipment=equipment_filter)
        
    if sub_equipment_filter:
        records = records.filter(sub_equipment=sub_equipment_filter)
        
    if sheet_filter:
        records = records.filter(sheet_name=sheet_filter)
        
    if date_start:
        records = records.filter(date__gte=date_start)
        
    if date_end:
        records = records.filter(date__lte=date_end)
        
    if int(dept_id) == 0:
        all_records = DelayRecord.objects.all()
    else:
        all_records = DelayRecord.objects.filter(department=department)
    
    # Filter by status
    status_filter = request.GET.get('status', 'unlocked').strip()
    if status_filter == 'unlocked':
        records = records.filter(is_locked=False)
    elif status_filter == 'locked':
        records = records.filter(is_locked=True)
        
    is_admin = request.user.is_admin()
    has_unlocked = all_records.filter(is_locked=False).exists()
    
    autocompletes = get_department_autocompletes(department, all_records)
    agencies = autocompletes['agencies']
    equipments = autocompletes['equipments']
    sub_agencies = autocompletes['sub_agencies']
    sub_equipments = autocompletes['sub_equipments']

    table_agencies = sorted(list(set(agencies + list(Department.objects.all().values_list('name', flat=True)))))

    # Decorate records with equipment category and build equipment select options list
    equipment_opts = DelayDropdownOption.objects.filter(category__iexact='Equipment')
    if department.id != 0:
        equipment_opts = equipment_opts.filter(department=department)
    equip_cat_map = {opt.value.strip().lower(): opt.parent_value for opt in equipment_opts if opt.parent_value}
    
    records_list = list(records[:1000])
    for r in records_list:
        eq_key = (r.equipment or '').strip().lower()
        r.equipment_category = equip_cat_map.get(eq_key)

    equipments_list = []
    for eq in equipments:
        cat = equip_cat_map.get(eq.strip().lower())
        display = f"{eq} ({cat})" if cat else eq
        equipments_list.append({'value': eq, 'display': display})

    return render(request, 'delays/partials/_records_table.html', {
        'records': records_list, # Limit query size for performance
        'department': department,
        'can_edit': can_edit,
        'is_admin': is_admin,
        'status': status_filter,
        'has_unlocked': has_unlocked,
        'agencies': agencies,
        'table_agencies': table_agencies,
        'equipments': equipments,
        'equipments_list': equipments_list,
        'sub_agencies': sub_agencies,
        'sub_equipments': sub_equipments,
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
    autocompletes = get_department_autocompletes(department, records)
    agencies = autocompletes['agencies']
    sub_agencies = autocompletes['sub_agencies']
    sections = autocompletes['sections']
    equipments = autocompletes['equipments']
    sub_equipments = autocompletes['sub_equipments']
    incharges = autocompletes['incharges']
    
    context = {
        'form': form,
        'department': department,
        'is_edit': False,
        'agencies': agencies,
        'sub_agencies': sub_agencies,
        'sections': sections,
        'equipments': equipments,
        'sub_equipments': sub_equipments,
        'incharges': incharges,
        'external_departments': Department.objects.exclude(id=department.id).order_by('name'),
        
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
        
    # Check if locked and verify admin permission
    if record.is_locked and not request.user.is_admin():
        messages.error(request, "This record is locked and can only be edited by an Admin.")
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
    autocompletes = get_department_autocompletes(department, records)
    agencies = autocompletes['agencies']
    sub_agencies = autocompletes['sub_agencies']
    sections = autocompletes['sections']
    equipments = autocompletes['equipments']
    sub_equipments = autocompletes['sub_equipments']
    incharges = autocompletes['incharges']
    
    context = {
        'form': form,
        'department': department,
        'record': record,
        'is_edit': True,
        'is_admin': request.user.is_admin(),
        'agencies': agencies,
        'sub_agencies': sub_agencies,
        'sections': sections,
        'equipments': equipments,
        'sub_equipments': sub_equipments,
        'incharges': incharges,
        'external_departments': Department.objects.exclude(id=department.id).order_by('name'),
        
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
        
    # Check if locked and verify admin permission
    if record.is_locked and not request.user.is_admin():
        if request.headers.get('HX-Request'):
            return HttpResponse('<div class="alert alert-danger">Access Denied: Record is Locked</div>', status=403)
        messages.error(request, "This record is locked and can only be deleted by an Admin.")
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
        
    # Check if locked and verify admin permission
    if record.is_locked and not request.user.is_admin():
        return HttpResponse('<tr class="table-danger"><td colspan="6">Access Denied: Record is Locked</td></tr>', status=403)
        
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
            if Department.objects.filter(name=agency_val).exists():
                record.agency_type = 'External'
            else:
                record.agency_type = 'Internal'
        record.equipment = equipment_val
        record.why = why_val
        
        # Handle required description
        eq_name = record.equipment or "Unknown Equipment"
        record.description = f"Manual delay entry for {eq_name} ({record.agency})"
        
        record.save()
        
        # Render the updated single row back
        all_records = DelayRecord.objects.filter(department=department)
        autocompletes = get_department_autocompletes(department, all_records)
        agencies = autocompletes['agencies']
        equipments = autocompletes['equipments']
        table_agencies = sorted(list(set(agencies + list(Department.objects.all().values_list('name', flat=True)))))
        
        # Decorate record with category and build equipments_list
        equipment_opts = DelayDropdownOption.objects.filter(category__iexact='Equipment')
        if department.id != 0:
            equipment_opts = equipment_opts.filter(department=department)
        equip_cat_map = {opt.value.strip().lower(): opt.parent_value for opt in equipment_opts if opt.parent_value}
        
        eq_key = (record.equipment or '').strip().lower()
        record.equipment_category = equip_cat_map.get(eq_key)

        equipments_list = []
        for eq in equipments:
            cat = equip_cat_map.get(eq.strip().lower())
            display = f"{eq} ({cat})" if cat else eq
            equipments_list.append({'value': eq, 'display': display})
            
        return render(request, 'delays/partials/_record_row.html', {
            'r': record,
            'department': department,
            'can_edit': True,
            'is_admin': request.user.is_admin(),
            'agencies': agencies,
            'table_agencies': table_agencies,
            'equipments': equipments,
            'equipments_list': equipments_list,
        })
        
    return HttpResponse('Method Not Allowed', status=405)


@login_required
def download_pdf_report(request, dept_id):
    """
    Generates and downloads the PDF analytics report for a department's delays.
    """
    if int(dept_id) == 0:
        class DummyDept:
            id = 0
            name = "Overall Plant"
            code = "Overall"
        department = DummyDept()
    else:
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


@login_required
def pareto_overall(request, dept_id):
    """
    Returns the overall Pareto Analysis content (HTMX endpoint).
    """
    if int(dept_id) == 0:
        class DummyDept:
            id = 0
            name = "Overall Plant"
            code = "Overall"
        department = DummyDept()
        records = DelayRecord.objects.all()
    else:
        department = get_object_or_404(Department, id=dept_id)
        records = DelayRecord.objects.filter(department=department)
    
    total_mins = records.aggregate(Sum('duration_mins'))['duration_mins__sum'] or 0.0
    
    # Pareto Calculation by Agency
    agency_breakdown = records.values('agency').annotate(total=Sum('duration_mins')).order_by('-total')
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
        Q(equipment__isnull=True) | Q(equipment='') | Q(equipment='-') | Q(equipment='NA')  # type: ignore
    ).values('equipment').annotate(total=Sum('duration_mins')).order_by('-total')
    
    total_equip_mins = sum(x['total'] for x in all_equip_breakdown)
    group_by_field = 'equipment'
    is_description = False
    
    # Fallback to description if no equipment data is available (like in SMS3 daily sheets)
    if total_equip_mins == 0:
        all_equip_breakdown = records.exclude(
            Q(description__isnull=True) | Q(description='') | Q(description='-') | Q(description='NA')  # type: ignore
        ).values('description').annotate(total=Sum('duration_mins')).order_by('-total')
        total_equip_mins = sum(x['total'] for x in all_equip_breakdown)
        group_by_field = 'description'
        is_description = True

    equip_pareto = []
    running_equip_mins = 0
    for idx, eb in enumerate(all_equip_breakdown):
        running_equip_mins += eb['total']
        cum_percent = (running_equip_mins / total_equip_mins * 100) if total_equip_mins > 0 else 0.0
        label_val = eb[group_by_field] or "N/A"
        equip_pareto.append({
            'equipment': label_val,
            'mins': round(eb['total'], 1),
            'percent': round((eb['total'] / total_equip_mins * 100) if total_equip_mins > 0 else 0.0, 1),
            'cum_percent': round(cum_percent, 1),
            'rank': idx + 1,
            'is_vital': cum_percent <= 85.0 or idx == 0
        })
        
    top_agency = agency_pareto[0]['agency'] if agency_pareto else "N/A"
    top_agency_mins = agency_pareto[0]['mins'] if agency_pareto else 0.0

    context = {
        'department': department,
        'agency_pareto': agency_pareto,
        'equip_pareto': equip_pareto[:10],
        'top_agency': top_agency,
        'top_agency_mins': top_agency_mins,
        'is_description': is_description,
        'pareto_labels_json': json.dumps([x['agency'] for x in agency_pareto]),
        'pareto_mins_json': json.dumps([x['mins'] for x in agency_pareto]),
        'pareto_cum_json': json.dumps([x['cum_percent'] for x in agency_pareto]),
    }
    return render(request, 'delays/partials/_pareto_content.html', context)


@login_required
def pareto_agency(request, dept_id):
    """
    Returns the equipment Pareto Analysis for a specific agency (HTMX endpoint).
    """
    agency_name = request.GET.get('agency', '')
    if int(dept_id) == 0:
        class DummyDept:
            id = 0
            name = "Overall Plant"
            code = "Overall"
        department = DummyDept()
        records = DelayRecord.objects.filter(agency=agency_name)
    else:
        department = get_object_or_404(Department, id=dept_id)
        records = DelayRecord.objects.filter(department=department, agency=agency_name)
    total_agency_mins = records.aggregate(Sum('duration_mins'))['duration_mins__sum'] or 0.0
    
    # Pareto Calculation by Equipment *within* that agency
    equip_breakdown = records.exclude(
        Q(equipment__isnull=True) | Q(equipment='') | Q(equipment='-') | Q(equipment='NA') | Q(equipment='None')  # type: ignore
    ).values('equipment').annotate(total=Sum('duration_mins')).order_by('-total')
    
    total_mins = sum(x['total'] for x in equip_breakdown)
    group_by_field = 'equipment'
    is_description = False
    
    # Fallback to description if no equipment data is available (like in SMS3 daily sheets)
    if total_mins == 0:
        equip_breakdown = records.exclude(
            Q(description__isnull=True) | Q(description='') | Q(description='-') | Q(description='NA')  # type: ignore
        ).values('description').annotate(total=Sum('duration_mins')).order_by('-total')
        total_mins = sum(x['total'] for x in equip_breakdown)
        group_by_field = 'description'
        is_description = True
        
    equip_pareto = []
    running_mins = 0
    for idx, eb in enumerate(equip_breakdown):
        running_mins += eb['total']
        cum_percent = (running_mins / total_mins * 100) if total_mins > 0 else 0.0
        
        label_val = eb[group_by_field] or "N/A"
        
        equip_pareto.append({
            'label': label_val,
            'mins': round(eb['total'], 1),
            'percent': round((eb['total'] / total_mins * 100) if total_mins > 0 else 0.0, 1),
            'cum_percent': round(cum_percent, 1),
            'rank': idx + 1,
            'is_vital': cum_percent <= 85.0 or idx == 0
        })
        
    top_equipment = equip_pareto[0]['label'] if equip_pareto else "N/A"
    top_equipment_mins = equip_pareto[0]['mins'] if equip_pareto else 0.0

    context = {
        'department': department,
        'agency_name': agency_name,
        'equip_pareto': equip_pareto,
        'total_mins': round(total_agency_mins, 1),
        'top_equipment': top_equipment,
        'top_equipment_mins': top_equipment_mins,
        'is_description': is_description,
        'pareto_labels_json': json.dumps([x['label'] for x in equip_pareto[:15]]),
        'pareto_mins_json': json.dumps([x['mins'] for x in equip_pareto[:15]]),
        'pareto_cum_json': json.dumps([x['cum_percent'] for x in equip_pareto[:15]]),
    }
    return render(request, 'delays/partials/_pareto_agency_content.html', context)


@login_required
def manage_options(request, dept_id):
    """
    Allows adding and removing custom options (Agency, Sub-Agency, Equipment, Sub-Equipment) per department.
    """
    department = get_object_or_404(Department, id=dept_id)
    if not request.user.is_admin():
        messages.error(request, "Only administrators can manage dropdown options.")
        return redirect('delays:dept_overview', dept_id=dept_id)

    if request.method == 'POST':
        action = request.POST.get('action')
        if action == 'add':
            category = request.POST.get('category', '').strip()
            value = request.POST.get('value', '').strip()
            parent_value = request.POST.get('parent_value', '').strip() or None
            
            if category and value:
                option, created = DelayDropdownOption.objects.get_or_create(
                    department=department,
                    category=category,
                    value=value,
                    parent_value=parent_value
                )
                if created:
                    messages.success(request, f"Option '{value}' added to '{category}' successfully.")
                else:
                    messages.info(request, f"Option '{value}' already exists in '{category}'.")
            else:
                messages.error(request, "Category and value are required.")
                
        elif action == 'delete':
            option_id = request.POST.get('option_id')
            option = get_object_or_404(DelayDropdownOption, id=option_id, department=department)
            val = option.value
            cat = option.category
            option.delete()
            messages.success(request, f"Option '{val}' removed from '{cat}'.")
            
        # Determine which tab category to redirect to so that Alpine.js opens the same tab
        from django.urls import reverse
        category_to_keep = category if action == 'add' else cat
        return redirect(f"{reverse('delays:manage_options', args=[dept_id])}?tab={category_to_keep}")

    # Auto-seed DelayDropdownOption if it is completely empty for this department
    if not DelayDropdownOption.objects.filter(department=department).exists():
        # 1. Default agencies
        default_agencies = ['Mechanical', 'Electrical', 'Planned', 'Operations', 'Instrumentation']
        for val in default_agencies:
            DelayDropdownOption.objects.get_or_create(
                department=department,
                category='Agency',
                value=val
            )
        # 2. Unique past values from DelayRecord
        records = DelayRecord.objects.filter(department=department)
        
        db_agencies = records.values_list('agency', flat=True).distinct().exclude(agency='')
        for val in db_agencies:
            DelayDropdownOption.objects.get_or_create(
                department=department,
                category='Agency',
                value=val
            )
            
        db_sub_agencies = records.values_list('sub_agency', flat=True).distinct().exclude(sub_agency='')
        for val in db_sub_agencies:
            DelayDropdownOption.objects.get_or_create(
                department=department,
                category='Sub-Agency',
                value=val
            )
            
        db_equipments = records.values_list('equipment', flat=True).distinct().exclude(equipment='')
        for val in db_equipments:
            DelayDropdownOption.objects.get_or_create(
                department=department,
                category='Equipment',
                value=val
            )
            
        db_sub_equipments = records.values_list('sub_equipment', flat=True).distinct().exclude(sub_equipment='')
        for val in db_sub_equipments:
            DelayDropdownOption.objects.get_or_create(
                department=department,
                category='Sub-Equipment',
                value=val
            )

    options = DelayDropdownOption.objects.filter(department=department).order_by('category', 'value')
    
    # Predefined suggested categories
    suggested_categories = ['Agency', 'Sub-Agency', 'Equipment', 'Sub-Equipment']
    db_categories = list(options.values_list('category', flat=True).distinct())
    for cat in db_categories:
        if cat not in suggested_categories:
            suggested_categories.append(cat)

    context = {
        'department': department,
        'options': options,
        'suggested_categories': suggested_categories,
        'active_dept_id': department.id,
        'active_module': 'Delays',
        'active_section': 'department_module',
        'is_manage_options_page': True,
        'active_tab': request.GET.get('tab', 'Agency'),
    }
    return render(request, 'delays/manage_options.html', context)


@login_required
def lock_records(request, dept_id):
    """
    POST view to lock all currently unlocked delay records for a department.
    """
    department = get_object_or_404(Department, id=dept_id)
    if not user_can_edit_module(request.user, department, 'Delays'):
        messages.error(request, "You do not have editing permissions to lock logs.")
        return redirect('delays:dept_overview', dept_id=dept_id)
        
    if request.method == 'POST':
        unlocked = DelayRecord.objects.filter(department=department, is_locked=False)
        count = unlocked.count()
        unlocked.update(is_locked=True)
        messages.success(request, f"Successfully saved and locked {count} delay records.")
        
    return redirect('delays:dept_overview', dept_id=dept_id)


@login_required
def mark_all_read(request, dept_id):
    """
    Mark all unread received notifications for the department as read.
    """
    if request.method == 'POST':
        if int(dept_id) == 0:
            if not request.user.is_admin():
                messages.error(request, "Permission denied.")
                return redirect('delays:dept_overview', dept_id=dept_id)
            DelayNotification.objects.filter(is_read=False).update(is_read=True)
        else:
            department = get_object_or_404(Department, id=dept_id)
            if not user_can_edit_module(request.user, department, 'Delays'):
                messages.error(request, "Permission denied.")
                return redirect('delays:dept_overview', dept_id=dept_id)
            DelayNotification.objects.filter(to_department=department, is_read=False).update(is_read=True)
        
        # Also mark matching PortalNotification for this user as read
        from portal.models import PortalNotification
        if int(dept_id) == 0:
            PortalNotification.objects.filter(
                user=request.user,
                link__startswith="/delays/department/",
                is_read=False
            ).update(is_read=True)
        else:
            PortalNotification.objects.filter(
                user=request.user,
                link=f"/delays/department/{dept_id}/",
                is_read=False
            ).update(is_read=True)
            
        messages.success(request, "All notifications marked as read.")
    return redirect('delays:dept_overview', dept_id=dept_id)


@login_required
def mark_read(request, dept_id, notification_id):
    """
    Mark a single notification as read.
    """
    if request.method == 'POST':
        if int(dept_id) == 0:
            if not request.user.is_admin():
                messages.error(request, "Permission denied.")
                return redirect('delays:dept_overview', dept_id=dept_id)
            notification = get_object_or_404(DelayNotification, id=notification_id)
        else:
            department = get_object_or_404(Department, id=dept_id)
            if not user_can_edit_module(request.user, department, 'Delays'):
                messages.error(request, "Permission denied.")
                return redirect('delays:dept_overview', dept_id=dept_id)
            notification = get_object_or_404(DelayNotification, id=notification_id, to_department=department)
            
        notification.is_read = True
        notification.save()
        
        # Also mark matching PortalNotification for this user as read
        from portal.models import PortalNotification
        PortalNotification.objects.filter(
            user=request.user,
            link=f"/delays/department/{notification.to_department.id}/",
            is_read=False
        ).update(is_read=True)
        
        messages.success(request, "Notification marked as read.")
    return redirect('delays:dept_overview', dept_id=dept_id)


@login_required
def submit_reason(request, dept_id, notification_id):
    """
    POST view to allow a department to submit a delay reason response.
    This reason is stored in the database and sent back to the department that filed the delay.
    """
    if request.method == 'POST':
        reason = request.POST.get('reason_response', '').strip()
        if not reason:
            messages.error(request, "Please enter a valid reason.")
            return redirect('delays:dept_overview', dept_id=dept_id)
            
        if int(dept_id) == 0:
            if not request.user.is_admin():
                messages.error(request, "Permission denied.")
                return redirect('delays:dept_overview', dept_id=dept_id)
            notification = get_object_or_404(DelayNotification, id=notification_id)
        else:
            department = get_object_or_404(Department, id=dept_id)
            if not user_can_edit_module(request.user, department, 'Delays'):
                messages.error(request, "Permission denied.")
                return redirect('delays:dept_overview', dept_id=dept_id)
            notification = get_object_or_404(DelayNotification, id=notification_id, to_department=department)
            
        # Store reason on original notification
        notification.response_reason = reason
        notification.is_read = True # mark as read automatically when reason is submitted
        notification.save()
        
        # Update the original DelayRecord's 'why' field with this reason
        record = notification.delay_record
        record.why = reason
        super(DelayRecord, record).save()
        
        # Send a response notification back to the sender department
        resp_msg = f"Department {notification.to_department.name} ({notification.to_department.code}) submitted a delay reason for the delay of {record.duration_mins} mins on {record.date}: '{reason}'"
        
        # Create the DelayNotification targeted to the department that filed it
        DelayNotification.objects.create(
            from_department=notification.to_department,
            to_department=notification.from_department,
            delay_record=record,
            message=resp_msg,
            is_read=False
        )
        
        # Create a PortalNotification for the users in the filing department
        try:
            from portal.models import PortalNotification
            from tpm.models import User
            from django.db.models import Q
            
            users = User.objects.filter(
                Q(department=notification.from_department) | 
                Q(module_access__department=notification.from_department, module_access__module__key='Delays') |
                Q(is_plant_admin=True)  # type: ignore
            ).exclude(department=notification.to_department).distinct()
            
            for u in users:
                PortalNotification.objects.get_or_create(
                    user=u,
                    message=resp_msg,
                    link=f"/delays/department/{notification.from_department.id}/",
                    is_read=False
                )
        except Exception:
            pass
            
        messages.success(request, f"Delay reason successfully submitted to {notification.from_department.name}.")
    return redirect('delays:dept_overview', dept_id=dept_id)
