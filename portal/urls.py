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
    path('dashboard/overall/', dashboard_views.overall_plant_dashboard, name='overall_plant_dashboard'),
    path('dashboard/capa/', dashboard_views.capa_reports, name='capa_reports'),
    path('department/<int:dept_id>/', department_views.dept_hub, name='dept_hub'),
    path('department/<int:dept_id>/module/<str:module_key>/enter/', department_views.enter_module, name='enter_module'),
    path('department/<int:dept_id>/coming-soon/<str:module_key>/', department_views.coming_soon, name='coming_soon'),

    # Admin access management
    path('portal-admin/access/', admin_views.manage_access, name='admin_access'),
    path('portal-admin/toggle-admin/', admin_views.toggle_admin, name='toggle_admin'),
    path('portal-admin/users/', admin_views.user_informations, name='user_informations'),
    path('portal-admin/users/create/', admin_views.admin_create_user, name='admin_create_user'),
    path('portal-admin/users/edit/<int:user_id>/', admin_views.admin_edit_user, name='admin_edit_user'),
    path('portal-admin/users/reset-password/', admin_views.admin_reset_password, name='admin_reset_password'),
    path('portal-admin/access-requests/reject/<int:req_id>/', admin_views.reject_access_request, name='reject_access_request'),

    # Profile Update
    path('profile/update/', auth_views.update_profile, name='update_profile'),

    # Password Reset
    path('forgot-password/', auth_views.forgot_password_view, name='forgot_password'),
    path('reset-password/<str:uidb64>/<str:token>/', auth_views.reset_password_view, name='reset_password'),
    path('request-access/', auth_views.request_access_view, name='request_access'),
]
