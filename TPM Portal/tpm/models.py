from django.db import models
from django.contrib.auth.models import AbstractUser

class Department(models.Model):
    name = models.CharField(max_length=100, unique=True)   # e.g., "Blast Furnace-1"
    code = models.CharField(max_length=10,  unique=True)   # e.g., "BF1"

    def __str__(self):
        return self.name


class User(AbstractUser):
    """Custom user: standard Django auth + department link"""
    ROLE_ADMIN = 'ADMIN'
    ROLE_USER  = 'USER'
    ROLE_CHOICES = [
        (ROLE_ADMIN, 'Admin'),
        (ROLE_USER, 'Department User')
    ]

    role = models.CharField(max_length=10, choices=ROLE_CHOICES, default=ROLE_USER)
    department = models.ForeignKey(
        Department, null=True, blank=True,
        on_delete=models.SET_NULL, related_name='users'
    )
    is_plant_admin = models.BooleanField(default=False)
    phone = models.CharField(max_length=20, blank=True)
    photo = models.ImageField(upload_to='profile_photos/', blank=True, null=True)
    employee_id = models.CharField(max_length=30, blank=True)
    designation = models.CharField(max_length=100, blank=True)
    last_active = models.DateTimeField(null=True, blank=True)

    def is_admin(self):
        return self.role == self.ROLE_ADMIN or self.is_superuser or self.is_plant_admin

    def get_display_name(self):
        full_name = self.get_full_name().strip()
        if full_name:
            return full_name
        return self.email.split('@')[0] if self.email else self.username.split('@')[0]


class PillarEntry(models.Model):
    """One submission per department x pillar x month x year"""

    class PillarType(models.TextChoices):
        KK    = 'KK',    'Kobetsu Kaizen'
        JH    = 'JH',    'Jishu Hozen'
        PM    = 'PM',    'Planned Maintenance'
        QM    = 'QM',    'Quality Maintenance'
        ET    = 'ET',    'Education & Training'
        DM    = 'DM',    'Design & Management'
        SHE   = 'SHE',   'Safety Health Environment'
        OTPM  = 'OTPM',  'Office TPM'

    class DataEntryType(models.TextChoices):
        MONTHLY = 'MONTHLY', 'Monthly'
        WEEKLY  = 'WEEKLY',  'Weekly'

    department = models.ForeignKey(Department, on_delete=models.CASCADE, related_name='pillar_entries')
    pillar = models.CharField(max_length=10, choices=PillarType.choices)
    month = models.PositiveSmallIntegerField()   # 1-12
    year = models.PositiveSmallIntegerField()
    data_entry_type = models.CharField(max_length=10, choices=DataEntryType.choices, default='MONTHLY')
    submitted_at = models.DateTimeField(null=True, blank=True)
    submitted_by = models.ForeignKey(User, null=True, blank=True, on_delete=models.SET_NULL)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ('department', 'pillar', 'month', 'year')
        verbose_name_plural = "Pillar Entries"

    def is_locked(self):
        return self.submitted_at is not None

    def __str__(self):
        return f"{self.department.code} - {self.pillar} - {self.month}/{self.year}"


class KPIValue(models.Model):
    """One row inside a PillarEntry - one KPI value for one period"""
    pillar_entry = models.ForeignKey(PillarEntry, on_delete=models.CASCADE, related_name='kpi_values')
    sl_no = models.CharField(max_length=10)   # "1", "1A", "8B" etc.
    kpi_name = models.CharField(max_length=300)
    uom = models.CharField(max_length=50, blank=True)
    benchmark = models.FloatField(null=True, blank=True)
    target = models.FloatField(null=True, blank=True)
    actual = models.FloatField(null=True, blank=True)
    availability = models.FloatField(null=True, blank=True)  # KK row 1 PRODUCTION only
    performance = models.FloatField(null=True, blank=True)   # KK row 1 PRODUCTION only
    quality = models.FloatField(null=True, blank=True)       # KK row 1 PRODUCTION only
    remarks = models.TextField(blank=True)

    class Meta:
        unique_together = ('pillar_entry', 'sl_no')
        verbose_name = "KPI Value"
        verbose_name_plural = "KPI Values"

    def __str__(self):
        return f"{self.pillar_entry} - Sl {self.sl_no}: {self.actual}"


# --- Workstation KPI (9th Pillar - different schema) ---

class Workstation(models.Model):
    department = models.ForeignKey(Department, on_delete=models.CASCADE, related_name='workstations')
    name = models.CharField(max_length=100)   # e.g., "Furnace Area", "Mill Area"
    leader = models.CharField(max_length=100)
    inception_date = models.DateField(null=True, blank=True)

    def __str__(self):
        return f"{self.department.code} - {self.name}"


class WorkstationKPI(models.Model):
    class GoodnessIndicator(models.TextChoices):
        HIGHER = 'HIGHER', 'Higher is Better ↑'
        LOWER  = 'LOWER',  'Lower is Better ↓'

    workstation = models.ForeignKey(Workstation, on_delete=models.CASCADE, related_name='kpis')
    kpi_name = models.CharField(max_length=200)
    uom = models.CharField(max_length=50)
    goodness_indicator = models.CharField(max_length=10, choices=GoodnessIndicator.choices, default='HIGHER')
    baseline = models.FloatField(null=True, blank=True)
    commitment = models.FloatField(null=True, blank=True)

    def __str__(self):
        return f"{self.workstation.name} - {self.kpi_name}"


class WorkstationValue(models.Model):
    workstation_kpi = models.ForeignKey(WorkstationKPI, on_delete=models.CASCADE, related_name='monthly_values')
    month = models.PositiveSmallIntegerField()
    year = models.PositiveSmallIntegerField()
    actual = models.FloatField(null=True, blank=True)
    remarks = models.TextField(blank=True)

    class Meta:
        unique_together = ('workstation_kpi', 'month', 'year')

    def __str__(self):
        return f"{self.workstation_kpi.kpi_name} - {self.month}/{self.year}: {self.actual}"
