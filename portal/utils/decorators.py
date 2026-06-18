from functools import wraps
from django.shortcuts import redirect, get_object_or_404
from tpm.models import Department
from portal.utils.access import user_can_access_module, user_can_edit_module

def dept_visibility_required(view_func):
    """
    Ensures that a user can only view a department page if:
    1. They are an admin.
    2. It is their own department.
    3. They have been granted module-level access inside that department.
    """
    @wraps(view_func)
    def wrapper(request, dept_id, *args, **kwargs):
        if not request.user.is_authenticated:
            return redirect('portal:login')
            
        if request.user.is_admin():
            return view_func(request, dept_id, *args, **kwargs)
            
        # User's primary department
        if request.user.department_id == int(dept_id):
            return view_func(request, dept_id, *args, **kwargs)
            
        # Cross-dept access?
        from portal.models import UserModuleAccess
        has_access = UserModuleAccess.objects.filter(
            user=request.user,
            department_id=dept_id
        ).exists()
        
        if has_access:
            return view_func(request, dept_id, *args, **kwargs)
            
        return redirect('portal:plant_dashboard')
    return wrapper

def module_access_required(module_key, require_edit=False):
    """
    Decorator for views inside module sub-apps (TPM, CMC, etc.).
    Verifies that the user has the required access level for the module in that department.
    """
    def decorator(view_func):
        @wraps(view_func)
        def wrapper(request, dept_id, *args, **kwargs):
            if not request.user.is_authenticated:
                return redirect('portal:login')
                
            if int(dept_id) == 0:
                if request.user.is_admin():
                    return view_func(request, dept_id, *args, **kwargs)
                return redirect('portal:plant_dashboard')

            department = get_object_or_404(Department, id=dept_id)
            
            if request.user.is_admin():
                allowed = True
            elif require_edit:
                allowed = user_can_edit_module(request.user, department, module_key)
            else:
                allowed = user_can_access_module(request.user, department, module_key)
                
            if not allowed:
                return redirect('portal:dept_hub', dept_id=dept_id)
                
            return view_func(request, dept_id, *args, **kwargs)
        return wrapper
    return decorator
