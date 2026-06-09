# tpm/utils/decorators.py

from functools import wraps
from django.core.exceptions import PermissionDenied
from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, redirect
from tpm.models import Department
from portal.utils.access import user_can_access_module

def get_main_portal_url(request, path=''):
    request_host = request.get_host().split(':')[0]
    return f"http://{request_host}:8000{path}"

def admin_required(view_func):
    @wraps(view_func)
    def wrapper(request, *args, **kwargs):
        if not request.user.is_authenticated:
            return redirect(get_main_portal_url(request, '/login/?next=' + request.build_absolute_uri()))
        if not request.user.is_admin():
            raise PermissionDenied
        return view_func(request, *args, **kwargs)
    return wrapper

def dept_access_required(view_func):
    """Admin passes through. USER must have TPM module access for requested department."""
    @wraps(view_func)
    def wrapper(request, *args, **kwargs):
        if not request.user.is_authenticated:
            return redirect(get_main_portal_url(request, '/login/?next=' + request.build_absolute_uri()))
        
        dept_id = kwargs.get('dept_id')
        if not request.user.is_admin():
            department = get_object_or_404(Department, id=dept_id)
            if not user_can_access_module(request.user, department, 'TPM'):
                return redirect(get_main_portal_url(request, f'/department/{dept_id}/'))
        return view_func(request, *args, **kwargs)
    return wrapper
