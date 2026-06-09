from django.urls import path
from portal.views import auth_views, dashboard_views, department_views, admin_views

app_name = 'portal'

urlpatterns = [
    # Auth
    path('', auth_views.root_redirect, name='root'),
    path('login/', auth_views.login_view, name='login'),
    path('logout/', auth_views.logout_view, name='logout'),

    # Dashboards & Hubs
    path('dashboard/', dashboard_views.plant_dashboard, name='plant_dashboard'),
    path('department/<int:dept_id>/', department_views.dept_hub, name='dept_hub'),
    path('department/<int:dept_id>/module/<str:module_key>/enter/', department_views.enter_module, name='enter_module'),
    path('department/<int:dept_id>/coming-soon/<str:module_key>/', department_views.coming_soon, name='coming_soon'),

    # Admin access management
    path('admin/access/', admin_views.manage_access, name='admin_access'),
    path('admin/toggle-admin/', admin_views.toggle_admin, name='toggle_admin'),
]
