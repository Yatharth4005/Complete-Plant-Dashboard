from django.db import models
from django.conf import settings

class HODKPIUpload(models.Model):
    department     = models.ForeignKey('tpm.Department', on_delete=models.CASCADE)
    uploaded_by    = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True)
    file           = models.FileField(upload_to='hod_kpi/uploads/%Y/%m/')
    month          = models.PositiveSmallIntegerField()          # 1–12
    year           = models.PositiveSmallIntegerField()
    reporting_date = models.DateField()                          # from Excel filename/content
    uploaded_at    = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('department', 'month', 'year')
        ordering = ['-year', '-month']

    def __str__(self):
        return f"Upload {self.department.name} - {self.month}/{self.year}"


class HODKPIRecord(models.Model):
    DOMAIN_CHOICES = [
        ('PRODUCTION', 'Production'),
        ('QUALITY',    'Quality'),
        ('OEE',        'OEE'),
        ('SAFETY',     'Safety'),
        ('COST',       'Cost'),
    ]

    VIEW_TYPE_CHOICES = [
        ('YTD', 'Year to Date'),
        ('MTD', 'Month to Date'),
        ('WTD', 'Week to Date'),
        ('NA',  'Not Applicable'),
    ]

    STATUS_CHOICES = [
        ('GREEN',  'Green'),
        ('YELLOW', 'Yellow'),
        ('RED',    'Red'),
    ]

    upload          = models.ForeignKey(HODKPIUpload, on_delete=models.CASCADE, related_name='records')
    domain          = models.CharField(max_length=20, choices=DOMAIN_CHOICES)
    kpi_name        = models.CharField(max_length=200)           # e.g. "Q/T Production", "OEE", "LTI"
    uom             = models.CharField(max_length=50, blank=True) # MT, %, Count, ₹/MT, Score
    view_type       = models.CharField(max_length=5, choices=VIEW_TYPE_CHOICES, default='NA')

    # Parsed values
    target          = models.FloatField(null=True, blank=True)
    actual          = models.FloatField(null=True, blank=True)
    achievement_pct = models.FloatField(null=True, blank=True)   # auto-calculated on save if not provided
    status          = models.CharField(max_length=10, choices=STATUS_CHOICES, default='GREEN')
    is_below_target = models.BooleanField(default=False)         # True if YELLOW or RED

    # HOD Feedback Fields (for below-target KPIs)
    reason_deviation   = models.TextField(blank=True, null=True)
    root_cause         = models.TextField(blank=True, null=True)
    corrective_action  = models.TextField(blank=True, null=True)
    responsible_owner  = models.CharField(max_length=150, blank=True, null=True)
    completion_date    = models.DateField(blank=True, null=True)
    remarks            = models.TextField(blank=True, null=True)

    class Meta:
        ordering = ['domain', 'kpi_name', 'view_type']

    def save(self, *args, **kwargs):
        # Auto-compute achievement_pct if target and actual are set and achievement_pct is not provided
        if self.target is not None and self.actual is not None and self.achievement_pct is None:
            if self.target == 0:
                self.achievement_pct = 100.0 if self.actual == 0 else 0.0
            else:
                if self.domain == 'COST':
                    if self.actual == 0:
                        self.achievement_pct = 100.0
                    else:
                        self.achievement_pct = round((self.target / self.actual) * 100.0, 2)
                else:
                    self.achievement_pct = round((self.actual / self.target) * 100.0, 2)
        
        # Set is_below_target automatically based on status
        self.is_below_target = self.status in ['YELLOW', 'RED']
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.upload.department.code} - {self.kpi_name} ({self.view_type}): {self.actual}/{self.target} ({self.status})"


class HODKPIDelayRecord(models.Model):
    upload            = models.ForeignKey(HODKPIUpload, on_delete=models.CASCADE, related_name='delays')
    reason            = models.CharField(max_length=300)
    department_cause  = models.CharField(max_length=150, blank=True)
    duration_mins     = models.FloatField(default=0.0)
    contribution_pct  = models.FloatField(null=True, blank=True)  # auto-calculated
    explanation       = models.TextField(blank=True)              # HOD explanation

    def __str__(self):
        return f"Delay: {self.reason} - {self.duration_mins} mins ({self.department_cause})"


class HODKPIMonthlySubmission(models.Model):
    STATUS_CHOICES = [
        ('DRAFT',     'Draft'),
        ('SUBMITTED', 'Submitted'),
    ]

    department         = models.ForeignKey('tpm.Department', on_delete=models.CASCADE)
    upload             = models.ForeignKey(HODKPIUpload, on_delete=models.CASCADE)
    submitted_by       = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True)
    month              = models.PositiveSmallIntegerField()
    year               = models.PositiveSmallIntegerField()
    status             = models.CharField(max_length=15, choices=STATUS_CHOICES, default='DRAFT')
    submitted_at       = models.DateTimeField(null=True, blank=True)

    # Monthly Summary Inputs
    achievements       = models.TextField(blank=True)
    risks              = models.TextField(blank=True)
    support_required   = models.TextField(blank=True)
    resources_required = models.TextField(blank=True)
    special_observations = models.TextField(blank=True)

    # AI Insights
    ai_summary         = models.TextField(blank=True)
    ai_recommendations = models.TextField(blank=True)

    class Meta:
        unique_together = ('department', 'month', 'year')

    def __str__(self):
        return f"Submission {self.department.name} - {self.month}/{self.year} ({self.status})"
