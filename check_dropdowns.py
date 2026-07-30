import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'main_portal.settings')
django.setup()

from tpm.models import Department
from delays.models import DelayDropdownOption

sms3 = Department.objects.filter(code__iexact="SMS3").first() or Department.objects.filter(code__iexact="SMS-3").first()
if not sms3:
    print("SMS3 department not found")
else:
    print(f"SMS-3 dropdown options ({DelayDropdownOption.objects.filter(department=sms3).count()} total):")
    opts = DelayDropdownOption.objects.filter(department=sms3)
    for cat in opts.values_list('category', flat=True).distinct():
        cat_opts = opts.filter(category=cat)
        print(f"  Category '{cat}': {cat_opts.count()} options")
        for o in cat_opts[:10]:
            print(f"    - '{o.value}' (parent: '{o.parent_value}')")
        if cat_opts.count() > 10:
            print("    ...")
