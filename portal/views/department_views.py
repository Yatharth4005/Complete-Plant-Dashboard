from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.http import HttpResponse
from portal.models import Department, Module, UserModuleAccess, AuditLog
from portal.utils.access import get_user_module_access_map
from portal.utils.decorators import dept_visibility_required, module_access_required

@login_required
@dept_visibility_required
def dept_hub(request, dept_id):
    """
    Department Hub. Displays modules (TPM, CMC, PRODUCTION, etc.) as cards.
    If the user has permissions, the module card is clickable and accessible.
    Otherwise, it is locked.
    """
    if int(dept_id) == 0:
        return redirect('portal:plant_dashboard')
        
    department = get_object_or_404(Department, id=dept_id)
    active_modules = Module.objects.filter(is_active=True).order_by('sort_order')
    
    # User access map: {module_key: access_level} (VIEW, EDIT, or None)
    access_map = get_user_module_access_map(request.user, department)
    
    module_cards = []
    for module in active_modules:
        access_level = access_map.get(module.key)
        module_cards.append({
            'module': module,
            'accessible': access_level is not None,
            'access_level': access_level,
        })
        
    recent_activity = AuditLog.objects.filter(
        department=department
    ).select_related('user', 'module').order_by('-timestamp')[:8]
    
    context = {
        'department': department,
        'module_cards': module_cards,
        'recent_activity': recent_activity,
        'active_dept_id': department.id,
    }
    return render(request, 'portal/department/dept_hub.html', context)

@login_required
def enter_module(request, dept_id, module_key):
    """
    Validates module access, logs it, and redirects to the module's target URL.
    This acts as the SSO gate.
    """
    department = get_object_or_404(Department, id=dept_id)
    module = get_object_or_404(Module, key__iexact=module_key, is_active=True)
    
    # Check permission
    access_map = get_user_module_access_map(request.user, department)
    if module.key not in access_map:
        if request.headers.get('HX-Request'):
            return HttpResponse(
                '<div style="color: var(--jspl-orange); font-weight: bold; padding: 10px; border: 1px solid var(--jspl-orange); border-radius: 4px; background: rgba(244,121,32,0.1);">You do not have access to this module.</div>',
                status=403
            )
        return redirect('portal:dept_hub', dept_id=dept_id)
        
    # Log Audit Entry
    AuditLog.objects.create(
        user=request.user,
        action='ACCESS_MODULE',
        department=department,
        module=module,
        ip_address=request.META.get('REMOTE_ADDR'),
    )
    
    # Interpolate redirect URL template (e.g. replacing {dept_id})
    target_url = module.redirect_url_template.format(dept_id=dept_id)
    
    # Dynamic host adjustment to ensure cookies are shared correctly
    request_host = request.get_host().split(':')[0] # e.g. 'localhost' or '127.0.0.1'
    if 'localhost' in target_url and request_host == '127.0.0.1':
        target_url = target_url.replace('localhost', '127.0.0.1')
    elif '127.0.0.1' in target_url and request_host == 'localhost':
        target_url = target_url.replace('127.0.0.1', 'localhost')
        
    return redirect(target_url)

@login_required
def coming_soon(request, dept_id, module_key):
    """
    Stub page rendered for modules that are configured but not yet built.
    """
    module = get_object_or_404(Module, key__iexact=module_key)
    
    if int(dept_id) == 0:
        if not request.user.is_admin():
            return redirect('portal:plant_dashboard')
        class DummyDept:
            id = 0
            name = "Overall Plant"
            code = "Overall"
        department = DummyDept()
    else:
        department = get_object_or_404(Department, id=dept_id)
        # Case-insensitive module check
        access_map = get_user_module_access_map(request.user, department)
        matched_key = next((k for k in access_map.keys() if k.upper() == module_key.upper()), None)
        if not matched_key:
            return redirect('portal:dept_hub', dept_id=dept_id)
        module_key = matched_key
    
    context = {
        'department': department,
        'module': module,
        'active_dept_id': department.id,
        'active_module': module_key,
    }
    
    if module_key.upper() == 'SAFETY':
        return render(request, 'portal/department/safety_dashboard.html', context)
    elif module_key.upper() == 'AVAILABILITY':
        return render(request, 'portal/department/availability_dashboard.html', context)
        
    return render(request, 'portal/department/coming_soon.html', context)
