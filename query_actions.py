import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'main_portal.settings')
django.setup()

from tpm.models import Department
from delays.models import DelayDropdownOption

sms2 = Department.objects.filter(code__iexact="SMS2").first()
opts = DelayDropdownOption.objects.filter(department=sms2, category='Action')
print(f"Total Action options: {opts.count()}")
for o in opts:
    print(f"Value: '{o.value}' | Parent: '{o.parent_value}'")
