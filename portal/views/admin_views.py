from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.http import HttpResponse
from django.contrib import messages
from tpm.models import User, Department
from portal.models import Module, UserModuleAccess
from tpm.utils.decorators import admin_required

@login_required
@admin_required
def manage_access(request):
    """
    Matrix interface for administrators to view and configure user permissions
    across modules and departments.
    """
    STANDARD_DEPTS = [
        'BF1', 'BF2', 'BP', 'CP', 'CO', 'DRI1', 'DRI2', 'EP', 'LDP', 'OP',
        'PGP1', 'PGP2', 'PGP3', 'PM', 'PP1', 'PP2', 'PP3', 'PPP3',
        'RMHS1', 'RMHS2', 'RMHS3', 'RM', 'SAF1', 'SAF2', 'SMS2', 'SMS3',
        'SINT', 'SPM'
    ]
    users = User.objects.filter(is_active=True).order_by('username')
    departments = Department.objects.filter(code__in=STANDARD_DEPTS).order_by('name')
    modules = Module.objects.filter(is_active=True).order_by('sort_order')
    
    if request.method == 'POST':
        user_id = request.POST.get('user_id')
        dept_id = request.POST.get('dept_id')
        module_key = request.POST.get('module_key')
        access_level = request.POST.get('access_level') # 'VIEW', 'EDIT', 'NONE'
        
        user = User.objects.get(id=user_id)
        dept = Department.objects.get(id=dept_id)
        module = Module.objects.get(key=module_key)
        
        if access_level == 'NONE':
            UserModuleAccess.objects.filter(user=user, department=dept, module=module).delete()
        else:
            UserModuleAccess.objects.update_or_create(
                user=user, department=dept, module=module,
                defaults={'access_level': access_level, 'granted_by': request.user}
            )
            
        if request.headers.get('HX-Request'):
            # Return updated cell partial
            context = {
                'u': user,
                'd': dept,
                'm': module,
                'access': access_level if access_level != 'NONE' else None,
            }
            return render(request, 'portal/admin/partials/_access_cell.html', context)
            
    # Compile access matrix: matrix[user_id][dept_id][module_key] = access_level
    accesses = UserModuleAccess.objects.all().select_related('user', 'department', 'module')
    matrix = {}
    for user in users:
        matrix[user.id] = {}
        for dept in departments:
            matrix[user.id][dept.id] = {}
            for module in modules:
                matrix[user.id][dept.id][module.key] = None
                
    for a in accesses:
        if a.user_id in matrix and a.department_id in matrix[a.user_id]:
            matrix[a.user_id][a.department_id][a.module.key] = a.access_level

    # Custom structure for template rendering
    users_data = []
    for user in users:
        dept_rows = []
        for dept in departments:
            module_cols = []
            for module in modules:
                module_cols.append({
                    'module': module,
                    'access': matrix[user.id][dept.id][module.key],
                })
            dept_rows.append({
                'dept': dept,
                'modules': module_cols,
            })
        users_data.append({
            'user': user,
            'departments': dept_rows,
        })

    context = {
        'users_data': users_data,
        'departments': departments,
        'modules': modules,
        'active_section': 'admin',
    }
    return render(request, 'portal/admin/manage_access.html', context)


@login_required
@admin_required
def toggle_admin(request):
    """
    Promote a user to Plant Admin or revoke their Plant Admin status.
    Expects POST with: user_id, action ('promote' | 'revoke')
    """
    if request.method != 'POST':
        return redirect('portal:admin_access')

    user_id = request.POST.get('user_id')
    action  = request.POST.get('action')

    try:
        target_user = User.objects.get(id=user_id)
    except User.DoesNotExist:
        messages.error(request, 'User not found.')
        return redirect('portal:admin_access')

    if action == 'promote':
        target_user.is_plant_admin = True
        target_user.role = User.ROLE_ADMIN
        target_user.save(update_fields=['is_plant_admin', 'role'])
        messages.success(request, f'{target_user.get_display_name()} has been made a Plant Admin.')
    elif action == 'revoke':
        target_user.is_plant_admin = False
        target_user.role = User.ROLE_USER
        target_user.save(update_fields=['is_plant_admin', 'role'])
        messages.success(request, f'Plant Admin privileges revoked for {target_user.get_display_name()}.')
    else:
        messages.error(request, 'Invalid action.')

    return redirect('portal:admin_access')


@login_required
@admin_required
def user_informations(request):
    """
    Renders user information management table.
    """
    STANDARD_DEPTS = [
        'BF1', 'BF2', 'BP', 'CP', 'CO', 'DRI1', 'DRI2', 'EP', 'LDP', 'OP',
        'PGP1', 'PGP2', 'PGP3', 'PM', 'PP1', 'PP2', 'PP3', 'PPP3',
        'RMHS1', 'RMHS2', 'RMHS3', 'RM', 'SAF1', 'SAF2', 'SMS2', 'SMS3',
        'SINT', 'SPM'
    ]
    users = User.objects.all().select_related('department').order_by('username')
    departments = Department.objects.filter(code__in=STANDARD_DEPTS).order_by('name')
    context = {
        'users': users,
        'departments': departments,
        'active_section': 'user_info',
    }
    return render(request, 'portal/admin/user_informations.html', context)


@login_required
@admin_required
def admin_reset_password(request):
    """
    Allows admin to reset any user's password directly.
    """
    if request.method == 'POST':
        user_id = request.POST.get('user_id')
        password = request.POST.get('password', '')
        confirm_password = request.POST.get('confirm_password', '')
        
        try:
            target_user = User.objects.get(id=user_id)
        except User.DoesNotExist:
            messages.error(request, 'User not found.')
            return redirect('portal:user_informations')
            
        if password and password == confirm_password:
            target_user.set_password(password)
            target_user.save()
            messages.success(request, f'Password for {target_user.get_display_name()} has been reset.')
        else:
            messages.error(request, 'Passwords do not match or are empty.')
            
    return redirect('portal:user_informations')


@login_required
@admin_required
def admin_create_user(request):
    """
    Creates a new user account with designation, role, department, etc.
    """
    if request.method == 'POST':
        username = request.POST.get('username', '').strip()
        password = request.POST.get('password', '').strip()
        first_name = request.POST.get('first_name', '').strip()
        last_name = request.POST.get('last_name', '').strip()
        email = request.POST.get('email', '').strip()
        phone = request.POST.get('phone', '').strip()
        designation = request.POST.get('designation', '').strip()
        dept_id = request.POST.get('department')
        role = request.POST.get('role', 'USER')
        
        if not username or not password:
            messages.error(request, "Username and password are required.")
            return redirect('portal:user_informations')
            
        if User.objects.filter(username=username).exists():
            messages.error(request, f"Username '{username}' already exists.")
            return redirect('portal:user_informations')
            
        from django.contrib.auth.hashers import make_password
        
        dept = None
        if role == 'USER' and dept_id:
            dept = Department.objects.filter(id=dept_id).first()
            
        User.objects.create(
            username=username,
            email=email,
            first_name=first_name,
            last_name=last_name,
            role=role,
            is_plant_admin=(role == 'ADMIN'),
            department=dept,
            phone=phone,
            password=make_password(password),
            designation=designation
        )
        messages.success(request, f"User '{username}' created successfully.")
        
    return redirect('portal:user_informations')


@login_required
@admin_required
def admin_edit_user(request, user_id):
    """
    Allows editing an existing user's details.
    """
    from django.shortcuts import get_object_or_404
    user = get_object_or_404(User, id=user_id)
    
    if request.method == 'POST':
        user.first_name = request.POST.get('first_name', '').strip()
        user.last_name = request.POST.get('last_name', '').strip()
        user.email = request.POST.get('email', '').strip()
        user.phone = request.POST.get('phone', '').strip()
        user.designation = request.POST.get('designation', '').strip()
        
        role = request.POST.get('role', 'USER')
        user.role = role
        user.is_plant_admin = (role == 'ADMIN')
        
        dept_id = request.POST.get('department')
        if role == 'USER' and dept_id:
            user.department = Department.objects.filter(id=dept_id).first()
        else:
            user.department = None
            
        user.save()
        messages.success(request, f"User '{user.username}' updated successfully.")
        
    return redirect('portal:user_informations')
