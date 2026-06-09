from django.contrib import admin
from cmc.models import Equipment, EquipmentBearingPoint, PMScheduleEntry, VibrationLog, VibrationReading, OilTestLog, WDALog, SAPNotification

class EquipmentBearingPointInline(admin.TabularInline):
    model = EquipmentBearingPoint
    extra = 4

@admin.register(Equipment)
class EquipmentAdmin(admin.ModelAdmin):
    list_display = ('name', 'department', 'equipment_class', 'frequency', 'scheduled_days', 'is_active')
    list_filter = ('department', 'equipment_class', 'frequency', 'is_active')
    search_fields = ('name', 'sap_code_mech', 'sap_code_elec')
    inlines = [EquipmentBearingPointInline]

@admin.register(EquipmentBearingPoint)
class EquipmentBearingPointAdmin(admin.ModelAdmin):
    list_display = ('equipment', 'label', 'bearing_no', 'sort_order')
    list_filter = ('equipment__department',)
    search_fields = ('equipment__name', 'label', 'bearing_no')

admin.site.register(PMScheduleEntry)
admin.site.register(VibrationLog)
admin.site.register(VibrationReading)
admin.site.register(OilTestLog)
admin.site.register(WDALog)
admin.site.register(SAPNotification)
