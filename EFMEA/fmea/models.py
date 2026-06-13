import uuid
from django.db import models
from django.conf import settings
from tpm.models import Department

class FMEAExcelUpload(models.Model):
    department = models.ForeignKey(Department, on_delete=models.CASCADE, related_name='excel_uploads')
    filename = models.CharField(max_length=255)
    sheet_date = models.DateField(null=True, blank=True)
    uploaded_at = models.DateTimeField(auto_now_add=True)
    uploaded_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True)
    is_manual = models.BooleanField(default=False)
    
    key_contact = models.CharField(max_length=255, default="", blank=True)
    core_team = models.TextField(default="", blank=True)
    objective = models.TextField(default="", blank=True)
    ref_no = models.CharField(max_length=100, default="", blank=True)

    class Meta:
        ordering = ['-uploaded_at']

    def __str__(self):
        date_str = self.sheet_date.strftime('%Y-%m-%d') if self.sheet_date else "No Date"
        return f"{self.filename} ({date_str})"


class FMEARecord(models.Model):
    # Core relationship
    department = models.ForeignKey(Department, on_delete=models.CASCADE, related_name='fmea_records')
    excel_upload = models.ForeignKey(FMEAExcelUpload, on_delete=models.CASCADE, null=True, blank=True, related_name='records')
    
    # Risk identifier
    risk_id = models.CharField(max_length=20, unique=True, editable=False)
    
    # Metadata fields
    identification_date = models.DateField(null=True, blank=True)
    risk_owner = models.CharField(max_length=100, default="", blank=True)
    target_date = models.DateField(null=True, blank=True)
    as_on_date = models.DateField(null=True, blank=True)
    status_remarks = models.TextField(default="", blank=True)
    
    # FMEA Grid columns
    sn = models.CharField(max_length=50, default="", blank=True)
    main_equipment = models.CharField(max_length=150, default="", blank=True)
    main_equipment_function = models.TextField(default="", blank=True)
    functional_failure = models.TextField(default="", blank=True)
    sub_equipment = models.CharField(max_length=150, default="", blank=True)
    component = models.CharField(max_length=150, default="", blank=True)
    component_function = models.TextField(default="", blank=True)
    potential_failure_mode = models.TextField(default="", blank=True)
    potential_effects = models.TextField(default="", blank=True) # maps to Event Consequences
    
    # RPN inputs
    severity = models.IntegerField(default=1)
    potential_causes = models.TextField(default="", blank=True)
    occurrence = models.IntegerField(default=1)
    current_controls = models.TextField(default="", blank=True)
    
    # Actions & Detection
    recommended_actions = models.TextField(default="", blank=True)
    detection = models.IntegerField(default=1)
    rpn = models.IntegerField(default=1) # severity * occurrence * detection
    
    contingency_plan = models.TextField(default="", blank=True)
    status = models.CharField(max_length=50, default="Not Started", blank=True)
    
    # Action results (Severity/Occurrence/Detection after corrective actions)
    action_taken = models.TextField(default="", blank=True)
    action_severity = models.IntegerField(null=True, blank=True)
    action_occurrence = models.IntegerField(null=True, blank=True)
    action_detection = models.IntegerField(null=True, blank=True)
    action_rpn = models.IntegerField(null=True, blank=True)
    
    # Quarterly Mitigation Action Text lists (stored as JSON arrays or simple multiline lists)
    mitigation_q1 = models.TextField(default="[]", blank=True)
    mitigation_q2 = models.TextField(default="[]", blank=True)
    mitigation_q3 = models.TextField(default="[]", blank=True)
    mitigation_q4 = models.TextField(default="[]", blank=True)
    
    mitigation_q1_target = models.DateField(null=True, blank=True)
    mitigation_q2_target = models.DateField(null=True, blank=True)
    mitigation_q3_target = models.DateField(null=True, blank=True)
    mitigation_q4_target = models.DateField(null=True, blank=True)
    
    mitigation_q1_status = models.CharField(max_length=30, default="Not Started", blank=True)
    mitigation_q2_status = models.CharField(max_length=30, default="Not Started", blank=True)
    mitigation_q3_status = models.CharField(max_length=30, default="Not Started", blank=True)
    mitigation_q4_status = models.CharField(max_length=30, default="Not Started", blank=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['sn', 'id']

    def save(self, *args, **kwargs):
        # Generate risk_id if not present
        if not self.risk_id:
            self.risk_id = f"EFMEA-{uuid.uuid4().hex[:8].upper()}"
            
        # Dynamically calculate RPN
        self.rpn = int(self.severity or 1) * int(self.occurrence or 1) * int(self.detection or 1)
        
        # Calculate Action RPN if all are set
        if self.action_severity is not None and self.action_occurrence is not None and self.action_detection is not None:
            self.action_rpn = int(self.action_severity) * int(self.action_occurrence) * int(self.action_detection)
        else:
            self.action_rpn = None
            
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.risk_id} - {self.main_equipment} ({self.department.code})"


class FMEAAuditLog(models.Model):
    record = models.ForeignKey(FMEARecord, on_delete=models.CASCADE, related_name='audit_logs')
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True)
    action = models.CharField(max_length=100) # e.g. 'CREATED', 'UPDATED', 'MITIGATED', 'EXCEL_UPLOADED'
    details = models.TextField(blank=True, default="")
    timestamp = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-timestamp']


class FMEACriticalSpare(models.Model):
    excel_upload = models.ForeignKey(FMEAExcelUpload, on_delete=models.CASCADE, null=True, blank=True, related_name='critical_spares')
    department = models.ForeignKey(Department, on_delete=models.CASCADE, related_name='critical_spares')
    spare_description = models.CharField(max_length=255, default="", blank=True)
    qty = models.CharField(max_length=50, default="", blank=True)
    remarks_1 = models.TextField(default="", blank=True)
    lead_time = models.CharField(max_length=100, default="", blank=True)
    remarks_2 = models.TextField(default="", blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['id']
