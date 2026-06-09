from datetime import date
from cmc.models import PMScheduleEntry

def compute_overall_status(last_vib, last_oil, last_wda):
    """
    Returns 'ok', 'attention', 'critical', or 'unknown'
    based on the latest readings from all three sources.
    """
    statuses = []
    if last_vib:
        if last_vib.status in ('NOT_OK',):
            statuses.append('critical')
        elif last_vib.status in ('ATTENTION', 'UM'):
            statuses.append('attention')
        else:
            statuses.append('ok')

    if last_oil:
        if last_oil.status == 'NOT_OK':
            statuses.append('critical')
        else:
            statuses.append('ok')

    if last_wda:
        if last_wda.final_status == 'NOT_OK':
            statuses.append('critical')
        elif last_wda.final_status == 'ATTENTION':
            statuses.append('attention')
        elif last_wda.final_status == 'OK':
            statuses.append('ok')

    if not statuses:
        return 'unknown'
    if 'critical' in statuses:
        return 'critical'
    if 'attention' in statuses:
        return 'attention'
    return 'ok'


def is_overdue(equipment, current_date):
    """Returns True if equipment is past its scheduled monitoring date with no entry."""
    latest_entry = PMScheduleEntry.objects.filter(
        equipment=equipment
    ).order_by('-scheduled_date').first()

    if not latest_entry:
        return False
    if latest_entry.status == 'PENDING' and latest_entry.scheduled_date < current_date:
        return True
    return False
