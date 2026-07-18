import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'main_portal.settings')
django.setup()

from tpm.models import KaizenSheet

sheets = KaizenSheet.objects.all().order_by('id')
seen = set()
duplicates_deleted = 0

for s in sheets:
    # Build unique key to identify exact duplicates
    key = (s.department_id, s.pillar, s.kaizen_no, s.theme, s.loss_name, s.area_equipment, s.circle_name)
    if key in seen:
        print(f"Deleting duplicate Kaizen ID: {s.id} | Dept: {s.department.name} | No: {s.kaizen_no} | Theme: {s.theme}")
        s.delete()
        duplicates_deleted += 1
    else:
        seen.add(key)

print(f"\nCleanup complete. Total duplicate Kaizen records deleted: {duplicates_deleted}")
