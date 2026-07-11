from django.db import models
from django.conf import settings
from tpm.models import Department

class DelayUpload(models.Model):
    objects = models.Manager()
    """
    Tracks Excel files uploaded for department delays parsing.
    """
    STATUS_CHOICES = [
        ('SUCCESS', 'Success'),
        ('FAILED', 'Failed'),
    ]

    department = models.ForeignKey(Department, on_delete=models.CASCADE, related_name='delay_uploads')
    file = models.FileField(upload_to='uploads/delays/', null=True, blank=True)
    uploaded_at = models.DateTimeField(auto_now_add=True)
    uploaded_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True)
    filename = models.CharField(max_length=255)
    status = models.CharField(max_length=15, choices=STATUS_CHOICES, default='SUCCESS')
    error_message = models.TextField(blank=True, null=True)

    class Meta:
        ordering = ['-uploaded_at']

    def __str__(self):
        return f"{self.filename} ({self.department.code}) - {self.uploaded_at.strftime('%Y-%m-%d %H:%M')}"


class DelayRecord(models.Model):
    objects = models.Manager()
    """
    Represents a single delay or downtime event, either parsed from an Excel or entered manually.
    """
    upload = models.ForeignKey(DelayUpload, on_delete=models.CASCADE, null=True, blank=True, related_name='records')
    department = models.ForeignKey(Department, on_delete=models.CASCADE, related_name='delay_records')
    sheet_name = models.CharField(max_length=100, default='Manual Entry')
    
    # Delay Event Details
    date = models.DateField()
    time_slot = models.CharField(max_length=100, blank=True, null=True, help_text="e.g. '22:00 - 23:00'")
    start_time = models.CharField(max_length=50, blank=True, null=True, help_text="e.g. '22:15'")
    end_time = models.CharField(max_length=50, blank=True, null=True, help_text="e.g. '22:25'")
    duration_mins = models.FloatField(default=0.0, help_text="Delay duration in minutes")
    production_loss = models.FloatField(default=0.0, blank=True, null=True, help_text="Production loss in Tons")
    
    # Categorization
    agency_type = models.CharField(max_length=50, default='Internal', choices=[('Internal', 'Internal'), ('External', 'External')])
    agency = models.CharField(max_length=150, help_text="Responsible agency, e.g. 'Planned Delay', 'Mechanical'")
    sub_agency = models.CharField(max_length=150, blank=True, null=True, help_text="Sub-agency, e.g. 'Length change'")
    sub_area = models.CharField(max_length=150, blank=True, null=True, help_text="Sub-area")
    section = models.CharField(max_length=150, blank=True, null=True, help_text="Rolled section, e.g. 'UC 254X254'")
    
    # Asset Details
    equipment = models.CharField(max_length=200, blank=True, null=True, help_text="Equipment name or ID")
    sub_equipment = models.CharField(max_length=200, blank=True, null=True, help_text="Sub equipment name or ID")
    shift_incharge = models.CharField(max_length=150, blank=True, null=True)
    
    # Breakdown Analysis
    description = models.TextField(help_text="Detailed description of the delay/breakdown")
    why = models.TextField(blank=True, null=True, help_text="Root cause or 'why-why' analysis")
    action = models.TextField(blank=True, null=True, help_text="Action taken to resolve the delay")
    is_locked = models.BooleanField(default=False, help_text="Locked records can only be edited by Admins")
    end_date = models.DateField(blank=True, null=True, help_text="End date of the delay/breakdown")

    class Meta:
        ordering = ['-date', 'start_time']

    def __str__(self):
        return f"{self.department.code} - {self.date} - {self.agency} ({self.duration_mins} min)"

    def save(self, *args, **kwargs):
        if not self.end_date and self.date:
            self.end_date = self.date
        super().save(*args, **kwargs)
        self.update_notifications()

    def update_notifications(self):
        to_dept = Department.objects.filter(name=self.agency).first()
        if self.agency_type == 'External' and to_dept and to_dept != self.department:
            DelayNotification.objects.update_or_create(
                delay_record=self,
                defaults={
                    'from_department': self.department,
                    'to_department': to_dept,
                    'message': f"Department {self.department.name} ({self.department.code}) filed a delay of {self.duration_mins} mins on {self.date} against you. Reason: {self.description or ''}"
                }
            )
            # Create a PortalNotification for all relevant users (target department, cross-access, admins)
            try:
                from portal.models import PortalNotification
                from tpm.models import User
                from django.db.models import Q
                
                users = User.objects.filter(
                    Q(department=to_dept) | 
                    Q(module_access__department=to_dept, module_access__module__key='Delays') |
                    Q(is_plant_admin=True)
                ).exclude(department=self.department).distinct()
                
                msg = f"Department {self.department.name} ({self.department.code}) filed a delay of {self.duration_mins} mins on {self.date} against your department. Reason: {self.description or ''}"
                for u in users:
                    PortalNotification.objects.get_or_create(
                        user=u,
                        message=msg,
                        link=f"/delays/department/{to_dept.id}/",
                        is_read=False
                    )
            except Exception:
                pass
        else:
            DelayNotification.objects.filter(delay_record=self).delete()


class DelayDropdownOption(models.Model):
    objects = models.Manager()
    department = models.ForeignKey(Department, on_delete=models.CASCADE, related_name='delay_dropdown_options')
    category = models.CharField(max_length=100, help_text="e.g. 'Agency', 'Sub-Agency', 'Equipment', 'Sub-Equipment', etc.")
    value = models.CharField(max_length=255)
    parent_value = models.CharField(max_length=255, blank=True, null=True, help_text="Optional parent value, e.g. parent agency for a sub-agency")
    is_header = models.BooleanField(default=False)

    class Meta:
        unique_together = ('department', 'category', 'value', 'parent_value')
        ordering = ['category', 'value']

    def __str__(self):
        return f"{self.department.code} - {self.category}: {self.value}"


class DelayNotification(models.Model):
    objects = models.Manager()
    from_department = models.ForeignKey(Department, on_delete=models.CASCADE, related_name='sent_delay_notifications')
    to_department = models.ForeignKey(Department, on_delete=models.CASCADE, related_name='received_delay_notifications')
    delay_record = models.ForeignKey(DelayRecord, on_delete=models.CASCADE, related_name='delay_notifications')
    message = models.TextField()
    response_reason = models.TextField(blank=True, null=True)
    is_read = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"From {self.from_department.code} to {self.to_department.code}: {self.message[:50]}"


class EquipmentShutdownSetting(models.Model):
    objects = models.Manager()
    department = models.ForeignKey(Department, on_delete=models.CASCADE, related_name='equipment_shutdown_settings')
    sub_area = models.CharField(max_length=255)
    equipment = models.CharField(max_length=255)
    shutdown_hrs = models.FloatField(default=0.0)

    class Meta:
        unique_together = ('department', 'sub_area', 'equipment')

    def __str__(self):
        return f"{self.department.code} - {self.sub_area} / {self.equipment}: {self.shutdown_hrs} hrs"


from django.utils import timezone

class MaintenanceChecklist(models.Model):
    objects = models.Manager()
    department = models.ForeignKey(Department, on_delete=models.CASCADE, related_name='maintenance_checklists')
    date = models.DateField(default=timezone.now)
    created_at = models.DateTimeField(default=timezone.now)
    frequency = models.CharField(max_length=50, default='Daily', choices=[
        ('Daily', 'Daily'),
        ('Weekly', 'Weekly'),
        ('Fortnightly', 'Fortnightly'),
        ('Monthly', 'Monthly'),
        ('Quarterly', 'Quarterly'),
        ('Half Yearly', 'Half Yearly'),
        ('Yearly', 'Yearly')
    ])
    agency_type = models.CharField(max_length=50, default='Internal')
    responsible_agency = models.CharField(max_length=150)
    area = models.CharField(max_length=150, blank=True, null=True)
    sub_area = models.CharField(max_length=150, blank=True, null=True)
    equipment = models.CharField(max_length=200, blank=True, null=True)
    sub_equipment = models.CharField(max_length=200, blank=True, null=True)
    shift_incharge = models.CharField(max_length=150, blank=True, null=True)
    engineer = models.CharField(max_length=150, blank=True, null=True)
    operator = models.CharField(max_length=150, blank=True, null=True)
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True)

    class Meta:
        ordering = ['-date', '-id']

    def __str__(self):
        return f"{self.department.code} - Checklist {self.id} ({self.date}) - {self.frequency}"

    def has_defects(self):
        return self.items.filter(status='NOT OK').exists()



class MaintenanceChecklistItem(models.Model):
    objects = models.Manager()
    checklist = models.ForeignKey(MaintenanceChecklist, on_delete=models.CASCADE, related_name='items')
    action_item = models.CharField(max_length=255)
    status = models.CharField(max_length=50, choices=[('OK', 'OK'), ('NOT OK', 'NOT OK')], blank=True, null=True)
    remarks = models.TextField(blank=True, null=True)
    is_header = models.BooleanField(default=False)

    def __str__(self):
        return f"Checklist {self.checklist.id} - {self.action_item} ({self.status or 'Header'})"



class ChecklistSchedule(models.Model):
    objects = models.Manager()
    department = models.ForeignKey(Department, on_delete=models.CASCADE, related_name='checklist_schedules')
    checklist_name = models.CharField(max_length=255)
    frequency = models.CharField(max_length=50, default='Daily')
    assigned_hod = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name='assigned_checklists')

    class Meta:
        unique_together = ('department', 'checklist_name')

    def __str__(self):
        return f"{self.checklist_name} ({self.frequency}) - HOD: {self.assigned_hod.username if self.assigned_hod else 'None'}"



