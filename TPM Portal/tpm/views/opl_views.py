import os
import random
import datetime
from django.shortcuts import render, get_object_or_404
from django.http import HttpResponse
from django.contrib.auth.decorators import login_required
from django.views.decorators.http import require_POST

from tpm.models import Department, OPLSheet
from tpm.utils.decorators import dept_access_required

def generate_random_opl_no():
    existing_nos = set(OPLSheet.objects.values_list('opl_no', flat=True))
    for _ in range(1000):
        num = random.randint(1, 999)
        candidate = f"OPL-{num:03d}"
        if candidate not in existing_nos:
            return candidate
    return f"OPL-{OPLSheet.objects.count() + 1:03d}"

@login_required
@dept_access_required
def opl_list_partial(request, dept_id, pillar_id):
    dept = get_object_or_404(Department, id=dept_id)
    sheets = OPLSheet.objects.filter(department=dept, pillar=pillar_id).order_by('-created_at')
    
    context = {
        'dept': dept,
        'pillar_id': pillar_id,
        'sheets': sheets,
    }
    return render(request, 'partials/_opl_list.html', context)

@login_required
@dept_access_required
def opl_edit_partial(request, dept_id, pillar_id, opl_id=None):
    dept = get_object_or_404(Department, id=dept_id)
    opl = None
    training_records = []
    if opl_id:
        opl = get_object_or_404(OPLSheet, id=opl_id, department=dept, pillar=pillar_id)
        records = list(opl.training_records)
        while len(records) < 5:
            records.append({'date': '', 'teacher': '', 'student': ''})
        training_records = records
    else:
        training_records = [
            {'date': '', 'teacher': '', 'student': ''},
            {'date': '', 'teacher': '', 'student': ''},
            {'date': '', 'teacher': '', 'student': ''},
            {'date': '', 'teacher': '', 'student': ''},
            {'date': '', 'teacher': '', 'student': ''},
        ]
        
    context = {
        'dept': dept,
        'pillar_id': pillar_id,
        'opl': opl,
        'training_records': training_records,
        'prefills': {
            'opl_no': generate_random_opl_no(),
        }
    }
    return render(request, 'partials/_opl_form.html', context)

@login_required
@dept_access_required
@require_POST
def opl_save(request, dept_id, pillar_id, opl_id=None):
    dept = get_object_or_404(Department, id=dept_id)
    if opl_id:
        opl = get_object_or_404(OPLSheet, id=opl_id, department=dept, pillar=pillar_id)
    else:
        opl = OPLSheet(department=dept, pillar=pillar_id, created_by=request.user)
        
    opl.opl_no = request.POST.get('opl_no', '').strip()
    opl.theme = request.POST.get('theme', '').strip()
    opl.circle_name_members = request.POST.get('circle_name_members', '').strip()
    opl.lesson_type = request.POST.get('lesson_type', 'basic').strip()
    opl.benefits = request.POST.get('benefits', '').strip()
    opl.prepared_by = request.POST.get('prepared_by', '').strip()
    opl.verified_by = request.POST.get('verified_by', '').strip()
    
    # Extract 5 columns of training table
    dates = request.POST.getlist('train_date')
    teachers = request.POST.getlist('train_teacher')
    students = request.POST.getlist('train_student')
    
    training_records = []
    for idx in range(5):
        d_val = dates[idx].strip() if idx < len(dates) else ""
        t_val = teachers[idx].strip() if idx < len(teachers) else ""
        s_val = students[idx].strip() if idx < len(students) else ""
        if d_val or t_val or s_val:
            training_records.append({
                'date': d_val,
                'teacher': t_val,
                'student': s_val
            })
            
    opl.training_records = training_records
    
    # Image uploads
    if 'before_image' in request.FILES:
        opl.before_image = request.FILES['before_image']
    if 'after_image' in request.FILES:
        opl.after_image = request.FILES['after_image']
        
    opl.save()
    
    return opl_list_partial(request, dept.id, pillar_id)

@login_required
@dept_access_required
@require_POST
def opl_delete(request, dept_id, pillar_id, opl_id):
    dept = get_object_or_404(Department, id=dept_id)
    opl = get_object_or_404(OPLSheet, id=opl_id, department=dept, pillar=pillar_id)
    opl.delete()
    return opl_list_partial(request, dept_id, pillar_id)
