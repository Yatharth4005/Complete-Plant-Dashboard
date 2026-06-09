from datetime import date
from django.shortcuts import render, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.http import HttpResponse
from tpm.models import Department
from cmc.models import Equipment, PMScheduleEntry, VibrationLog, OilTestLog, WDALog, SAPNotification
from cmc.utils.export import generate_pdf_report, generate_excel_report
from portal.utils.decorators import module_access_required

@login_required
@module_access_required('CMC')
def report_page(request, dept_id):
    department = get_object_or_404(Department, id=dept_id)
    today = date.today()
    
    month = int(request.GET.get('month', today.month))
    year = int(request.GET.get('year', today.year))
    
    # Simple summary counts for the HTML preview
    entries = PMScheduleEntry.objects.filter(
        equipment__department=department,
        scheduled_date__month=month,
        scheduled_date__year=year
    )
    total_inspections = entries.count()
    completed_inspections = entries.filter(status=PMScheduleEntry.VisitStatus.DONE).count()
    compliance_rate = (completed_inspections / total_inspections * 100) if total_inspections > 0 else 100.0
    
    vibration_count = VibrationLog.objects.filter(equipment__department=department, date__month=month, date__year=year).count()
    oil_count = OilTestLog.objects.filter(equipment__department=department, date__month=month, date__year=year).count()
    wda_count = WDALog.objects.filter(equipment__department=department, date__month=month, date__year=year).count()
    notif_count = SAPNotification.objects.filter(equipment__department=department, raised_date__month=month, raised_date__year=year).count()

    context = {
        'department': department,
        'month': month,
        'year': year,
        'total_inspections': total_inspections,
        'completed_inspections': completed_inspections,
        'compliance_rate': round(compliance_rate, 1),
        'vibration_count': vibration_count,
        'oil_count': oil_count,
        'wda_count': wda_count,
        'notif_count': notif_count,
        'months': [
            (1, 'January'), (2, 'February'), (3, 'March'), (4, 'April'),
            (5, 'May'), (6, 'June'), (7, 'July'), (8, 'August'),
            (9, 'September'), (10, 'October'), (11, 'November'), (12, 'December')
        ],
        'years': range(2025, today.year + 2),
        'active_tab': 'reports',
        'query_params': f"month={month}&year={year}",
    }
    return render(request, 'cmc/reports/report_page.html', context)


@login_required
@module_access_required('CMC')
def export_pdf(request, dept_id):
    department = get_object_or_404(Department, id=dept_id)
    today = date.today()
    month = int(request.GET.get('month', today.month))
    year = int(request.GET.get('year', today.year))
    
    pdf_data = generate_pdf_report(department, month, year)
    
    response = HttpResponse(pdf_data, content_type='application/pdf')
    filename = f"CMC_Report_{department.code}_{year}_{month:02d}.pdf"
    response['Content-Disposition'] = f'attachment; filename="{filename}"'
    return response


@login_required
@module_access_required('CMC')
def export_excel(request, dept_id):
    department = get_object_or_404(Department, id=dept_id)
    today = date.today()
    month = int(request.GET.get('month', today.month))
    year = int(request.GET.get('year', today.year))
    
    excel_data = generate_excel_report(department, month, year)
    
    response = HttpResponse(
        excel_data,
        content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
    )
    filename = f"CMC_Report_{department.code}_{year}_{month:02d}.xlsx"
    response['Content-Disposition'] = f'attachment; filename="{filename}"'
    return response
