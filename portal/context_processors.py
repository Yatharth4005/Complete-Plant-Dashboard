from tpm.models import Department
from portal.models import UserModuleAccess, Module

def sidebar_context(request):
    """
    Context processor to automatically provide sidebar links and active state
    based on the current request path and user authorization.
    """
    if not request.user.is_authenticated:
        return {}
        
    # Fetch unread notifications for the header icon dropdown
    header_notifications = []
    header_notifications_count = 0
    try:
        from portal.models import PortalNotification
        header_notifications = PortalNotification.objects.filter(user=request.user, is_read=False).order_by('-created_at')[:10]
        header_notifications_count = PortalNotification.objects.filter(user=request.user, is_read=False).count()
    except Exception:
        pass

    if request.user.is_admin():
        depts = Department.objects.filter(is_active=True).order_by('name')
    else:
        # Resolve user's primary department + any cross-dept access depts
        dept_ids = set()
        if request.user.department_id:
            dept_ids.add(request.user.department_id)
        
        # Check permissions for other departments
        permitted_accesses = UserModuleAccess.objects.filter(user=request.user)
        for access in permitted_accesses:
            dept_ids.add(access.department_id)
            
        depts = Department.objects.filter(id__in=dept_ids, is_active=True).order_by('name')

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
            
    if not active_dept_id:
        dept_param = request.GET.get('department_id')
        if dept_param:
            try:
                active_dept_id = int(dept_param)
            except ValueError:
                pass
            
    tab_param = request.GET.get('tab', '').lower()
    parts_lower = [p.lower() for p in parts]
    if 'tpm' in parts_lower:
        active_module = 'TPM'
    elif 'cmc' in parts_lower:
        active_module = 'CMC'
    elif 'iso' in parts_lower:
        active_module = 'ISO'
    elif 'checklist' in tab_param or 'checklist' in parts_lower:
        active_module = 'Checklist'
    elif 'delays' in parts_lower:
        active_module = 'Delays'
    elif 'oee' in parts_lower:
        active_module = 'OEE'
    elif 'availability' in parts_lower:
        active_module = 'Availability'
    elif 'fmea' in parts_lower:
        active_module = 'FMEA'
    elif 'capa' in parts_lower:
        active_module = 'CAPA'
    elif 'spare' in parts_lower:
        active_module = 'SPARE'
    elif 'dakshata' in parts_lower:
        active_module = 'DAKSHATA'
    elif 'smed' in parts_lower:
        active_module = 'SMED'
    elif 'hod-kpi' in parts_lower:
        active_module = 'HOD_KPI'

    # Get user access mapping for the current department to display sidebar indicators
    user_modules_map = {}
    if active_dept_id:
        from portal.utils.access import get_user_module_access_map
        try:
            curr_dept = Department.objects.get(id=active_dept_id)
            user_modules_map = get_user_module_access_map(request.user, curr_dept)
        except Department.DoesNotExist:
            pass

    sidebar_modules = Module.objects.filter(is_active=True).order_by('sort_order')

    # Build access lists per department for offline (non-active) expanding
    sidebar_departments_data = []
    if request.user.is_admin():
        admin_modules = [m.key for m in sidebar_modules]
        for d in depts:
            sidebar_departments_data.append({
                'dept': d,
                'accessible_modules': admin_modules
            })
    else:
        for d in depts:
            records = UserModuleAccess.objects.filter(user=request.user, department=d, module__is_active=True).select_related('module')
            accessible_modules = [r.module.key for r in records]
            sidebar_departments_data.append({
                'dept': d,
                'accessible_modules': accessible_modules
            })

    pillars = [
        {'id': 'KK', 'label': 'KK (Kobetsu Kaizen)'},
        {'id': 'JH', 'label': 'JH (Jishu Hozen)'},
        {'id': 'PM', 'label': 'PM (Planned Maintenance)'},
        {'id': 'QM', 'label': 'QM (Quality Maintenance)'},
        {'id': 'ET', 'label': 'ET (Education & Training)'},
        {'id': 'DM', 'label': 'DM (Initial Flow/Design)'},
        {'id': 'SHE', 'label': 'SHE (Safety & Health)'},
        {'id': 'OTPM', 'label': 'OTPM (Office TPM)'},
    ]

    return {
        'sidebar_departments': depts,
        'sidebar_departments_data': sidebar_departments_data,
        'sidebar_modules': sidebar_modules,
        'active_dept_id': active_dept_id,
        'active_module': active_module,
        'user_modules_map': user_modules_map,
        'pillars': pillars,
        'header_notifications': header_notifications,
        'header_notifications_count': header_notifications_count,
    }
