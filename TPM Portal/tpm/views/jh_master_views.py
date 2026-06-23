import datetime
from django.shortcuts import render, get_object_or_404
from django.http import HttpResponse, HttpResponseForbidden, JsonResponse
from django.views.decorators.http import require_POST
from django.contrib.auth.decorators import login_required

from tpm.models import Department, JHMachine, JHDepartmentSettings, JHMasterPlanCell
from tpm.utils.decorators import dept_access_required
from tpm.utils.toasts import render_toast
from portal.utils.access import user_can_edit_module


@login_required
@dept_access_required
def jh_master_equipments(request, dept_id):
    dept = get_object_or_404(Department, id=dept_id)
    settings, created = JHDepartmentSettings.objects.get_or_create(
        department=dept,
        defaults={
            'hod_name': 'Mr. ',
            'coordinator_name': 'Mr. ',
            'plan_start_date': datetime.date(datetime.date.today().year, 1, 1),
            'plan_end_date': datetime.date(datetime.date.today().year, 12, 31)
        }
    )
    machines = JHMachine.objects.filter(department=dept).order_by('id')
    can_edit = user_can_edit_module(request.user, dept, 'TPM')
    context = {
        'dept': dept,
        'settings': settings,
        'machines': machines,
        'can_edit': can_edit,
        'active_tab': 'equipments',
    }
    return render(request, 'partials/_jh_master_equipments.html', context)


@login_required
@dept_access_required
def jh_machine_list(request, dept_id):
    dept = get_object_or_404(Department, id=dept_id)
    settings, created = JHDepartmentSettings.objects.get_or_create(
        department=dept,
        defaults={
            'hod_name': 'Mr. ',
            'coordinator_name': 'Mr. ',
            'plan_start_date': datetime.date(datetime.date.today().year, 1, 1),
            'plan_end_date': datetime.date(datetime.date.today().year, 12, 31)
        }
    )
    machines = JHMachine.objects.filter(department=dept).order_by('id')
    can_edit = user_can_edit_module(request.user, dept, 'TPM')
    context = {
        'dept': dept,
        'settings': settings,
        'machines': machines,
        'can_edit': can_edit,
        'active_tab': 'machines',
    }
    return render(request, 'partials/_jh_machine_list.html', context)


@login_required
@dept_access_required
def jh_master_plan(request, dept_id):
    dept = get_object_or_404(Department, id=dept_id)
    settings, created = JHDepartmentSettings.objects.get_or_create(
        department=dept,
        defaults={
            'hod_name': 'Mr. ',
            'coordinator_name': 'Mr. ',
            'plan_start_date': datetime.date(datetime.date.today().year, 1, 1),
            'plan_end_date': datetime.date(datetime.date.today().year, 12, 31)
        }
    )
    machines = JHMachine.objects.filter(department=dept).order_by('id')
    can_edit = user_can_edit_module(request.user, dept, 'TPM')
    
    start = settings.plan_start_date or datetime.date(datetime.date.today().year, 1, 1)
    end = settings.plan_end_date or datetime.date(datetime.date.today().year, 12, 31)
    
    grouped_years = []
    curr = datetime.date(start.year, start.month, 1)
    end_first_day = datetime.date(end.year, end.month, 1)
    
    months_count = 0
    # Limit to max 24 months to prevent grid layouts from breaking
    while curr <= end_first_day and months_count < 24:
        year_val = curr.year
        month_val = curr.month
        month_name = curr.strftime('%b').upper()
        
        year_item = next((item for item in grouped_years if item['year'] == year_val), None)
        if not year_item:
            year_item = {
                'year': year_val,
                'months': [],
                'total_cols': 0
            }
            grouped_years.append(year_item)
            
        year_item['months'].append({
            'num': month_val,
            'name': month_name,
            'cols': 4
        })
        year_item['total_cols'] += 4
        
        # Increment month
        if curr.month == 12:
            curr = datetime.date(curr.year + 1, 1, 1)
        else:
            curr = datetime.date(curr.year, curr.month + 1, 1)
        months_count += 1
        
    plan_cells = JHMasterPlanCell.objects.filter(machine__department=dept)
    plan_cells_dict = {}
    for cell in plan_cells:
        key = f"{cell.machine_id}-{cell.step}-{cell.year}-{cell.month}-{cell.week}"
        plan_cells_dict[key] = cell.status
        
    context = {
        'dept': dept,
        'settings': settings,
        'machines': machines,
        'can_edit': can_edit,
        'active_tab': 'plan',
        'grouped_years': grouped_years,
        'steps_range': range(1, 8),
        'plan_cells_dict': plan_cells_dict,
    }
    return render(request, 'partials/_jh_master_plan.html', context)


@login_required
@dept_access_required
@require_POST
def save_jh_machine(request, dept_id, machine_id=None):
    dept = get_object_or_404(Department, id=dept_id)
    if not user_can_edit_module(request.user, dept, 'TPM'):
        return HttpResponseForbidden("Permission denied")
        
    if machine_id:
        machine = get_object_or_404(JHMachine, id=machine_id, department=dept)
    else:
        machine = JHMachine(department=dept)
        
    if 'machine_name' in request.POST:
        machine.machine_name = request.POST.get('machine_name', '').strip()
    if 'no_of_equipment' in request.POST:
        try:
            machine.no_of_equipment = int(request.POST.get('no_of_equipment', 1))
        except ValueError:
            machine.no_of_equipment = 1
    if 'rank' in request.POST:
        machine.rank = request.POST.get('rank', 'A')
    if 'present_step' in request.POST:
        machine.present_step = request.POST.get('present_step', 'Step 1')
    if 'present_step_date' in request.POST:
        date_str = request.POST.get('present_step_date')
        if date_str:
            try:
                machine.present_step_date = datetime.datetime.strptime(date_str, '%Y-%m-%d').date()
            except ValueError:
                machine.present_step_date = None
        else:
            machine.present_step_date = None
    if 'circle_name' in request.POST:
        machine.circle_name = request.POST.get('circle_name', '').strip()
    if 'circle_leader' in request.POST:
        machine.circle_leader = request.POST.get('circle_leader', '').strip()
        
    machine.save()
    
    is_new = (machine_id is None)
    if is_new:
        if 'present_step' in request.POST or 'circle_name' in request.POST or 'circle_leader' in request.POST:
            return jh_machine_list(request, dept_id)
        else:
            return jh_master_equipments(request, dept_id)
    else:
        toast_html = render_toast(f'Saved "{machine.machine_name}"')
        return HttpResponse(toast_html)


@login_required
@dept_access_required
@require_POST
def delete_jh_machine(request, dept_id, machine_id):
    dept = get_object_or_404(Department, id=dept_id)
    if not user_can_edit_module(request.user, dept, 'TPM'):
        return HttpResponseForbidden("Permission denied")
        
    machine = get_object_or_404(JHMachine, id=machine_id, department=dept)
    name = machine.machine_name
    machine.delete()
    
    toast_html = render_toast(f'Deleted "{name}"')
    
    tab = request.GET.get('tab', 'equipments')
    if tab == 'machines':
        response = jh_machine_list(request, dept_id)
    else:
        response = jh_master_equipments(request, dept_id)
        
    response.content = response.content + toast_html.encode('utf-8')
    return response


@login_required
@dept_access_required
@require_POST
def save_jh_settings(request, dept_id):
    dept = get_object_or_404(Department, id=dept_id)
    if not user_can_edit_module(request.user, dept, 'TPM'):
        return HttpResponseForbidden("Permission denied")
        
    settings, created = JHDepartmentSettings.objects.get_or_create(department=dept)
    
    settings.hod_name = request.POST.get('hod_name', 'Mr. ').strip()
    settings.coordinator_name = request.POST.get('coordinator_name', 'Mr. ').strip()
    
    start_str = request.POST.get('plan_start_date')
    end_str = request.POST.get('plan_end_date')
    
    if start_str:
        try:
            settings.plan_start_date = datetime.datetime.strptime(start_str, '%Y-%m-%d').date()
        except ValueError:
            pass
    if end_str:
        try:
            settings.plan_end_date = datetime.datetime.strptime(end_str, '%Y-%m-%d').date()
        except ValueError:
            pass
            
    settings.save()
    
    toast_html = render_toast("Settings updated successfully")
    
    active_tab = request.POST.get('active_tab', 'equipments')
    if active_tab == 'plan':
        response = jh_master_plan(request, dept_id)
    elif active_tab == 'machines':
        response = jh_machine_list(request, dept_id)
    else:
        response = jh_master_equipments(request, dept_id)
        
    response.content = response.content + toast_html.encode('utf-8')
    return response


@login_required
@dept_access_required
@require_POST
def save_jh_plan_cell(request, dept_id):
    dept = get_object_or_404(Department, id=dept_id)
    if not user_can_edit_module(request.user, dept, 'TPM'):
        return JsonResponse({"success": False, "error": "Permission denied"}, status=403)
        
    machine_id = request.POST.get('machine_id')
    step = request.POST.get('step')
    year = request.POST.get('year')
    month = request.POST.get('month')
    week = request.POST.get('week')
    status = request.POST.get('status', '').strip().upper()
    
    if not all([machine_id, step, year, month, week]):
        return JsonResponse({"success": False, "error": "Missing parameters"}, status=400)
        
    machine = get_object_or_404(JHMachine, id=machine_id, department=dept)
    
    try:
        step = int(step)
        year = int(year)
        month = int(month)
        week = int(week)
    except ValueError:
        return JsonResponse({"success": False, "error": "Invalid format"}, status=400)
        
    if status == '':
        JHMasterPlanCell.objects.filter(
            machine=machine, step=step, year=year, month=month, week=week
        ).delete()
    else:
        if status not in ['PLAN', 'UNDER_PROGRESS', 'COMPLETED']:
            return JsonResponse({"success": False, "error": "Invalid status value"}, status=400)
            
        cell, created = JHMasterPlanCell.objects.get_or_create(
            machine=machine, step=step, year=year, month=month, week=week,
            defaults={'status': status}
        )
        if not created:
            cell.status = status
            cell.save()
            
    return JsonResponse({"success": True})
