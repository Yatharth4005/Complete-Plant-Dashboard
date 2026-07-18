from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from tpm.models import Department, CAPAReport
from portal.models import Module, UserModuleAccess
from portal.utils.access import get_user_module_access_map

@login_required
def plant_dashboard(request):
    """
    Landing dashboard listing departments as cards.
    Non-admin users only see departments they are permitted to view.
    """
    if request.user.is_admin():
        departments = Department.objects.filter(is_active=True).order_by('name')
    else:
        # Resolve user's primary department + any cross-dept access depts
        dept_ids = set()
        if request.user.department_id:
            dept_ids.add(request.user.department_id)
        
        # Check permissions for other departments
        permitted_accesses = UserModuleAccess.objects.filter(user=request.user)
        for access in permitted_accesses:
            dept_ids.add(access.department_id)
            
        departments = Department.objects.filter(id__in=dept_ids, is_active=True).order_by('name')

    active_modules = Module.objects.filter(is_active=True).order_by('sort_order')
    
    departments_data = []
    for dept in departments:
        # Get module accesses for the current user in this department
        access_map = get_user_module_access_map(request.user, dept)
        
        module_states = []
        for module in active_modules:
            if module.key == 'PERFORMANCE' and dept.code not in ['SMS2', 'SMS3']:
                continue
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
            'key': 'Governance',
            'label': 'Governance Structure',
            'description': 'Organizational governance structure, roles, and department users information',
            'icon': 'award',
            'color_class': 'module-governance',
            'url': '/tpm/governance/structure/',
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
            'url': '/delays/department/0/',
        },
        {
            'key': 'Checklist',
            'label': 'Checklist',
            'description': 'Manage department shift checklists, inspections, and actions',
            'icon': 'clipboard-list',
            'color_class': 'module-checklist',
            'url': '/delays/department/0/?tab=checklist_schedule',
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
        {
            'key': 'SAFETY',
            'label': 'Safety',
            'description': 'Safety audits, hazard reporting, and incident tracking',
            'icon': 'life-buoy',
            'color_class': 'module-safety',
            'url': '/department/0/coming-soon/SAFETY/',
        },
        {
            'key': 'PERFORMANCE',
            'label': 'Performance',
            'description': 'Track, record, and analyze daily planned and actual production performance metrics',
            'icon': 'layers',
            'color_class': 'module-performance',
            'url': '/delays/department/0/?tab=performance',
        },
        {
            'key': 'QUALITY',
            'label': 'Quality',
            'description': 'Quality control parameters, rejection tracking, and testing logs',
            'icon': 'check-square',
            'color_class': 'module-quality',
            'url': '/department/0/coming-soon/QUALITY/',
        },
        {
            'key': 'SPARE',
            'label': 'Spare Management',
            'description': 'Inventory tracking, critical spares management, and consumption logs',
            'icon': 'archive',
            'color_class': 'module-spare',
            'url': '/department/0/coming-soon/SPARE/',
        },
        {
            'key': 'DAKSHATA',
            'label': 'Improvement Project Dakshata',
            'description': 'Continuous improvement initiatives, Kaizen tracking, and project status',
            'icon': 'trending-up',
            'color_class': 'module-dakshata',
            'url': '/department/0/coming-soon/DAKSHATA/',
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
        except Department.DoesNotExist:  # type: ignore
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


from django.views.decorators.http import require_POST
from django.http import JsonResponse
from portal.models import PortalNotification

@login_required
@require_POST
def mark_notification_read(request, notification_id):
    try:
        notification = PortalNotification.objects.get(id=notification_id, user=request.user)
        notification.is_read = True
        notification.save()
        return JsonResponse({'status': 'success'})
    except PortalNotification.DoesNotExist:  # type: ignore
        return JsonResponse({'status': 'error', 'message': 'Notification not found'}, status=404)


@login_required
@require_POST
def mark_all_notifications_read(request):
    PortalNotification.objects.filter(user=request.user, is_read=False).update(is_read=True)
    return JsonResponse({'status': 'success'})


@login_required
def tpm_admin_dashboard(request):
    """
    Dashboard for TPM Admin under Administration tab.
    Shows cards for Kaizens, OPLs, and Fuguai Registers.
    Supports filtering by department, month, date range, and lists all files plantwide.
    """
    if not request.user.is_admin():
        from django.contrib import messages
        messages.error(request, "Only administrators can access the TPM Admin Dashboard.")
        return redirect('portal:plant_dashboard')

    import os
    from tpm.models import KaizenSheet, OPLSheet, FuguaiRegister
    from tpm.models import Department

    # Get search/filter parameters
    selected_dept_id = request.GET.get('department_id')
    doc_type = request.GET.get('doc_type', 'kaizen') # 'kaizen', 'opl', 'fuguai'
    filter_month = request.GET.get('filter_month', '')
    start_date = request.GET.get('start_date', '')
    end_date = request.GET.get('end_date', '')

    departments = Department.objects.filter(is_active=True).order_by('name')

    # Base lists
    kaizens_list = KaizenSheet.objects.all().select_related('department').order_by('-created_at')
    opls_list = OPLSheet.objects.all().select_related('department').order_by('-created_at')
    fuguais_list = FuguaiRegister.objects.all().select_related('department').order_by('-created_at')

    # Apply Department Filter
    if selected_dept_id:
        try:
            dept_id = int(selected_dept_id)
            kaizens_list = kaizens_list.filter(department_id=dept_id)
            opls_list = opls_list.filter(department_id=dept_id)
            fuguais_list = fuguais_list.filter(department_id=dept_id)
        except ValueError:
            pass

    # Apply Month Filter (YYYY-MM)
    if filter_month:
        try:
            year, month = map(int, filter_month.split('-'))
            kaizens_list = kaizens_list.filter(created_at__year=year, created_at__month=month)
            opls_list = opls_list.filter(created_at__year=year, created_at__month=month)
            fuguais_list = fuguais_list.filter(created_at__year=year, created_at__month=month)
        except (ValueError, TypeError):
            pass

    # Apply Date Range Filter (YYYY-MM-DD)
    if start_date:
        kaizens_list = kaizens_list.filter(created_at__date__gte=start_date)
        opls_list = opls_list.filter(created_at__date__gte=start_date)
        fuguais_list = fuguais_list.filter(created_at__date__gte=start_date)
    if end_date:
        kaizens_list = kaizens_list.filter(created_at__date__lte=end_date)
        opls_list = opls_list.filter(created_at__date__lte=end_date)
        fuguais_list = fuguais_list.filter(created_at__date__lte=end_date)

    # Handle ZIP Download
    if request.GET.get('download_zip') == '1':
        import zipfile
        import io
        from django.http import HttpResponse
        from django.contrib import messages

        zip_buffer = io.BytesIO()
        files_added = 0

        with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED) as zip_file:
            if doc_type == 'kaizen':
                from tpm.views.kaizen_views import generate_kaizen_pdf
                for item in kaizens_list:
                    if item.uploaded_file:
                        try:
                            file_path = item.uploaded_file.path
                            if os.path.exists(file_path):
                                filename = os.path.basename(file_path)
                                zip_file.write(file_path, f"Kaizen_{item.kaizen_no or item.id}_{filename}")
                                files_added += 1
                        except Exception:
                            pass
                    else:
                        try:
                            pdf_bytes = generate_kaizen_pdf(item)
                            pdf_name = f"KAIZEN_{item.kaizen_no or item.id}.pdf"
                            zip_file.writestr(pdf_name, pdf_bytes)
                            files_added += 1
                        except Exception:
                            pass

            elif doc_type == 'opl':
                for item in opls_list:
                    if item.uploaded_file:
                        try:
                            file_path = item.uploaded_file.path
                            if os.path.exists(file_path):
                                filename = os.path.basename(file_path)
                                zip_file.write(file_path, f"OPL_{item.opl_no or item.id}_{filename}")
                                files_added += 1
                        except Exception:
                            pass

            elif doc_type == 'fuguai':
                for item in fuguais_list:
                    if item.uploaded_file:
                        try:
                            file_path = item.uploaded_file.path
                            if os.path.exists(file_path):
                                filename = os.path.basename(file_path)
                                zip_file.write(file_path, f"Fuguai_{item.id}_{filename}")
                                files_added += 1
                        except Exception:
                            pass

        if files_added == 0:
            messages.error(request, "No files found to download for the current filters.")
            query_params = request.GET.copy()
            if 'download_zip' in query_params:
                del query_params['download_zip']
            return redirect(f"{request.path}?{query_params.urlencode()}")

        zip_buffer.seek(0)
        response = HttpResponse(zip_buffer.getvalue(), content_type='application/zip')
        response['Content-Disposition'] = f'attachment; filename="TPM_{doc_type.upper()}_FILES.zip"'
        return response

    # Total counts for cards matching the current filters
    total_kaizens = kaizens_list.count()
    total_opls = opls_list.count()
    total_fuguais = fuguais_list.count()

    # Handle file uploads for Fuguai Register or others if needed
    if request.method == 'POST':
        action = request.POST.get('action')
        if action == 'upload_fuguai':
            dept_id = request.POST.get('upload_dept_id')
            theme = request.POST.get('theme', '').strip()
            fuguai_file = request.FILES.get('fuguai_file')
            if dept_id and fuguai_file:
                try:
                    dept = Department.objects.get(id=dept_id)
                    FuguaiRegister.objects.create(
                        department=dept,
                        theme=theme,
                        uploaded_file=fuguai_file,
                        created_by=request.user
                    )
                    from django.contrib import messages
                    messages.success(request, f"Fuguai Register for {dept.name} uploaded successfully.")
                except Exception as e:
                    from django.contrib import messages
                    messages.error(request, f"Error uploading Fuguai Register: {str(e)}")
            else:
                from django.contrib import messages
                messages.error(request, "Please select a department and file to upload.")
            return redirect('portal:tpm_admin_dashboard')

    context = {
        'departments': departments,
        'selected_dept_id': selected_dept_id,
        'doc_type': doc_type,
        'filter_month': filter_month,
        'start_date': start_date,
        'end_date': end_date,
        'total_kaizens': total_kaizens,
        'total_opls': total_opls,
        'total_fuguais': total_fuguais,
        'kaizens_list': kaizens_list,
        'opls_list': opls_list,
        'fuguais_list': fuguais_list,
        'active_section': 'tpm_admin_dashboard',
    }
    return render(request, 'portal/dashboard/tpm_admin_dashboard.html', context)

