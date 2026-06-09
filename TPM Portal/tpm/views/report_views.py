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
    
    report_data = []
    today = datetime.date.today()
    
    # Standard 8 Pillars scores calculation for HTML review
    for code, name in pillars_meta:
        # Check if entries exist/submitted
        entries = PillarEntry.objects.filter(
            get_date_range_q(from_month=from_month, from_year=from_year, to_month=to_month, to_year=to_year),
            department=dept,
            pillar=code
        )
        all_submitted = entries.exists() and all(e.is_locked() for e in entries)
        
        definitions = KPI_DEFINITIONS.get(code, [])
        kpi_list = []
        achievements = []
        
        for d in definitions:
            kpi_values = KPIValue.objects.filter(
                get_date_range_q(prefix='pillar_entry__', from_month=from_month, from_year=from_year, to_month=to_month, to_year=to_year),
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
        'report_data': report_data,
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
