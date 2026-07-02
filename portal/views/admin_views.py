from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.views.decorators.http import require_http_methods
from django.http import HttpResponse
from django.contrib import messages
from django.db import models
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
    users = User.objects.filter(is_active=True, email__contains='@').order_by('-is_plant_admin', 'username')
    departments = Department.objects.filter(is_active=True).order_by('name')
    modules = Module.objects.filter(is_active=True).order_by('sort_order')
    
    if request.method == 'POST':
        user_id = request.POST.get('user_id')
        dept_id = request.POST.get('dept_id')
        module_key = request.POST.get('module_key')
        access_level = request.POST.get('access_level') # 'VIEW', 'EDIT', 'NONE'
        
        user = User.objects.get(id=user_id)
        if user.is_super_admin():
            return HttpResponse("Cannot modify access for the super admin.", status=403)
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
            has_access = False
            for module in modules:
                access_level = matrix[user.id][dept.id][module.key]
                if access_level is not None:
                    has_access = True
                module_cols.append({
                    'module': module,
                    'access': access_level,
                })
            dept_rows.append({
                'dept': dept,
                'modules': module_cols,
                'has_access': has_access,
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
        if target_user.is_super_admin():
            messages.error(request, 'Super admin privileges cannot be revoked.')
            return redirect('portal:admin_access')
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
    users = User.objects.all().select_related('department').order_by('username')
    departments = Department.objects.filter(is_active=True).order_by('name')
    
    from collections import defaultdict
    accesses = UserModuleAccess.objects.filter(user__in=users)
    user_dept_map = defaultdict(set)
    for a in accesses:
        user_dept_map[a.user_id].add(a.department_id)
        
    users_data = []
    for u in users:
        dept_ids = list(user_dept_map[u.id])
        if u.department_id and u.department_id not in dept_ids:
            dept_ids.append(u.department_id)
        users_data.append({
            'user': u,
            'accessed_dept_ids': dept_ids
        })
        
    context = {
        'users_data': users_data,
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
        dept_ids = [int(x) for x in request.POST.getlist('departments') if x.isdigit()]
        role = request.POST.get('role', 'USER')
        
        # If username is not passed, use email as username
        username = request.POST.get('username', '').strip()
        if not username:
            username = email
            
        password = request.POST.get('password', '').strip()
        
        if not email:
            messages.error(request, "Email address is required.")
            return redirect(request.META.get('HTTP_REFERER', 'portal:user_informations'))
            
        existing_user = User.objects.filter(models.Q(username=username) | models.Q(email=email)).first()
        if existing_user:
            if not existing_user.is_active:
                dept = None
                if role == 'USER' and dept_ids:
                    dept = Department.objects.filter(id=dept_ids[0]).first()
                
                existing_user.first_name = first_name
                existing_user.last_name = last_name
                existing_user.phone = phone
                existing_user.designation = designation
                existing_user.role = role
                existing_user.is_plant_admin = (role == 'ADMIN')
                existing_user.department = dept
                existing_user.is_active = True
                
                if password:
                    existing_user.set_password(password)
                
                existing_user.save()
                
                # Grant access to selected departments
                if role == 'USER' and dept_ids:
                    active_modules = Module.objects.filter(is_active=True)
                    for d_id in dept_ids:
                        d = Department.objects.filter(id=d_id).first()
                        if d:
                            for m in active_modules:
                                UserModuleAccess.objects.update_or_create(
                                    user=existing_user,
                                    department=d,
                                    module=m,
                                    defaults={'access_level': 'EDIT', 'granted_by': request.user}
                                )
                
                # Grant plant-wide access if checked
                grant_all_access = request.POST.get('grant_all_access') == 'on'
                if grant_all_access:
                    depts = Department.objects.filter(is_active=True)
                    mods = Module.objects.filter(is_active=True)
                    for d in depts:
                        for m in mods:
                            UserModuleAccess.objects.update_or_create(
                                user=existing_user,
                                department=d,
                                module=m,
                                defaults={'access_level': 'EDIT', 'granted_by': request.user}
                            )
                
                # Resolve AccessRequest if it exists
                request_id = request.POST.get('request_id')
                if request_id:
                    from portal.models import AccessRequest
                    AccessRequest.objects.filter(id=request_id).delete()
                
                messages.success(request, f"User '{email}' has been approved and activated. They can now log in.")
                return redirect(request.META.get('HTTP_REFERER', 'portal:user_informations'))
            else:
                messages.error(request, f"A user with email/username '{email}' already exists.")
                return redirect(request.META.get('HTTP_REFERER', 'portal:user_informations'))
            
        dept = None
        if role == 'USER' and dept_ids:
            dept = Department.objects.filter(id=dept_ids[0]).first()
            
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
        
        # Grant access to selected departments
        if role == 'USER' and dept_ids:
            active_modules = Module.objects.filter(is_active=True)
            for d_id in dept_ids:
                d = Department.objects.filter(id=d_id).first()
                if d:
                    for m in active_modules:
                        UserModuleAccess.objects.update_or_create(
                            user=user,
                            department=d,
                            module=m,
                            defaults={'access_level': 'EDIT', 'granted_by': request.user}
                        )
        
        # Grant plant-wide access if checked
        grant_all_access = request.POST.get('grant_all_access') == 'on'
        if grant_all_access:
            depts = Department.objects.filter(is_active=True)
            mods = Module.objects.filter(is_active=True)
            for d in depts:
                for m in mods:
                    UserModuleAccess.objects.update_or_create(
                        user=user,
                        department=d,
                        module=m,
                        defaults={'access_level': 'EDIT', 'granted_by': request.user}
                    )
        
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
        new_email = request.POST.get('email', '').strip().lower()
        if user.is_super_admin() and new_email != user.email.strip().lower():
            messages.error(request, "Super admin email address cannot be changed.")
            return redirect('portal:user_informations')
        if new_email == 'lalit.goyal@jindalsteel.in' and not user.is_super_admin():
            messages.error(request, "Cannot set user email to the super admin email address.")
            return redirect('portal:user_informations')

        user.first_name = request.POST.get('first_name', '').strip()
        user.last_name = request.POST.get('last_name', '').strip()
        user.email = new_email
        user.phone = request.POST.get('phone', '').strip()
        user.designation = request.POST.get('designation', '').strip()
        
        if user.is_super_admin():
            user.role = 'ADMIN'
            user.is_plant_admin = True
        else:
            role = request.POST.get('role', 'USER')
            user.role = role
            user.is_plant_admin = (role == 'ADMIN')
        
        dept_ids = [int(x) for x in request.POST.getlist('departments') if x.isdigit()]
        if user.role == 'USER' and dept_ids:
            user.department = Department.objects.filter(id=dept_ids[0]).first()
        else:
            user.department = None
            
        user.save()
        
        # Grant plant-wide access if checked
        grant_all_access = request.POST.get('grant_all_access') == 'on'
        if grant_all_access:
            depts = Department.objects.filter(is_active=True)
            mods = Module.objects.filter(is_active=True)
            for d in depts:
                for m in mods:
                    UserModuleAccess.objects.update_or_create(
                        user=user,
                        department=d,
                        module=m,
                        defaults={'access_level': 'EDIT', 'granted_by': request.user}
                    )
            messages.success(request, f"User '{user.username}' updated and granted full access to all departments/modules.")
        else:
            if user.role == 'USER':
                # Get existing accesses
                existing_levels = {
                    (access.department_id, access.module_id): access.access_level
                    for access in UserModuleAccess.objects.filter(user=user)
                }
                
                # Revoke module accesses for any department not in the selected dept_ids
                UserModuleAccess.objects.filter(user=user).exclude(department_id__in=dept_ids).delete()
                
                # Grant/update access for each selected department
                active_modules = Module.objects.filter(is_active=True)
                access_level_chosen = request.POST.get('access_control_level')
                
                for d_id in dept_ids:
                    d = Department.objects.filter(id=d_id).first()
                    if d:
                        for m in active_modules:
                            if access_level_chosen in ('EDIT', 'VIEW'):
                                target_level = access_level_chosen
                            else:
                                target_level = existing_levels.get((d.id, m.id), 'EDIT')
                                
                            UserModuleAccess.objects.update_or_create(
                                user=user,
                                department=d,
                                module=m,
                                defaults={'access_level': target_level, 'granted_by': request.user}
                            )
                messages.success(request, f"User '{user.username}' updated and department access updated.")
            else:
                messages.success(request, f"User '{user.username}' updated successfully.")
        
    return redirect('portal:user_informations')


@login_required
@admin_required
def admin_delete_user(request, user_id):
    """
    Permanently deletes a user account.
    """
    if request.method == 'POST':
        from django.shortcuts import get_object_or_404
        user = get_object_or_404(User, id=user_id)
        if user.is_super_admin():
            messages.error(request, "Super admin account cannot be deleted.")
            return redirect('portal:user_informations')
        if request.user.id == user_id:
            messages.error(request, "You cannot delete your own account.")
            return redirect('portal:user_informations')
            
        username = user.username
        user.delete()
        messages.success(request, f"User '{username}' has been deleted successfully.")
        
    return redirect('portal:user_informations')



@login_required
@admin_required
@require_http_methods(['POST'])
def reject_access_request(request, req_id):
    """
    Rejects/deletes an access sign-up request and deletes the inactive user.
    """
    from portal.models import AccessRequest
    try:
        req = AccessRequest.objects.get(id=req_id)
        email = req.email
        req.delete()
        
        # Delete corresponding inactive user if it exists
        User.objects.filter(email=email, is_active=False).delete()
        
        messages.success(request, f"Access request for '{email}' has been rejected.")
    except AccessRequest.DoesNotExist:
        messages.error(request, "Access request not found.")
        
    return redirect('portal:admin_access')


@login_required
@admin_required
def admin_departments(request):
    """
    Interface for administrators to view, create, and dissolve (deactivate) departments.
    """
    if request.method == 'POST':
        action = request.POST.get('action')
        
        if action == 'create':
            name = request.POST.get('name', '').strip()
            code = request.POST.get('code', '').strip().upper()
            
            if not name or not code:
                messages.error(request, "Both Department Name and Code are required.")
            else:
                # Check for duplicates (active or dissolved)
                existing = Department.objects.filter(models.Q(name__iexact=name) | models.Q(code__iexact=code)).first()
                if existing:
                    if not existing.is_active:
                        messages.warning(request, f"Department '{existing.name}' ({existing.code}) already exists but is currently dissolved. You can reactivate it in the list below.")
                    else:
                        messages.error(request, f"A department with Name '{name}' or Code '{code}' already exists.")
                else:
                    Department.objects.create(name=name, code=code, is_active=True)
                    messages.success(request, f"Department '{name}' ({code}) has been created successfully.")
                    
        elif action == 'toggle_status':
            dept_id = request.POST.get('dept_id')
            if dept_id:
                from django.shortcuts import get_object_or_404
                dept = get_object_or_404(Department, id=dept_id)
                dept.is_active = not dept.is_active
                dept.save(update_fields=['is_active'])
                
                status_str = "activated" if dept.is_active else "dissolved"
                msg_type = messages.success if dept.is_active else messages.warning
                msg_type(request, f"Department '{dept.name}' ({dept.code}) has been successfully {status_str}.")
                
        elif action == 'delete':
            dept_id = request.POST.get('dept_id')
            if dept_id:
                from django.shortcuts import get_object_or_404
                dept = get_object_or_404(Department, id=dept_id)
                name = dept.name
                code = dept.code
                dept.delete()
                messages.success(request, f"Department '{name}' ({code}) has been permanently deleted.")
                
        return redirect('portal:admin_departments')

    departments = Department.objects.all().order_by('-is_active', 'name')
    context = {
        'departments': departments,
        'active_section': 'admin_departments',
    }
    return render(request, 'portal/admin/manage_departments.html', context)


@login_required
@admin_required
@require_http_methods(['POST'])
def toggle_department_access(request):
    """
    HTMX endpoint to toggle access to a department for a user.
    If the user has access, revokes it by deleting all their module access records for that department.
    If the user does not have access, grants it by creating VIEW access records for all active modules.
    """
    from django.shortcuts import get_object_or_404
    
    user_id = request.POST.get('user_id')
    dept_id = request.POST.get('dept_id')
    stripe_str = request.POST.get('stripe', 'false')
    stripe = (stripe_str == 'true')
    
    user = get_object_or_404(User, id=user_id)
    dept = get_object_or_404(Department, id=dept_id)
    
    # Check if they have access currently
    has_access = UserModuleAccess.objects.filter(user=user, department=dept).exists()
    
    if has_access:
        # Revoke access: delete all module access records for this user and department
        UserModuleAccess.objects.filter(user=user, department=dept).delete()
        has_access = False
    else:
        # Grant access: create a VIEW access record for all active modules
        active_modules = Module.objects.filter(is_active=True)
        for m in active_modules:
            UserModuleAccess.objects.update_or_create(
                user=user,
                department=dept,
                module=m,
                defaults={'access_level': 'VIEW', 'granted_by': request.user}
            )
        has_access = True
        
    # Build list of active modules and their access states for template rendering
    active_modules = Module.objects.filter(is_active=True).order_by('sort_order')
    access_map = {m.key: None for m in active_modules}
    if has_access:
        records = UserModuleAccess.objects.filter(user=user, department=dept, module__is_active=True)
        for r in records:
            access_map[r.module.key] = r.access_level
            
    modules_data = []
    for m in active_modules:
        modules_data.append({
            'module': m,
            'access': access_map.get(m.key)
        })
        
    context = {
        'u': user,
        'dept': dept,
        'has_access': has_access,
        'modules_data': modules_data,
        'stripe': stripe,
    }
    return render(request, 'portal/admin/partials/_dept_row.html', context)
