import json
import os
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import HttpResponse, JsonResponse
from django.db import models
from django.db.models import Q, Sum, Avg, Count
from django.utils import timezone
from datetime import date
from tpm.models import Department
from delays.models import DelayUpload, DelayRecord, DelayDropdownOption, DelayNotification, EquipmentShutdownSetting, MaintenanceChecklist, MaintenanceChecklistItem
from delays.forms import DelayRecordForm
from delays.utils.parser import parse_excel_file, normalize_agency_name
from portal.utils.access import user_can_access_module, user_can_edit_module

import re

def clean_equipment_name(name):
    if not name:
        return ""
    name_upper = name.strip().upper()
    # Match digit followed by spaces/hyphens then 'T' or 'MT' or 'TON'
    match = re.search(r'(\d+)\s*(?:-|)?\s*(?:T|MT|TON|TONS)', name_upper)
    if match and 'CRANE' in name_upper:
        tonnage = match.group(1)
        return f"{tonnage}T CRANE"
    return name_upper

def get_equipment_filter_q(selected_equipment):
    if not selected_equipment:
        return Q()
    cleaned = clean_equipment_name(selected_equipment)
    match = re.match(r'^(\d+)T CRANE$', cleaned)
    if match:
        tonnage = match.group(1)
        return Q(equipment__icontains=tonnage) & Q(equipment__icontains='crane')
    return Q(equipment__iexact=selected_equipment)

def get_department_autocompletes(department, records):
    if department.id == 0:
        custom_options = DelayDropdownOption.objects.none()
    else:
        custom_options = DelayDropdownOption.objects.filter(department=department)
    
    raw_agencies = custom_options.filter(category__iexact='Agency').values_list('value', flat=True).distinct()
    agencies_set = set(normalize_agency_name(a) for a in raw_agencies if a)
    if not agencies_set:
        agencies_set.update(['Mechanical', 'Electrical', 'Planned', 'Operations', 'Instrumentation'])
    agencies = sorted(list(agencies_set))
        
    sub_agencies_set = set(custom_options.filter(category__iexact='Sub-Agency').values_list('value', flat=True).distinct())
    sub_agencies_set.update(records.exclude(sub_agency__isnull=True).exclude(sub_agency='').values_list('sub_agency', flat=True).distinct())
    sub_agencies = sorted([x for x in sub_agencies_set if x])
    
    sub_areas_set = set(custom_options.filter(category__iexact='Sub-Area').values_list('value', flat=True).distinct())
    sub_areas_set.update(records.exclude(sub_area__isnull=True).exclude(sub_area='').values_list('sub_area', flat=True).distinct())
    sub_areas = sorted([x for x in sub_areas_set if x])
    
    sections_set = set(records.order_by('section').values_list('section', flat=True).distinct().exclude(section=''))
    sections = sorted([x for x in sections_set if x])
    
    equipments_set = set(custom_options.filter(category__iexact='Equipment').values_list('value', flat=True).distinct())
    equipments_set.update(records.exclude(equipment__isnull=True).exclude(equipment='').exclude(equipment='NIL').values_list('equipment', flat=True).distinct())
    normalized_eqs_set = set(clean_equipment_name(x) for x in equipments_set if x.strip())
    equipments = sorted(list(normalized_eqs_set))
    
    sub_equipments_set = set(custom_options.filter(category__iexact='Sub-Equipment').values_list('value', flat=True).distinct())
    sub_equipments = sorted([x for x in sub_equipments_set if x])
    
    incharges_set = set(custom_options.filter(category__iexact='Shift Incharge').values_list('value', flat=True).distinct())
    incharges_set.update(records.order_by('shift_incharge').values_list('shift_incharge', flat=True).distinct().exclude(shift_incharge=''))
    incharges = sorted([x for x in incharges_set if x])
    
    actions_set = set(custom_options.filter(category__iexact='Action').values_list('value', flat=True).distinct())
    if not actions_set:
        actions_set.update([
            "Check motor body temperature and vibration levels",
            "Inspect belt tension, pulley alignment, and look for tear/slip",
            "Verify oil level in gearboxes and check for hydraulic leaks",
            "Inspect mechanical coupling, spindles, and foundation bolts tightness",
            "Verify limit switches operation and cable connection health"
        ])
    actions = sorted(list(actions_set))
    
    return {
        'agencies': agencies,
        'sub_agencies': sub_agencies,
        'sub_areas': sub_areas,
        'sections': sections,
        'equipments': equipments,
        'sub_equipments': sub_equipments,
        'incharges': incharges,
        'actions': actions
    }

@login_required
def dept_overview(request, dept_id):
    """
    Main overview and dashboard for department delays.
    Displays metrics, charts, upload features, and logs tables.
    """
    tab = request.GET.get('tab', 'dashboard').strip()
    if tab in ['summary', 'pareto', 'mttr_mtbf', 'capa_summary', 'checklist_summary', 'manual_checklist']:
        active_tab = tab
    else:
        active_tab = 'dashboard'
    date_start = request.GET.get('date_start', '').strip()
    date_end = request.GET.get('date_end', '').strip()

    # Set default date range if not specified
    today = timezone.localtime(timezone.now()).date()
    if not date_start:
        # Current Financial Year start (April 1st of the current financial year)
        if today.month >= 4:
            date_start = date(today.year, 4, 1).strftime('%Y-%m-%d')
        else:
            date_start = date(today.year - 1, 4, 1).strftime('%Y-%m-%d')
    
    if not date_end:
        date_end = today.strftime('%Y-%m-%d')

    days_span = 0
    if date_start and date_end:
        try:
            from datetime import datetime
            d1 = datetime.strptime(date_start, '%Y-%m-%d').date()
            d2 = datetime.strptime(date_end, '%Y-%m-%d').date()
            days_span = (d2 - d1).days
        except Exception:
            pass

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

        # Ensure default Crane options exist for E&I / SMS-II EOT Cranes if EOT or Crane is mentioned
        if int(dept_id) != 0:
            crane_exists = DelayDropdownOption.objects.filter(department=department, category='Sub-Agency', value__iexact='Crane').exists()
            if not crane_exists:
                # Seed Area 'Crane'
                DelayDropdownOption.objects.get_or_create(
                    department=department,
                    category='Sub-Agency',
                    value='Crane'
                )
                # Seed Equipment 'MAIN HOIST -1' with parent_value='Crane'
                DelayDropdownOption.objects.get_or_create(
                    department=department,
                    category='Equipment',
                    value='MAIN HOIST -1',
                    parent_value='Crane'
                )
                # Seed Equipment 'MAIN HOIST -2' with parent_value='Crane'
                DelayDropdownOption.objects.get_or_create(
                    department=department,
                    category='Equipment',
                    value='MAIN HOIST -2',
                    parent_value='Crane'
                )
                # Seed Actions for MAIN HOIST -1
                hoist_1_actions = [
                    "CHECK CONTACTOR AND ITS KIT",
                    "CHECK TIGHTNESS MAIN INCOMING MCCB",
                    "CHECK TIGHTNESS OF ALL CARDS & ITS POWER TERMINALS ASTAT DRIVE POWER MODULE",
                    "CHECK TIGHTNESS OF ALL CARDS & ITS POWER TERMINALS ASTAT DRIVE CONTROL MODULE",
                    "CHECK TIGHTNESS ALL CONTROL & POWER CONTACTORS AND ITS KITS",
                    "CHECK TIGHTNESS ALL CONTROL & POWER CONNECTIONS",
                    "CHECK TIGHTNESS ALL CONNECTION OF RESISTANCE BOX",
                    "CHECK TIGHTNESS GRAVITY LIMIT SWITCH OPERATING MECHANISM",
                    "CHECK TIGHTNESS RORATY LIMIT SWITCH OPERATING MECHANISM",
                    "CHECK TIGHTNESS TACHO CONNECTION & MOUNTING",
                    "CHECK TIGHTNESS ELECTROMAGNETIC BRAKE CONNECTION",
                    "ENSURE LIMIT SWITCH / BRAKE / TACHO OPERATION",
                    "CHECK TIGHTNESS OF MOTOR TERMINAL, CARBON BRUSH & SLIP RING",
                    "PROPER ARRANGEMENT TO COVER THE DRIVE PANELS AGAINST DUST",
                    "ENSURE THE HEAT EXCHANGER/DRIVE FAN IS HEALTHY OR NOT",
                    "CHECK PANEL COVER, RESISTANCE BOX COVER."
                ]
                for act in hoist_1_actions:
                    DelayDropdownOption.objects.get_or_create(
                        department=department,
                        category='Action',
                        value=act,
                        parent_value='MAIN HOIST -1'
                    )
                
                # Seed Actions for MAIN HOIST -2
                hoist_2_actions = [
                    "CHECK CONTACTOR AND ITS KIT",
                    "CHECK TIGHTNESS MAIN INCOMING MCCB",
                    "CHECK TIGHTNESS OF ALL CARDS & ITS POWER TERMINALS ASTAT DRIVE POWER MODULE",
                    "CHECK TIGHTNESS OF ALL CARDS & ITS POWER TERMINALS ASTAT DRIVE CONTROL MODULE",
                    "CHECK TIGHTNESS ALL CONTROL & POWER CONTACTORS AND ITS KITS",
                    "CHECK TIGHTNESS ALL CONTROL & POWER CONNECTIONS",
                    "CHECK TIGHTNESS ALL CONNECTION OF RESISTANCE BOX"
                ]
                for act in hoist_2_actions:
                    DelayDropdownOption.objects.get_or_create(
                        department=department,
                        category='Action',
                        value=act,
                        parent_value='MAIN HOIST -2'
                    )
    
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
        if days_span <= 60:
            # If date range is 60 days or less, show DAILY trend
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
        ).values('equipment').annotate(total=Sum('duration_mins'))
        
        py_eq_totals = {}
        for eb in equip_breakdown:
            cleaned = clean_equipment_name(eb['equipment'])
            if cleaned:
                py_eq_totals[cleaned] = py_eq_totals.get(cleaned, 0.0) + (eb['total'] or 0.0)
                
        sorted_py_eqs = sorted(py_eq_totals.items(), key=lambda x: x[1], reverse=True)
        equip_labels = [x[0] for x in sorted_py_eqs[:5]]
        equip_data = [round(x[1], 1) for x in sorted_py_eqs[:5]]
    
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
    sub_areas = autocompletes['sub_areas']
    sections = autocompletes['sections']
    equipments = autocompletes['equipments']
    sub_equipments = autocompletes['sub_equipments']
    incharges = autocompletes['incharges']
    actions = autocompletes['actions']
 
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
        Q(equipment__isnull=True) | Q(equipment='') | Q(equipment='-') | Q(equipment='NA') | Q(equipment='NIL')  # type: ignore
    ).values('equipment').annotate(total=Sum('duration_mins'))
    
    py_eq_totals_pareto = {}
    for eb in all_equip_breakdown:
        cleaned = clean_equipment_name(eb['equipment'])
        if cleaned:
            py_eq_totals_pareto[cleaned] = py_eq_totals_pareto.get(cleaned, 0.0) + (eb['total'] or 0.0)
            
    sorted_py_eqs_pareto = sorted(py_eq_totals_pareto.items(), key=lambda x: x[1], reverse=True)
    total_equip_mins = sum(x[1] for x in sorted_py_eqs_pareto)
    
    group_by_field = 'equipment'
    is_description = False
    
    # Fallback to description if no equipment data is available (like in SMS3 or Overall plant view)
    if total_equip_mins == 0:
        all_desc_breakdown = all_records.exclude(
            Q(description__isnull=True) | Q(description='') | Q(description='-') | Q(description='NA')  # type: ignore
        ).values('description').annotate(total=Sum('duration_mins'))
        
        py_desc_totals = {}
        for db in all_desc_breakdown:
            cleaned = (db['description'] or '').strip()
            if cleaned:
                py_desc_totals[cleaned] = py_desc_totals.get(cleaned, 0.0) + (db['total'] or 0.0)
                
        sorted_py_eqs_pareto = sorted(py_desc_totals.items(), key=lambda x: x[1], reverse=True)
        total_equip_mins = sum(x[1] for x in sorted_py_eqs_pareto)
        group_by_field = 'description'
        is_description = True

    equip_pareto = []
    running_equip_mins = 0
    for idx, (eq, total) in enumerate(sorted_py_eqs_pareto):
        running_equip_mins += total
        cum_percent = (running_equip_mins / total_equip_mins * 100) if total_equip_mins > 0 else 0.0
        equip_pareto.append({
            'equipment': eq or "N/A",
            'mins': round(total, 1),
            'percent': round((total / total_equip_mins * 100) if total_equip_mins > 0 else 0.0, 1),
            'cum_percent': round(cum_percent, 1),
            'rank': idx + 1,
            'is_vital': cum_percent <= 85.0 or idx == 0
        })

    # Pareto Frequency Calculation by Agency
    agency_counts = {}
    for r in all_records:
        ag = (r.agency or '').strip()
        if ag:
            agency_counts[ag] = agency_counts.get(ag, 0) + 1
    agency_frequency_sorted = sorted(agency_counts.items(), key=lambda x: x[1], reverse=True)
    top_agency_freq = agency_frequency_sorted[0][0] if agency_frequency_sorted else "N/A"
    top_agency_freq_count = agency_frequency_sorted[0][1] if agency_frequency_sorted else 0
    
    agency_pareto_freq = []
    running_counts = 0
    for idx, (ag, count) in enumerate(agency_frequency_sorted):
        running_counts += count
        cum_percent = (running_counts / total_events * 100) if total_events > 0 else 0.0
        agency_pareto_freq.append({
            'agency': ag,
            'count': count,
            'percent': round((count / total_events * 100) if total_events > 0 else 0.0, 1),
            'cum_percent': round(cum_percent, 1),
            'rank': idx + 1,
            'is_vital': cum_percent <= 85.0 or idx == 0
        })

    # Pareto Frequency Calculation by Equipment
    all_equip_counts = all_records.exclude(
        Q(equipment__isnull=True) | Q(equipment='') | Q(equipment='-') | Q(equipment='NA') | Q(equipment='NIL')
    ).values('equipment').annotate(total=Count('id'))
    
    py_eq_counts_pareto = {}
    for eb in all_equip_counts:
        cleaned = clean_equipment_name(eb['equipment'])
        if cleaned:
            py_eq_counts_pareto[cleaned] = py_eq_counts_pareto.get(cleaned, 0) + eb['total']
            
    sorted_py_eqs_counts = sorted(py_eq_counts_pareto.items(), key=lambda x: x[1], reverse=True)
    total_equip_counts = sum(x[1] for x in sorted_py_eqs_counts)
    
    if total_equip_counts == 0:
        all_desc_counts = all_records.exclude(
            Q(description__isnull=True) | Q(description='') | Q(description='-') | Q(description='NA')
        ).values('description').annotate(total=Count('id'))
        
        py_desc_counts = {}
        for db in all_desc_counts:
            cleaned = (db['description'] or '').strip()
            if cleaned:
                py_desc_counts[cleaned] = py_desc_counts.get(cleaned, 0) + db['total']
                
        sorted_py_eqs_counts = sorted(py_desc_counts.items(), key=lambda x: x[1], reverse=True)
        total_equip_counts = sum(x[1] for x in sorted_py_eqs_counts)

    equip_pareto_freq = []
    running_equip_counts = 0
    for idx, (eq, count) in enumerate(sorted_py_eqs_counts):
        running_equip_counts += count
        cum_percent = (running_equip_counts / total_equip_counts * 100) if total_equip_counts > 0 else 0.0
        equip_pareto_freq.append({
            'equipment': eq or "N/A",
            'count': count,
            'percent': round((count / total_equip_counts * 100) if total_equip_counts > 0 else 0.0, 1),
            'cum_percent': round(cum_percent, 1),
            'rank': idx + 1,
            'is_vital': cum_percent <= 85.0 or idx == 0
        })

    # Internal Agency Bottlenecks
    internal_recs = all_records.filter(agency_type='Internal')
    internal_eqs = (
        internal_recs.exclude(Q(equipment__isnull=True) | Q(equipment='') | Q(equipment='-') | Q(equipment='NA'))
        .values('equipment')
        .annotate(total=Sum('duration_mins'))
        .order_by('-total')
    )
    from collections import defaultdict
    internal_grouped = defaultdict(float)
    for eq in internal_eqs:
        cleaned = clean_equipment_name(eq['equipment']) or "General"
        internal_grouped[cleaned] += (eq['total'] or 0.0)
    sorted_internal = sorted(internal_grouped.items(), key=lambda x: x[1], reverse=True)[:5]
    internal_list = [{'name': name, 'mins': round(mins, 1)} for name, mins in sorted_internal]

    internal_summaries = []
    for item in internal_list[:3]:
        recs = internal_recs.filter(equipment__icontains=item['name']).exclude(description__isnull=True).exclude(description='').order_by('-duration_mins')[:2]
        reasons = [r.description for r in recs if r.description]
        if reasons:
            internal_summaries.append({
                'equipment': item['name'],
                'reasons': reasons
            })

    # External Agency Bottlenecks
    external_recs = all_records.filter(agency_type='External')
    external_ags = (
        external_recs.exclude(Q(agency__isnull=True) | Q(agency='') | Q(agency='-') | Q(agency='NA'))
        .values('agency')
        .annotate(total=Sum('duration_mins'))
        .order_by('-total')
    )
    external_grouped = defaultdict(float)
    for ag in external_ags:
        cleaned = ag['agency'] or "Other External"
        external_grouped[cleaned] += (ag['total'] or 0.0)
    sorted_external = sorted(external_grouped.items(), key=lambda x: x[1], reverse=True)[:5]
    external_list = [{'name': name, 'mins': round(mins, 1)} for name, mins in sorted_external]

    external_summaries = []
    for item in external_list[:3]:
        recs = external_recs.filter(agency__icontains=item['name']).exclude(description__isnull=True).exclude(description='').order_by('-duration_mins')[:2]
        reasons = [r.description for r in recs if r.description]
        if reasons:
            external_summaries.append({
                'agency': item['name'],
                'reasons': reasons
            })

    import json
    internal_labels_json = json.dumps([x['name'] for x in internal_list])
    internal_data_json = json.dumps([x['mins'] for x in internal_list])
    external_labels_json = json.dumps([x['name'] for x in external_list])
    external_data_json = json.dumps([x['mins'] for x in external_list])

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
        act_val = (r.action or '').lower()
        matched = set()
        for kw, category in keywords_map.items():
            if kw in desc or kw in why or kw in act_val:
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
    status_filter = request.GET.get('status', 'all').strip()
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
            'sub_areas': sub_areas,
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

    # MTTR/MTBF calculations
    from django.db.models import Min, Max
    import datetime
    d1 = None
    d2 = None
    try:
        if date_start:
            d1 = datetime.datetime.strptime(date_start, '%Y-%m-%d').date()
        if date_end:
            d2 = datetime.datetime.strptime(date_end, '%Y-%m-%d').date()
    except Exception:
        pass
        
    if not d1 or not d2:
        if all_records.exists():
            d1 = all_records.aggregate(Min('date'))['date__min'] or datetime.date.today().replace(day=1)
            d2 = all_records.aggregate(Max('date'))['date__max'] or datetime.date.today()
        else:
            d1 = datetime.date.today().replace(day=1)
            d2 = datetime.date.today()
            
    total_days = max((d2 - d1).days + 1, 1)
    total_calendar_hrs = total_days * 24.0

    from collections import defaultdict
    reliability_data = defaultdict(lambda: {
        'total_downtime_mins': 0.0,
        'total_shutdown_mins': 0.0,
        'failures_count': 0,
        'total_count': 0,
    })
    
    for r in all_records:
        key = (r.sub_agency or 'N/A', r.equipment or 'N/A')
        duration = r.duration_mins or 0.0
        agency_clean = (r.agency or '').strip().lower()
        is_planned = 'planned' in agency_clean or 'shutdown' in agency_clean
        
        reliability_data[key]['total_count'] += 1
        if is_planned:
            reliability_data[key]['total_shutdown_mins'] += duration
        else:
            reliability_data[key]['total_downtime_mins'] += duration
            reliability_data[key]['failures_count'] += 1

    # Fetch manual shutdown settings for the department
    if department.id == 0:
        shutdown_settings = {
            (s.sub_area, s.equipment): s.shutdown_hrs
            for s in EquipmentShutdownSetting.objects.all()
        }
    else:
        shutdown_settings = {
            (s.sub_area, s.equipment): s.shutdown_hrs
            for s in EquipmentShutdownSetting.objects.filter(department=department)
        }

    mttr_mtbf_list = []
    for (area, equip), stats in reliability_data.items():
        # Use manual shutdown hours if exists, otherwise aggregate from delays logs
        shutdown_hrs = shutdown_settings.get((area or 'N/A', equip or 'N/A'), stats['total_shutdown_mins'] / 60.0)
        downtime_hrs = stats['total_downtime_mins'] / 60.0
        failures = stats['failures_count']
        total_events = stats['total_count']
        
        # MTTR (Hrs)
        mttr = downtime_hrs / failures if failures > 0 else 0.0
        
        # MTBF (Hrs)
        op_time_hrs = max(total_calendar_hrs - downtime_hrs - shutdown_hrs, 0.0)
        mtbf = op_time_hrs / failures if failures > 0 else total_calendar_hrs
        
        # Availability %
        divisor = max(total_calendar_hrs - shutdown_hrs, 0.1)
        availability = (op_time_hrs / divisor) * 100.0
        if availability > 100.0:
            availability = 100.0
            
        mttr_mtbf_list.append({
            'area': area,
            'equipment': equip,
            'shutdown_hrs': round(shutdown_hrs, 1),
            'downtime_hrs': round(downtime_hrs, 1),
            'failures': failures,
            'repeatability': total_events,
            'mttr': round(mttr, 1),
            'mtbf': round(mtbf, 1),
            'availability': round(availability, 2)
        })
        
    mttr_mtbf_list.sort(key=lambda x: x['downtime_hrs'], reverse=True)

    # Fetch CAPA reports
    from tpm.models import CAPAReport
    if department.id == 0:
        capa_reports = CAPAReport.objects.all().order_by('-id')
    else:
        capa_reports = CAPAReport.objects.filter(department=department).order_by('-id')

    context = {
        'department': department,
        'active_tab': active_tab,
        'is_description': is_description,
        'is_monthly_trend': days_span > 60,
        'departments': departments,
        'date_start': date_start,
        'date_end': date_end,
        'total_calendar_hrs': total_calendar_hrs,
        'mttr_mtbf_list': mttr_mtbf_list,
        'mttr_mtbf_list_json': json.dumps(mttr_mtbf_list),
        'capa_reports': capa_reports,
        'internal_list': internal_list,
        'internal_summaries': internal_summaries,
        'external_list': external_list,
        'external_summaries': external_summaries,
        'internal_labels_json': internal_labels_json,
        'internal_data_json': internal_data_json,
        'external_labels_json': external_labels_json,
        'external_data_json': external_data_json,
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
        
        # Pareto Frequency JSONs
        'pareto_freq_labels_json': json.dumps([x['agency'] for x in agency_pareto_freq]),
        'pareto_freq_count_json': json.dumps([x['count'] for x in agency_pareto_freq]),
        'pareto_freq_cum_json': json.dumps([x['cum_percent'] for x in agency_pareto_freq]),
        
        # Lists
        'records': records_list, # Limit initially
        'sheets_parsed': sheets_parsed,
        'uploads': uploads,
        
        # Pareto Context Lists
        'agency_pareto': agency_pareto,
        'equip_pareto': equip_pareto[:10], # Top 10 for display
        'agency_pareto_freq': agency_pareto_freq,
        'equip_pareto_freq': equip_pareto_freq[:10],
        'top_agency_freq': top_agency_freq,
        'top_agency_freq_count': top_agency_freq_count,
        
        # Mitigation
        'mitigation_categories': sorted_keywords,
        'top_mitigation_category': sorted_keywords[0]['category'] if sorted_keywords and sorted_keywords[0]['count'] > 0 else "N/A",
        
        # Autocomplete
        'agencies': agencies,
        'table_agencies': sorted(list(set(agencies + list(Department.objects.all().values_list('name', flat=True))))),
        'sub_agencies': sub_agencies,
        'sub_areas': sub_areas,
        'sections': sections,
        'equipments': equipments,
        'equipments_list': equipments_list,
        'sub_equipments': sub_equipments,
        'incharges': incharges,
        'actions': actions,
        
        # Fetch Checklist items from manual entry
        'checklist_items': MaintenanceChecklistItem.objects.select_related('checklist', 'checklist__department').order_by('-checklist__date', '-checklist__id', 'id') if department.id == 0 else MaintenanceChecklistItem.objects.filter(
            checklist__department=department
        ).select_related('checklist').order_by('-checklist__date', '-checklist__id', 'id'),

        # Sidebar/Layout settings
        'active_dept_id': department.id,
        'active_module': 'Delays',
        'active_section': 'department_module',
    }
    
    # Serialize dropdown options for Alpine.js hierarchy
    dropdown_options_list = []
    if department.id != 0:
        for opt in DelayDropdownOption.objects.filter(department=department):
            dropdown_options_list.append({
                'category': opt.category,
                'value': opt.value,
                'parent_value': opt.parent_value or '',
            })
    context['dropdown_options_json'] = json.dumps(dropdown_options_list)
    
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
    sub_area_filter = request.GET.get('sub_area', '').strip()
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
            Q(why__icontains=query) |
            Q(action__icontains=query)  # type: ignore
        )
        
    if agency_type_filter:
        records = records.filter(agency_type=agency_type_filter)

    if agency_filter:
        records = records.filter(agency=agency_filter)

        
    if sub_agency_filter:
        records = records.filter(sub_agency=sub_agency_filter)
        
    if sub_area_filter:
        records = records.filter(sub_area=sub_area_filter)
        
    if equipment_filter:
        eq_filter = get_equipment_filter_q(equipment_filter)
        records = records.filter(eq_filter)
        
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
    status_filter = request.GET.get('status', 'all').strip()
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
    sub_areas = autocompletes['sub_areas']
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
        'sub_areas': sub_areas,
        'sub_equipments': sub_equipments,
    })


@login_required
def new_record(request, dept_id):
    """
    Create a new manual delay record entry.
    """
    department = get_object_or_404(Department, id=dept_id)
    
    # Get safe next redirect url
    next_url = request.GET.get('next') or request.META.get('HTTP_REFERER')
    if next_url:
        from urllib.parse import urlparse
        parsed = urlparse(next_url)
        if parsed.netloc and parsed.netloc != request.get_host():
            next_url = None
        else:
            next_url = parsed.path
            if parsed.query:
                next_url += f"?{parsed.query}"
    if not next_url or '/records/' in next_url:
        next_url = f"/delays/department/{dept_id}/?tab=summary"
    
    if not user_can_edit_module(request.user, department, 'Delays'):
        messages.error(request, "You do not have editing permissions to log manual entries.")
        return redirect(next_url)
        
    if request.method == 'POST':
        form = DelayRecordForm(request.POST, department=department)
        if form.is_valid():
            record = form.save(commit=False)
            record.department = department
            record.sheet_name = 'Manual Entry'
            record.save()
            messages.success(request, f"Manual delay entry on {record.date} successfully logged.")
            return redirect(next_url)
    else:
        form = DelayRecordForm(department=department)
        
    # Fetch autocompletes
    records = DelayRecord.objects.filter(department=department)
    autocompletes = get_department_autocompletes(department, records)
    agencies = autocompletes['agencies']
    sub_agencies = autocompletes['sub_agencies']
    sub_areas = autocompletes['sub_areas']
    sections = autocompletes['sections']
    equipments = autocompletes['equipments']
    sub_equipments = autocompletes['sub_equipments']
    incharges = autocompletes['incharges']
    
    context = {
        'form': form,
        'department': department,
        'active_tab': 'entry',
        'is_edit': False,
        'can_edit': True,
        'next_url': next_url,
        'agencies': agencies,
        'sub_agencies': sub_agencies,
        'sub_areas': sub_areas,
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
    
    # Get safe next redirect url
    next_url = request.GET.get('next') or request.META.get('HTTP_REFERER')
    if next_url:
        from urllib.parse import urlparse
        parsed = urlparse(next_url)
        if parsed.netloc and parsed.netloc != request.get_host():
            next_url = None
        else:
            next_url = parsed.path
            if parsed.query:
                next_url += f"?{parsed.query}"
    if not next_url or '/records/' in next_url:
        next_url = f"/delays/department/{dept_id}/?tab=summary"
        
    if not user_can_edit_module(request.user, department, 'Delays'):
        messages.error(request, "You do not have permissions to edit records.")
        return redirect(next_url)
        
    # Check if locked and verify admin permission
    if record.is_locked and not request.user.is_admin():
        messages.error(request, "This record is locked and can only be edited by an Admin.")
        return redirect(next_url)
        
    if request.method == 'POST':
        form = DelayRecordForm(request.POST, instance=record, department=department)
        if form.is_valid():
            form.save()
            messages.success(request, "Delay record updated successfully.")
            return redirect(next_url)
    else:
        form = DelayRecordForm(instance=record, department=department)
        
    # Fetch autocompletes
    records = DelayRecord.objects.filter(department=department)
    autocompletes = get_department_autocompletes(department, records)
    agencies = autocompletes['agencies']
    sub_agencies = autocompletes['sub_agencies']
    sub_areas = autocompletes['sub_areas']
    sections = autocompletes['sections']
    equipments = autocompletes['equipments']
    sub_equipments = autocompletes['sub_equipments']
    incharges = autocompletes['incharges']
    
    context = {
        'form': form,
        'department': department,
        'active_tab': 'entry',
        'record': record,
        'is_edit': True,
        'can_edit': True,
        'next_url': next_url,
        'is_admin': request.user.is_admin(),
        'agencies': agencies,
        'sub_agencies': sub_agencies,
        'sub_areas': sub_areas,
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
            record.agency = normalize_agency_name(agency_val)
            if Department.objects.filter(name=record.agency).exists():
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
            'is_editing': False,
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
    pareto_type = request.GET.get('pareto_type', 'time').strip()
    
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
    
    # Apply date filters if present in parameters
    date_start = request.GET.get('date_start', '').strip()
    date_end = request.GET.get('date_end', '').strip()
    if date_start:
        records = records.filter(date__gte=date_start)
    if date_end:
        records = records.filter(date__lte=date_end)
        
    total_mins = records.aggregate(Sum('duration_mins'))['duration_mins__sum'] or 0.0
    total_events = records.count()
    
    # --- Time-based Agency Pareto ---
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

    # --- Time-based Equipment Pareto ---
    all_equip_breakdown = records.exclude(
        Q(equipment__isnull=True) | Q(equipment='') | Q(equipment='-') | Q(equipment='NA') | Q(equipment='NIL')
    ).values('equipment').annotate(total=Sum('duration_mins')).order_by('-total')
    
    py_eq_totals_pareto = {}
    for eb in all_equip_breakdown:
        cleaned = clean_equipment_name(eb['equipment'])
        if cleaned:
            py_eq_totals_pareto[cleaned] = py_eq_totals_pareto.get(cleaned, 0.0) + (eb['total'] or 0.0)
            
    sorted_py_eqs_pareto = sorted(py_eq_totals_pareto.items(), key=lambda x: x[1], reverse=True)
    total_equip_mins = sum(x[1] for x in sorted_py_eqs_pareto)
    
    group_by_field = 'equipment'
    is_description = False
    
    # Fallback to description if no equipment data is available
    if total_equip_mins == 0:
        all_desc_breakdown = records.exclude(
            Q(description__isnull=True) | Q(description='') | Q(description='-') | Q(description='NA')
        ).values('description').annotate(total=Sum('duration_mins')).order_by('-total')
        
        py_desc_totals = {}
        for db in all_desc_breakdown:
            cleaned = (db['description'] or '').strip()
            if cleaned:
                py_desc_totals[cleaned] = py_desc_totals.get(cleaned, 0.0) + (db['total'] or 0.0)
                
        sorted_py_eqs_pareto = sorted(py_desc_totals.items(), key=lambda x: x[1], reverse=True)
        total_equip_mins = sum(x[1] for x in sorted_py_eqs_pareto)
        group_by_field = 'description'
        is_description = True

    equip_pareto = []
    running_equip_mins = 0
    for idx, (eq, total) in enumerate(sorted_py_eqs_pareto):
        running_equip_mins += total
        cum_percent = (running_equip_mins / total_equip_mins * 100) if total_equip_mins > 0 else 0.0
        equip_pareto.append({
            'equipment': eq or "N/A",
            'mins': round(total, 1),
            'percent': round((total / total_equip_mins * 100) if total_equip_mins > 0 else 0.0, 1),
            'cum_percent': round(cum_percent, 1),
            'rank': idx + 1,
            'is_vital': cum_percent <= 85.0 or idx == 0
        })

    # --- Frequency-based Agency Pareto ---
    agency_counts = {}
    for r in records:
        ag = (r.agency or '').strip()
        if ag:
            agency_counts[ag] = agency_counts.get(ag, 0) + 1
    agency_frequency_sorted = sorted(agency_counts.items(), key=lambda x: x[1], reverse=True)
    top_agency_freq = agency_frequency_sorted[0][0] if agency_frequency_sorted else "N/A"
    top_agency_freq_count = agency_frequency_sorted[0][1] if agency_frequency_sorted else 0
    
    agency_pareto_freq = []
    running_counts = 0
    for idx, (ag, count) in enumerate(agency_frequency_sorted):
        running_counts += count
        cum_percent = (running_counts / total_events * 100) if total_events > 0 else 0.0
        agency_pareto_freq.append({
            'agency': ag,
            'count': count,
            'percent': round((count / total_events * 100) if total_events > 0 else 0.0, 1),
            'cum_percent': round(cum_percent, 1),
            'rank': idx + 1,
            'is_vital': cum_percent <= 85.0 or idx == 0
        })

    # --- Frequency-based Equipment Pareto ---
    all_equip_counts = records.exclude(
        Q(equipment__isnull=True) | Q(equipment='') | Q(equipment='-') | Q(equipment='NA') | Q(equipment='NIL')
    ).values('equipment').annotate(total=Count('id'))
    
    py_eq_counts_pareto = {}
    for eb in all_equip_counts:
        cleaned = clean_equipment_name(eb['equipment'])
        if cleaned:
            py_eq_counts_pareto[cleaned] = py_eq_counts_pareto.get(cleaned, 0) + eb['total']
            
    sorted_py_eqs_counts = sorted(py_eq_counts_pareto.items(), key=lambda x: x[1], reverse=True)
    total_equip_counts = sum(x[1] for x in sorted_py_eqs_counts)
    
    if total_equip_counts == 0:
        all_desc_counts = records.exclude(
            Q(description__isnull=True) | Q(description='') | Q(description='-') | Q(description='NA')
        ).values('description').annotate(total=Count('id'))
        
        py_desc_counts = {}
        for db in all_desc_counts:
            cleaned = (db['description'] or '').strip()
            if cleaned:
                py_desc_counts[cleaned] = py_desc_counts.get(cleaned, 0) + db['total']
                
        sorted_py_eqs_counts = sorted(py_desc_counts.items(), key=lambda x: x[1], reverse=True)
        total_equip_counts = sum(x[1] for x in sorted_py_eqs_counts)

    equip_pareto_freq = []
    running_equip_counts = 0
    for idx, (eq, count) in enumerate(sorted_py_eqs_counts):
        running_equip_counts += count
        cum_percent = (running_equip_counts / total_equip_counts * 100) if total_equip_counts > 0 else 0.0
        equip_pareto_freq.append({
            'equipment': eq or "N/A",
            'count': count,
            'percent': round((count / total_equip_counts * 100) if total_equip_counts > 0 else 0.0, 1),
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
        'agency_pareto_freq': agency_pareto_freq,
        'equip_pareto_freq': equip_pareto_freq[:10],
        'top_agency': top_agency,
        'top_agency_mins': top_agency_mins,
        'top_agency_freq': top_agency_freq,
        'top_agency_freq_count': top_agency_freq_count,
        'is_description': is_description,
        'pareto_type': pareto_type,
        
        # Safe JSONs
        'pareto_labels_json': json.dumps([x['agency'] for x in agency_pareto]),
        'pareto_mins_json': json.dumps([x['mins'] for x in agency_pareto]),
        'pareto_cum_json': json.dumps([x['cum_percent'] for x in agency_pareto]),
        'pareto_freq_labels_json': json.dumps([x['agency'] for x in agency_pareto_freq]),
        'pareto_freq_count_json': json.dumps([x['count'] for x in agency_pareto_freq]),
        'pareto_freq_cum_json': json.dumps([x['cum_percent'] for x in agency_pareto_freq]),
    }
    return render(request, 'delays/partials/_pareto_content.html', context)


@login_required
def pareto_agency(request, dept_id):
    """
    Returns the equipment Pareto Analysis for a specific agency (HTMX endpoint).
    """
    agency_name = request.GET.get('agency', '')
    pareto_type = request.GET.get('pareto_type', 'time').strip()
    
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
        
    # Apply date filters if present in parameters
    date_start = request.GET.get('date_start', '').strip()
    date_end = request.GET.get('date_end', '').strip()
    if date_start:
        records = records.filter(date__gte=date_start)
    if date_end:
        records = records.filter(date__lte=date_end)

    total_agency_mins = records.aggregate(Sum('duration_mins'))['duration_mins__sum'] or 0.0
    total_agency_events = records.count()
    
    group_by_field = 'equipment'
    is_description = False
    
    if pareto_type == 'frequency':
        # Pareto Calculation by Equipment *within* that agency (as per frequency)
        equip_breakdown = records.exclude(
            Q(equipment__isnull=True) | Q(equipment='') | Q(equipment='-') | Q(equipment='NA') | Q(equipment='None') | Q(equipment='NIL')
        ).values('equipment').annotate(total=Count('id')).order_by('-total')
        
        total_units = sum(x['total'] for x in equip_breakdown)
        
        if total_units == 0:
            equip_breakdown = records.exclude(
                Q(description__isnull=True) | Q(description='') | Q(description='-') | Q(description='NA')
            ).values('description').annotate(total=Count('id')).order_by('-total')
            total_units = sum(x['total'] for x in equip_breakdown)
            group_by_field = 'description'
            is_description = True
            
        equip_pareto = []
        running_units = 0
        for idx, eb in enumerate(equip_breakdown):
            running_units += eb['total']
            cum_percent = (running_units / total_units * 100) if total_units > 0 else 0.0
            label_val = eb[group_by_field] or "N/A"
            equip_pareto.append({
                'label': label_val,
                'count': eb['total'],
                'percent': round((eb['total'] / total_units * 100) if total_units > 0 else 0.0, 1),
                'cum_percent': round(cum_percent, 1),
                'rank': idx + 1,
                'is_vital': cum_percent <= 85.0 or idx == 0
            })
            
        top_equipment = equip_pareto[0]['label'] if equip_pareto else "N/A"
        top_equipment_val = f"{equip_pareto[0]['count']} events" if equip_pareto else "0 events"
    else:
        # Pareto Calculation by Equipment *within* that agency (as per downtime mins)
        equip_breakdown = records.exclude(
            Q(equipment__isnull=True) | Q(equipment='') | Q(equipment='-') | Q(equipment='NA') | Q(equipment='None') | Q(equipment='NIL')
        ).values('equipment').annotate(total=Sum('duration_mins')).order_by('-total')
        
        total_units = sum(x['total'] for x in equip_breakdown)
        
        if total_units == 0:
            equip_breakdown = records.exclude(
                Q(description__isnull=True) | Q(description='') | Q(description='-') | Q(description='NA')
            ).values('description').annotate(total=Sum('duration_mins')).order_by('-total')
            total_units = sum(x['total'] for x in equip_breakdown)
            group_by_field = 'description'
            is_description = True
            
        equip_pareto = []
        running_units = 0
        for idx, eb in enumerate(equip_breakdown):
            running_units += eb['total']
            cum_percent = (running_units / total_units * 100) if total_units > 0 else 0.0
            label_val = eb[group_by_field] or "N/A"
            equip_pareto.append({
                'label': label_val,
                'mins': round(eb['total'], 1),
                'percent': round((eb['total'] / total_units * 100) if total_units > 0 else 0.0, 1),
                'cum_percent': round(cum_percent, 1),
                'rank': idx + 1,
                'is_vital': cum_percent <= 85.0 or idx == 0
            })
            
        top_equipment = equip_pareto[0]['label'] if equip_pareto else "N/A"
        top_equipment_val = f"{equip_pareto[0]['mins']} mins" if equip_pareto else "0 mins"

    context = {
        'department': department,
        'agency_name': agency_name,
        'equip_pareto': equip_pareto,
        'total_mins': round(total_agency_mins, 1),
        'total_events': total_agency_events,
        'top_equipment': top_equipment,
        'top_equipment_val': top_equipment_val,
        'is_description': is_description,
        'pareto_type': pareto_type,
        
        'pareto_labels_json': json.dumps([x['label'] for x in equip_pareto[:15]]),
        'pareto_values_json': json.dumps([x['count'] if pareto_type == 'frequency' else x['mins'] for x in equip_pareto[:15]]),
        'pareto_cum_json': json.dumps([x['cum_percent'] for x in equip_pareto[:15]]),
    }
    return render(request, 'delays/partials/_pareto_agency_content.html', context)


@login_required
def manage_options(request, dept_id):
    """
    Allows adding and removing custom options (Agency, Sub-Agency, Equipment, Sub-Equipment) per department.
    """
    department = get_object_or_404(Department, id=dept_id)
    if not user_can_edit_module(request.user, department, 'Delays'):
        messages.error(request, "You do not have permission to manage dropdown options.")
        return redirect('delays:dept_overview', dept_id=dept_id)
    def capitalize_first_letters(s):
        if not s:
            return s
        return ' '.join(word[0].upper() + word[1:] if word else '' for word in s.split(' '))

    if request.method == 'POST':
        action = request.POST.get('action')
        if action == 'add':
            category = request.POST.get('category', '').strip()
            value = capitalize_first_letters(request.POST.get('value', '').strip())
            raw_parent = request.POST.get('parent_value', '').strip() or None
            
            if category and value:
                if category == 'Shift Incharge':
                    role = capitalize_first_letters(request.POST.get('role', '').strip())
                    phone = request.POST.get('phone', '').strip()
                    parent_value = f"{role}|{phone}"
                else:
                    if category == 'Equipment' and raw_parent:
                        if raw_parent.upper() in ['A', 'B', 'C']:
                            parent_value = raw_parent.upper()
                        else:
                            parent_value = raw_parent
                    elif category == 'Action' and raw_parent:
                        parent_value = raw_parent
                    else:
                        parent_value = capitalize_first_letters(raw_parent)
                
                value_clean = normalize_agency_name(value) if category.lower() == 'agency' else value
                option, created = DelayDropdownOption.objects.get_or_create(
                    department=department,
                    category=category,
                    value=value_clean,
                    parent_value=parent_value
                )
                if created:
                    messages.success(request, f"Option '{value_clean}' added to '{category}' successfully.")
                else:
                    messages.info(request, f"Option '{value_clean}' already exists in '{category}'.")
            else:
                messages.error(request, "Category and value are required.")
                
        elif action == 'delete':
            option_id = request.POST.get('option_id')
            option = get_object_or_404(DelayDropdownOption, id=option_id, department=department)
            val = option.value
            cat = option.category
            option.delete()
            messages.success(request, f"Option '{val}' removed from '{cat}'.")
            
        elif action == 'edit':
            option_id = request.POST.get('option_id')
            option = get_object_or_404(DelayDropdownOption, id=option_id, department=department)
            new_value = capitalize_first_letters(request.POST.get('value', '').strip())
            cat = option.category
            
            if new_value:
                old_val = option.value
                if cat == 'Shift Incharge':
                    role = capitalize_first_letters(request.POST.get('role', '').strip())
                    phone = request.POST.get('phone', '').strip()
                    parent_value = f"{role}|{phone}"
                else:
                    raw_parent = request.POST.get('parent_value', '').strip() or None
                    if cat == 'Equipment' and raw_parent:
                        if raw_parent.upper() in ['A', 'B', 'C']:
                            parent_value = raw_parent.upper()
                        else:
                            parent_value = raw_parent
                    elif cat == 'Action' and raw_parent:
                        parent_value = raw_parent
                    else:
                        parent_value = capitalize_first_letters(raw_parent)
                
                option.value = normalize_agency_name(new_value) if cat.lower() == 'agency' else new_value
                option.parent_value = parent_value
                try:
                    option.save()
                    messages.success(request, f"Option '{old_val}' updated to '{option.value}' successfully.")
                except Exception as e:
                    messages.error(request, f"Error saving option: {str(e)}")
            else:
                messages.error(request, "Value cannot be empty.")
            
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
            val_clean = normalize_agency_name(val)
            DelayDropdownOption.objects.get_or_create(
                department=department,
                category='Agency',
                value=val_clean
            )
            
        db_sub_agencies = records.values_list('sub_agency', flat=True).distinct().exclude(sub_agency='')
        for val in db_sub_agencies:
            DelayDropdownOption.objects.get_or_create(
                department=department,
                category='Sub-Agency',
                value=val
            )
            
        db_sub_areas = records.values_list('sub_area', flat=True).distinct().exclude(sub_area='')
        for val in db_sub_areas:
            DelayDropdownOption.objects.get_or_create(
                department=department,
                category='Sub-Area',
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
            
        db_incharges = records.values_list('shift_incharge', flat=True).distinct().exclude(shift_incharge='')
        for val in db_incharges:
            DelayDropdownOption.objects.get_or_create(
                department=department,
                category='Shift Incharge',
                value=val
            )

    options = DelayDropdownOption.objects.filter(department=department).order_by('category', 'value')
    
    # Predefined suggested categories
    suggested_categories = ['Agency', 'Sub-Agency', 'Sub-Area', 'Equipment', 'Sub-Equipment', 'Shift Incharge', 'Action']
    db_categories = list(options.values_list('category', flat=True).distinct())
    for cat in db_categories:
        if cat not in suggested_categories:
            suggested_categories.append(cat)

    for opt in options:
        if opt.category == 'Shift Incharge' and opt.parent_value:
            parts = opt.parent_value.split('|')
            opt.role = parts[0] if len(parts) > 0 else ''
            opt.phone = parts[1] if len(parts) > 1 else ''
        else:
            opt.role = ''
            opt.phone = ''

    areas = sorted(list(set(options.filter(category='Sub-Agency').values_list('value', flat=True))))
    equipments = sorted(list(set(options.filter(category='Equipment').values_list('value', flat=True))))

    context = {
        'department': department,
        'active_tab': 'options',
        'options': options,
        'suggested_categories': suggested_categories,
        'active_dept_id': department.id,
        'active_module': 'Delays',
        'active_section': 'department_module',
        'is_manage_options_page': True,
        'can_edit': True,
        'active_tab': request.GET.get('tab', 'Agency'),
        'areas': areas,
        'equipments': equipments,
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


from django.views.decorators.csrf import csrf_exempt

@csrf_exempt
def save_shutdown(request, dept_id):
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            sub_area = data.get('sub_area') or 'N/A'
            equipment = data.get('equipment') or 'N/A'
            shutdown_hrs = float(data.get('shutdown_hrs', 0.0))
            
            department = get_object_or_404(Department, id=dept_id)
            
            setting, created = EquipmentShutdownSetting.objects.update_or_create(
                department=department,
                sub_area=sub_area,
                equipment=equipment,
                defaults={'shutdown_hrs': shutdown_hrs}
            )
            return JsonResponse({'status': 'success', 'shutdown_hrs': setting.shutdown_hrs})
        except Exception as e:
            return JsonResponse({'status': 'error', 'message': str(e)}, status=400)
    return JsonResponse({'status': 'error', 'message': 'Invalid request method'}, status=405)


@login_required
def create_checklist(request, dept_id):
    if request.method == 'POST':
        try:
            department = get_object_or_404(Department, id=dept_id)
            data = json.loads(request.body)
            
            agency_type = data.get('agency_type', 'Internal')
            responsible_agency = data.get('responsible_agency', '')
            area = data.get('area', '')
            sub_area = data.get('sub_area', '')
            equipment = data.get('equipment', '')
            sub_equipment = data.get('sub_equipment', '')
            shift_incharge = data.get('shift_incharge', '')
            items_data = data.get('items', [])
            
            if not responsible_agency:
                return JsonResponse({'status': 'error', 'message': 'Responsible agency is required.'}, status=400)
            
            # Group items by equipment
            from collections import defaultdict
            items_by_eq = defaultdict(list)
            
            for item in items_data:
                eq_name = item.get('equipment', equipment) or ''
                items_by_eq[eq_name].append(item)
                
            if not items_by_eq:
                # Fallback if items list is empty
                checklist = MaintenanceChecklist.objects.create(
                    department=department,
                    agency_type=agency_type,
                    responsible_agency=responsible_agency,
                    area=area,
                    sub_area=sub_area,
                    equipment=equipment,
                    sub_equipment=sub_equipment,
                    shift_incharge=shift_incharge,
                    created_by=request.user
                )
                return JsonResponse({'status': 'success', 'checklist_id': checklist.id})
                
            last_checklist_id = None
            for eq_name, group in items_by_eq.items():
                checklist = MaintenanceChecklist.objects.create(
                    department=department,
                    agency_type=agency_type,
                    responsible_agency=responsible_agency,
                    area=area,
                    sub_area=sub_area,
                    equipment=eq_name,
                    sub_equipment=sub_equipment if eq_name == equipment else '',
                    shift_incharge=shift_incharge,
                    created_by=request.user
                )
                last_checklist_id = checklist.id
                
                for item in group:
                    action_item = item.get('action_item', '')
                    status = item.get('status', 'OK')
                    remarks = item.get('remarks', '')
                    if action_item:
                        MaintenanceChecklistItem.objects.create(
                            checklist=checklist,
                            action_item=action_item,
                            status=status,
                            remarks=remarks
                        )
            return JsonResponse({'status': 'success', 'checklist_id': checklist.id})
        except Exception as e:
            return JsonResponse({'status': 'error', 'message': str(e)}, status=400)
    return JsonResponse({'status': 'error', 'message': 'Invalid request method'}, status=405)


@login_required
def delete_checklist_item(request, dept_id, item_id):
    if int(dept_id) == 0:
        department = get_object_or_404(Department, id=0) if Department.objects.filter(id=0).exists() else None
        can_edit = request.user.is_admin()
    else:
        department = get_object_or_404(Department, id=dept_id)
        can_edit = user_can_edit_module(request.user, department, 'Delays')
        
    if not can_edit:
        messages.error(request, "You do not have permission to delete checklist items.")
        return redirect('delays:dept_overview', dept_id=dept_id)
        
    item = get_object_or_404(MaintenanceChecklistItem, id=item_id)
    checklist = item.checklist
    
    # If not department 0 (overall), check department of the checklist matches
    if int(dept_id) != 0 and checklist.department != department:
        messages.error(request, "Permission denied.")
        return redirect('delays:dept_overview', dept_id=dept_id)
        
    item.delete()
    
    # If no items left under this checklist, delete checklist as well
    if not checklist.items.exists():
        checklist.delete()
        
    messages.success(request, "Checklist item deleted successfully.")
    return redirect(f"/delays/department/{dept_id}/?tab=checklist_summary")

