import calendar
from datetime import date
from django.shortcuts import render, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.views.decorators.http import require_POST
from django.http import HttpResponse
from tpm.models import Department
from cmc.models import Equipment, PMScheduleEntry
from cmc.utils.schedule_generator import ensure_monthly_schedule
from portal.utils.decorators import module_access_required

@login_required
@module_access_required('CMC')
def schedule_grid(request, dept_id):
    department = get_object_or_404(Department, id=dept_id)
    
    # Get parameters or defaults
    today = date.today()
    month = int(request.GET.get('month', today.month))
    year = int(request.GET.get('year', today.year))
    search_query = request.GET.get('q', '').strip()
    equip_class = request.GET.get('class', '').strip()

    # Ensure schedule records are populated in database
    ensure_monthly_schedule(department, month, year)

    # Days in month
    num_days = calendar.monthrange(year, month)[1]
    days_list = list(range(1, num_days + 1))

    # Fetch equipment
    equip_qs = Equipment.objects.filter(department=department, is_active=True)
    if search_query:
        equip_qs = equip_qs.filter(name__icontains=search_query)
    if equip_class:
        equip_qs = equip_qs.filter(equipment_class=equip_class)

    # Fetch all entries for this month
    entries_qs = PMScheduleEntry.objects.filter(
        equipment__department=department,
        scheduled_date__month=month,
        scheduled_date__year=year
    )

    # Map to dictionary: { (equipment_id, day): entry }
    schedule_map = {}
    for entry in entries_qs:
        schedule_map[(entry.equipment_id, entry.scheduled_date.day)] = entry

    # Structure data for rendering
    grid_data = []
    for eq in equip_qs:
        row = {
            'equipment': eq,
            'days': []
        }
        for d in days_list:
            row['days'].append({
                'day': d,
                'entry': schedule_map.get((eq.id, d))
            })
        grid_data.append(row)

    # Calculate compliance %
    total_scheduled = entries_qs.count()
    completed = entries_qs.filter(status=PMScheduleEntry.VisitStatus.DONE).count()
    compliance_rate = round((completed / total_scheduled * 100), 1) if total_scheduled > 0 else 100.0

    context = {
        'department': department,
        'month': month,
        'year': year,
        'search_query': search_query,
        'equip_class': equip_class,
        'days_list': days_list,
        'grid_data': grid_data,
        'compliance_rate': compliance_rate,
        'months': [
            (1, 'January'), (2, 'February'), (3, 'March'), (4, 'April'),
            (5, 'May'), (6, 'June'), (7, 'July'), (8, 'August'),
            (9, 'September'), (10, 'October'), (11, 'November'), (12, 'December')
        ],
        'years': range(2025, today.year + 2),
        'active_tab': 'schedule',
        'query_params': f"month={month}&year={year}&q={search_query}&class={equip_class}",
    }
    return render(request, 'cmc/schedule/schedule_grid.html', context)


@login_required
@module_access_required('CMC')
@require_POST
def update_cell(request, dept_id):
    department = get_object_or_404(Department, id=dept_id)
    entry_id = request.POST.get('entry_id')
    new_status = request.POST.get('status')
    
    entry = get_object_or_404(PMScheduleEntry, id=entry_id, equipment__department=department)
    entry.status = new_status
    if new_status == PMScheduleEntry.VisitStatus.DONE:
        entry.actual_date = date.today()
    else:
        entry.actual_date = None
    entry.done_by = request.user
    entry.save()

    # Re-render only this schedule cell
    context = {
        'day': entry.scheduled_date.day,
        'entry': entry,
        'department': department
    }
    return render(request, 'cmc/partials/_schedule_cell.html', context)
