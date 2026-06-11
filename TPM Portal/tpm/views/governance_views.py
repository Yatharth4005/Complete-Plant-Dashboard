from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from tpm.models import User, Department

@login_required
def tpm_governance_structure(request):
    """
    Renders the TPM Governance Structure flowchart and details.
    """
    context = {
        'active_section': 'governance',
        'active_tab': 'structure',
    }
    return render(request, 'governance/structure.html', context)


@login_required
def tpm_governance_users(request):
    """
    Renders the User Informations contact directory.
    Visible to all logged in users.
    Only admins have edit/delete action controls.
    """
    STANDARD_DEPTS = [
        'BF1', 'BF2', 'BP', 'CP', 'CO', 'DRI1', 'DRI2', 'EP', 'LDP', 'OP',
        'PGP1', 'PGP2', 'PGP3', 'PM', 'PP1', 'PP2', 'PP3', 'PPP3',
        'RMHS1', 'RMHS2', 'RMHS3', 'RM', 'SAF1', 'SAF2', 'SMS2', 'SMS3',
        'SINT', 'SPM'
    ]
    departments = Department.objects.filter(code__in=STANDARD_DEPTS).order_by('name')
    
    # Admins see all users (active & inactive), normal users see only active users
    if request.user.is_admin():
        users = User.objects.all().select_related('department').order_by('username')
    else:
        users = User.objects.filter(is_active=True).select_related('department').order_by('username')

    context = {
        'users': users,
        'departments': departments,
        'active_section': 'governance',
        'active_tab': 'users',
    }
    return render(request, 'governance/users.html', context)
