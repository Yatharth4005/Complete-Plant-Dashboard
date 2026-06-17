from django.shortcuts import render, redirect
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
    active_modules = Module.objects.filter(is_active=True).exclude(key__in=['FMEA', 'CAPA']).order_by('sort_order')
    
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
def overall_plant_dashboard(request):
    """
    Dashboard for Admins showing cards for all 8 modules.
    Only accessible to admins.
    """
    if not request.user.is_admin():
        from django.contrib import messages
        messages.error(request, "Only administrators can access the Overall Plant Dashboard.")
        return redirect('portal:plant_dashboard')

    modules_data = [
        {
            'key': 'TPM',
            'label': 'Total Productive Maintenance',
            'description': 'KPI tracking across 8 pillars + Workstation KPIs',
            'icon': 'gear',
            'color_class': 'module-tpm',
            'url': '/tpm/dashboard/',
        },
        {
            'key': 'CMC',
            'label': 'Condition Monitoring Cell',
            'description': 'Machinery health: vibration monitoring, oil testing, and wear debris analysis (WDA)',
            'icon': 'file-contract',
            'color_class': 'module-cmc',
            'url': '/cmc/department/0/',
        },
        {
            'key': 'ISO',
            'label': 'ISO Compliance & Standards',
            'description': 'Standard operating procedures, internal audit compliance logs',
            'icon': 'award',
            'color_class': 'module-iso',
            'url': '/department/0/coming-soon/ISO/',
        },
        {
            'key': 'Delays',
            'label': 'Delay Logs & Tracking',
            'description': 'Production line downtime, log summaries, and breakdown analysis',
            'icon': 'clock',
            'color_class': 'module-delays',
            'url': '/delays/department/0/',
        },
        {
            'key': 'OEE',
            'label': 'Overall Equipment Effectiveness',
            'description': 'Equipment performance, availability, and quality metrics',
            'icon': 'bar-chart',
            'color_class': 'module-oee',
            'url': '/department/0/coming-soon/OEE/',
        },
        {
            'key': 'Availability',
            'label': 'Availability Logs',
            'description': 'Uptime monitoring, machine availability logs, and maintenance alerts',
            'icon': 'activity',
            'color_class': 'module-availability',
            'url': '/department/0/coming-soon/Availability/',
        },
        {
            'key': 'FMEA',
            'label': 'FMEA',
            'description': 'Failure Mode and Effects Analysis for risk identification and mitigation',
            'icon': 'shield',
            'color_class': 'module-fmea',
            'url': '/fmea/department/0/',
        },
        {
            'key': 'CAPA',
            'label': 'CAPA Reports',
            'description': 'Corrective Action and Preventive Action tracking and report generation',
            'icon': 'clipboard',
            'color_class': 'module-capa',
            'url': '/capa/department/0/',
        },
    ]

    context = {
        'modules_data': modules_data,
        'active_section': 'overall_dashboard',
    }
    return render(request, 'portal/dashboard/overall_plant_dashboard.html', context)

@login_required
def capa_reports(request):
    """
    Renders the CAPA reports list inside the main portal dashboard.
    Supports showing the new form and prefilling fields via delay_record_id or query parameters.
    """
    action = request.GET.get('action')
    show_new_form = (action == 'new')
    
    reports = CAPAReport.objects.all().order_by('-created_at')
    
    # Fetch all departments for selection list
    depts = Department.objects.all().order_by('name')
    
    # Setup default prefills
    prefills = {
        'capa_no': f"CAPA-{(CAPAReport.objects.count() + 1):03d}",
        'responsible_team': [
            {'name': '', 'members': '', 'role': '', 'contact': ''},
            {'name': '', 'members': '', 'role': '', 'contact': ''},
            {'name': '', 'members': '', 'role': '', 'contact': ''},
        ],
        'corrective_actions': [
            {'action': '', 'responsibility': '', 'target_date': '', 'impl_date': ''},
            {'action': '', 'responsibility': '', 'target_date': '', 'impl_date': ''},
        ],
        'preventive_actions': [
            {'action': '', 'responsibility': '', 'target_date': '', 'impl_date': ''},
            {'action': '', 'responsibility': '', 'target_date': '', 'impl_date': ''},
        ]
    }
    
    # Check GET parameters for prefilling
    dept_id = request.GET.get('department_id')
    dept = None
    if dept_id:
        try:
            dept = Department.objects.get(id=dept_id)
        except Department.DoesNotExist:
            pass
            
    report = None
    delay_record_id = request.GET.get('delay_record_id')
    if delay_record_id:
        try:
            from delays.models import DelayRecord
            delay_rec = DelayRecord.objects.get(id=delay_record_id)
            dept = delay_rec.department
            date_str = delay_rec.date.strftime('%d.%m.%Y') if delay_rec.date else ""
            dur_hrs = str(round(delay_rec.duration_mins / 60.0, 2)) if delay_rec.duration_mins else ""
            problem_what = delay_rec.description or f"Breakdown on {delay_rec.equipment or 'Equipment'} ({delay_rec.agency})"
            
            report = CAPAReport(
                department=dept,
                area_section=delay_rec.equipment or "",
                date_incident=date_str,
                problem_what=problem_what,
                breakdown_hrs=dur_hrs
            )
        except Exception:
            pass
            
    if not report:
        report = CAPAReport(
            department=dept,
            area_section=request.GET.get('area_section', ''),
            date_incident=request.GET.get('date_incident', ''),
            problem_what=request.GET.get('problem_what', ''),
            breakdown_hrs=request.GET.get('breakdown_hrs', '')
        )
        
    context = {
        'reports': reports,
        'active_section': 'capa',
        'show_new_form': show_new_form,
        'report': report,
        'depts': depts,
        'prefills': prefills,
    }
    return render(request, 'portal/dashboard/capa_reports.html', context)
