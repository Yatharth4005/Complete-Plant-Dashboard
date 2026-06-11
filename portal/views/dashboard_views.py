from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from tpm.models import Department, CAPAReport
from portal.models import Module, UserModuleAccess
from portal.utils.access import get_user_module_access_map

@login_required
def plant_dashboard(request):
    """
    Landing dashboard listing all 28 departments as cards.
    Each card displays its subparts/modules (TPM, CMC, etc.) with lock/unlock status.
    """
    STANDARD_DEPTS = [
        'BF1', 'BF2', 'BP', 'CP', 'CO', 'DRI1', 'DRI2', 'EP', 'LDP', 'OP',
        'PGP1', 'PGP2', 'PGP3', 'PM', 'PP1', 'PP2', 'PP3', 'PPP3',
        'RMHS1', 'RMHS2', 'RMHS3', 'RM', 'SAF1', 'SAF2', 'SMS2', 'SMS3',
        'SINT', 'SPM'
    ]
    departments = Department.objects.filter(code__in=STANDARD_DEPTS).order_by('name')
    active_modules = Module.objects.filter(is_active=True).order_by('sort_order')
    
    departments_data = []
    for dept in departments:
        # Get module accesses for the current user in this department
        access_map = get_user_module_access_map(request.user, dept)
        
        module_states = []
        for module in active_modules:
            access_level = access_map.get(module.key)
            module_states.append({
                'module': module,
                'accessible': access_level is not None,
                'access_level': access_level,
            })
            
        departments_data.append({
            'dept': dept,
            'modules': module_states,
        })
        
    context = {
        'departments_data': departments_data,
        'active_section': 'dashboard',
    }
    return render(request, 'portal/dashboard/plant_dashboard.html', context)

@login_required
def capa_reports(request):
    """
    Renders the CAPA reports list inside the main portal dashboard.
    """
    reports = CAPAReport.objects.all().order_by('-created_at')
    context = {
        'reports': reports,
        'active_section': 'capa',
    }
    return render(request, 'portal/dashboard/capa_reports.html', context)
