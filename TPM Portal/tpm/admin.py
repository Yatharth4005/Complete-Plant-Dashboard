from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from tpm.models import User, Department, PillarEntry, KPIValue, Workstation, WorkstationKPI, WorkstationValue, OPLSheet

class CustomUserAdmin(UserAdmin):
    fieldsets = UserAdmin.fieldsets + (
        ('TPM Settings', {'fields': ('role', 'department')}),
    )
    list_display = ('username', 'email', 'first_name', 'last_name', 'role', 'department', 'is_staff')
    list_filter = ('role', 'department', 'is_staff', 'is_active')

class KPIValueInline(admin.TabularInline):
    model = KPIValue
    extra = 1

class PillarEntryAdmin(admin.ModelAdmin):
    list_display = ('department', 'pillar', 'month', 'year', 'submitted_at', 'submitted_by')
    list_filter = ('pillar', 'month', 'year', 'department')
    inlines = [KPIValueInline]

class WorkstationKPIInline(admin.TabularInline):
    model = WorkstationKPI
    extra = 1

class WorkstationAdmin(admin.ModelAdmin):
    list_display = ('name', 'department', 'leader', 'inception_date')
    list_filter = ('department',)
    inlines = [WorkstationKPIInline]

class WorkstationValueAdmin(admin.ModelAdmin):
    list_display = ('workstation_kpi', 'month', 'year', 'actual', 'remarks')
    list_filter = ('month', 'year', 'workstation_kpi__workstation__department')

class OPLSheetAdmin(admin.ModelAdmin):
    list_display = ('opl_no', 'theme', 'department', 'pillar', 'lesson_type', 'prepared_by', 'created_at')
    list_filter = ('department', 'pillar', 'lesson_type')

admin.site.register(User, CustomUserAdmin)
admin.site.register(Department)
admin.site.register(PillarEntry, PillarEntryAdmin)
admin.site.register(KPIValue)
admin.site.register(Workstation, WorkstationAdmin)
admin.site.register(WorkstationKPI)
admin.site.register(WorkstationValue, WorkstationValueAdmin)
admin.site.register(OPLSheet, OPLSheetAdmin)
