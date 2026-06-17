from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.views.decorators.http import require_POST
from django.http import JsonResponse
from tpm.models import User, Department, TPMGovernanceAssignment

@login_required
def tpm_governance_structure(request):
    """
    Renders the TPM Governance Structure flowchart and details.
    """
    assignments = TPMGovernanceAssignment.objects.all().select_related('user__department')
    
    # Group assignments by role_key
    assignments_by_role = {}
    for choice_key, choice_name in TPMGovernanceAssignment.ROLE_CHOICES:
        assignments_by_role[choice_key] = []
        
    for a in assignments:
        if a.role_key in assignments_by_role:
            assignments_by_role[a.role_key].append(a)
            
    # All active users for the drag/drop sidebar (admin only)
    all_users = []
    if request.user.is_admin():
        all_users = User.objects.filter(is_active=True).select_related('department').order_by('first_name', 'last_name')
        
    context = {
        'active_section': 'governance',
        'active_tab': 'structure',
        'assignments': assignments_by_role,
        'all_users': all_users,
    }
    return render(request, 'governance/structure.html', context)


@login_required
@require_POST
def assign_role(request):
    if not request.user.is_admin():
        return JsonResponse({'status': 'error', 'message': 'Permission denied.'}, status=403)
        
    user_id = request.POST.get('user_id')
    role_key = request.POST.get('role_key')
    
    if not user_id or not role_key:
        return JsonResponse({'status': 'error', 'message': 'Missing user_id or role_key.'}, status=400)
        
    user = get_object_or_404(User, id=user_id)
    
    # Check if this role key is single-person
    single_person_roles = ['sponsor', 'chairman', 'vice_chairman', 'coordinator_pillar', 'coordinator_cell']
    
    if role_key in single_person_roles:
        # Delete any existing assignment for this role
        TPMGovernanceAssignment.objects.filter(role_key=role_key).delete()
        
    # Check if assignment already exists
    assignment, created = TPMGovernanceAssignment.objects.get_or_create(
        role_key=role_key,
        user=user
    )
    
    return JsonResponse({
        'status': 'success',
        'message': f'Assigned {user.get_display_name()} to {role_key}.',
        'user_name': user.get_display_name(),
        'user_id': user.id
    })


@login_required
@require_POST
def unassign_role(request):
    if not request.user.is_admin():
        return JsonResponse({'status': 'error', 'message': 'Permission denied.'}, status=403)
        
    user_id = request.POST.get('user_id')
    role_key = request.POST.get('role_key')
    
    if not user_id or not role_key:
        return JsonResponse({'status': 'error', 'message': 'Missing user_id or role_key.'}, status=400)
        
    TPMGovernanceAssignment.objects.filter(role_key=role_key, user_id=user_id).delete()
    
    return JsonResponse({'status': 'success', 'message': 'Assignment removed.'})


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
    
    # Get all assigned user IDs and build a mapping to their roles
    assignments = TPMGovernanceAssignment.objects.all().select_related('user')
    assigned_user_ids = [a.user_id for a in assignments]
    
    # Map user_id to list of governance roles
    user_roles = {}
    for a in assignments:
        role_display = a.get_role_key_display()
        if a.user_id not in user_roles:
            user_roles[a.user_id] = []
        user_roles[a.user_id].append(role_display)
    
    # Filter users based on whether they are assigned to the structure
    if request.user.is_admin():
        users = User.objects.filter(id__in=assigned_user_ids).select_related('department').order_by('username')
    else:
        users = User.objects.filter(id__in=assigned_user_ids, is_active=True).select_related('department').order_by('username')

    # Attach governance roles list to each user object
    for u in users:
        u.governance_roles = user_roles.get(u.id, [])
        u.governance_roles_str = ", ".join(u.governance_roles)

    context = {
        'users': users,
        'departments': departments,
        'active_section': 'governance',
        'active_tab': 'users',
    }
    return render(request, 'governance/users.html', context)

