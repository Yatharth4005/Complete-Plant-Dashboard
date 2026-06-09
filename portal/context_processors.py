from tpm.models import Department
from portal.models import UserModuleAccess, Module

def sidebar_context(request):
    """
    Context processor to automatically provide sidebar links and active state
    based on the current request path and user authorization.
    """
    if not request.user.is_authenticated:
        return {}
        
    if request.user.is_admin():
        depts = Department.objects.all().order_by('name')
    else:
        # Resolve user's primary department + any cross-dept access depts
        dept_ids = set()
        if request.user.department_id:
            dept_ids.add(request.user.department_id)
        
        # Check permissions for other departments
        permitted_accesses = UserModuleAccess.objects.filter(user=request.user)
        for access in permitted_accesses:
            dept_ids.add(access.department_id)
            
        depts = Department.objects.filter(id__in=dept_ids).order_by('name')

    # Automatically identify active department ID and active module from URL
    path = request.path
    active_dept_id = None
    active_module = None
    
    parts = [p for p in path.split('/') if p]
    if 'department' in parts:
        try:
            idx = parts.index('department')
            if idx + 1 < len(parts):
                active_dept_id = int(parts[idx + 1])
        except ValueError:
            pass
            
    # Detect module namespace in path
    if 'tpm' in parts:
        active_module = 'TPM'
    elif 'cmc' in parts:
        active_module = 'CMC'
    elif 'iso' in parts:
        active_module = 'ISO'
    elif 'delays' in parts:
        active_module = 'Delays'
    elif 'oee' in parts:
        active_module = 'OEE'
    elif 'availability' in parts:
        active_module = 'Availability'

    # Get user access mapping for the current department to display sidebar indicators
    user_modules_map = {}
    if active_dept_id:
        from portal.utils.access import get_user_module_access_map
        try:
            curr_dept = Department.objects.get(id=active_dept_id)
            user_modules_map = get_user_module_access_map(request.user, curr_dept)
        except Department.DoesNotExist:
            pass

    return {
        'sidebar_departments': depts,
        'sidebar_modules': Module.objects.all().order_by('sort_order'),
        'active_dept_id': active_dept_id,
        'active_module': active_module,
        'user_modules_map': user_modules_map,
    }
