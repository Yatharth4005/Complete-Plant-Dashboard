from django.shortcuts import redirect
from django.contrib.auth import logout
from django.contrib import messages

def redirect_root(request):
    if request.user.is_authenticated:
        if request.user.is_admin():
            return redirect('http://localhost:8000/dashboard/')
        elif request.user.department:
            return redirect('dept_overview', dept_id=request.user.department.id)
        else:
            messages.error(request, "User department is not configured. Contact Administrator.")
            logout(request)
            return redirect('http://localhost:8000/login/')
    return redirect('http://localhost:8000/login/')

def logout_view(request):
    logout(request)
    messages.success(request, "Logged out successfully.")
    return redirect('http://localhost:8000/login/')

