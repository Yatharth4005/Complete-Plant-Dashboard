from django.db import models
from tpm.models import Department, User, CAPAReport

class Incident(models.Model):
    SEVERITY_CHOICES = [
        ('LTI', 'Lost Time Injury (LTI)'),
        ('RWC', 'Restricted Work Case (RWC)'),
        ('MTC', 'Medical Treatment Case (MTC)'),
        ('FA', 'First Aid (FA)'),
        ('NM', 'Near Miss (NM)'),
    ]
    
    UNSAFE_CHOICES = [
        ('UA', 'Unsafe Act (UA)'),
        ('UC', 'Unsafe Condition (UC)'),
        ('NONE', 'None (Actual Incident)'),
    ]
    
    CATEGORY_CHOICES = [
        ('Material Handling', 'Material Handling'),
        ('Slip/Trip/Fall', 'Slip/Trip/Fall'),
        ('PPE Violation', 'PPE Violation'),
        ('Equipment Interaction', 'Equipment Interaction'),
        ('Fire Hazard', 'Fire Hazard'),
        ('Other', 'Other'),
    ]
    
    STATUS_CHOICES = [
        ('Pending', 'Pending Review'),
        ('Investigation', 'Under Investigation'),
        ('Closed', 'Closed'),
    ]

    department = models.ForeignKey(Department, on_delete=models.CASCADE, related_name='safety_incidents')
    date_incident = models.DateField()
    severity = models.CharField(max_length=10, choices=SEVERITY_CHOICES, default='FA')
    unsafe_type = models.CharField(max_length=10, choices=UNSAFE_CHOICES, default='NONE')
    category = models.CharField(max_length=50, choices=CATEGORY_CHOICES, default='Other')
    description = models.TextField()
    image = models.ImageField(upload_to='incidents/', null=True, blank=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='Pending')
    
    # Review / Investigation fields
    investigation_findings = models.TextField(blank=True, default='')
    capa_report = models.ForeignKey(CAPAReport, on_delete=models.SET_NULL, null=True, blank=True, related_name='linked_incidents')
    closure_date = models.DateField(null=True, blank=True)
    
    reported_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, related_name='reported_incidents')
    reviewed_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='reviewed_incidents')
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-date_incident', '-created_at']

    def __str__(self):
        return f"{self.severity} at {self.department.code} on {self.date_incident}"
