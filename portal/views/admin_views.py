from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.views.decorators.http import require_http_methods
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
        'SINT', 'SPM', 'MRSS'
    ]
    users = User.objects.filter(is_active=True, email__contains='@').order_by('-is_plant_admin', 'username')
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
        
        from portal.models import PortalNotification
        if access_level == 'NONE':
            exists = UserModuleAccess.objects.filter(user=user, department=dept, module=module).exists()
            if exists:
                UserModuleAccess.objects.filter(user=user, department=dept, module=module).delete()
                PortalNotification.objects.create(
                    user=user,
                    message=f"Your access to the {module.key} module for department {dept.name} ({dept.code}) has been revoked by {request.user.get_display_name()}.",
                    link="/",
                    is_read=False
                )
        else:
            existing_access = UserModuleAccess.objects.filter(user=user, department=dept, module=module).first()
            obj, created = UserModuleAccess.objects.update_or_create(
                user=user, department=dept, module=module,
                defaults={'access_level': access_level, 'granted_by': request.user}
            )
            if created or (existing_access and existing_access.access_level != access_level):
                verb = "granted" if created else "updated to"
                PortalNotification.objects.create(
                    user=user,
                    message=f"You have been {verb} {access_level} access to the {module.key} module for department {dept.name} ({dept.code}) by {request.user.get_display_name()}.",
                    link=f"/department/{dept.id}/",
                    is_read=False
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

    from portal.models import AccessRequest
    pending_requests = AccessRequest.objects.filter(status=AccessRequest.STATUS_PENDING).select_related('department')

    context = {
        'users_data': users_data,
        'departments': departments,
        'modules': modules,
        'active_section': 'admin',
        'pending_requests': pending_requests,
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

    from portal.models import PortalNotification
    if action == 'promote':
        target_user.is_plant_admin = True
        target_user.role = User.ROLE_ADMIN
        target_user.save(update_fields=['is_plant_admin', 'role'])
        PortalNotification.objects.create(
            user=target_user,
            message=f"You have been promoted to Plant Admin by {request.user.get_display_name()}.",
            link="/portal-admin/access/",
            is_read=False
        )
        messages.success(request, f'{target_user.get_display_name()} has been made a Plant Admin.')
    elif action == 'revoke':
        target_user.is_plant_admin = False
        target_user.role = User.ROLE_USER
        target_user.save(update_fields=['is_plant_admin', 'role'])
        PortalNotification.objects.create(
            user=target_user,
            message=f"Your Plant Admin privileges have been revoked by {request.user.get_display_name()}.",
            link="/",
            is_read=False
        )
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
        'SINT', 'SPM', 'MRSS'
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
    If no password is provided, invites the user via email to set their password.
    """
    if request.method == 'POST':
        email = request.POST.get('email', '').strip().lower()
        first_name = request.POST.get('first_name', '').strip()
        last_name = request.POST.get('last_name', '').strip()
        phone = request.POST.get('phone', '').strip()
        designation = request.POST.get('designation', '').strip()
        dept_id = request.POST.get('department')
        role = request.POST.get('role', 'USER')
        
        # If username is not passed, use email as username
        username = request.POST.get('username', '').strip()
        if not username:
            username = email
            
        password = request.POST.get('password', '').strip()
        
        if not email:
            messages.error(request, "Email address is required.")
            return redirect(request.META.get('HTTP_REFERER', 'portal:user_informations'))
            
        if User.objects.filter(username=username).exists() or User.objects.filter(email=email).exists():
            messages.error(request, f"A user with email/username '{email}' already exists.")
            return redirect(request.META.get('HTTP_REFERER', 'portal:user_informations'))
            
        dept = None
        if role == 'USER' and dept_id:
            dept = Department.objects.filter(id=dept_id).first()
            
        # Create user instance
        user = User(
            username=username,
            email=email,
            first_name=first_name,
            last_name=last_name,
            role=role,
            is_plant_admin=(role == 'ADMIN'),
            department=dept,
            phone=phone,
            designation=designation
        )
        
        is_invite = False
        if not password:
            is_invite = True
            user.set_unusable_password()
        else:
            user.set_password(password)
            
        user.save()
        
        # Resolve AccessRequest if it exists
        request_id = request.POST.get('request_id')
        if request_id:
            from portal.models import AccessRequest
            AccessRequest.objects.filter(id=request_id).delete()
        
        if is_invite:
            from django.contrib.auth.tokens import default_token_generator
            from django.utils.http import urlsafe_base64_encode
            from django.utils.encoding import force_bytes
            from django.core.mail import send_mail
            from django.urls import reverse
            
            uid = urlsafe_base64_encode(force_bytes(user.pk))
            token = default_token_generator.make_token(user)
            setup_link = request.build_absolute_uri(
                reverse('portal:reset_password', kwargs={'uidb64': uid, 'token': token})
            )
            
            subject = "Account Invitation — Jindal Steel Operations Portal"
            message = (
                f"Hello {user.get_display_name()},\n\n"
                f"An account has been created for you on the Jindal Steel Operations Portal.\n"
                f"Role: {user.get_role_display() or role}\n"
                f"Department: {user.department.name if user.department else 'N/A'}\n\n"
                f"Please click the link below to verify your email, set your password, and log in to the dashboard:\n\n"
                f"{setup_link}\n\n"
                f"If you did not expect this invitation, please ignore this email.\n\n"
                f"Regards,\n"
                f"Jindal Steel Operations Portal Admin"
            )
            try:
                send_mail(
                    subject,
                    message,
                    'no-reply@jindalsteel.in',
                    [user.email],
                    fail_silently=False,
                )
                messages.success(request, f"User '{email}' created successfully. Invitation sent to verify and set password.")
            except Exception as e:
                messages.warning(request, f"User created successfully, but failed to send invitation email: {str(e)}")
        else:
            messages.success(request, f"User '{username}' created successfully.")
            
    return redirect(request.META.get('HTTP_REFERER', 'portal:user_informations'))


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


@login_required
@admin_required
@require_http_methods(['POST'])
def reject_access_request(request, req_id):
    """
    Rejects/deletes an access sign-up request.
    """
    from portal.models import AccessRequest
    try:
        req = AccessRequest.objects.get(id=req_id)
        email = req.email
        req.delete()
        messages.success(request, f"Access request for '{email}' has been rejected.")
    except AccessRequest.DoesNotExist:
        messages.error(request, "Access request not found.")
        
    return redirect('portal:admin_access')
