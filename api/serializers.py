from rest_framework import serializers
from django.contrib.auth import get_user_model
from tpm.models import Department, FuguaiTag
from portal.models import Module, UserModuleAccess
from delays.models import ChecklistSchedule, MaintenanceChecklist, MaintenanceChecklistItem

User = get_user_model()

class DepartmentSerializer(serializers.ModelSerializer):
    class Meta:
        model = Department
        fields = ['id', 'name', 'code']

class UserSerializer(serializers.ModelSerializer):
    department_details = DepartmentSerializer(source='department', read_only=True)
    
    class Meta:
        model = User
        fields = ['id', 'username', 'email', 'first_name', 'last_name', 'role', 'is_plant_admin', 'department', 'department_details']

class ModuleSerializer(serializers.ModelSerializer):
    class Meta:
        model = Module
        fields = ['id', 'key', 'label', 'description', 'icon', 'color_class', 'redirect_url_template']

class UserModuleAccessSerializer(serializers.ModelSerializer):
    module_details = ModuleSerializer(source='module', read_only=True)
    department_details = DepartmentSerializer(source='department', read_only=True)
    
    class Meta:
        model = UserModuleAccess
        fields = ['id', 'module', 'module_details', 'department', 'department_details', 'access_level']

class ChecklistScheduleSerializer(serializers.ModelSerializer):
    assigned_hod_details = UserSerializer(source='assigned_hod', read_only=True)
    
    class Meta:
        model = ChecklistSchedule
        fields = ['id', 'department', 'checklist_name', 'frequency', 'assigned_hod', 'assigned_hod_details', 'shift_incharge']

class MaintenanceChecklistItemSerializer(serializers.ModelSerializer):
    class Meta:
        model = MaintenanceChecklistItem
        fields = ['id', 'action_item', 'status', 'remarks', 'is_header']

class MaintenanceChecklistSerializer(serializers.ModelSerializer):
    items = MaintenanceChecklistItemSerializer(many=True, read_only=True)
    created_by_details = UserSerializer(source='created_by', read_only=True)
    department_details = DepartmentSerializer(source='department', read_only=True)
    
    class Meta:
        model = MaintenanceChecklist
        fields = [
            'id', 'department', 'department_details', 'date', 'created_at', 'frequency', 
            'agency_type', 'responsible_agency', 'area', 'sub_area', 'equipment', 
            'sub_equipment', 'shift_incharge', 'engineer', 'operator', 'remark', 
            'created_by', 'created_by_details', 'items'
        ]


class FuguaiTagSerializer(serializers.ModelSerializer):
    created_by_details = UserSerializer(source='created_by', read_only=True)
    department_details = DepartmentSerializer(source='department', read_only=True)
    
    class Meta:
        model = FuguaiTag
        fields = [
            'id', 'department', 'department_details', 'theme', 'tag_color',
            'before_image', 'after_image', 'created_at', 'rectified_at', 'created_by', 'created_by_details'
        ]

