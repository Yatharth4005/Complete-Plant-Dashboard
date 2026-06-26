import datetime
from django.shortcuts import render, get_object_or_404
from django.http import HttpResponse
from tpm.models import Department, PillarEntry, KPIValue
from tpm.utils.decorators import dept_access_required
from tpm.utils.export import generate_pillar_pdf, generate_pillar_excel
from tpm.utils.kpi_definitions import KPI_DEFINITIONS
from tpm.utils.calculations import compute_achievement, parse_period, get_date_range_q, aggregate_kpi_actual

def get_months_list():
    return [
        (1, 'January'), (2, 'February'), (3, 'March'), (4, 'April'),
        (5, 'May'), (6, 'June'), (7, 'July'), (8, 'August'),
        (9, 'September'), (10, 'October'), (11, 'November'), (12, 'December')
    ]

def calculate_month_report_data(dept, m, y):
    pillars_meta = [
        ('KK', 'Kobetsu Kaizen'),
        ('JH', 'Jishu Hozen'),
        ('PM', 'Planned Maintenance'),
        ('QM', 'Quality Maintenance'),
        ('ET', 'Education & Training'),
        ('DM', 'Initial Flow Control / Design & Management'),
        ('SHE', 'Safety, Health & Environment'),
        ('OTPM', 'Office TPM')
    ]
    report_data = []
    
    for code, name in pillars_meta:
        # Check if entries exist/submitted
        entries = PillarEntry.objects.filter(
            month=m, year=y,
            department=dept,
            pillar=code
        )
        all_submitted = entries.exists() and all(e.is_locked() for e in entries)
        
        definitions = KPI_DEFINITIONS.get(code, [])
        kpi_list = []
        achievements = []
        
        for d in definitions:
            kpi_values = KPIValue.objects.filter(
                pillar_entry__month=m,
                pillar_entry__year=y,
                pillar_entry__department=dept,
                pillar_entry__pillar=code,
                sl_no=d['sl_no']
            )
            
            if kpi_values.exists():
                actual, target, benchmark = aggregate_kpi_actual(kpi_values, d['uom'], d['name'])
                remarks_list = [v.remarks.strip() for v in kpi_values if v.remarks.strip()]
                remarks = " | ".join(remarks_list) if remarks_list else ""
            else:
                actual = None
                target = d['target']
                benchmark = d['benchmark']
                remarks = ''
                
            achievement = None
            status = 'pending'
            if actual is not None and target is not None:
                achievement = compute_achievement(actual, target, d['name'])
                status = 'on-track' if achievement >= 90 else ('at-risk' if achievement >= 75 else 'behind')
                achievements.append(achievement)
                
            kpi_list.append({
                'sl_no': d['sl_no'],
                'name': d['name'],
                'uom': d['uom'],
                'benchmark': benchmark,
                'target': target,
                'actual': actual,
                'achievement': achievement,
                'remarks': remarks,
                'status': status,
            })
            
        avg_achievement = sum(achievements) / len(achievements) if achievements else 0.0
        
        report_data.append({
            'code': code,
            'name': name,
            'kpis': kpi_list,
            'achievement': round(avg_achievement, 1),
            'submitted': all_submitted,
            'submitted_by': entries.first().submitted_by if entries.exists() and all_submitted else None,
        })
        
    return report_data


def get_months_in_range(from_month, from_year, to_month, to_year):
    months = []
    current_month = from_month
    current_year = from_year
    while current_year < to_year or (current_year == to_year and current_month <= to_month):
        months.append((current_month, current_year))
        current_month += 1
        if current_month > 12:
            current_month = 1
            current_year += 1
    return months


@dept_access_required
def report_page(request, dept_id):
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
    
    pillars_meta = [
        ('KK', 'Kobetsu Kaizen'),
        ('JH', 'Jishu Hozen'),
        ('PM', 'Planned Maintenance'),
        ('QM', 'Quality Maintenance'),
        ('ET', 'Education & Training'),
        ('DM', 'Initial Flow Control / Design & Management'),
        ('SHE', 'Safety, Health & Environment'),
        ('OTPM', 'Office TPM')
    ]
    
    today = datetime.date.today()
    monthly_reports = []
    comparison_data = {}
    
    if filter_type == 'range':
        months_in_range = get_months_in_range(from_month, from_year, to_month, to_year)
        months_labels = []
        months_map_short = dict([
            (1, 'Jan'), (2, 'Feb'), (3, 'Mar'), (4, 'Apr'),
            (5, 'May'), (6, 'Jun'), (7, 'Jul'), (8, 'Aug'),
            (9, 'Sep'), (10, 'Oct'), (11, 'Nov'), (12, 'Dec')
        ])
        
        pillar_trends = {code: [] for code, _ in pillars_meta}
        overall_trends = []
        
        for m, y in months_in_range:
            label = f"{months_map_short.get(m)} {str(y)[2:]}"
            months_labels.append(label)
            
            m_report = calculate_month_report_data(dept, m, y)
            monthly_reports.append({
                'month': m,
                'year': y,
                'label': f"{dict(get_months_list()).get(m)} {y}",
                'report_data': m_report
            })
            
            # Collect comparison/trend data
            month_scores = []
            for p_data in m_report:
                pillar_trends[p_data['code']].append(p_data['achievement'])
                month_scores.append(p_data['achievement'])
                
            overall_score = round(sum(month_scores) / len(month_scores), 1) if month_scores else 0.0
            overall_trends.append(overall_score)
            
        pillar_rows = []
        for code, name in pillars_meta:
            pillar_rows.append({
                'code': code,
                'name': name,
                'scores': pillar_trends[code]
            })
            
        comparison_data = {
            'labels': months_labels,
            'overall': overall_trends,
            'pillars': pillar_trends,
            'pillar_names': {code: name for code, name in pillars_meta},
            'pillar_rows': pillar_rows
        }
    else:
        # single month
        m_report = calculate_month_report_data(dept, month, year)
        monthly_reports = [{
            'month': month,
            'year': year,
            'label': period_label,
            'report_data': m_report
        }]
        
        # Count KPI statuses for Pie Chart
        on_track = 0
        at_risk = 0
        behind = 0
        for p_data in m_report:
            for kpi in p_data['kpis']:
                if kpi['achievement'] is not None:
                    if kpi['achievement'] >= 90.0:
                        on_track += 1
                    elif kpi['achievement'] >= 75.0:
                        at_risk += 1
                    else:
                        behind += 1
        
        # Chart.js pillar comparison for single month
        labels = [p_data['name'] for p_data in m_report]
        scores = [p_data['achievement'] for p_data in m_report]
        comparison_data = {
            'labels': labels,
            'scores': scores,
            'on_track': on_track,
            'at_risk': at_risk,
            'behind': behind
        }
        
    if filter_type == 'range':
        query_params = f"filter_type=range&from_month={from_month}&from_year={from_year}&to_month={to_month}&to_year={to_year}"
    else:
        query_params = f"filter_type=single&month={month}&year={year}"

    context = {
        'dept': dept,
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
        'monthly_reports': monthly_reports,
        'comparison_data': comparison_data,
        'month_label': period_label,
    }
    return render(request, 'department/report.html', context)


@dept_access_required
def export_pdf(request, dept_id):
    dept = get_object_or_404(Department, id=dept_id)
    period = parse_period(request)
    filter_type = period['filter_type']
    from_month = period['from_month']
    from_year = period['from_year']
    to_month = period['to_month']
    to_year = period['to_year']
    
    pdf_content = generate_pillar_pdf(dept, from_month, from_year, to_month, to_year, filter_type)
    
    response = HttpResponse(pdf_content, content_type='application/pdf')
    if filter_type == 'range':
        filename = f"TPM_Report_{dept.code}_{from_year}_{from_month}_to_{to_year}_{to_month}.pdf"
    else:
        filename = f"TPM_Report_{dept.code}_{from_year}_{from_month}.pdf"
    response['Content-Disposition'] = f'attachment; filename="{filename}"'
    return response


@dept_access_required
def export_excel(request, dept_id):
    dept = get_object_or_404(Department, id=dept_id)
    period = parse_period(request)
    filter_type = period['filter_type']
    from_month = period['from_month']
    from_year = period['from_year']
    to_month = period['to_month']
    to_year = period['to_year']
    
    excel_content = generate_pillar_excel(dept, from_month, from_year, to_month, to_year, filter_type)
    
    response = HttpResponse(
        excel_content,
        content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
    )
    if filter_type == 'range':
        filename = f"TPM_Report_{dept.code}_{from_year}_{from_month}_to_{to_year}_{to_month}.xlsx"
    else:
        filename = f"TPM_Report_{dept.code}_{from_year}_{from_month}.xlsx"
    response['Content-Disposition'] = f'attachment; filename="{filename}"'
    return response
