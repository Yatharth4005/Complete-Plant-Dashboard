import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'main_portal.settings')
django.setup()

from django.contrib.auth import authenticate, get_user_model
UserModel = get_user_model()

print("=== DIAGNOSTICS ===")
print("User count in DB:", UserModel.objects.count())

for user in UserModel.objects.all():
    print(f"\nUser: username={user.username}, email={user.email}, is_active={user.is_active}, role={getattr(user, 'role', 'N/A')}")
    
    # Check direct check_password
    for pwd in ['Dept@1234', 'Admin@1234']:
        match = user.check_password(pwd)
        print(f"  Direct check_password('{pwd}'): {match}")
        
    # Check Django authenticate
    for pwd in ['Dept@1234', 'Admin@1234']:
        res = authenticate(username=user.email, password=pwd)
        print(f"  django.contrib.auth.authenticate(username='{user.email}', password='{pwd}'): {res}")
