# tpm/templatetags/tpm_tags.py

from django import template
from tpm.utils.calculations import get_status_css_class, get_status

register = template.Library()

@register.filter
def get_item(dictionary, key):
    """Fetches dictionary values dynamically in templates"""
    if not isinstance(dictionary, dict):
        return None
    return dictionary.get(str(key)) or dictionary.get(key)

@register.filter
def achievement_class(achievement):
    """Returns CSS badge class based on achievement percentage"""
    if achievement is None:
        return 'badge-muted'
    status = get_status(achievement)
    return get_status_css_class(status)

@register.filter
def percentage(value):
    """Formats float to percentage string"""
    if value is None:
        return '—'
    return f"{round(value, 1)}%"

@register.filter
def make_range(value):
    """Returns range for pagination or grid displays"""
    return range(1, int(value) + 1)


@register.filter
def split_str(value, key):
    """Splits a string by a delimiter"""
    if not isinstance(value, str):
        return []
    return value.split(key)


@register.filter
def index_list(lst, idx):
    """Gets list element at index idx, returns empty string on failure"""
    try:
        if not lst:
            return ""
        return lst[int(idx)]
    except (IndexError, ValueError, TypeError):
        return ""


@register.simple_tag
def get_list_item(lst, idx):
    """Gets list element at index idx, returns empty dict on failure"""
    try:
        if not lst:
            return {}
        return lst[int(idx)]
    except (IndexError, ValueError, TypeError):
        return {}


@register.simple_tag
def get_plan_cell_status(plan_cells_dict, machine_id, step, year, month, week):
    key = f"{machine_id}-{step}-{year}-{month}-{week}"
    return plan_cells_dict.get(key, "")


