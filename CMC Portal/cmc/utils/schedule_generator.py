import calendar
from datetime import date
from cmc.models import PMScheduleEntry, Equipment

def ensure_monthly_schedule(department, month, year):
    """
    Ensure PMScheduleEntry objects exist for all scheduled days of all equipment
    in the given department for the specified month and year.
    """
    equipments = Equipment.objects.filter(department=department, is_active=True)
    num_days = calendar.monthrange(year, month)[1]
    
    entries_to_create = []
    
    # Prefetch existing schedule entries for this month/year to prevent duplicate hits
    existing_dates = set(
        PMScheduleEntry.objects.filter(
            equipment__department=department,
            scheduled_date__month=month,
            scheduled_date__year=year
        ).values_list('equipment_id', 'scheduled_date')
    )
    
    for eq in equipments:
        if not eq.scheduled_days:
            continue
            
        # Parse scheduled days, e.g. "1, 15" or "5"
        days_parts = [p.strip() for p in eq.scheduled_days.split(',') if p.strip()]
        for part in days_parts:
            try:
                day = int(part)
                if 1 <= day <= num_days:
                    sched_date = date(year, month, day)
                    if (eq.id, sched_date) not in existing_dates:
                        entries_to_create.append(
                            PMScheduleEntry(
                                equipment=eq,
                                scheduled_date=sched_date,
                                status=PMScheduleEntry.VisitStatus.PENDING
                            )
                        )
            except ValueError:
                pass
                
    if entries_to_create:
        PMScheduleEntry.objects.bulk_create(entries_to_create)
