import os
import django
from django.test import Client
from django.contrib.auth import get_user_model

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'main_portal.settings')
django.setup()

User = get_user_model()
target_user = User.objects.filter(email='lalit.goyal@jindalsteel.in').first()

c = Client()
c.force_login(target_user)

response = c.get('/fmea/department/5/report/', follow=True)
html = response.content.decode('utf-8')

# Find the severity td
import re
severity_matches = re.findall(r'<td style="text-align: center; font-size: 0\.85rem; font-weight: bold; vertical-align: middle;">(.*?)</td>', html, re.DOTALL)
if severity_matches:
    print("Found severity cells:")
    for idx, match in enumerate(severity_matches[:3]):
        print(f"\nCell {idx+1}:")
        print(match.strip())
else:
    print("Could not find severity cells in HTML!")
