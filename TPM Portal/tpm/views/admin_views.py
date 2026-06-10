from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.contrib.auth.hashers import make_password
from django.http import HttpResponse, HttpResponseForbidden
from django.views.decorators.http import require_POST
from tpm.models import User, Department, PillarEntry, KPIValue
from tpm.utils.decorators import admin_required
from tpm.utils.kpi_definitions import KPI_DEFINITIONS
from tpm.utils.calculations import compute_achievement

@admin_required
def users_list(request):
    STANDARD_DEPTS = [
        'BF1', 'BF2', 'BP', 'CP', 'CO', 'DRI1', 'DRI2', 'EP', 'LDP', 'OP',
        'PGP1', 'PGP2', 'PGP3', 'PM', 'PP1', 'PP2', 'PP3', 'PPP3',
        'RMHS1', 'RMHS2', 'RMHS3', 'RM', 'SAF1', 'SAF2', 'SMS2', 'SMS3',
        'SINT', 'SPM'
    ]
    users = User.objects.all().order_by('username')
    departments = Department.objects.filter(code__in=STANDARD_DEPTS).order_by('name')
    return render(request, 'admin/users.html', {'users': users, 'departments': departments})

@admin_required
def add_user(request):
    if request.method == 'POST':
        username = request.POST.get('username', '').strip()
        email = request.POST.get('email', '').strip()
        first_name = request.POST.get('first_name', '').strip()
        last_name = request.POST.get('last_name', '').strip()
        role = request.POST.get('role', 'USER')
        dept_id = request.POST.get('department')
        password = request.POST.get('password', '').strip()
        
        if not username or not password:
            messages.error(request, "Username and password are required.")
            return redirect('admin_users')
            
        if User.objects.filter(username=username).exists():
            messages.error(request, "Username already exists.")
            return redirect('admin_users')
            
        dept = None
        if role == 'USER' and dept_id:
            dept = Department.objects.filter(id=dept_id).first()
            
        user = User.objects.create(
            username=username,
            email=email,
            first_name=first_name,
            last_name=last_name,
            role=role,
            department=dept,
            password=make_password(password)
        )
        messages.success(request, f"User '{username}' created successfully.")
    return redirect('admin_users')

@admin_required
def edit_user(request, user_id):
    user = get_object_or_404(User, id=user_id)
    if request.method == 'POST':
        user.email = request.POST.get('email', '').strip()
        user.first_name = request.POST.get('first_name', '').strip()
        user.last_name = request.POST.get('last_name', '').strip()
        user.role = request.POST.get('role', 'USER')
        
        dept_id = request.POST.get('department')
        if user.role == 'USER' and dept_id:
            user.department = Department.objects.filter(id=dept_id).first()
        else:
            user.department = None
            
        password = request.POST.get('password', '').strip()
        if password:
            user.password = make_password(password)
            
        user.is_active = 'is_active' in request.POST
        user.save()
        messages.success(request, f"User '{user.username}' updated successfully.")
    return redirect('admin_users')

@admin_required
def departments(request):
    STANDARD_DEPTS = [
        'BF1', 'BF2', 'BP', 'CP', 'CO', 'DRI1', 'DRI2', 'EP', 'LDP', 'OP',
        'PGP1', 'PGP2', 'PGP3', 'PM', 'PP1', 'PP2', 'PP3', 'PPP3',
        'RMHS1', 'RMHS2', 'RMHS3', 'RM', 'SAF1', 'SAF2', 'SMS2', 'SMS3',
        'SINT', 'SPM'
    ]
    depts = Department.objects.filter(code__in=STANDARD_DEPTS).order_by('name')
    if request.method == 'POST':
        name = request.POST.get('name', '').strip()
        code = request.POST.get('code', '').strip()
        if name and code:
            if Department.objects.filter(code=code).exists() or Department.objects.filter(name=name).exists():
                messages.error(request, "Department or code already exists.")
            else:
                Department.objects.create(name=name, code=code)
                messages.success(request, f"Department '{name}' added successfully.")
        return redirect('admin_departments')
    return render(request, 'admin/departments.html', {'departments': depts})

@admin_required
@require_POST
def unlock_entry(request, entry_id):
    entry = get_object_or_404(PillarEntry, id=entry_id)
    entry.submitted_at = None
    entry.submitted_by = None
    entry.save()
    
    # Reload KPI rows to return the table partial
    pillar_id = entry.pillar
    dept = entry.department
    month = entry.month
    year = entry.year
    
    # helper logic to merge
    definitions = KPI_DEFINITIONS.get(pillar_id, [])
    kpi_rows = []
    for d in definitions:
        row_data = {
            'sl_no': d['sl_no'],
            'kpi_name': d['name'],
            'uom': d['uom'],
            'benchmark': d['benchmark'],
            'target': d['target'],
            'actual': None,
            'availability': None,
            'performance': None,
            'quality': None,
            'remarks': '',
            'is_PRODUCTION_row': d.get('is_PRODUCTION_row', False),
            'achievement': None,
        }
        db_val = KPIValue.objects.filter(pillar_entry=entry, sl_no=d['sl_no']).first()
        if db_val:
            row_data['actual'] = db_val.actual
            row_data['availability'] = db_val.availability
            row_data['performance'] = db_val.performance
            row_data['quality'] = db_val.quality
            row_data['remarks'] = db_val.remarks
            if db_val.target is not None:
                row_data['target'] = db_val.target
            if db_val.benchmark is not None:
                row_data['benchmark'] = db_val.benchmark
                
        if row_data['actual'] is not None and row_data['target'] is not None:
            row_data['achievement'] = compute_achievement(row_data['actual'], row_data['target'], row_data['kpi_name'])
        kpi_rows.append(row_data)

    months_list = [
        (1, 'January'), (2, 'February'), (3, 'March'), (4, 'April'),
        (5, 'May'), (6, 'June'), (7, 'July'), (8, 'August'),
        (9, 'September'), (10, 'October'), (11, 'November'), (12, 'December')
    ]
    month_label = dict(months_list).get(month)

    context = {
        'dept': dept,
        'pillar_id': pillar_id,
        'month': month,
        'year': year,
        'kpi_rows': kpi_rows,
        'is_locked': False,
        'entry': entry,
        'month_label': month_label,
    }
    
    toast_html = f'<div id="toast-container" hx-swap-oob="true"><div class="toast toast-success">Entry Unlocked Successfully</div></div>'
    response = render(request, 'partials/_kpi_table.html', context)
    response.content = response.content + toast_html.encode('utf-8')
    return response
