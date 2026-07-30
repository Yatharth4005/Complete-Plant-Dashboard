import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'main_portal.settings')
django.setup()

from tpm.models import Department
from delays.models import DelayDropdownOption

sms2 = Department.objects.filter(code__iexact="SMS2").first()
if not sms2:
    print("SMS2 department not found")
else:
    print(f"SMS2 department: {sms2.name} (ID: {sms2.id})")
    opts = DelayDropdownOption.objects.filter(department=sms2)
    print(f"Total options: {opts.count()}")
    
    # 1. Print all Sub-Agency options
    sub_agencies = opts.filter(category='Sub-Agency')
    print(f"\nSub-Agencies ({sub_agencies.count()} found):")
    for sa in sub_agencies:
        print(f"  - {sa.value}")
        
    # 2. Print all Equipment options
    equipments = opts.filter(category='Equipment')
    print(f"\nEquipments ({equipments.count()} found):")
    for eq in equipments:
        print(f"  - Value: '{eq.value}', Parent: '{eq.parent_value}'")
        
    # 3. Check for Crane and Maintenance options
    crane_opts = opts.filter(parent_value='Crane')
    print(f"\nOptions with parent_value='Crane' ({crane_opts.count()} found):")
    for opt in crane_opts[:10]:
        print(f"  - {opt.category}: '{opt.value}'")
    if crane_opts.count() > 10:
        print("  ...")
        
    maint_opts = opts.filter(parent_value='Maintenance')
    print(f"\nOptions with parent_value='Maintenance' ({maint_opts.count()} found):")
    for opt in maint_opts[:10]:
        print(f"  - {opt.category}: '{opt.value}'")
    if maint_opts.count() > 10:
        print("  ...")
