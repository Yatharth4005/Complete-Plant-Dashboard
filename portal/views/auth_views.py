from django.shortcuts import render, redirect
from django.contrib.auth import authenticate, login, logout
from django.views.decorators.http import require_http_methods
from django.contrib import messages
from portal.models import AuditLog

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

@require_http_methods(['GET', 'POST'])
def login_view(request):
    """
    Unified login view for the entire operations portal.
    """
    if request.user.is_authenticated:
        return redirect('portal:root')

    error = None

    if request.method == 'POST':
        email = request.POST.get('email', '').strip().lower()
        password = request.POST.get('password', '')

        # Validate domain name
        if not (email.endswith('@jindalsteel.in') or email.endswith('@jspl.com') or email == 'admin'):
            error = 'Please use your @jindalsteel.in email address.'
        else:
            # If the user input is 'admin', allow standard login, otherwise auth by email
            username_to_auth = email
            user = authenticate(request, username=username_to_auth, password=password)

            if user is not None and user.is_active:
                login(request, user)
                
                # Write Audit log
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
