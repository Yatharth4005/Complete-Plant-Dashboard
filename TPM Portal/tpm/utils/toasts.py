# tpm/utils/toasts.py

from django.template.loader import render_to_string

def render_toast(message, toast_type='success'):
    """
    Renders the unified, self-dismissing toast notification HTML with inline CSS styles
    and Alpine.js auto-hide logic to prevent caching issues.
    """
    return render_to_string('partials/_toast.html', {
        'message': message,
        'type': toast_type
    })
