from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from django.contrib.auth import get_user_model
from django.shortcuts import get_object_or_404
from datetime import datetime

from tpm.models import Department, FuguaiTag
from portal.models import Module, UserModuleAccess
from delays.models import ChecklistSchedule, MaintenanceChecklist, MaintenanceChecklistItem, DelayDropdownOption
from api.serializers import (
    UserSerializer, DepartmentSerializer, ModuleSerializer,
    ChecklistScheduleSerializer, MaintenanceChecklistSerializer,
    FuguaiTagSerializer
)

User = get_user_model()

class MeView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        serializer = UserSerializer(request.user)
        return Response(serializer.data)

class DashboardView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        user = request.user
        active_modules = Module.objects.filter(is_active=True).order_by('sort_order')
        active_modules_serialized = ModuleSerializer(active_modules, many=True).data

        # Determine departments list
        if hasattr(user, 'is_admin') and user.is_admin():
            depts = Department.objects.filter(is_active=True).order_by('name')
        else:
            dept_ids = set()
            if user.department_id:
                dept_ids.add(user.department_id)
            
            permitted_accesses = UserModuleAccess.objects.filter(user=user)
            for access in permitted_accesses:
                dept_ids.add(access.department_id)
            
            depts = Department.objects.filter(id__in=dept_ids, is_active=True).order_by('name')

        depts_data = []
        for d in depts:
            if hasattr(user, 'is_admin') and user.is_admin():
                accessible_module_keys = [m.key for m in active_modules]
            else:
                records = UserModuleAccess.objects.filter(
                    user=user, 
                    department=d, 
                    module__is_active=True
                ).select_related('module')
                accessible_module_keys = [r.module.key for r in records]

            depts_data.append({
                'id': d.id,
                'name': d.name,
                'code': d.code,
                'accessible_modules': accessible_module_keys
            })

        return Response({
            'user': UserSerializer(user).data,
            'modules': active_modules_serialized,
            'departments': depts_data
        })

# ─────────────────────────────────────────────
# CHECKLIST ENDPOINTS (PHASE 1 - MODULE GET/POST)
# ─────────────────────────────────────────────

class ChecklistSchedulesView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        dept_id = request.query_params.get('department_id')
        if not dept_id:
            return Response({'error': 'department_id query parameter is required'}, status=status.HTTP_400_BAD_REQUEST)
        
        department = get_object_or_404(Department, id=dept_id)
        schedules = ChecklistSchedule.objects.filter(department=department).order_by('checklist_name')
        serializer = ChecklistScheduleSerializer(schedules, many=True)
        return Response(serializer.data)

class ChecklistsListView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        dept_id = request.query_params.get('department_id')
        if not dept_id:
            return Response({'error': 'department_id query parameter is required'}, status=status.HTTP_400_BAD_REQUEST)
        
        department = get_object_or_404(Department, id=dept_id)
        checklists = MaintenanceChecklist.objects.filter(department=department).order_by('-date', '-id')
        
        date_str = request.query_params.get('date')
        if date_str:
            try:
                target_date = datetime.strptime(date_str, '%Y-%m-%d').date()
                checklists = checklists.filter(date=target_date)
            except ValueError:
                return Response({'error': 'Invalid date format, use YYYY-MM-DD'}, status=status.HTTP_400_BAD_REQUEST)
                
        serializer = MaintenanceChecklistSerializer(checklists, many=True)
        return Response(serializer.data)

class ChecklistDetailView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, checklist_id):
        checklist = get_object_or_404(MaintenanceChecklist, id=checklist_id)
        serializer = MaintenanceChecklistSerializer(checklist)
        return Response(serializer.data)

class ChecklistInitializeView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        dept_id = request.data.get('department_id')
        equipment_name = request.data.get('equipment')
        date_str = request.data.get('date')

        if not dept_id or not equipment_name or not date_str:
            return Response({'error': 'department_id, equipment, and date are required.'}, status=status.HTTP_400_BAD_REQUEST)

        try:
            checklist_date = datetime.strptime(date_str, '%Y-%m-%d').date()
        except ValueError:
            return Response({'error': 'Invalid date format, use YYYY-MM-DD.'}, status=status.HTTP_400_BAD_REQUEST)

        department = get_object_or_404(Department, id=dept_id)

        # Check if already exists to avoid double creation
        checklist = MaintenanceChecklist.objects.filter(
            department=department,
            equipment=equipment_name,
            date=checklist_date
        ).first()

        created = False
        if not checklist:
            # Determine default agency and area
            opt = DelayDropdownOption.objects.filter(
                department=department,
                category__iexact='Equipment',
                value=equipment_name,
                parent_value='Maintenance'
            ).first()
            default_area = opt.parent_value if opt else ""
            
            # Fetch default HOD/agency schedule
            sched = ChecklistSchedule.objects.filter(department=department, checklist_name=equipment_name).first()
            default_agency = 'Mechanical'
            
            checklist = MaintenanceChecklist.objects.create(
                department=department,
                date=checklist_date,
                equipment=equipment_name,
                responsible_agency=default_agency,
                area=default_area,
                shift_incharge=sched.shift_incharge if (sched and sched.shift_incharge) else '',
                created_by=request.user
            )
            created = True
            
            # Fetch all action items seeded for this equipment
            actions = DelayDropdownOption.objects.filter(
                department=department,
                category__iexact='Action',
                parent_value=equipment_name
            ).order_by('id')
            
            for act in actions:
                MaintenanceChecklistItem.objects.create(
                    checklist=checklist,
                    action_item=act.value,
                    status=None,
                    is_header=act.is_header
                )

        serializer = MaintenanceChecklistSerializer(checklist)
        return Response({
            'created': created,
            'checklist': serializer.data
        }, status=status.HTTP_201_CREATED if created else status.HTTP_200_OK)

class ChecklistSaveView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, checklist_id):
        checklist = get_object_or_404(MaintenanceChecklist, id=checklist_id)
        
        # Update metadata fields if provided
        if 'responsible_agency' in request.data:
            checklist.responsible_agency = request.data.get('responsible_agency')
        if 'area' in request.data:
            checklist.area = request.data.get('area')
        if 'sub_area' in request.data:
            checklist.sub_area = request.data.get('sub_area')
        if 'sub_equipment' in request.data:
            checklist.sub_equipment = request.data.get('sub_equipment')
        if 'shift_incharge' in request.data:
            checklist.shift_incharge = request.data.get('shift_incharge')
        if 'engineer' in request.data:
            checklist.engineer = request.data.get('engineer')
        if 'operator' in request.data:
            checklist.operator = request.data.get('operator')
        if 'remark' in request.data:
            checklist.remark = request.data.get('remark')
        
        checklist.save()

        # Update items status & remarks
        items_data = request.data.get('items', [])
        for item in items_data:
            item_id = item.get('id')
            item_status = item.get('status') # 'OK' or 'NOT OK' or None
            item_remarks = item.get('remarks', '')
            
            if item_id:
                checklist_item = MaintenanceChecklistItem.objects.filter(id=item_id, checklist=checklist).first()
                if checklist_item:
                    checklist_item.status = item_status
                    checklist_item.remarks = item_remarks
                    checklist_item.save()

        serializer = MaintenanceChecklistSerializer(checklist)
        return Response(serializer.data, status=status.HTTP_200_OK)


# ─────────────────────────────────────────────
# FUGUAI REGISTER ENDPOINTS
# ─────────────────────────────────────────────
from rest_framework.parsers import MultiPartParser, FormParser

class FuguaiTagListView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        dept_id = request.query_params.get('department_id')
        if not dept_id:
            return Response({'error': 'department_id is required.'}, status=status.HTTP_400_BAD_REQUEST)
        
        department = get_object_or_404(Department, id=dept_id)
        tags = FuguaiTag.objects.filter(department=department).order_by('-created_at')
        serializer = FuguaiTagSerializer(tags, many=True)
        return Response(serializer.data)

class FuguaiTagCreateView(APIView):
    permission_classes = [IsAuthenticated]
    parser_classes = [MultiPartParser, FormParser]

    def post(self, request):
        dept_id = request.data.get('department_id')
        theme = request.data.get('theme', '')
        before_image = request.FILES.get('before_image')
        tag_color = request.data.get('tag_color', 'WHITE')
        if tag_color not in ('WHITE', 'RED'):
            tag_color = 'WHITE'

        if not dept_id:
            return Response({'error': 'department_id is required.'}, status=status.HTTP_400_BAD_REQUEST)

        department = get_object_or_404(Department, id=dept_id)
        
        tag = FuguaiTag.objects.create(
            department=department,
            theme=theme,
            tag_color=tag_color,
            before_image=before_image,
            created_by=request.user
        )
        serializer = FuguaiTagSerializer(tag)
        return Response(serializer.data, status=status.HTTP_201_CREATED)

class FuguaiTagUpdateView(APIView):
    permission_classes = [IsAuthenticated]
    parser_classes = [MultiPartParser, FormParser]

    def post(self, request, tag_id):
        tag = get_object_or_404(FuguaiTag, id=tag_id)
        
        after_image = request.FILES.get('after_image')
        if after_image:
            from django.utils import timezone
            tag.after_image = after_image
            tag.rectified_at = timezone.now()
            
        theme = request.data.get('theme')
        if theme:
            tag.theme = theme
            
        tag.save()
        serializer = FuguaiTagSerializer(tag)
        return Response(serializer.data, status=status.HTTP_200_OK)


from rest_framework_simplejwt.tokens import AccessToken
from django.contrib.auth import get_user_model, login
from django.shortcuts import redirect
from django.http import HttpResponse

def auto_login_view(request):
    token_str = request.GET.get('token')
    next_url = request.GET.get('next', '/')
    
    if not token_str:
        return HttpResponse("Token is missing", status=400)
        
    try:
        token = AccessToken(token_str)
        user_id = token['user_id']
        
        User = get_user_model()
        user = User.objects.get(id=user_id)
        
        login(request, user, backend='django.contrib.auth.backends.ModelBackend')
        request.session['is_mobile_webview'] = True
        return redirect(next_url)
    except Exception as e:
        return HttpResponse(f"Invalid or expired token: {str(e)}", status=403)


from django.http import JsonResponse
from rest_framework_simplejwt.tokens import RefreshToken
from django.contrib.auth.decorators import login_required

@login_required
def webview_token_view(request):
    try:
        refresh = RefreshToken.for_user(request.user)
        return JsonResponse({
            'access': str(refresh.access_token),
            'refresh': str(refresh),
        })
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)



