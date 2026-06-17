import json
import datetime
from django.shortcuts import render
from django.db.models import Avg, Sum
from tpm.models import Department, PillarEntry, KPIValue, WorkstationValue, WorkstationKPI
from django.contrib.auth.decorators import login_required
from tpm.utils.decorators import admin_required
from tpm.utils.calculations import compute_achievement, parse_period, get_date_range_q

def sidebar_context_processor(request):
    if not request.user.is_authenticated:
        return {}
    
    depts = Department.objects.all().order_by('name')
        
    pillars = [
        {'id': 'KK', 'label': 'KK (Kobetsu Kaizen)'},
        {'id': 'JH', 'label': 'JH (Jishu Hozen)'},
        {'id': 'PM', 'label': 'PM (Planned Maintenance)'},
        {'id': 'QM', 'label': 'QM (Quality Maintenance)'},
        {'id': 'ET', 'label': 'ET (Education & Training)'},
        {'id': 'DM', 'label': 'DM (Initial Flow/Design)'},
        {'id': 'SHE', 'label': 'SHE (Safety & Health)'},
        {'id': 'OTPM', 'label': 'OTPM (Office TPM)'},
    ]
    return {
        'sidebar_departments': depts,
        'pillars': pillars,
    }


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


def _get_plant_dashboard_context(request):
    period = parse_period(request)
    filter_type = period['filter_type']
    selected_month = period['month']
    selected_year = period['year']
    from_month = period['from_month']
    from_year = period['from_year']
    to_month = period['to_month']
    to_year = period['to_year']
    period_label = period['label']
    
    depts = Department.objects.all().order_by('name')
    today = datetime.date.today()
    
    # 1. Plant Overall PRODUCTION (average KK row 1 actuals for selected month/year/range)
    PRODUCTION_avg = KPIValue.objects.filter(
        get_date_range_q(prefix='pillar_entry__', from_month=from_month, from_year=from_year, to_month=to_month, to_year=to_year),
        pillar_entry__pillar='KK',
        sl_no='1'
    ).aggregate(avg=Avg('actual'))['avg'] or 0.0

    # 2. Total Kaizens (KK sl_no='7' actuals over period)
    kaizen_ytd = KPIValue.objects.filter(
        get_date_range_q(prefix='pillar_entry__', from_month=from_month, from_year=from_year, to_month=to_month, to_year=to_year),
        pillar_entry__pillar='KK',
        sl_no='7'
    ).aggregate(total=Sum('actual'))['total'] or 0.0

    # 3. SHE: Zero LTI Count (sum of LTI numbers)
    lti_sum = KPIValue.objects.filter(
        get_date_range_q(prefix='pillar_entry__', from_month=from_month, from_year=from_year, to_month=to_month, to_year=to_year),
        pillar_entry__pillar='SHE',
        sl_no__in=['2A', '2B']  # Fatal + LTI
    ).aggregate(total=Sum('actual'))['total'] or 0.0

    # 4. PM Compliance (average of PM scheduled compliance row 14)
    pm_compliance = KPIValue.objects.filter(
        get_date_range_q(prefix='pillar_entry__', from_month=from_month, from_year=from_year, to_month=to_month, to_year=to_year),
        pillar_entry__pillar='PM',
        sl_no='14'
    ).aggregate(avg=Avg('actual'))['avg'] or 0.0

    # Department Cards Detail
    dept_cards = []
    for d in depts:
        # Compute department average achievement across all pillars for the month/range
        kpi_vals = KPIValue.objects.filter(
            get_date_range_q(prefix='pillar_entry__', from_month=from_month, from_year=from_year, to_month=to_month, to_year=to_year),
            pillar_entry__department=d
        )
        
        achievements = []
        for val in kpi_vals:
            if val.actual is not None and val.target is not None:
                ach = compute_achievement(val.actual, val.target, val.kpi_name)
                achievements.append(ach)
                
        # Workstation KPIs
        ws_vals = WorkstationValue.objects.filter(
            get_date_range_q(from_month=from_month, from_year=from_year, to_month=to_month, to_year=to_year),
            workstation_kpi__workstation__department=d
        )
        for val in ws_vals:
            if val.actual is not None and val.workstation_kpi.commitment is not None:
                indicator = val.workstation_kpi.goodness_indicator
                target = val.workstation_kpi.commitment
                if indicator == 'LOWER':
                    ach = min(100.0, (target / val.actual) * 100.0) if val.actual != 0 else 100.0
                else:
                    ach = (val.actual / target) * 100.0 if target != 0 else 100.0
                achievements.append(ach)

        avg_achievement = sum(achievements) / len(achievements) if achievements else 0.0
        
        # Color Class mapping
        if avg_achievement >= 90.0:
            status = 'on-track'
            status_class = 'bg-success-subtle text-success border-success'
        elif avg_achievement >= 75.0:
            status = 'at-risk'
            status_class = 'bg-warning-subtle text-warning border-warning'
        else:
            status = 'behind'
            status_class = 'bg-danger-subtle text-danger border-danger'
            
        # Sparkline data (PRODUCTION actuals over last 6 months leading to end of range)
        sparkline_data = []
        for i in range(5, -1, -1):
            sm = to_month - i
            sy = to_year
            if sm <= 0:
                sm += 12
                sy -= 1
            val = KPIValue.objects.filter(
                pillar_entry__department=d,
                pillar_entry__pillar='KK',
                pillar_entry__month=sm,
                pillar_entry__year=sy,
                sl_no='1'
            ).first()
            sparkline_data.append(val.actual if val else 0.0)

        dept_cards.append({
            'id': d.id,
            'name': d.name,
            'code': d.code,
            'achievement': round(avg_achievement, 1),
            'status': status,
            'status_class': status_class,
            'sparkline': sparkline_data,
        })

    # Top & Bottom Performers
    sorted_cards = sorted(dept_cards, key=lambda x: x['achievement'], reverse=True)
    top_performers = sorted_cards[:5]
    bottom_performers = sorted_cards[-5:][::-1] if len(sorted_cards) >= 5 else sorted_cards[::-1]

    # Chart data structure: Monthly Plant PRODUCTION trend
    months_labels = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec']
    if filter_type == 'range':
        range_months = get_months_in_range(from_month, from_year, to_month, to_year)
    else:
        range_months = [{
            'month': m,
            'year': selected_year,
            'label': months_labels[m-1]
        } for m in range(1, 13)]

    PRODUCTION_trend_actuals = []
    PRODUCTION_trend_targets = []
    chart_labels = []
    for rm in range_months:
        avg_act = KPIValue.objects.filter(
            pillar_entry__pillar='KK',
            pillar_entry__month=rm['month'],
            pillar_entry__year=rm['year'],
            sl_no='1'
        ).aggregate(avg=Avg('actual'))['avg'] or None
        PRODUCTION_trend_actuals.append(avg_act)
        PRODUCTION_trend_targets.append(85.0)  # Plant benchmark target is 85%
        chart_labels.append(rm['label'])

    # Radar Chart: average achievement for each of the 9 pillars plant-wide
    radar_data = []
    radar_labels = ['KK', 'JH', 'PM', 'QM', 'ET', 'DM', 'SHE', 'OTPM', 'WS KPI']
    for pillar in ['KK', 'JH', 'PM', 'QM', 'ET', 'DM', 'SHE', 'OTPM']:
        vals = KPIValue.objects.filter(
            get_date_range_q(prefix='pillar_entry__', from_month=from_month, from_year=from_year, to_month=to_month, to_year=to_year),
            pillar_entry__pillar=pillar
        )
        ach_list = []
        for val in vals:
            if val.actual is not None and val.target is not None:
                ach_list.append(compute_achievement(val.actual, val.target, val.kpi_name))
        radar_data.append(round(sum(ach_list)/len(ach_list), 1) if ach_list else 0.0)

    # Workstation KPI average achievement
    ws_kpis = WorkstationValue.objects.filter(
        get_date_range_q(from_month=from_month, from_year=from_year, to_month=to_month, to_year=to_year)
    )
    ws_ach_list = []
    for val in ws_kpis:
        if val.actual is not None and val.workstation_kpi.commitment is not None:
            indicator = val.workstation_kpi.goodness_indicator
            target = val.workstation_kpi.commitment
            if indicator == 'LOWER':
                ach = min(100.0, (target / val.actual) * 100.0) if val.actual != 0 else 100.0
            else:
                ach = (val.actual / target) * 100.0 if target != 0 else 100.0
            ws_ach_list.append(ach)
    radar_data.append(round(sum(ws_ach_list)/len(ws_ach_list), 1) if ws_ach_list else 0.0)

    # Compliance Heatmap Grid
    heatmap = []
    heatmap_months = []
    for i in range(5, -1, -1):
        target_month = to_month - i
        target_year = to_year
        if target_month <= 0:
            target_month += 12
            target_year -= 1
        heatmap_months.append({
            'month': target_month,
            'year': target_year,
            'label': f"{months_labels[target_month-1]} '{str(target_year)[-2:]}"
        })

    for d in depts:
        row = {'dept_name': d.name, 'scores': []}
        for hm in heatmap_months:
            kpis = KPIValue.objects.filter(
                pillar_entry__department=d,
                pillar_entry__month=hm['month'],
                pillar_entry__year=hm['year']
            )
            ach_list = []
            for k in kpis:
                if k.actual is not None and k.target is not None:
                    ach_list.append(compute_achievement(k.actual, k.target, k.kpi_name))
            
            ws_vals = WorkstationValue.objects.filter(
                workstation_kpi__workstation__department=d,
                month=hm['month'],
                year=hm['year']
            )
            for ws_v in ws_vals:
                if ws_v.actual is not None and ws_v.workstation_kpi.commitment is not None:
                    indicator = ws_v.workstation_kpi.goodness_indicator
                    target = ws_v.workstation_kpi.commitment
                    if indicator == 'LOWER':
                        ach = min(100.0, (target / ws_v.actual) * 100.0) if ws_v.actual != 0 else 100.0
                    else:
                        ach = (ws_v.actual / target) * 100.0 if target != 0 else 100.0
                    ach_list.append(ach)

            avg_ach = sum(ach_list) / len(ach_list) if ach_list else None
            
            color_class = 'bg-light text-muted'
            if avg_ach is not None:
                if avg_ach >= 90.0:
                    color_class = 'bg-success text-white'
                elif avg_ach >= 75.0:
                    color_class = 'bg-warning text-dark'
                else:
                    color_class = 'bg-danger text-white'

            row['scores'].append({
                'value': round(avg_ach, 1) if avg_ach is not None else 'N/A',
                'class': color_class
            })
        heatmap.append(row)

    if filter_type == 'range':
        query_params = f"filter_type=range&from_month={from_month}&from_year={from_year}&to_month={to_month}&to_year={to_year}"
    else:
        query_params = f"filter_type=single&month={selected_month}&year={selected_year}"

    return {
        'filter_type': filter_type,
        'month': selected_month,
        'year': selected_year,
        'from_month': from_month,
        'from_year': from_year,
        'to_month': to_month,
        'to_year': to_year,
        'period_label': period_label,
        'query_params': query_params,
        'months': get_months_list(),
        'years': range(2025, today.year + 2),
        'PRODUCTION_avg': round(PRODUCTION_avg, 1),
        'kaizen_ytd': int(kaizen_ytd),
        'lti_sum': int(lti_sum),
        'pm_compliance': round(pm_compliance, 1),
        'dept_cards': dept_cards,
        'top_performers': top_performers,
        'bottom_performers': bottom_performers,
        'heatmap_months': heatmap_months,
        'heatmap': heatmap,
        'PRODUCTION_trend_actuals_json': json.dumps(PRODUCTION_trend_actuals),
        'PRODUCTION_trend_targets_json': json.dumps(PRODUCTION_trend_targets),
        'radar_labels_json': json.dumps(radar_labels),
        'radar_data_json': json.dumps(radar_data),
        'months_labels_json': json.dumps(chart_labels),
    }

@login_required
def plant_dashboard(request):
    context = _get_plant_dashboard_context(request)
    tab = request.GET.get('tab', 'overview')
    context['active_tab'] = tab
    context['active_section'] = 'capa' if tab == 'capa' else 'tpm_dashboard'
    from tpm.models import CAPAReport
    context['reports'] = CAPAReport.objects.all().order_by('-created_at')
    return render(request, 'dashboard/plant_dashboard.html', context)

@login_required
def plant_overview_partial(request):
    context = _get_plant_dashboard_context(request)
    return render(request, 'partials/_plant_overview.html', context)
