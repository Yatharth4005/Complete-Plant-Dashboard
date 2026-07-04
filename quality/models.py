from django.db import models
from django.conf import settings
from tpm.models import Department

class QualityEntry(models.Model):
    STATUS_DRAFT = 'DRAFT'
    STATUS_SUBMITTED = 'SUBMITTED'
    STATUS_CHOICES = [
        (STATUS_DRAFT, 'Draft'),
        (STATUS_SUBMITTED, 'Submitted'),
    ]

    # Header metadata
    department = models.ForeignKey(Department, on_delete=models.CASCADE, related_name='quality_entries')
    entry_no = models.CharField(max_length=50, unique=True) # e.g. Q-000001
    date = models.DateField()
    shift = models.CharField(max_length=5, choices=[('A', 'A'), ('B', 'B'), ('C', 'C')], blank=True, null=True)
    status = models.CharField(max_length=15, choices=STATUS_CHOICES, default=STATUS_DRAFT)
    
    # Heat & Product Details
    caster_type = models.CharField(max_length=100, blank=True, null=True)
    product_type = models.CharField(max_length=100, blank=True, null=True)
    section_type = models.CharField(max_length=100, blank=True, null=True)
    grade = models.CharField(max_length=100, blank=True, null=True)
    heat_number = models.CharField(max_length=100, blank=True, null=True)
    inspected_qty = models.FloatField(default=0.0)
    ftr_qty = models.FloatField(default=0.0)
    
    # Defect Details
    defect_type = models.CharField(max_length=100, blank=True, null=True)
    defect_category = models.CharField(max_length=100, blank=True, null=True)
    defect_severity = models.CharField(max_length=100, blank=True, null=True)
    defect_qty = models.FloatField(default=0.0)
    rejected_qty = models.FloatField(default=0.0)
    reason_of_defect = models.TextField(blank=True, null=True)
    
    # Rework Details
    rework_type = models.CharField(max_length=100, blank=True, null=True)
    rework_qty = models.FloatField(default=0.0)
    reason_for_rework = models.TextField(blank=True, null=True)
    
    # Diversion Details
    diversion_type = models.CharField(max_length=100, blank=True, null=True)
    diversion_qty = models.FloatField(default=0.0)
    reason_for_diversion = models.TextField(blank=True, null=True)
    
    # Mix Grade Details
    mix_grade = models.CharField(max_length=100, blank=True, null=True)
    mix_qty = models.FloatField(default=0.0)
    reason_for_mix_grade = models.TextField(blank=True, null=True)
    
    # POR Details
    por_type = models.CharField(max_length=100, blank=True, null=True)
    por_qty = models.FloatField(default=0.0)
    por_doc_ref = models.CharField(max_length=100, blank=True, null=True)
    por_remarks = models.TextField(blank=True, null=True)
    
    # FTR Details
    accepted_qty = models.FloatField(default=0.0)
    ftr_percent = models.FloatField(default=0.0)
    inspection_status = models.CharField(max_length=50, blank=True, null=True)
    
    # PSFS Details
    psfs_type = models.CharField(max_length=100, blank=True, null=True)
    psfs_qty = models.FloatField(default=0.0)
    reason_for_psfs = models.TextField(blank=True, null=True)
    
    remarks = models.TextField(blank=True, null=True)
    attachment = models.FileField(upload_to='quality_attachments/', blank=True, null=True)
    
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-date', '-created_at']

    def __str__(self):
        return f"{self.entry_no} - {self.department.code} - {self.date}"

class NonFTRReason(models.Model):
    quality_entry = models.ForeignKey(QualityEntry, on_delete=models.CASCADE, related_name='non_ftr_reasons')
    reason = models.CharField(max_length=255)
    qty = models.FloatField(default=0.0)

    def __str__(self):
        return f"{self.reason}: {self.qty} T"
