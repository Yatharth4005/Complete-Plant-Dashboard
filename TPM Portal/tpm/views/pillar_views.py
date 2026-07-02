import json
import datetime
from django.shortcuts import render, get_object_or_404
from django.http import HttpResponse, HttpResponseForbidden
from django.views.decorators.http import require_POST
from django.contrib.auth.decorators import login_required
from tpm.models import Department, PillarEntry, KPIValue, CustomKPIDefinition
from tpm.utils.decorators import dept_access_required
from tpm.utils.kpi_definitions import KPI_DEFINITIONS
from tpm.utils.calculations import compute_achievement, compute_PRODUCTION, parse_period, get_date_range_q, aggregate_kpi_actual, get_jh_kaizen_count, get_jh_kaizen_count_range
from tpm.utils.toasts import render_toast
from portal.utils.access import user_can_edit_module

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

from django.db.models import Q
def get_equipment_filter_q(selected_equipment):
    if not selected_equipment:
        return Q()
    cleaned = clean_equipment_name(selected_equipment)
    match = re.match(r'^(\d+)T CRANE$', cleaned)
    if match:
        tonnage = match.group(1)
        return Q(equipment__icontains=tonnage) & Q(equipment__icontains='crane')
    return Q(equipment__iexact=selected_equipment)

def get_months_list():
    return [
        (1, 'January'), (2, 'February'), (3, 'March'), (4, 'April'),
        (5, 'May'), (6, 'June'), (7, 'July'), (8, 'August'),
        (9, 'September'), (10, 'October'), (11, 'November'), (12, 'December')
    ]

def get_months_in_range(from_month, from_year, to_month, to_year):
    months_labels_short = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec']
    result = []
    m = from_month
    y = from_year
    while y < to_year or (y == to_year and m <= to_month):
        result.append({
            'month': m,
            'year': y,
            'label': f"{months_labels_short[m-1]} '{str(y)[-2:]}"
        })
        m += 1
        if m > 12:
            m = 1
            y += 1
    return result

def get_pillar_display(pillar_id):
    return {
        'KK': 'Kobetsu Kaizen',
        'JH': 'Jishu Hozen',
        'PM': 'Planned Maintenance',
        'QM': 'Quality Maintenance',
        'ET': 'Education & Training',
        'DM': 'Design & Management',
        'SHE': 'Safety Health Environment',
        'OTPM': 'Office TPM',
    }.get(pillar_id, pillar_id)

def get_kpi_rows(dept, pillar_id, month, year, selected_equipment=None):
    """Fetch defined KPIs for the pillar and merge with existing database entries"""
    # Auto clean up any accidental header imports from database
    bad_customs = CustomKPIDefinition.objects.filter(
        sl_no__in=['S. NO.', 'S.NO.', 'S.No.', 'S. NO', 'S.NO', 's.no.', 's.no', 'SNO', 'Sno', 'sno', 'SL. NO.', 'SL.NO.', 'SL. NO', 'SL.NO', 'SLNO']
    )
    for bc in bad_customs:
        KPIValue.objects.filter(pillar_entry__department=bc.department, pillar_entry__pillar=bc.pillar, sl_no=bc.sl_no).delete()
        bc.delete()

    definitions = list(KPI_DEFINITIONS.get(pillar_id, []))
    custom_defs = CustomKPIDefinition.objects.filter(department=dept, pillar=pillar_id).order_by('id')
    for cd in custom_defs:
        definitions.append({
            'sl_no': cd.sl_no,
            'name': cd.name,
            'uom': cd.uom,
            'benchmark': cd.benchmark,
            'target': cd.target,
            'is_custom': True,
            'custom_id': cd.id,
        })

    entry = PillarEntry.objects.filter(
        department=dept, pillar=pillar_id, month=month, year=year
    ).first()
    
    # Calculate PM breakdown numbers/hours from Delay records
    bd_nos = None
    bd_hours = None
    repetitive = None
    if pillar_id == 'PM':
        try:
            from delays.models import DelayRecord
            base_delays = DelayRecord.objects.filter(
                department=dept,
                date__month=month,
                date__year=year
            )
            if selected_equipment:
                eq_filter = get_equipment_filter_q(selected_equipment)
                eq_delays = base_delays.filter(eq_filter)
                bd_nos = eq_delays.count()
                bd_hours = sum(d.duration_mins for d in eq_delays) / 60.0
                repetitive = bd_nos
            else:
                bd_nos = base_delays.count()
                bd_hours = sum(d.duration_mins for d in base_delays) / 60.0
                
                # Count repetitive breakdowns under normalized name in Python!
                eq_counts = {}
                for r in base_delays.exclude(equipment__isnull=True).exclude(equipment=''):
                    cleaned = clean_equipment_name(r.equipment)
                    if cleaned:
                        eq_counts[cleaned] = eq_counts.get(cleaned, 0) + 1
                repetitive = sum(1 for eq, count in eq_counts.items() if count >= 2)
        except Exception as e:
            print(f"Error calculating PM actuals: {e}")
            
    kpi_rows = []
    for d in definitions:
        row_data = {
            'sl_no': d['sl_no'],
            'kpi_name': d['name'],
            'uom': d['uom'],
            'benchmark': d['benchmark'],
            'target': d['target'],
            'actual': None,
            'availability': None,
            'performance': None,
            'quality': None,
            'remarks': '',
            'is_PRODUCTION_row': d.get('is_PRODUCTION_row', False),
            'achievement': None,
            'is_custom': d.get('is_custom', False),
            'custom_id': d.get('custom_id'),
        }
        
        # If database value exists, overlay it
        if entry:
            db_val = KPIValue.objects.filter(pillar_entry=entry, sl_no=d['sl_no']).first()
            if db_val:
                row_data['actual'] = db_val.actual
                row_data['availability'] = db_val.availability
                row_data['performance'] = db_val.performance
                row_data['quality'] = db_val.quality
                row_data['remarks'] = db_val.remarks
                if db_val.target is not None:
                    row_data['target'] = db_val.target
                if db_val.benchmark is not None:
                    row_data['benchmark'] = db_val.benchmark

        # For JH pillar, row 6 (JH Kaizen Completed): auto-calculate actual from KaizenSheet objects if not in DB
        if pillar_id == 'JH' and d['sl_no'] == '6':
            db_val_exists = entry and KPIValue.objects.filter(pillar_entry=entry, sl_no='6').exclude(actual__isnull=True).exists()
            if not db_val_exists:
                count = get_jh_kaizen_count(dept, month, year)
                row_data['actual'] = count
                if entry:
                    db_val, created_val = KPIValue.objects.get_or_create(
                        pillar_entry=entry, sl_no='6',
                        defaults={
                            'kpi_name': d['name'],
                            'uom': d['uom'],
                            'benchmark': d['benchmark'],
                            'target': d['target'],
                            'actual': count
                        }
                    )
                    if not created_val and db_val.actual != count:
                        db_val.actual = count
                        db_val.save(update_fields=['actual'])

        # For PM pillar, rows 1, 2, 3: auto-calculate actual from DelayRecords if not in DB
        if pillar_id == 'PM' and d['sl_no'] in ('1', '2', '3'):
            db_val_exists = entry and KPIValue.objects.filter(pillar_entry=entry, sl_no=d['sl_no']).exclude(actual__isnull=True).exists()
            if not db_val_exists:
                val = None
                if d['sl_no'] == '1' and bd_nos is not None:
                    val = float(bd_nos)
                elif d['sl_no'] == '2' and bd_hours is not None:
                    val = round(bd_hours, 2)
                elif d['sl_no'] == '3' and repetitive is not None:
                    val = float(repetitive)
                    
                if val is not None:
                    row_data['actual'] = val
                    if entry:
                        db_val, created_val = KPIValue.objects.get_or_create(
                            pillar_entry=entry, sl_no=d['sl_no'],
                            defaults={
                                'kpi_name': d['name'],
                                'uom': d['uom'],
                                'benchmark': d['benchmark'],
                                'target': d['target'],
                                'actual': val
                            }
                        )
                        if not created_val and db_val.actual != val:
                            db_val.actual = val
                            db_val.save(update_fields=['actual'])

        # Calculate achievement if actual & target are present
        if row_data['actual'] is not None and row_data['target'] is not None:
            row_data['achievement'] = compute_achievement(row_data['actual'], row_data['target'], row_data['kpi_name'])
        
        kpi_rows.append(row_data)
        
    return kpi_rows, entry

def get_kpi_rows_range(dept, pillar_id, from_month, from_year, to_month, to_year, selected_equipment=None):
    # Auto clean up any accidental header imports from database
    bad_customs = CustomKPIDefinition.objects.filter(
        sl_no__in=['S. NO.', 'S.NO.', 'S.No.', 'S. NO', 'S.NO', 's.no.', 's.no', 'SNO', 'Sno', 'sno', 'SL. NO.', 'SL.NO.', 'SL. NO', 'SL.NO', 'SLNO']
    )
    for bc in bad_customs:
        KPIValue.objects.filter(pillar_entry__department=bc.department, pillar_entry__pillar=bc.pillar, sl_no=bc.sl_no).delete()
        bc.delete()

    definitions = list(KPI_DEFINITIONS.get(pillar_id, []))
    custom_defs = CustomKPIDefinition.objects.filter(department=dept, pillar=pillar_id).order_by('id')
    for cd in custom_defs:
        definitions.append({
            'sl_no': cd.sl_no,
            'name': cd.name,
            'uom': cd.uom,
            'benchmark': cd.benchmark,
            'target': cd.target,
            'is_custom': True,
            'custom_id': cd.id,
        })
    
    # Calculate PM breakdown numbers/hours from Delay records for range
    bd_nos = None
    bd_hours = None
    repetitive = None
    if pillar_id == 'PM':
        try:
            from delays.models import DelayRecord
            import calendar
            start_date = datetime.date(from_year, from_month, 1)
            last_day = calendar.monthrange(to_year, to_month)[1]
            end_date = datetime.date(to_year, to_month, last_day)
            
            base_delays = DelayRecord.objects.filter(
                department=dept,
                date__gte=start_date,
                date__lte=end_date
            )
            
            if selected_equipment:
                eq_filter = get_equipment_filter_q(selected_equipment)
                eq_delays = base_delays.filter(eq_filter)
                bd_nos = eq_delays.count()
                bd_hours = sum(d.duration_mins for d in eq_delays) / 60.0
                repetitive = bd_nos
            else:
                bd_nos = base_delays.count()
                bd_hours = sum(d.duration_mins for d in base_delays) / 60.0
                
                # Average repetitive breakdown count per month in range
                monthly_eq_counts = {}
                for r in base_delays.exclude(equipment__isnull=True).exclude(equipment=''):
                    cleaned = clean_equipment_name(r.equipment)
                    if cleaned and r.date:
                        key = (r.date.year, r.date.month, cleaned)
                        monthly_eq_counts[key] = monthly_eq_counts.get(key, 0) + 1
                
                month_sums = {}
                for (y, m, eq), count in monthly_eq_counts.items():
                    key = (y, m)
                    if count >= 2:
                        month_sums[key] = month_sums.get(key, 0) + 1
                
                total_months = (to_year - from_year) * 12 + (to_month - from_month) + 1
                repetitive = sum(month_sums.values()) / float(total_months) if total_months > 0 else 0.0
        except Exception as e:
            print(f"Error calculating PM range actuals: {e}")
            
    kpi_rows = []
    for d in definitions:
        row_data = {
            'sl_no': d['sl_no'],
            'kpi_name': d['name'],
            'uom': d['uom'],
            'benchmark': d['benchmark'],
            'target': d['target'],
            'actual': None,
            'availability': None,
            'performance': None,
            'quality': None,
            'remarks': '',
            'is_PRODUCTION_row': d.get('is_PRODUCTION_row', False),
            'achievement': None,
            'is_custom': d.get('is_custom', False),
            'custom_id': d.get('custom_id'),
        }
        
        # Query all KPIValue objects for this sl_no inside the range
        kpi_values = KPIValue.objects.filter(
            get_date_range_q(prefix='pillar_entry__', from_month=from_month, from_year=from_year, to_month=to_month, to_year=to_year),
            pillar_entry__department=dept,
            pillar_entry__pillar=pillar_id,
            sl_no=d['sl_no']
        )
        
        if kpi_values.exists():
            # Aggregate actual, target, benchmark
            actual, target, benchmark = aggregate_kpi_actual(kpi_values, d['uom'], d['name'])
            row_data['actual'] = actual
            if target is not None:
                row_data['target'] = target
            if benchmark is not None:
                row_data['benchmark'] = benchmark
                
            # Collect remarks
            remarks_list = [v.remarks.strip() for v in kpi_values if v.remarks.strip()]
            row_data['remarks'] = " | ".join(remarks_list) if remarks_list else ""
            
            # For PRODUCTION row, also aggregate A, P, Q components!
            if d.get('is_PRODUCTION_row', False):
                from django.db.models import Avg
                row_data['availability'] = kpi_values.aggregate(val=Avg('availability'))['val']
                row_data['performance'] = kpi_values.aggregate(val=Avg('performance'))['val']
                row_data['quality'] = kpi_values.aggregate(val=Avg('quality'))['val']
                if row_data['availability'] is not None: row_data['availability'] = round(row_data['availability'], 2)
                if row_data['performance'] is not None: row_data['performance'] = round(row_data['performance'], 2)
                if row_data['quality'] is not None: row_data['quality'] = round(row_data['quality'], 2)
        
        if pillar_id == 'JH' and d['sl_no'] == '6' and not kpi_values.exists():
            row_data['actual'] = get_jh_kaizen_count_range(dept, from_month, from_year, to_month, to_year)

        # For PM pillar, rows 1, 2, 3: override with dynamically calculated values if not in DB
        if pillar_id == 'PM' and d['sl_no'] in ('1', '2', '3') and bd_nos is not None and not kpi_values.exists():
            val = None
            if d['sl_no'] == '1':
                val = float(bd_nos)
            elif d['sl_no'] == '2':
                val = round(bd_hours, 2)
            elif d['sl_no'] == '3':
                val = round(repetitive, 2)
            row_data['actual'] = val

        # Calculate achievement if actual & target are present
        if row_data['actual'] is not None and row_data['target'] is not None:
            row_data['achievement'] = compute_achievement(row_data['actual'], row_data['target'], row_data['kpi_name'])
            
        kpi_rows.append(row_data)
        
    return kpi_rows

@dept_access_required
def pillar_page(request, dept_id, pillar_id):
    dept = get_object_or_404(Department, id=dept_id)
    period = parse_period(request)
    filter_type = period['filter_type']
    month = period['month']
    year = period['year']
    from_month = period['from_month']
    from_year = period['from_year']
    to_month = period['to_month']
    to_year = period['to_year']
    period_label = period['label']
    
    selected_equipment = request.GET.get('selected_equipment', '').strip()
    selected_kpi = request.GET.get('selected_kpi', '').strip()
    
    if filter_type == 'range':
        kpi_rows = get_kpi_rows_range(dept, pillar_id, from_month, from_year, to_month, to_year, selected_equipment)
        is_locked = True
        entry = None
    else:
        kpi_rows, entry = get_kpi_rows(dept, pillar_id, month, year, selected_equipment)
        is_locked = entry.is_locked() if entry else False
        
    today = datetime.date.today()
    
    if filter_type == 'range':
        query_params = f"filter_type=range&from_month={from_month}&from_year={from_year}&to_month={to_month}&to_year={to_year}"
    else:
        query_params = f"filter_type=single&month={month}&year={year}"

    active_tab = request.GET.get('tab', 'entry')
    sheets = None
    settings = None
    machines = None
    grouped_years = None
    plan_cells_dict = None
    steps_range = None
    
    if active_tab == 'kaizen':
        from tpm.models import KaizenSheet
        sheets = KaizenSheet.objects.filter(department=dept, pillar=pillar_id).order_by('-created_at')
    elif active_tab in ['jh-master-equip', 'jh-master-machines', 'jh-master-plan']:
        from tpm.models import JHDepartmentSettings, JHMachine, JHMasterPlanCell
        settings, created = JHDepartmentSettings.objects.get_or_create(
            department=dept,
            defaults={
                'hod_name': 'Mr. ',
                'coordinator_name': 'Mr. ',
                'plan_start_date': datetime.date(datetime.date.today().year, 1, 1),
                'plan_end_date': datetime.date(datetime.date.today().year, 12, 31)
            }
        )
        machines = JHMachine.objects.filter(department=dept).order_by('id')
        if active_tab == 'jh-master-plan':
            steps_range = range(1, 8)
            start = settings.plan_start_date or datetime.date(datetime.date.today().year, 1, 1)
            end = settings.plan_end_date or datetime.date(datetime.date.today().year, 12, 31)
            grouped_years = []
            curr = datetime.date(start.year, start.month, 1)
            end_first_day = datetime.date(end.year, end.month, 1)
            months_count = 0
            while curr <= end_first_day and months_count < 24:
                year_val = curr.year
                month_val = curr.month
                month_name = curr.strftime('%b').upper()
                year_item = next((item for item in grouped_years if item['year'] == year_val), None)
                if not year_item:
                    year_item = {
                        'year': year_val,
                        'months': [],
                        'total_cols': 0
                    }
                    grouped_years.append(year_item)
                year_item['months'].append({
                    'num': month_val,
                    'name': month_name,
                    'cols': 4
                })
                year_item['total_cols'] += 4
                if curr.month == 12:
                    curr = datetime.date(curr.year + 1, 1, 1)
                else:
                    curr = datetime.date(curr.year, curr.month + 1, 1)
                months_count += 1
                
            plan_cells = JHMasterPlanCell.objects.filter(machine__department=dept)
            plan_cells_dict = {}
            for cell in plan_cells:
                key = f"{cell.machine_id}-{cell.step}-{cell.year}-{cell.month}-{cell.week}"
                plan_cells_dict[key] = cell.status

    equipments = []
    if pillar_id == 'PM':
        try:
            from delays.models import DelayRecord
            raw_eqs = DelayRecord.objects.filter(department=dept).exclude(equipment__isnull=True).exclude(equipment='').values_list('equipment', flat=True).distinct()
            normalized_eqs = sorted(list(set(clean_equipment_name(e) for e in raw_eqs if e.strip())))
            equipments = normalized_eqs
        except Exception:
            pass

    can_edit = user_can_edit_module(request.user, dept, 'TPM')
    
    analytics_ctx = {}
    if active_tab == 'analytics':
        analytics_ctx = get_analytics_context(request, dept, pillar_id)
        
    context = {
        'dept': dept,
        'pillar_id': pillar_id,
        'pillar_name': get_pillar_display(pillar_id),
        'filter_type': filter_type,
        'month': month,
        'year': year,
        'from_month': from_month,
        'from_year': from_year,
        'to_month': to_month,
        'to_year': to_year,
        'period_label': period_label,
        'query_params': query_params,
        'months': get_months_list(),
        'years': range(2025, today.year + 2),
        'kpi_rows': kpi_rows,
        'is_locked': is_locked,
        'entry': entry,
        'month_label': period_label,
        'active_tab': active_tab,
        'sheets': sheets,
        'settings': settings,
        'machines': machines,
        'grouped_years': grouped_years,
        'plan_cells_dict': plan_cells_dict,
        'steps_range': steps_range,
        'can_edit': can_edit,
        'equipments': equipments,
        'selected_equipment': selected_equipment,
        'selected_kpi': selected_kpi,
    }
    context.update(analytics_ctx)
    return render(request, 'department/pillar_entry.html', context)


@dept_access_required
def kpi_table_partial(request, dept_id, pillar_id):
    dept = get_object_or_404(Department, id=dept_id)
    period = parse_period(request)
    filter_type = period['filter_type']
    month = period['month']
    year = period['year']
    from_month = period['from_month']
    from_year = period['from_year']
    to_month = period['to_month']
    to_year = period['to_year']
    period_label = period['label']
    
    selected_equipment = request.GET.get('selected_equipment', '').strip()
    
    if filter_type == 'range':
        kpi_rows = get_kpi_rows_range(dept, pillar_id, from_month, from_year, to_month, to_year, selected_equipment)
        is_locked = True
        entry = None
    else:
        kpi_rows, entry = get_kpi_rows(dept, pillar_id, month, year, selected_equipment)
        is_locked = entry.is_locked() if entry else False
        
    equipments = []
    if pillar_id == 'PM':
        try:
            from delays.models import DelayRecord
            raw_eqs = DelayRecord.objects.filter(department=dept).exclude(equipment__isnull=True).exclude(equipment='').values_list('equipment', flat=True).distinct()
            normalized_eqs = sorted(list(set(clean_equipment_name(e) for e in raw_eqs if e.strip())))
            equipments = normalized_eqs
        except Exception:
            pass

    can_edit = user_can_edit_module(request.user, dept, 'TPM')
    context = {
        'dept': dept,
        'pillar_id': pillar_id,
        'filter_type': filter_type,
        'month': month,
        'year': year,
        'from_month': from_month,
        'from_year': from_year,
        'to_month': to_month,
        'to_year': to_year,
        'period_label': period_label,
        'kpi_rows': kpi_rows,
        'is_locked': is_locked,
        'entry': entry,
        'month_label': period_label,
        'can_edit': can_edit,
        'equipments': equipments,
        'selected_equipment': selected_equipment,
    }
    return render(request, 'partials/_kpi_table.html', context)


@dept_access_required
@require_POST
def save_kpi_row(request, dept_id, pillar_id):
    dept = get_object_or_404(Department, id=dept_id)
    if not user_can_edit_module(request.user, dept, 'TPM'):
        return HttpResponseForbidden("You do not have permission to edit this department's TPM.")
        
    month = int(request.GET.get('month'))
    year = int(request.GET.get('year'))
    sl_no = request.GET.get('sl_no')
    selected_equipment = request.GET.get('selected_equipment', '').strip()
    
    entry, created = PillarEntry.objects.get_or_create(
        department=dept, pillar=pillar_id, month=month, year=year
    )
    
    if entry.is_locked():
        return HttpResponseForbidden("This entry is locked and cannot be edited.")
        
    # Get definitions config for defaults
    definitions = list(KPI_DEFINITIONS.get(pillar_id, []))
    custom_defs = CustomKPIDefinition.objects.filter(department=dept, pillar=pillar_id)
    for cd in custom_defs:
        definitions.append({
            'sl_no': cd.sl_no,
            'name': cd.name,
            'uom': cd.uom,
            'benchmark': cd.benchmark,
            'target': cd.target,
            'is_custom': True,
            'custom_id': cd.id,
        })
    kpi_meta = next((d for d in definitions if d['sl_no'] == sl_no), None)
    if not kpi_meta:
        return HttpResponse("KPI definition not found", status=400)
        
    db_val, created_val = KPIValue.objects.get_or_create(
        pillar_entry=entry, sl_no=sl_no,
        defaults={
            'kpi_name': kpi_meta['name'],
            'uom': kpi_meta['uom'],
            'benchmark': kpi_meta['benchmark'],
            'target': kpi_meta['target'],
        }
    )
    
    # Extract values from POST
    actual_str = request.POST.get('actual')
    remarks = request.POST.get('remarks', '').strip()
    
    if request.user.is_admin() and 'benchmark' in request.POST:
        benchmark_str = request.POST.get('benchmark')
        db_val.benchmark = float(benchmark_str) if benchmark_str else None



        
    # KK Pillar PRODUCTION calculation
    is_PRODUCTION_row = kpi_meta.get('is_PRODUCTION_row', False)
    if is_PRODUCTION_row:
        avail_str = request.POST.get('availability')
        perf_str = request.POST.get('performance')
        qual_str = request.POST.get('quality')
        
        db_val.availability = float(avail_str) if avail_str else None
        db_val.performance = float(perf_str) if perf_str else None
        db_val.quality = float(qual_str) if qual_str else None
        
        # Calculate PRODUCTION actual
        if db_val.availability is not None and db_val.performance is not None and db_val.quality is not None:
            db_val.actual = round(compute_PRODUCTION(db_val.availability, db_val.performance, db_val.quality), 2)
        else:
            db_val.actual = float(actual_str) if actual_str else None
    else:
        db_val.actual = float(actual_str) if actual_str else None
        
    db_val.remarks = remarks
    db_val.save()
    
    # Re-calculate achievement
    achievement = None
    if db_val.actual is not None and db_val.target is not None:
        achievement = compute_achievement(db_val.actual, db_val.target, db_val.kpi_name)
        
    row_data = {
        'sl_no': db_val.sl_no,
        'kpi_name': db_val.kpi_name,
        'uom': db_val.uom,
        'benchmark': db_val.benchmark,
        'target': db_val.target,
        'actual': db_val.actual,
        'availability': db_val.availability,
        'performance': db_val.performance,
        'quality': db_val.quality,
        'remarks': db_val.remarks,
        'is_PRODUCTION_row': is_PRODUCTION_row,
        'achievement': achievement,
        'is_custom': kpi_meta.get('is_custom', False),
        'custom_id': kpi_meta.get('custom_id'),
    }
    
    context = {
        'row': row_data,
        'dept': dept,
        'pillar_id': pillar_id,
        'month': month,
        'year': year,
        'is_locked': False,
        'can_edit': True,
        'filter_type': 'single',
        'show_toast': True,
        'toast_message': f"Row {row_data['sl_no']} Saved",
        'selected_equipment': selected_equipment,
    }
    
    return render(request, 'partials/_kpi_row.html', context)


@dept_access_required
@require_POST
def submit_pillar_entry(request, dept_id, pillar_id):
    dept = get_object_or_404(Department, id=dept_id)
    if not user_can_edit_module(request.user, dept, 'TPM'):
        return HttpResponseForbidden("You do not have permission to submit this department's TPM.")
        
    month = int(request.GET.get('month'))
    year = int(request.GET.get('year'))
    
    entry, created = PillarEntry.objects.get_or_create(
        department=dept, pillar=pillar_id, month=month, year=year
    )
    
    # Save submission metadata
    entry.submitted_at = datetime.datetime.now()
    entry.submitted_by = request.user
    entry.save()
    
    kpi_rows, entry = get_kpi_rows(dept, pillar_id, month, year)
    
    context = {
        'dept': dept,
        'pillar_id': pillar_id,
        'month': month,
        'year': year,
        'kpi_rows': kpi_rows,
        'is_locked': True,
        'entry': entry,
        'month_label': dict(get_months_list()).get(month),
        'can_edit': user_can_edit_module(request.user, dept, 'TPM'),
    }
    
    toast_html = render_toast("Entry Submitted & Locked Successfully")
    response = render(request, 'partials/_kpi_table.html', context)
    response.content = response.content + toast_html.encode('utf-8')
    return response


@dept_access_required
@require_POST
def delete_pillar_entry(request, dept_id, pillar_id):
    dept = get_object_or_404(Department, id=dept_id)
    month = int(request.GET.get('month'))
    year = int(request.GET.get('year'))
    
    if not user_can_edit_module(request.user, dept, 'TPM'):
        return HttpResponseForbidden("You do not have permission to delete/clear entries for this department.")
        
    entry = PillarEntry.objects.filter(
        department=dept, pillar=pillar_id, month=month, year=year
    ).first()
    
    if entry:
        entry.delete()
        
    kpi_rows, entry = get_kpi_rows(dept, pillar_id, month, year)
    is_locked = False
    
    context = {
        'dept': dept,
        'pillar_id': pillar_id,
        'filter_type': 'single',
        'month': month,
        'year': year,
        'kpi_rows': kpi_rows,
        'is_locked': is_locked,
        'entry': entry,
        'month_label': dict(get_months_list()).get(month),
        'can_edit': True,
    }
    
    toast_html = render_toast("Monthly entry cleared/deleted successfully")
    response = render(request, 'partials/_kpi_table.html', context)
    response.content = response.content + toast_html.encode('utf-8')
    return response


@dept_access_required
@require_POST
def add_custom_kpi(request, dept_id, pillar_id):
    dept = get_object_or_404(Department, id=dept_id)
    if not user_can_edit_module(request.user, dept, 'TPM'):
        return HttpResponseForbidden("You do not have permission to edit this department's TPM.")
        
    name = request.POST.get('name', '').strip()
    uom = request.POST.get('uom', '').strip()
    benchmark_str = request.POST.get('benchmark', '').strip()
    target_str = request.POST.get('target', '').strip()
    
    if not name:
        return HttpResponse("KPI Name is required", status=400)
        
    apply_all = request.POST.get('apply_all_depts') == 'true'
    
    benchmark = float(benchmark_str) if benchmark_str else None
    target = float(target_str) if target_str else None
    
    if apply_all:
        active_depts = Department.objects.filter(is_active=True)
        for d in active_depts:
            if not CustomKPIDefinition.objects.filter(department=d, pillar=pillar_id, name=name).exists():
                count = CustomKPIDefinition.objects.filter(department=d, pillar=pillar_id).count()
                sl_no = f"C{count + 1}"
                CustomKPIDefinition.objects.create(
                    department=d,
                    pillar=pillar_id,
                    sl_no=sl_no,
                    name=name,
                    uom=uom,
                    benchmark=benchmark,
                    target=target
                )
    else:
        if not CustomKPIDefinition.objects.filter(department=dept, pillar=pillar_id, name=name).exists():
            count = CustomKPIDefinition.objects.filter(department=dept, pillar=pillar_id).count()
            sl_no = f"C{count + 1}"
            CustomKPIDefinition.objects.create(
                department=dept,
                pillar=pillar_id,
                sl_no=sl_no,
                name=name,
                uom=uom,
                benchmark=benchmark,
                target=target
            )
    
    # Refresh table
    month = int(request.GET.get('month', datetime.date.today().month))
    year = int(request.GET.get('year', datetime.date.today().year))
    kpi_rows, entry = get_kpi_rows(dept, pillar_id, month, year)
    is_locked = entry.is_locked() if entry else False
    can_edit = True
    
    context = {
        'dept': dept,
        'pillar_id': pillar_id,
        'filter_type': 'single',
        'month': month,
        'year': year,
        'kpi_rows': kpi_rows,
        'is_locked': is_locked,
        'entry': entry,
        'month_label': dict(get_months_list()).get(month),
        'can_edit': can_edit,
    }
    
    msg = f'Custom field "{name}" added to all departments' if apply_all else f'Custom field "{name}" added successfully'
    toast_html = render_toast(msg)
    response = render(request, 'partials/_kpi_table.html', context)
    response.content = response.content + toast_html.encode('utf-8')
    return response


@dept_access_required
@require_POST
def delete_custom_kpi(request, dept_id, pillar_id, custom_id):
    dept = get_object_or_404(Department, id=dept_id)
    if not user_can_edit_module(request.user, dept, 'TPM'):
        return HttpResponseForbidden("You do not have permission to edit this department's TPM.")
        
    cd = get_object_or_404(CustomKPIDefinition, id=custom_id, department=dept, pillar=pillar_id)
    name = cd.name
    # Cascade delete any associated KPIValues inside this department & pillar
    KPIValue.objects.filter(pillar_entry__department=dept, pillar_entry__pillar=pillar_id, sl_no=cd.sl_no).delete()
    cd.delete()
    
    # Refresh table
    month = int(request.GET.get('month', datetime.date.today().month))
    year = int(request.GET.get('year', datetime.date.today().year))
    kpi_rows, entry = get_kpi_rows(dept, pillar_id, month, year)
    is_locked = entry.is_locked() if entry else False
    can_edit = True
    
    context = {
        'dept': dept,
        'pillar_id': pillar_id,
        'filter_type': 'single',
        'month': month,
        'year': year,
        'kpi_rows': kpi_rows,
        'is_locked': is_locked,
        'entry': entry,
        'month_label': dict(get_months_list()).get(month),
        'can_edit': can_edit,
    }
    
    toast_html = render_toast(f'Custom field "{name}" deleted')
    response = render(request, 'partials/_kpi_table.html', context)
    response.content = response.content + toast_html.encode('utf-8')
    return response


def get_analytics_context(request, dept, pillar_id):
    period = parse_period(request)
    filter_type = period['filter_type']
    month = period['month']
    year = period['year']
    from_month = period['from_month']
    from_year = period['from_year']
    to_month = period['to_month']
    to_year = period['to_year']
    period_label = period['label']
    
    months_labels_short = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec']
    if filter_type == 'range':
        range_months = get_months_in_range(from_month, from_year, to_month, to_year)
    else:
        range_months = [{
            'month': m,
            'year': year,
            'label': months_labels_short[m-1]
        } for m in range(1, 13)]
        
    chart_labels = [rm['label'] for rm in range_months]
    
    definitions = list(KPI_DEFINITIONS.get(pillar_id, []))
    custom_defs = CustomKPIDefinition.objects.filter(department=dept, pillar=pillar_id).order_by('id')
    for cd in custom_defs:
        definitions.append({
            'sl_no': cd.sl_no,
            'name': cd.name,
            'uom': cd.uom,
            'benchmark': cd.benchmark,
            'target': cd.target,
            'is_custom': True,
            'custom_id': cd.id,
        })
        
    selected_kpi = request.GET.get('selected_kpi', '').strip()
    
    kpis_trend_data = {}
    for d in definitions:
        kpis_trend_data[d['sl_no']] = {
            'name': d['name'],
            'actuals': [],
            'targets': [],
            'benchmarks': []
        }
        for rm in range_months:
            val = KPIValue.objects.filter(
                pillar_entry__department=dept,
                pillar_entry__pillar=pillar_id,
                pillar_entry__month=rm['month'],
                pillar_entry__year=rm['year'],
                sl_no=d['sl_no']
            ).first()
            kpis_trend_data[d['sl_no']]['actuals'].append(val.actual if (val and val.actual is not None) else 0.0)
            kpis_trend_data[d['sl_no']]['targets'].append(val.target if val and val.target is not None else d.get('target'))
            kpis_trend_data[d['sl_no']]['benchmarks'].append(val.benchmark if val and val.benchmark is not None else d.get('benchmark'))

    # Bar chart achievement rates for current month/range
    if filter_type == 'range':
        kpi_rows = get_kpi_rows_range(dept, pillar_id, from_month, from_year, to_month, to_year)
    else:
        kpi_rows, entry = get_kpi_rows(dept, pillar_id, month, year)
    
    bar_labels = []
    bar_values = []
    bar_colors = []
    
    for row in kpi_rows:
        bar_labels.append(f"Sl {row['sl_no']}")
        ach = row['achievement']
        if ach is not None:
            bar_values.append(round(ach, 1))
            if ach >= 90:
                bar_colors.append('#16A34A')  # Green
            elif ach >= 75:
                bar_colors.append('#D97706')  # Orange
            else:
                bar_colors.append('#DC2626')  # Red
        else:
            bar_values.append(0.0)
            bar_colors.append('#6B7A99')  # Gray
            
    return {
        'dept': dept,
        'pillar_id': pillar_id,
        'filter_type': filter_type,
        'month': month,
        'year': year,
        'from_month': from_month,
        'from_year': from_year,
        'to_month': to_month,
        'to_year': to_year,
        'period_label': period_label,
        'kpis_trend_data_json': json.dumps(kpis_trend_data),
        'bar_labels_json': json.dumps(bar_labels),
        'bar_values_json': json.dumps(bar_values),
        'bar_colors_json': json.dumps(bar_colors),
        'months_labels_json': json.dumps(chart_labels),
        'kpi_rows': kpi_rows,
        'selected_kpi': selected_kpi,
    }


@dept_access_required
def analytics_partial(request, dept_id, pillar_id):
    dept = get_object_or_404(Department, id=dept_id)
    context = get_analytics_context(request, dept, pillar_id)
    return render(request, 'partials/_analytics_charts.html', context)
