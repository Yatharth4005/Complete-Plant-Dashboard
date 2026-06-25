import os
from datetime import datetime, date, timedelta
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.db.models import Count, Avg, Q
from django.http import HttpResponseForbidden, JsonResponse
from tpm.models import Department, User, CAPAReport
from Safety.models import Incident

# Check and auto-seed safety data if empty
def check_and_seed_safety_data():
    if Incident.objects.count() > 0:
        return
        
    depts = list(Department.objects.all())
    if not depts:
        return
        
    # Get standard seed users
    users = list(User.objects.all())
    admin_user = next((u for u in users if u.is_admin()), None)
    if not admin_user and users:
        admin_user = users[0]
        
    # Let's seed incidents across the last 6 months
    today = date.today()
    
    # 1. Lost Time Injury (LTI)
    Incident.objects.create(
        department=depts[0] if len(depts) > 0 else None,
        date_incident=today - timedelta(days=90),
        severity='LTI',
        unsafe_type='NONE',
        category='Equipment Interaction',
        description='Operator hand caught in conveyor belt pulley while clearing jamming without isolating power (LOTO violation).',
        status='Closed',
        investigation_findings='Root cause identified as lack of machine guard and LOTO procedure violation. Guard installed, LOTO training conducted.',
        closure_date=today - timedelta(days=80),
        reported_by=admin_user,
        reviewed_by=admin_user
    )
    
    # 2. Restricted Work Cases (RWC) - 7 cases
    rwc_categories = ['Material Handling', 'Slip/Trip/Fall', 'Equipment Interaction', 'Other']
    for i in range(7):
        dept = depts[i % len(depts)]
        Incident.objects.create(
            department=dept,
            date_incident=today - timedelta(days=15 * (i + 1)),
            severity='RWC',
            unsafe_type='NONE',
            category=rwc_categories[i % len(rwc_categories)],
            description=f'Employee suffered minor back sprain/strain during heavy load lifting of {10 * (i + 1)}kg manual handling.',
            status='Closed' if i < 5 else 'Investigation',
            investigation_findings=f'Incorrect lifting posture. Action: Refresher training on manual handling safety posture completed.' if i < 5 else '',
            closure_date=today - timedelta(days=15 * i + 5) if i < 5 else None,
            reported_by=admin_user,
            reviewed_by=admin_user if i < 5 else None
        )
        
    # 3. Medical Treatment Cases (MTC) - 4 cases
    mtc_categories = ['Slip/Trip/Fall', 'PPE Violation', 'Material Handling', 'Fire Hazard']
    for i in range(4):
        dept = depts[(i + 2) % len(depts)]
        Incident.objects.create(
            department=dept,
            date_incident=today - timedelta(days=22 * (i + 1)),
            severity='MTC',
            unsafe_type='NONE',
            category=mtc_categories[i % len(mtc_categories)],
            description=f'Deep laceration on hand while adjusting machine settings without cut-resistant safety gloves.',
            status='Closed' if i < 3 else 'Pending',
            investigation_findings=f'Inadequate PPE audit. Standardized cut-resistant gloves mandatory for all setup technicians.' if i < 3 else '',
            closure_date=today - timedelta(days=22 * i + 8) if i < 3 else None,
            reported_by=admin_user,
            reviewed_by=admin_user if i < 3 else None
        )
        
    # 4. First Aid Cases (FA) - 9 cases
    fa_categories = ['Slip/Trip/Fall', 'PPE Violation', 'Material Handling', 'Fire Hazard', 'Other']
    for i in range(9):
        dept = depts[(i + 4) % len(depts)]
        Incident.objects.create(
            department=dept,
            date_incident=today - timedelta(days=10 * (i + 1)),
            severity='FA',
            unsafe_type='NONE',
            category=fa_categories[i % len(fa_categories)],
            description=f'First aid minor splash of grease in eye / minor skin scrape against raw metal shelf during sorting.',
            status='Closed',
            investigation_findings='Administered eye wash and band-aid. Advised strictly wearing safety goggles in sorting area.',
            closure_date=today - timedelta(days=10 * i + 1),
            reported_by=admin_user,
            reviewed_by=admin_user
        )
        
    # 5. Near Miss (NM) - 10 cases
    nm_categories = ['Material Handling', 'Slip/Trip/Fall', 'PPE Violation', 'Equipment Interaction', 'Fire Hazard']
    for i in range(10):
        dept = depts[(i + 1) % len(depts)]
        Incident.objects.create(
            department=dept,
            date_incident=today - timedelta(days=8 * (i + 1)),
            severity='NM',
            unsafe_type='NONE',
            category=nm_categories[i % len(nm_categories)],
            description=f'A forklift passed closely, dropping a poorly stacked load block {1.5} meters away from a pedestrian pathway.',
            status='Closed' if i < 8 else 'Pending',
            investigation_findings=f'Pathway demarcated. Restacked pallets correctly and adjusted forklift speed limits.' if i < 8 else '',
            closure_date=today - timedelta(days=8 * i + 2) if i < 8 else None,
            reported_by=admin_user,
            reviewed_by=admin_user if i < 8 else None
        )
        
    # 6. Unsafe Acts (UA) & Unsafe Conditions (UC)
    for i in range(30):
        dept = depts[(i + 3) % len(depts)]
        unsafe_type = 'UA' if i % 2 == 0 else 'UC'
        Incident.objects.create(
            department=dept,
            date_incident=today - timedelta(days=4 * (i + 1)),
            severity='FA',  # We can set FA or NM severity for observations, or standard
            unsafe_type=unsafe_type,
            category='PPE Violation' if unsafe_type == 'UA' else 'Equipment Interaction',
            description=f'{"Employee working without safety harness" if unsafe_type == "UA" else "Oil spill near the conveyor gearbox"}. observed during safety walk.',
            status='Closed' if i < 25 else 'Pending',
            investigation_findings='Corrected immediately on observation.' if i < 25 else '',
            closure_date=today - timedelta(days=4 * i) if i < 25 else None,
            reported_by=admin_user,
            reviewed_by=admin_user if i < 25 else None
        )


@login_required
def im_dashboard(request, dept_id):
    # Resolve current department context
    if int(dept_id) == 0:
        department = type('DummyDept', (object,), {
            'id': 0,
            'name': 'Overall Plant',
            'code': 'Overall'
        })()
        incidents_query = Incident.objects.all()
    else:
        department = get_object_or_404(Department, id=dept_id)
        incidents_query = Incident.objects.filter(department=department)
        
    # 1. KPI calculations
    total_incidents = incidents_query.count()
    pending_count = incidents_query.filter(status__in=['Pending', 'Investigation']).count()
    completed_count = incidents_query.filter(status='Closed').count()
    
    # Calculate Average Closure Days
    closed_incidents = incidents_query.filter(status='Closed', closure_date__isnull=False)
    total_days = 0
    closed_with_duration_count = 0
    for inc in closed_incidents:
        if inc.closure_date and inc.date_incident:
            total_days += (inc.closure_date - inc.date_incident).days
            closed_with_duration_count += 1
            
    avg_closure_days = round(total_days / closed_with_duration_count, 1) if closed_with_duration_count > 0 else 0
    
    # Reports open >15 Days
    today = date.today()
    over_15_days_ago = today - timedelta(days=15)
    reports_over_15_days = incidents_query.filter(
        status__in=['Pending', 'Investigation'],
        date_incident__lt=over_15_days_ago
    ).count()
    
    # Compliance score
    compliance_pct = round((completed_count / total_incidents) * 100) if total_incidents > 0 else 100
    
    # 2. Charts Data Processing
    
    # (a) Incident Severity Distribution (LTI, RWC, MTC, FA, NM)
    severity_counts = list(
        incidents_query.filter(unsafe_type='NONE')
        .values('severity')
        .annotate(count=Count('id'))
    )
    severity_data = {'LTI': 0, 'RWC': 0, 'MTC': 0, 'FA': 0, 'NM': 0}
    for item in severity_counts:
        if item['severity'] in severity_data:
            severity_data[item['severity']] = item['count']
            
    # Include Near Misses specifically in NM
    nm_count = incidents_query.filter(severity='NM').count()
    severity_data['NM'] = nm_count
    
    # (b) Unsafe Act (UA) vs Unsafe Condition (UC) Donut
    ua_count = incidents_query.filter(unsafe_type='UA').count()
    uc_count = incidents_query.filter(unsafe_type='UC').count()
    total_uauc = ua_count + uc_count
    ua_pct = round((ua_count / total_uauc) * 100) if total_uauc > 0 else 50
    uc_pct = 100 - ua_pct if total_uauc > 0 else 50
    
    # (c) Monthly Incident & UA/UC Trends (Last 6 Months)
    months_list = []
    monthly_sev_data = {
        'LTI': [], 'RWC': [], 'MTC': [], 'FA': [], 'NM': [], 'UA': [], 'UC': []
    }
    
    # Let's slide back 6 months from today
    for i in range(5, -1, -1):
        # Calculate month starting date
        first_of_month = (today.replace(day=1) - timedelta(days=30 * i)).replace(day=1)
        months_list.append(first_of_month.strftime('%b %y'))
        
        # Calculate end of month date
        next_month = first_of_month + timedelta(days=32)
        end_of_month = next_month.replace(day=1) - timedelta(days=1)
        
        # Filter monthly queries
        m_query = incidents_query.filter(date_incident__range=[first_of_month, end_of_month])
        
        monthly_sev_data['LTI'].append(m_query.filter(severity='LTI', unsafe_type='NONE').count())
        monthly_sev_data['RWC'].append(m_query.filter(severity='RWC', unsafe_type='NONE').count())
        monthly_sev_data['MTC'].append(m_query.filter(severity='MTC', unsafe_type='NONE').count())
        monthly_sev_data['FA'].append(m_query.filter(severity='FA', unsafe_type='NONE').count())
        monthly_sev_data['NM'].append(m_query.filter(severity='NM').count())
        monthly_sev_data['UA'].append(m_query.filter(unsafe_type='UA').count())
        monthly_sev_data['UC'].append(m_query.filter(unsafe_type='UC').count())
        
    # (d) Near Miss Analysis Pareto Data
    nm_cat_query = list(
        incidents_query.filter(severity='NM')
        .values('category')
        .annotate(count=Count('id'))
        .order_by('-count')
    )
    
    nm_categories = ['Material Handling', 'Slip/Trip/Fall', 'PPE Violation', 'Equipment Interaction', 'Fire Hazard']
    nm_counts = {cat: 0 for cat in nm_categories}
    for item in nm_cat_query:
        cat = item['category']
        if cat in nm_counts:
            nm_counts[cat] = item['count']
        else:
            nm_counts['Other'] = nm_counts.get('Other', 0) + item['count']
            
    # Sort categories by count
    sorted_nm = sorted(nm_counts.items(), key=lambda x: x[1], reverse=True)
    pareto_labels = [item[0] for item in sorted_nm]
    pareto_counts = [item[1] for item in sorted_nm]
    
    # Calculate cumulative percentage
    total_nm_cats = sum(pareto_counts)
    cumulative_sum = 0
    pareto_cum_pct = []
    for count in pareto_counts:
        cumulative_sum += count
        pct = round((cumulative_sum / total_nm_cats) * 100) if total_nm_cats > 0 else 0
        pareto_cum_pct.append(pct)
        
    # (e) CAPA Stacked Bar Chart per Department (pulling directly from CAPAReport model)
    departments_list = list(Department.objects.filter(is_active=True).order_by('name'))
    capa_labels = []
    capa_open = []
    capa_closed = []
    capa_overdue = []
    
    for d in departments_list:
        capa_labels.append(d.code)
        reports = CAPAReport.objects.filter(department=d)
        
        open_c = reports.filter(status__in=['Open', 'In Progress']).count()
        closed_c = reports.filter(status='Closed').count()
        
        # Calculate Overdue CAPAs
        overdue_c = 0
        for r in reports.filter(status__in=['Open', 'In Progress']):
            is_overdue = False
            for act in r.corrective_actions:
                t_date = act.get('target_date')
                if t_date:
                    try:
                        parsed_date = datetime.strptime(t_date, "%Y-%m-%d").date()
                        if parsed_date < today and not act.get('impl_date'):
                            is_overdue = True
                    except ValueError:
                        try:
                            parsed_date = datetime.strptime(t_date, "%d.%m.%Y").date()
                            if parsed_date < today and not act.get('impl_date'):
                                is_overdue = True
                        except ValueError:
                            pass
            if is_overdue:
                overdue_c += 1
                
        capa_open.append(open_c - overdue_c if open_c >= overdue_c else 0)
        capa_closed.append(closed_c)
        capa_overdue.append(overdue_c)
        
    # Incident Lists
    pending_reviews = incidents_query.filter(status__in=['Pending', 'Investigation']).select_related('department', 'reported_by')
    all_incidents = incidents_query.select_related('department', 'reported_by', 'capa_report')
    
    # HOD and Admin context variables
    is_hod = (request.user.designation == 'HOD')
    is_admin = request.user.is_admin()
    user_dept_id = request.user.department_id
    
    # Available CAPA reports for HOD/Admin review dropdown
    available_capas = []
    if is_admin:
        available_capas = CAPAReport.objects.filter(status__in=['Open', 'In Progress'])
    elif is_hod and user_dept_id:
        available_capas = CAPAReport.objects.filter(department_id=user_dept_id, status__in=['Open', 'In Progress'])
        
    context = {
        'department': department,
        'dept_id': int(dept_id),
        'active_dept_id': int(dept_id),
        'active_module': 'SAFETY',
        'is_hod': is_hod,
        'is_admin': is_admin,
        'user_dept_id': user_dept_id,
        
        # KPIs
        'pending_count': pending_count,
        'completed_count': completed_count,
        'avg_closure_days': avg_closure_days,
        'reports_over_15_days': reports_over_15_days,
        'compliance_pct': compliance_pct,
        
        # Incident Lists
        'pending_reviews': pending_reviews,
        'all_incidents': all_incidents,
        'available_capas': available_capas,
        
        # Charts Data JSON
        'chart_severity': severity_data,
        'chart_uauc': {
            'ua_count': ua_count,
            'uc_count': uc_count,
            'ua_pct': ua_pct,
            'uc_pct': uc_pct,
        },
        'chart_trends': {
            'months': months_list,
            'LTI': monthly_sev_data['LTI'],
            'RWC': monthly_sev_data['RWC'],
            'MTC': monthly_sev_data['MTC'],
            'FA': monthly_sev_data['FA'],
            'NM': monthly_sev_data['NM'],
            'UA': monthly_sev_data['UA'],
            'UC': monthly_sev_data['UC'],
        },
        'chart_pareto': {
            'labels': pareto_labels,
            'counts': pareto_counts,
            'cumulative': pareto_cum_pct,
        },
        'chart_capa': {
            'labels': capa_labels,
            'open': capa_open,
            'closed': capa_closed,
            'overdue': capa_overdue,
        }
    }
    return render(request, 'safety/im_dashboard.html', context)


@login_required
def report_incident(request, dept_id):
    if request.method == 'POST':
        # Resolve target department
        form_dept_id = request.POST.get('department')
        if form_dept_id:
            incident_dept = get_object_or_404(Department, id=form_dept_id)
        elif int(dept_id) != 0:
            incident_dept = get_object_or_404(Department, id=dept_id)
        else:
            # overall plant but didn't choose department
            return redirect('safety:im_dashboard', dept_id=dept_id)
            
        date_str = request.POST.get('date_incident')
        date_incident = datetime.strptime(date_str, "%Y-%m-%d").date() if date_str else date.today()
        
        severity = request.POST.get('severity')
        unsafe_type = request.POST.get('unsafe_type', 'NONE')
        category = request.POST.get('category', 'Other')
        description = request.POST.get('description', '')
        image = request.FILES.get('image')
        
        Incident.objects.create(
            department=incident_dept,
            date_incident=date_incident,
            severity=severity,
            unsafe_type=unsafe_type,
            category=category,
            description=description,
            image=image,
            status='Pending',
            reported_by=request.user
        )
        
    return redirect('safety:im_dashboard', dept_id=dept_id)


@login_required
def review_incident(request, dept_id, incident_id):
    incident = get_object_or_404(Incident, id=incident_id)
    
    # Permission check: Admin or department HOD
    is_admin = request.user.is_admin()
    is_hod = (request.user.designation == 'HOD' and request.user.department_id == incident.department_id)
    
    if not (is_admin or is_hod):
        return HttpResponseForbidden("You do not have permissions to review this incident.")
        
    if request.method == 'POST':
        status = request.POST.get('status')
        findings = request.POST.get('investigation_findings', '')
        capa_id = request.POST.get('capa_report')
        
        incident.status = status
        incident.investigation_findings = findings
        
        if capa_id:
            try:
                incident.capa_report_id = int(capa_id)
            except ValueError:
                incident.capa_report = None
        else:
            incident.capa_report = None
            
        if status == 'Closed':
            closure_str = request.POST.get('closure_date')
            incident.closure_date = datetime.strptime(closure_str, "%Y-%m-%d").date() if closure_str else date.today()
        else:
            incident.closure_date = None
            
        incident.reviewed_by = request.user
        incident.save()
        
    return redirect('safety:im_dashboard', dept_id=dept_id)
