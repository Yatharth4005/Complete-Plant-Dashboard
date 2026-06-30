from django.contrib import admin
from .models import HODKPIUpload, HODKPIRecord, HODKPIDelayRecord, HODKPIMonthlySubmission

@admin.register(HODKPIUpload)
class HODKPIUploadAdmin(admin.ModelAdmin):
    list_display = ('department', 'month', 'year', 'reporting_date', 'uploaded_at', 'uploaded_by')
    list_filter = ('department', 'year', 'month')
    search_fields = ('department__name', 'file')

@admin.register(HODKPIRecord)
class HODKPIRecordAdmin(admin.ModelAdmin):
    list_display = ('upload', 'domain', 'kpi_name', 'view_type', 'target', 'actual', 'achievement_pct', 'status', 'is_below_target')
    list_filter = ('domain', 'view_type', 'status', 'is_below_target', 'upload__department')
    search_fields = ('kpi_name', 'upload__department__name')

@admin.register(HODKPIDelayRecord)
class HODKPIDelayRecordAdmin(admin.ModelAdmin):
    list_display = ('upload', 'reason', 'department_cause', 'duration_mins', 'contribution_pct')
    list_filter = ('department_cause', 'upload__department')
    search_fields = ('reason', 'department_cause')

@admin.register(HODKPIMonthlySubmission)
class HODKPIMonthlySubmissionAdmin(admin.ModelAdmin):
    list_display = ('department', 'month', 'year', 'status', 'submitted_at', 'submitted_by')
    list_filter = ('status', 'year', 'month', 'department')
    search_fields = ('department__name',)
