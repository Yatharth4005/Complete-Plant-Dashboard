import json
import datetime
from django.shortcuts import render, get_object_or_404
from django.http import HttpResponse, HttpResponseForbidden
from django.views.decorators.http import require_POST
from django.contrib.auth.decorators import login_required
from tpm.models import Department, PillarEntry, KPIValue, CustomKPIDefinition
from tpm.utils.decorators import dept_access_required
from tpm.utils.kpi_definitions import KPI_DEFINITIONS
from tpm.utils.calculations import compute_achievement, compute_PRODUCTION, parse_period, get_date_range_q, aggregate_kpi_actual
from portal.utils.access import user_can_edit_module

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

def get_kpi_rows(dept, pillar_id, month, year):
    """Fetch defined KPIs for the pillar and merge with existing database entries"""
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

        # Calculate achievement if actual & target are present
        if row_data['actual'] is not None and row_data['target'] is not None:
            row_data['achievement'] = compute_achievement(row_data['actual'], row_data['target'], row_data['kpi_name'])
        
        kpi_rows.append(row_data)
        
    return kpi_rows, entry

def get_kpi_rows_range(dept, pillar_id, from_month, from_year, to_month, to_year):
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
    
    if filter_type == 'range':
        kpi_rows = get_kpi_rows_range(dept, pillar_id, from_month, from_year, to_month, to_year)
        is_locked = True
        entry = None
    else:
        kpi_rows, entry = get_kpi_rows(dept, pillar_id, month, year)
        is_locked = entry.is_locked() if entry else False
        
    today = datetime.date.today()
    
    if filter_type == 'range':
        query_params = f"filter_type=range&from_month={from_month}&from_year={from_year}&to_month={to_month}&to_year={to_year}"
    else:
        query_params = f"filter_type=single&month={month}&year={year}"

    active_tab = request.GET.get('tab', 'entry')
    sheets = None
    if active_tab == 'kaizen':
        from tpm.models import KaizenSheet
        sheets = KaizenSheet.objects.filter(department=dept, pillar=pillar_id).order_by('-created_at')

    can_edit = user_can_edit_module(request.user, dept, 'TPM')
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
        'can_edit': can_edit,
    }
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
    
    if filter_type == 'range':
        kpi_rows = get_kpi_rows_range(dept, pillar_id, from_month, from_year, to_month, to_year)
        is_locked = True
        entry = None
    else:
        kpi_rows, entry = get_kpi_rows(dept, pillar_id, month, year)
        is_locked = entry.is_locked() if entry else False
        
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
    
    if request.user.is_admin() and 'target' in request.POST:
        target_str = request.POST.get('target')
        db_val.target = float(target_str) if target_str else None
        
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
    }
    
    # Return row template view along with the toast script tag
    toast_html = f'<div id="toast-container" hx-swap-oob="true"><div class="toast toast-success">Row {sl_no} Saved</div></div>'
    context = {
        'row': row_data,
        'dept': dept,
        'pillar_id': pillar_id,
        'month': month,
        'year': year,
        'is_locked': False,
        'can_edit': True,
    }
    
    response = render(request, 'partials/_kpi_row.html', context)
    response.content = response.content + toast_html.encode('utf-8')
    return response


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
    
    toast_html = f'<div id="toast-container" hx-swap-oob="true"><div class="toast toast-success">Entry Submitted & Locked Successfully</div></div>'
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
    
    toast_html = f'<div id="toast-container" hx-swap-oob="true"><div class="toast toast-success">Monthly entry cleared/deleted successfully</div></div>'
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
        
    # Auto-generate sl_no: count existing custom KPIs for this dept and pillar
    count = CustomKPIDefinition.objects.filter(department=dept, pillar=pillar_id).count()
    sl_no = f"C{count + 1}"
    
    benchmark = float(benchmark_str) if benchmark_str else None
    target = float(target_str) if target_str else None
    
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
    
    toast_html = f'<div id="toast-container" hx-swap-oob="true"><div class="toast toast-success">Custom field &quot;{name}&quot; added successfully</div></div>'
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
    
    toast_html = f'<div id="toast-container" hx-swap-oob="true"><div class="toast toast-success">Custom field &quot;{name}&quot; deleted</div></div>'
    response = render(request, 'partials/_kpi_table.html', context)
    response.content = response.content + toast_html.encode('utf-8')
    return response


@dept_access_required
def analytics_partial(request, dept_id, pillar_id):
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
    
    definitions = KPI_DEFINITIONS.get(pillar_id, [])
    
    kpis_trend_data = {}
    for d in definitions:
        kpis_trend_data[d['sl_no']] = {
            'name': d['name'],
            'actuals': [],
            'targets': []
        }
        for rm in range_months:
            val = KPIValue.objects.filter(
                pillar_entry__department=dept,
                pillar_entry__pillar=pillar_id,
                pillar_entry__month=rm['month'],
                pillar_entry__year=rm['year'],
                sl_no=d['sl_no']
            ).first()
            kpis_trend_data[d['sl_no']]['actuals'].append(val.actual if val else None)
            kpis_trend_data[d['sl_no']]['targets'].append(val.target if val and val.target is not None else d['target'])

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
        'kpis_trend_data_json': json.dumps(kpis_trend_data),
        'bar_labels_json': json.dumps(bar_labels),
        'bar_values_json': json.dumps(bar_values),
        'bar_colors_json': json.dumps(bar_colors),
        'months_labels_json': json.dumps(chart_labels),
        'kpi_rows': kpi_rows,
    }
    return render(request, 'partials/_analytics_charts.html', context)
