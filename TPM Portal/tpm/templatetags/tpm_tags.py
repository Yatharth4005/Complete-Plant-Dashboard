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
