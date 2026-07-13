import json
import datetime
from django.shortcuts import render, get_object_or_404, redirect
from django.http import JsonResponse, HttpResponseForbidden
from django.contrib.auth.decorators import login_required
from django.views.decorators.http import require_POST
from tpm.models import Department
from smed.models import SMEDTemplate, SMEDSubActivityConfig, SMEDRun, SMEDRunItem
from portal.utils.access import user_can_edit_module

def parse_time(time_str):
    if not time_str or time_str == 'None' or time_str == '':
        return None
    try:
        # Expected format "HH:MM"
        return datetime.datetime.strptime(time_str, "%H:%M").time()
    except ValueError:
        try:
            return datetime.datetime.strptime(time_str, "%H:%M:%S").time()
        except ValueError:
            return None

def format_time(t):
    if t is None:
        return ""
    return t.strftime("%H:%M")

@login_required
def smed_dashboard(request, dept_id):
    department = get_object_or_404(Department, id=dept_id)
    templates = SMEDTemplate.objects.filter(department=department)
    
    if not templates.exists():
        # Create a default template for the department so they have a starting workspace
        default_template = SMEDTemplate.objects.create(
            department=department,
            name="SMED EAF SHELL CHANGE",
            code="EAF_SHELL_CHANGE"
        )
        # Create one initial subactivity config
        SMEDSubActivityConfig.objects.create(
            template=default_template,
            group_name="Pre Operational Activity of Delta & Shell Change (48 Minutes)",
            name="Furnace Power Off",
            default_planned_duration_mins=0,
            order=0
        )
        templates = SMEDTemplate.objects.filter(department=department)

    selected_template_id = request.GET.get('template_id')
    selected_template = None
    if selected_template_id:
        selected_template = templates.filter(id=selected_template_id).first()
    if not selected_template and templates.exists():
        selected_template = templates.first()

    # Permission check
    can_edit = user_can_edit_module(request.user, department, 'TPM')

    context = {
        'department': department,
        'templates': templates,
        'selected_template': selected_template,
        'can_edit': can_edit,
        'active_module': 'SMED',
        'active_dept_id': department.id,
    }
    return render(request, 'smed/dashboard.html', context)


@login_required
def get_smed_run_data(request, dept_id, template_id):
    department = get_object_or_404(Department, id=dept_id)
    template = get_object_or_404(SMEDTemplate, id=template_id, department=department)
    
    date_str = request.GET.get('date')
    if not date_str:
        date_val = datetime.date.today()
    else:
        try:
            date_val = datetime.datetime.strptime(date_str, "%Y-%m-%d").date()
        except ValueError:
            date_val = datetime.date.today()
            
    # Check if run already exists
    run = SMEDRun.objects.filter(template=template, date=date_val).first()
    
    data_items = []
    if run:
        items = run.items.all().order_by('order')
        for item in items:
            data_items.append({
                'id': item.id,
                'group_name': item.group_name,
                'name': item.name,
                'start_time_planned': format_time(item.start_time_planned),
                'finish_time_planned': format_time(item.finish_time_planned),
                'planned_duration': item.planned_duration,
                'start_time_actual': format_time(item.start_time_actual),
                'finish_time_actual': format_time(item.finish_time_actual),
                'actual_duration': item.actual_duration,
                'responsibility': item.responsibility or '',
                'remark': item.remark or '',
                'status': item.status,
                'order': item.order,
                'is_header': False
            })
        run_data = {
            'exists': True,
            'total_planned_time': run.total_planned_time,
            'total_actual_time': run.total_actual_time,
            'status': run.status,
            'compliance_percentage': run.compliance_percentage,
            'extra_time': run.extra_time,
            'is_locked': run.is_locked,
            'items': data_items
        }
    else:
        # Load from config templates
        configs = template.sub_activities.all().order_by('order')
        for idx, cfg in enumerate(configs):
            data_items.append({
                'id': idx + 1,
                'group_name': cfg.group_name,
                'name': cfg.name,
                'start_time_planned': "",
                'finish_time_planned': "",
                'planned_duration': cfg.default_planned_duration_mins,
                'start_time_actual': "",
                'finish_time_actual': "",
                'actual_duration': 0,
                'responsibility': cfg.default_responsibility or '',
                'remark': '',
                'status': 'PENDING',
                'order': cfg.order,
                'is_header': False
            })
        run_data = {
            'exists': False,
            'total_planned_time': sum(cfg.default_planned_duration_mins for cfg in configs),
            'total_actual_time': 0,
            'status': 'In-LIMIT',
            'compliance_percentage': 0.0,
            'extra_time': 0,
            'items': data_items
        }
        
    return JsonResponse(run_data)


@login_required
@require_POST
def save_smed_run(request, dept_id, template_id):
    department = get_object_or_404(Department, id=dept_id)
    if not user_can_edit_module(request.user, department, 'TPM'):
        return HttpResponseForbidden("Permission denied.")
        
    template = get_object_or_404(SMEDTemplate, id=template_id, department=department)
    
    try:
        data = json.loads(request.body)
        date_str = data.get('date')
        if not date_str:
            return JsonResponse({'status': 'error', 'message': 'Date is required.'}, status=400)
            
        date_val = datetime.datetime.strptime(date_str, "%Y-%m-%d").date()
        
        run, created = SMEDRun.objects.update_or_create(
            template=template,
            date=date_val,
            defaults={
                'total_planned_time': int(data.get('total_planned_time', 0)),
                'total_actual_time': int(data.get('total_actual_time', 0)),
                'status': data.get('status', 'In-LIMIT'),
                'compliance_percentage': float(data.get('compliance_percentage', 0.0)),
                'extra_time': int(data.get('extra_time', 0)),
                'is_locked': data.get('is_locked', False),
                'created_by': request.user
            }
        )
        
        # Delete old run items
        run.items.all().delete()
        
        # Create new run items
        items_data = data.get('items', [])
        for idx, item in enumerate(items_data):
            SMEDRunItem.objects.create(
                run=run,
                group_name=item.get('group_name', ''),
                name=item.get('name', ''),
                start_time_planned=parse_time(item.get('start_time_planned')),
                finish_time_planned=parse_time(item.get('finish_time_planned')),
                planned_duration=int(item.get('planned_duration', 0)),
                start_time_actual=parse_time(item.get('start_time_actual')),
                finish_time_actual=parse_time(item.get('finish_time_actual')),
                actual_duration=int(item.get('actual_duration', 0)),
                responsibility=item.get('responsibility', ''),
                remark=item.get('remark', ''),
                status=item.get('status', 'PENDING'),
                order=idx
            )
            
        return JsonResponse({'status': 'success', 'run_id': run.id})
    except Exception as e:
        return JsonResponse({'status': 'error', 'message': str(e)}, status=400)


@login_required
def smed_history(request, dept_id, template_id):
    department = get_object_or_404(Department, id=dept_id)
    template = get_object_or_404(SMEDTemplate, id=template_id, department=department)
    runs = SMEDRun.objects.filter(template=template).order_by('-date')
    
    runs_list = []
    for r in runs:
        # Planned Time formatting
        p_hrs = r.total_planned_time // 60
        p_mins = r.total_planned_time % 60
        if p_hrs > 0:
            r.planned_time_formatted = f"{p_hrs}h {p_mins}m ({r.total_planned_time} mins)"
        else:
            r.planned_time_formatted = f"{r.total_planned_time} mins"
            
        # Actual Time formatting
        a_hrs = r.total_actual_time // 60
        a_mins = r.total_actual_time % 60
        if a_hrs > 0:
            r.actual_time_formatted = f"{a_hrs}h {a_mins}m ({r.total_actual_time} mins)"
        else:
            r.actual_time_formatted = f"{r.total_actual_time} mins"
            
        runs_list.append(r)
        
    is_admin = request.user.is_superuser or getattr(request.user, 'is_plant_admin', False)

    context = {
        'department': department,
        'template': template,
        'runs': runs_list,
        'is_admin': is_admin,
        'active_module': 'SMED',
        'active_dept_id': department.id,
    }
    return render(request, 'smed/history.html', context)


@login_required
@require_POST
def delete_smed_run(request, dept_id, run_id):
    department = get_object_or_404(Department, id=dept_id)
    is_admin = request.user.is_superuser or getattr(request.user, 'is_plant_admin', False)
    if not is_admin:
        return HttpResponseForbidden("Only admins can delete run sheets.")
        
    run = get_object_or_404(SMEDRun, id=run_id, template__department=department)
    template_id = run.template.id
    run.delete()
    
    return redirect(f"/smed/department/{dept_id}/template/{template_id}/history/")
