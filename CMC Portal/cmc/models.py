from django.db import models
from django.conf import settings
from tpm.models import Department

# ─────────────────────────────────────────────────────────
# EQUIPMENT MASTER (from PM Schedule)
# ─────────────────────────────────────────────────────────

class Equipment(models.Model):
    """
    Master list of all equipment monitored by CMC.
    Seeded from the CMC Schedule Excel file (~600+ rows).
    Admin can add/edit via Django admin.
    """
    class EquipmentClass(models.TextChoices):
        A = 'A', 'Class A (Critical)'
        B = 'B', 'Class B (Important)'

    class FrequencyType(models.TextChoices):
        WEEKLY       = 'WEEKLY',       'Weekly'
        FORTNIGHTLY  = 'FORTNIGHTLY',  'Fortnightly'
        MONTHLY      = 'MONTHLY',      'Monthly'
        QUARTERLY    = 'QUARTERLY',    'Quarterly'
        BIMONTHLY    = 'BIMONTHLY',    'Bi-Monthly'

    department         = models.ForeignKey(Department, on_delete=models.CASCADE, related_name='cmc_equipment')
    name               = models.CharField(max_length=300)  # full equipment description
    equipment_class    = models.CharField(max_length=2, choices=EquipmentClass.choices)
    sap_code_mech      = models.CharField(max_length=30, blank=True)
    sap_code_elec      = models.CharField(max_length=30, blank=True)
    asset_cost         = models.CharField(max_length=50, blank=True)   # e.g. "M-2.2L"
    production_loss    = models.CharField(max_length=50, blank=True)   # e.g. "F-3.8L"
    rating_kw          = models.FloatField(null=True, blank=True)       # motor power in kW
    frequency          = models.CharField(max_length=15, choices=FrequencyType.choices)
    scheduled_days     = models.CharField(max_length=50, blank=True)   # e.g. "1, 15" or "2, 9, 16, 23"
    category           = models.CharField(max_length=10, blank=True)   # Route category
    is_active          = models.BooleanField(default=True)
    notes              = models.TextField(blank=True)

    class Meta:
        ordering = ['department__name', 'name']

    def __str__(self):
        return f"{self.department.code} — {self.name}"


class EquipmentBearingPoint(models.Model):
    """
    Each equipment can have 1–8 named bearing points for vibration measurement.
    Pre-defined when equipment is set up; used as column headers in vibration entry.
    """
    equipment     = models.ForeignKey(Equipment, on_delete=models.CASCADE, related_name='bearing_points')
    label         = models.CharField(max_length=100)  # e.g. "DE", "NDE", "Pump Bearing", "Motor NDE"
    bearing_no    = models.CharField(max_length=50, blank=True)   # optional bearing number
    sort_order    = models.PositiveSmallIntegerField(default=0)

    class Meta:
        ordering = ['sort_order']

    def __str__(self):
        return f"{self.equipment.name} → {self.label}"


# ─────────────────────────────────────────────────────────
# PM SCHEDULE TRACKING (which equipment was checked when)
# ─────────────────────────────────────────────────────────

class PMScheduleEntry(models.Model):
    """
    Tracks whether equipment was monitored on a given date.
    One record per equipment per visit.
    Status mirrors the Excel grid: done date / NR / SD / NA / NP / blank
    """
    class VisitStatus(models.TextChoices):
        DONE            = 'DONE',   'Completed'
        NOT_RUNNING     = 'NR',     'Not Running'
        SHUTDOWN        = 'SD',     'Shutdown'
        NOT_APPLICABLE  = 'NA',     'Not Applicable'
        NOT_APPROACHABLE = 'NP',    'Not Approachable'
        PENDING         = 'PENDING', 'Pending'

    equipment     = models.ForeignKey(Equipment, on_delete=models.CASCADE, related_name='schedule_entries')
    scheduled_date = models.DateField()
    actual_date   = models.DateField(null=True, blank=True)
    status        = models.CharField(max_length=15, choices=VisitStatus.choices, default='PENDING')
    done_by       = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL)
    notes         = models.TextField(blank=True)

    class Meta:
        unique_together = ('equipment', 'scheduled_date')
        ordering = ['scheduled_date']


# ─────────────────────────────────────────────────────────
# VIBRATION MONITORING LOG
# ─────────────────────────────────────────────────────────

class VibrationLog(models.Model):
    """
    One vibration monitoring session for one piece of equipment.
    Digitizes the JSPL Form F-520 (Vibration Monitoring Log Sheet).
    """
    class InstrumentType(models.TextChoices):
        ENPAC = 'ENPAC', 'ENPAC'
        SKF   = 'SKF',   'SKF'
        CSI   = 'CSI',   'CSI'
        OTHER = 'OTHER', 'Other'

    class ReportType(models.TextChoices):
        ROUTE      = 'ROUTE',      'Route'
        ON_REQUEST = 'ON_REQUEST', 'On Request'

    class VibrationStatus(models.TextChoices):
        OK            = 'OK',         'OK'
        NOT_OK        = 'NOT_OK',     'Not OK'
        UNDER_MONITOR = 'UM',         'Under Monitoring (UM)'
        NEED_ATTENTION = 'ATTENTION', 'Need Attention'

    equipment       = models.ForeignKey(Equipment, on_delete=models.CASCADE, related_name='vibration_logs')
    date            = models.DateField()
    time            = models.TimeField(null=True, blank=True)
    instrument      = models.CharField(max_length=10, choices=InstrumentType.choices)
    report_type     = models.CharField(max_length=15, choices=ReportType.choices, default='ROUTE')
    stored_in       = models.CharField(max_length=100, blank=True)  # instrument data storage ref
    reported_through = models.CharField(max_length=100, blank=True)  # who requested
    status          = models.CharField(max_length=15, choices=VibrationStatus.choices)
    remarks         = models.TextField(blank=True)
    entered_by      = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL)
    created_at      = models.DateTimeField(auto_now_add=True)

    # Link to PM schedule visit (optional — if this was a scheduled visit)
    schedule_entry  = models.OneToOneField(
        PMScheduleEntry, null=True, blank=True,
        on_delete=models.SET_NULL, related_name='vibration_log'
    )

    class Meta:
        ordering = ['-date', 'equipment__name']


class VibrationReading(models.Model):
    """
    One row in the vibration log grid — readings for one bearing point.
    Each VibrationLog can have 1–8 VibrationReadings (one per bearing point).
    """
    vibration_log   = models.ForeignKey(VibrationLog, on_delete=models.CASCADE, related_name='readings')
    bearing_point   = models.ForeignKey(
        EquipmentBearingPoint, null=True, blank=True,
        on_delete=models.SET_NULL
    )
    bearing_label   = models.CharField(max_length=100)  # stored as text in case bearing point changes
    bearing_no      = models.CharField(max_length=50, blank=True)
    horizontal_r1   = models.FloatField(null=True, blank=True)   # mm/s or µm pk-pk
    vertical_r2     = models.FloatField(null=True, blank=True)
    axial           = models.FloatField(null=True, blank=True)
    unit            = models.CharField(max_length=20, default='mm/s')  # mm/s or µm
    iso_limit       = models.FloatField(null=True, blank=True)   # acceptable limit for this bearing
    notes           = models.CharField(max_length=200, blank=True)

    class Meta:
        ordering = ['bearing_point__sort_order']


# ─────────────────────────────────────────────────────────
# OIL TESTING LOG
# ─────────────────────────────────────────────────────────

class OilTestLog(models.Model):
    """
    One oil sample test record — digitizes the Oil Testing Register logbook.
    """
    class OilStatus(models.TextChoices):
        OK     = 'OK',     'OK'
        NOT_OK = 'NOT_OK', 'Not OK'

    equipment     = models.ForeignKey(Equipment, on_delete=models.CASCADE, related_name='oil_tests')
    date          = models.DateField()
    viscosity     = models.FloatField(null=True, blank=True)    # in cSt
    moisture      = models.CharField(max_length=50, blank=True) # e.g. "<0.1%", "<200ppm", "1500ppm"
    nas_class     = models.CharField(max_length=10, blank=True) # NAS cleanliness class, e.g. "11", ">12"
    test_no       = models.PositiveIntegerField(null=True, blank=True)
    status        = models.CharField(max_length=10, choices=OilStatus.choices)
    notification_no = models.CharField(max_length=50, blank=True)   # SAP notification, e.g. "10469680,Mt"
    login_by      = models.CharField(max_length=20, blank=True)     # initials, e.g. "PKA", "NT", "AG"
    sent_date     = models.DateField(null=True, blank=True)
    remarks       = models.TextField(blank=True)
    entered_by    = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL)
    created_at    = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-date', 'equipment__name']


# ─────────────────────────────────────────────────────────
# WDA (WEAR DEBRIS ANALYSIS) LOG
# ─────────────────────────────────────────────────────────

class WDALog(models.Model):
    """
    One WDA test record — digitizes the WDA Report logbook.
    WDA is tracked per department (not per individual equipment in some cases).
    """
    class WDAStatus(models.TextChoices):
        OK             = 'OK',         'OK'
        NEED_ATTENTION = 'ATTENTION',  'Need Attention'
        NOT_OK         = 'NOT_OK',     'Not OK'
        NA             = 'NA',         'Not Applicable'

    equipment       = models.ForeignKey(Equipment, on_delete=models.CASCADE, related_name='wda_logs')
    date            = models.DateField()
    ratio           = models.CharField(max_length=20, blank=True)  # e.g. "1:10", "1:100", "1:1000"
    dl              = models.FloatField(null=True, blank=True)      # Direct Load
    ds              = models.FloatField(null=True, blank=True)      # Direct Sediment
    wpc             = models.FloatField(null=True, blank=True)      # Wear Particle Count
    slide           = models.CharField(max_length=50, blank=True)   # Slide type used
    checked_by      = models.CharField(max_length=20, blank=True)   # initials, e.g. "AG", "NT", "PKA", "TS"
    final_status    = models.CharField(max_length=15, choices=WDAStatus.choices)
    notification_no = models.CharField(max_length=100, blank=True)  # SAP notification ref
    sent_login      = models.CharField(max_length=20, blank=True)
    sent_date       = models.DateField(null=True, blank=True)
    remarks         = models.TextField(blank=True)
    entered_by      = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL)
    created_at      = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-date', 'equipment__name']


# ─────────────────────────────────────────────────────────
# SAP NOTIFICATION TRACKER (cross-referenced by all 3 modules)
# ─────────────────────────────────────────────────────────

class SAPNotification(models.Model):
    """
    Tracks SAP maintenance notifications raised due to CMC findings.
    Can be linked to any combination of oil test, WDA, or vibration log.
    """
    class NotifStatus(models.TextChoices):
        OPEN   = 'OPEN',   'Open'
        CLOSED = 'CLOSED', 'Closed'
        PENDING = 'PENDING', 'Pending Action'

    notification_no = models.CharField(max_length=50, unique=True)
    equipment       = models.ForeignKey(Equipment, on_delete=models.CASCADE, related_name='sap_notifications')
    raised_by       = models.CharField(max_length=20)  # initials
    raised_date     = models.DateField()
    description     = models.TextField(blank=True)
    status          = models.CharField(max_length=10, choices=NotifStatus.choices, default='OPEN')
    closed_date     = models.DateField(null=True, blank=True)
    action_taken    = models.TextField(blank=True)

    # FK links to source records
    vibration_log   = models.ForeignKey(VibrationLog, null=True, blank=True, on_delete=models.SET_NULL)
    oil_test        = models.ForeignKey(OilTestLog, null=True, blank=True, on_delete=models.SET_NULL)
    wda_log         = models.ForeignKey(WDALog, null=True, blank=True, on_delete=models.SET_NULL)
