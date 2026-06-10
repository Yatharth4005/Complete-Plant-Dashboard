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
        
        # Designation
        if 'designation' in request.POST:
            user.designation = request.POST.get('designation', '').strip()
        
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


@require_http_methods(['POST'])
def forgot_password_view(request):
    from django.contrib.auth.tokens import default_token_generator
    from django.utils.http import urlsafe_base64_encode
    from django.utils.encoding import force_bytes
    from django.core.mail import send_mail
    from django.urls import reverse
    from tpm.models import User
    
    email = request.POST.get('email', '').strip().lower()
    if not email:
        messages.error(request, "Please enter your Jindal Steel Email first.")
        return redirect('portal:login')
        
    user = User.objects.filter(email__iexact=email).first()
    if user:
        uid = urlsafe_base64_encode(force_bytes(user.pk))
        token = default_token_generator.make_token(user)
        reset_link = request.build_absolute_uri(
            reverse('portal:reset_password', kwargs={'uidb64': uid, 'token': token})
        )
        
        subject = "Password Reset Request — JSPL Unified Portal"
        message = (
            f"Hello {user.get_display_name()},\n\n"
            f"You requested a password reset for your JSPL Plant Portal account.\n"
            f"Please click the link below to reset your password:\n\n"
            f"{reset_link}\n\n"
            f"If you did not request this, please ignore this email.\n\n"
            f"Regards,\n"
            f"JSPL IT Support Services"
        )
        try:
            send_mail(
                subject,
                message,
                'no-reply@jindalsteel.in',
                [user.email],
                fail_silently=False,
            )
            messages.success(request, f"A password reset link has been sent to {user.email}. Check your email/console.")
        except Exception as e:
            messages.error(request, f"Failed to send email: {str(e)}")
    else:
        # Standard secure practice: show a success-like message even if user doesn't exist
        messages.success(request, f"If {email} is registered in our system, a password reset link has been sent.")
        
    return redirect('portal:login')


@require_http_methods(['GET', 'POST'])
def reset_password_view(request, uidb64, token):
    from django.contrib.auth.tokens import default_token_generator
    from django.utils.http import urlsafe_base64_decode
    from django.utils.encoding import force_str
    from tpm.models import User
    
    try:
        uid = force_str(urlsafe_base64_decode(uidb64))
        user = User.objects.get(pk=uid)
    except (TypeError, ValueError, OverflowError, User.DoesNotExist):
        user = None
        
    if user is not None and default_token_generator.check_token(user, token):
        if request.method == 'POST':
            password = request.POST.get('password', '')
            confirm_password = request.POST.get('confirm_password', '')
            
            if not password:
                messages.error(request, "Password cannot be empty.")
                return render(request, 'portal/auth/reset_password.html', {'uidb64': uidb64, 'token': token})
                
            if password == confirm_password:
                user.set_password(password)
                user.save()
                messages.success(request, "Your password has been reset successfully. Please log in with your new password.")
                return redirect('portal:login')
            else:
                messages.error(request, "Passwords do not match.")
                
        return render(request, 'portal/auth/reset_password.html', {'uidb64': uidb64, 'token': token})
    else:
        messages.error(request, "The password reset link is invalid or has expired.")
        return redirect('portal:login')
