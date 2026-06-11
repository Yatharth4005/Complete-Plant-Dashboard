from django.contrib import admin
from delays.models import DelayUpload, DelayRecord, DelayDropdownOption

@admin.register(DelayDropdownOption)
class DelayDropdownOptionAdmin(admin.ModelAdmin):
    list_display = ('department', 'category', 'value', 'parent_value')
    list_filter = ('department', 'category')
    search_fields = ('value', 'parent_value')

@admin.register(DelayUpload)
class DelayUploadAdmin(admin.ModelAdmin):
    list_display = ('filename', 'department', 'uploaded_at', 'status')
    list_filter = ('department', 'status')

@admin.register(DelayRecord)
class DelayRecordAdmin(admin.ModelAdmin):
    list_display = ('department', 'date', 'agency', 'equipment', 'duration_mins')
    list_filter = ('department', 'agency')
    search_fields = ('equipment', 'description', 'why')
