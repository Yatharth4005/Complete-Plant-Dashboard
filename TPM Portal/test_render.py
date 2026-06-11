import os
import django

def main():
    os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'jspl_tpm.settings')
    django.setup()
    
    from django.test import RequestFactory
    from tpm.views.kaizen_views import kaizen_edit_partial
    from django.contrib.auth import get_user_model
    
    rf = RequestFactory()
    req = rf.get('/tpm/department/2/pillar/KK/kaizen/new/')
    
    User = get_user_model()
    u = User.objects.first()
    if not u:
        print("No user found in database, creating a dummy user...")
        u = User.objects.create_user(username='dummy_test_user', password='password123')
        
    req.user = u
    
    try:
        # We need to bypass the @dept_access_required decorator if it checks department linkage
        # Let's call the inner view function directly if decorators get in the way.
        # But let's try the decorated view function first
        resp = kaizen_edit_partial(req, dept_id=2, pillar_id='KK')
        print(f"RENDERED_SUCCESSFULLY, status_code: {resp.status_code}")
    except Exception as e:
        import traceback
        print("\n--- TRACEBACK ---")
        traceback.print_exc()

if __name__ == '__main__':
    main()
