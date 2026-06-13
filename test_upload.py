import os
import django
from django.test import Client
from django.core.files.uploadedfile import SimpleUploadedFile
from django.contrib.auth import get_user_model

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'main_portal.settings')
django.setup()

from fmea.models import FMEARecord

# 1. Clean up first
FMEARecord.objects.filter(department_id=5).delete()

User = get_user_model()
target_user = User.objects.filter(email='lalit.goyal@jindalsteel.in').first() or User.objects.first()

c = Client()
c.force_login(target_user)

# 2. Load the excel file
file_path = r"e:\Jindal Steel Projects\DEPARTMENTS DASHBOARD\EFMEA\fmea\Rail Mill Raigarh - EFMEA and Action Plan.xlsx"
if not os.path.exists(file_path):
    print(f"File not found at: {file_path}")
    exit(1)

with open(file_path, 'rb') as f:
    excel_file = SimpleUploadedFile("Rail_Mill_EFMEA.xlsx", f.read(), content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")

# 3. POST upload-excel
response = c.post('/fmea/department/5/upload-excel/', {'excel_file': excel_file}, follow=True)
print(f"Upload response status: {response.status_code}")

# 4. Check DB
records = FMEARecord.objects.filter(department_id=5).order_by('id')
print(f"\nNumber of records created: {records.count()}")
for idx, r in enumerate(records):
    print(f"Record {idx+1}: SN={r.sn} | Equip={r.main_equipment} | Component={r.component} | Sev={r.severity} | Occ={r.occurrence} | Det={r.detection} | RPN={r.rpn}")
