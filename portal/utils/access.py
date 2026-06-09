from portal.models import UserModuleAccess, Module

def get_user_module_access_map(user, department) -> dict:
    """
    Returns a dictionary of module accesses for a user in a specific department:
    { module_key: access_level ('VIEW' or 'EDIT') }
    Admins get 'EDIT' access to all active modules.
    """
    if not user.is_authenticated:
        return {}
        
    if user.is_admin():
        active_modules = Module.objects.filter(is_active=True)
        return {m.key: 'EDIT' for m in active_modules}
        
    records = UserModuleAccess.objects.filter(
        user=user,
        department=department,
        module__is_active=True
    ).select_related('module')
    
    return {r.module.key: r.access_level for r in records}

def user_can_access_module(user, department, module_key) -> bool:
    access_map = get_user_module_access_map(user, department)
    return module_key in access_map

def user_can_edit_module(user, department, module_key) -> bool:
    access_map = get_user_module_access_map(user, department)
    return access_map.get(module_key) == 'EDIT'
