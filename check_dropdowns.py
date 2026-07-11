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
    print(f"SMS2 department ID: {sms2.id}")
    opts = DelayDropdownOption.objects.filter(department=sms2)
    print(f"Total options for SMS2: {opts.count()}")
    for cat in opts.values_list('category', flat=True).distinct():
        cat_opts = opts.filter(category=cat)
        print(f"  Category '{cat}': {cat_opts.count()} options")
        if cat in ('Equipment', 'Action'):
            for o in cat_opts[:5]:
                print(f"    - {o.value} (parent: {o.parent_value})")
            if cat_opts.count() > 5:
                print("    ...")
