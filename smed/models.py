from django.db import models
from django.conf import settings
from tpm.models import Department

class SMEDTemplate(models.Model):
    department = models.ForeignKey(Department, on_delete=models.CASCADE, related_name='smed_templates')
    name = models.CharField(max_length=255)
    code = models.CharField(max_length=100)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['name']
        unique_together = ('department', 'code')

    def __str__(self):
        return f"{self.name} ({self.department.code})"


class SMEDSubActivityConfig(models.Model):
    template = models.ForeignKey(SMEDTemplate, on_delete=models.CASCADE, related_name='sub_activities')
    group_name = models.CharField(max_length=255, help_text="e.g. 'Pre Operational Activity of Delta & Shell Change'")
    name = models.CharField(max_length=255, help_text="e.g. 'Furnace Power Off'")
    default_planned_duration_mins = models.IntegerField(default=0)
    default_responsibility = models.CharField(max_length=150, blank=True, null=True)
    order = models.IntegerField(default=0)

    class Meta:
        ordering = ['order']

    def __str__(self):
        return f"{self.template.name} - {self.group_name} - {self.name}"


class SMEDRun(models.Model):
    template = models.ForeignKey(SMEDTemplate, on_delete=models.CASCADE, related_name='runs')
    date = models.DateField()
    total_planned_time = models.IntegerField(default=0, help_text="Total planned duration in minutes")
    total_actual_time = models.IntegerField(default=0, help_text="Total actual duration in minutes")
    status = models.CharField(max_length=50, default='In-LIMIT', choices=[('In-LIMIT', 'In-LIMIT'), ('BREACHED', 'BREACHED')])
    compliance_percentage = models.FloatField(default=0.0)
    extra_time = models.IntegerField(default=0)
    is_locked = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True)

    class Meta:
        unique_together = ('template', 'date')
        ordering = ['-date', '-created_at']

    def __str__(self):
        return f"{self.template.name} - {self.date} ({self.status})"


class SMEDRunItem(models.Model):
    run = models.ForeignKey(SMEDRun, on_delete=models.CASCADE, related_name='items')
    group_name = models.CharField(max_length=255)
    name = models.CharField(max_length=255)
    
    # Planned values
    start_time_planned = models.TimeField(null=True, blank=True)
    finish_time_planned = models.TimeField(null=True, blank=True)
    planned_duration = models.IntegerField(default=0)

    # Actual values
    start_time_actual = models.TimeField(null=True, blank=True)
    finish_time_actual = models.TimeField(null=True, blank=True)
    actual_duration = models.IntegerField(default=0)

    responsibility = models.CharField(max_length=150, blank=True, null=True)
    remark = models.TextField(blank=True, null=True)
    status = models.CharField(max_length=50, default='PENDING', choices=[('In-LIMIT', 'In-LIMIT'), ('BREACHED', 'BREACHED'), ('PENDING', 'PENDING')])
    order = models.IntegerField(default=0)

    class Meta:
        ordering = ['order']

    def __str__(self):
        return f"Run {self.run.id} - {self.name} ({self.status})"
