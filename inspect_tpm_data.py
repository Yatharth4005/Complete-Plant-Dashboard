import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'main_portal.settings')
django.setup()

from tpm.models import PillarEntry, KPIValue, Department

print("=== TPM DATABASE INSPECTION ===")
print(f"Total Department count: {Department.objects.count()}")
print(f"Total PillarEntry count: {PillarEntry.objects.count()}")
print(f"Total KPIValue count: {KPIValue.objects.count()}")

# Group by department, month, year, showing some samples
entries = PillarEntry.objects.all().order_by('year', 'month', 'department__code')
if entries.exists():
    print("\nSummary of first 20 entries:")
    for e in entries[:20]:
        val_count = e.kpi_values.count()
        # Get unique remarks from values to see if they are mock
        remarks = list(e.kpi_values.values_list('remarks', flat=True).distinct()[:3])
        print(f" - {e.year}-{e.month:02d} | Dept: {e.department.code} | Pillar: {e.pillar} | Values: {val_count} | Submitted: {e.submitted_at} | Remarks: {remarks}")
    
    if entries.count() > 20:
        print(f"... and {entries.count() - 20} more entries.")
else:
    print("\nNo PillarEntry records found.")
