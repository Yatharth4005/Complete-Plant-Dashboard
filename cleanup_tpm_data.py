import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'main_portal.settings')
django.setup()

from tpm.models import PillarEntry, KPIValue

print("=== TPM DATA CLEANUP ===")

# Find all entries with demo/mock remarks
demo_remarks_keywords = ['mock', 'seeded', 'Calculated from subcomponents']

all_entries = PillarEntry.objects.all()
demo_entry_ids = set()

for entry in all_entries:
    # Check if any KPI values under this entry match mock remarks
    has_demo_vals = entry.kpi_values.filter(
        remarks__icontains='mock'
    ).exists() or entry.kpi_values.filter(
        remarks__icontains='seeded'
    ).exists() or entry.kpi_values.filter(
        remarks__icontains='Calculated from subcomponents'
    ).exists()
    
    if has_demo_vals:
        demo_entry_ids.add(entry.id)

real_entries = all_entries.exclude(id__in=demo_entry_ids)
demo_entries = all_entries.filter(id__in=demo_entry_ids)

print(f"Total PillarEntry records found: {all_entries.count()}")
print(f"Demo entries to delete: {demo_entries.count()}")
print(f"Real entries to keep: {real_entries.count()}")

if real_entries.exists():
    print("\nReal entries that will be KEPT:")
    for re in real_entries[:20]:
        print(f" - {re.year}-{re.month:02d} | Dept: {re.department.code} | Pillar: {re.pillar} | Submitted By: {re.submitted_by}")
    if real_entries.count() > 20:
        print(f"... and {real_entries.count() - 20} more.")
else:
    print("\nNo real entries found (all entries appear to be demo data).")

# Perform deletion
deleted_count, _ = demo_entries.delete()
print(f"\n[SUCCESS] Deleted {deleted_count} database objects (PillarEntries and cascading KPIValues).")
