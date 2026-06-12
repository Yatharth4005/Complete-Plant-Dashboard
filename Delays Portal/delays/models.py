from django.db import models
from django.conf import settings
from tpm.models import Department

class DelayUpload(models.Model):
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
    
    # Categorization
    agency = models.CharField(max_length=150, help_text="Responsible agency, e.g. 'Planned Delay', 'Mechanical'")
    sub_agency = models.CharField(max_length=150, blank=True, null=True, help_text="Sub-agency, e.g. 'Length change'")
    section = models.CharField(max_length=150, blank=True, null=True, help_text="Rolled section, e.g. 'UC 254X254'")
    
    # Asset Details
    equipment = models.CharField(max_length=200, blank=True, null=True, help_text="Equipment name or ID")
    sub_equipment = models.CharField(max_length=200, blank=True, null=True, help_text="Sub equipment name or ID")
    shift_incharge = models.CharField(max_length=150, blank=True, null=True)
    
    # Breakdown Analysis
    description = models.TextField(help_text="Detailed description of the delay/breakdown")
    why = models.TextField(blank=True, null=True, help_text="Root cause or 'why-why' analysis")
    is_locked = models.BooleanField(default=False, help_text="Locked records can only be edited by Admins")

    class Meta:
        ordering = ['-date', 'start_time']

    def __str__(self):
        return f"{self.department.code} - {self.date} - {self.agency} ({self.duration_mins} min)"


class DelayDropdownOption(models.Model):
    department = models.ForeignKey(Department, on_delete=models.CASCADE, related_name='delay_dropdown_options')
    category = models.CharField(max_length=100, help_text="e.g. 'Agency', 'Sub-Agency', 'Equipment', 'Sub-Equipment', etc.")
    value = models.CharField(max_length=255)
    parent_value = models.CharField(max_length=255, blank=True, null=True, help_text="Optional parent value, e.g. parent agency for a sub-agency")

    class Meta:
        unique_together = ('department', 'category', 'value', 'parent_value')
        ordering = ['category', 'value']

    def __str__(self):
        return f"{self.department.code} - {self.category}: {self.value}"

