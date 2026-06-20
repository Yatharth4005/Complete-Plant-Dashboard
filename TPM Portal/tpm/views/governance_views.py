from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.views.decorators.http import require_POST
from django.http import JsonResponse
from tpm.models import User, Department, TPMGovernanceAssignment, TPMGovernanceRoleDescription

def seed_default_role_descriptions():
    defaults = {
        'sponsor': {
            'title': 'Project Sponsor',
            'designation': 'Executive Director (Unit Head — JSP Raigarh++)',
            'responsibilities': "Ensure the TPM initiative aligns with the organization's overall strategic goals and objectives.\nResource Allocation and key Decision Making for the TPM implementation."
        },
        'steering': {
            'title': 'Steering Committee',
            'designation': 'Chairman, Vice Chairman & Board Members',
            'responsibilities': "Approve TPM implementation roadmap.\nConduct monthly TPM progress review.\nRecommend teams for reward & recognition.\nArrange for recognition and felicitation for teams achieving TPM quarterly targets."
        },
        'coordinators': {
            'title': 'TPM Coordinators',
            'designation': 'Raj Bhushan (Pillar) & Raunika (Workstation/Cell)',
            'responsibilities': "Pillar (Raj Bhushan): Prepare and manage the training calendar, release monthly reports, sign off milestone stages, and audit documentation (OPL/Standards).\nLogistics (Raunika): Maintain trainee attendance, coordinate assessments, and manage training organization scheduling, travel, accommodation & bills."
        },
        'hod': {
            'title': 'HOD / Area Owners',
            'designation': 'Department Heads & Zonal Heads',
            'responsibilities': "Identify cells and workstations along with their team members.\nReview and approve quarterly targets of workstations and cells.\nEnsure participation & attendance of teams in TPM related trainings.\nEnsure active participation of the Cell and Workstation teams during reviews.\nProvide necessary resources (e.g. tools, materials) and conduct fortnightly reviews."
        },
        'cell': {
            'title': 'Cell Leaders',
            'designation': 'Cell Team Heads',
            'responsibilities': "Provide necessary technical guidance to the workstation teams.\nAddress any cross-functional coordination and alignment issues.\nConduct weekly progress reviews for cell workstations."
        },
        'workstation': {
            'title': 'Workstation Leads',
            'designation': 'Workstation SPOC / Lead Operators',
            'responsibilities': "Achieve quarterly goals of KPIs.\nEnsure timely actions on identified abnormalities.\nLead Zero leakage drives and assign tasks to team members.\nEnsure presence of team and timely action on review feedbacks."
        },
        'workforce': {
            'title': 'Workstation / Cell Teams',
            'designation': 'Ground workforce execution teams',
            'responsibilities': "Identify abnormalities / failures and address them including analysis, RCA with permanent solutions.\nComplete the allocated tasks on time.\nParticipate in internal & external reviews.\nMaintain 5S in Workstations."
        }
    }
    for key, data in defaults.items():
        TPMGovernanceRoleDescription.objects.get_or_create(
            role_key=key,
            defaults={
                'title': data['title'],
                'designation': data['designation'],
                'responsibilities': data['responsibilities']
            }
        )

@login_required
def tpm_governance_structure(request):
    """
    Renders the TPM Governance Structure flowchart and details.
    """
    seed_default_role_descriptions()
    role_descriptions = {r.role_key: r for r in TPMGovernanceRoleDescription.objects.all()}
    
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
        'role_descriptions': role_descriptions,
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
    departments = Department.objects.filter(is_active=True).order_by('name')
    
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


@login_required
@require_POST
def save_role_description(request):
    if not request.user.is_admin():
        return JsonResponse({'status': 'error', 'message': 'Permission denied.'}, status=403)
        
    role_key = request.POST.get('role_key')
    title = request.POST.get('title')
    designation = request.POST.get('designation')
    responsibilities = request.POST.get('responsibilities')
    
    if not role_key or not title:
        return JsonResponse({'status': 'error', 'message': 'Missing role_key or title.'}, status=400)
        
    role_desc, created = TPMGovernanceRoleDescription.objects.get_or_create(role_key=role_key)
    role_desc.title = title
    role_desc.designation = designation or ''
    role_desc.responsibilities = responsibilities or ''
    role_desc.save()
    
    return JsonResponse({'status': 'success', 'message': 'Role description updated successfully.'})


