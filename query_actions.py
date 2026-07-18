import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'main_portal.settings')
django.setup()

from tpm.models import KaizenSheet

sheets = KaizenSheet.objects.all().order_by('id')
print(f"Total Kaizen sheets in DB: {sheets.count()}")
for s in sheets:
    print(f"ID: {s.id} | Dept: {s.department.name} | No: {s.kaizen_no} | Theme: {s.theme} | Created: {s.created_at}")
