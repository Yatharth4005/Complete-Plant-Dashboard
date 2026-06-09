from django.shortcuts import render, redirect
from django.contrib.auth import authenticate, login, logout, update_session_auth_hash
from django.views.decorators.http import require_http_methods
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from portal.models import AuditLog
from tpm.models import Department

def root_redirect(request):
    """
    Redirects user to the appropriate page based on auth state.
    """
    if not request.user.is_authenticated:
        return redirect('portal:login')
    if request.user.is_admin():
        return redirect('portal:plant_dashboard')
    if request.user.department_id:
        return redirect('portal:dept_hub', dept_id=request.user.department_id)
    return redirect('portal:plant_dashboard')

# ... login_view and logout_view ...
# (preserving lines 20-75 content)
@require_http_methods(['GET', 'POST'])
def login_view(request):
    if request.user.is_authenticated:
        return redirect('portal:root')

    error = None

    if request.method == 'POST':
        email = request.POST.get('email', '').strip().lower()
        password = request.POST.get('password', '')

        if not (email.endswith('@jindalsteel.in') or email.endswith('@jspl.com') or email == 'admin'):
            error = 'Please use your @jindalsteel.in email address.'
        else:
            username_to_auth = email
            user = authenticate(request, username=username_to_auth, password=password)

            if user is not None and user.is_active:
                login(request, user)
                
                AuditLog.objects.create(
                    user=user,
                    action='LOGIN',
                    ip_address=get_client_ip(request),
                )
                
                next_url = request.GET.get('next')
                if next_url:
                    return redirect(next_url)
                return redirect('portal:root')
            else:
                error = 'Invalid email or password. Please try again.'

    return render(request, 'portal/auth/login.html', {'error': error})

def logout_view(request):
    if request.user.is_authenticated:
        AuditLog.objects.create(
            user=request.user,
            action='LOGOUT',
            ip_address=get_client_ip(request)
        )
    logout(request)
    return redirect('portal:login')

def get_client_ip(request):
    x_forwarded = request.META.get('HTTP_X_FORWARDED_FOR')
    if x_forwarded:
        return x_forwarded.split(',')[0].strip()
    return request.META.get('REMOTE_ADDR')


@login_required
def update_profile(request):
    if request.method == 'POST':
        user = request.user
        
        # Name
        full_name = request.POST.get('name', '').strip()
        if full_name:
            parts = full_name.split(' ', 1)
            user.first_name = parts[0]
            user.last_name = parts[1] if len(parts) > 1 else ''
            
        # Phone
        user.phone = request.POST.get('phone', '').strip()
        
        # Department
        dept_id = request.POST.get('department')
        if dept_id:
            try:
                user.department = Department.objects.get(id=dept_id)
            except Department.DoesNotExist:
                pass
                
        # Photo
        if 'photo' in request.FILES:
            user.photo = request.FILES['photo']
            
        # Password Reset
        password = request.POST.get('password', '')
        confirm_password = request.POST.get('confirm_password', '')
        if password:
            if password == confirm_password:
                user.set_password(password)
                user.save()
                update_session_auth_hash(request, user)
                messages.success(request, 'Profile and password updated successfully.')
            else:
                messages.error(request, 'Passwords do not match.')
                user.save()
                return redirect(request.META.get('HTTP_REFERER', '/'))
        else:
            user.save()
            messages.success(request, 'Profile updated successfully.')
            
    return redirect(request.META.get('HTTP_REFERER', '/'))
