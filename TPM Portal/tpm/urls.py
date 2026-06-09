# tpm/urls.py

from django.urls import path
from tpm.views import auth_views, dashboard_views, department_views
from tpm.views import pillar_views, ws_kpi_views, report_views, admin_views

urlpatterns = [
    # Auth
    path('',             auth_views.redirect_root,   name='root'),
    path('logout/',      auth_views.logout_view,      name='logout'),

    # Admin plant-wide dashboard
    path('dashboard/',   dashboard_views.plant_dashboard, name='tpm_dashboard'),

    # Department
    path('department/<int:dept_id>/',
         department_views.dept_overview, name='dept_overview'),

    # Workstation KPI
    path('department/<int:dept_id>/pillar/ws-kpi/',
         ws_kpi_views.ws_kpi_page, name='ws_kpi_page'),

    path('department/<int:dept_id>/pillar/ws-kpi/save/<int:ws_id>/',
         ws_kpi_views.save_workstation, name='save_workstation'),

    # Pillar (standard 8)
    path('department/<int:dept_id>/pillar/<str:pillar_id>/',
         pillar_views.pillar_page, name='pillar_page'),

    # HTMX partial: load/refresh KPI table (swaps #kpi-table-container)
    path('department/<int:dept_id>/pillar/<str:pillar_id>/table/',
         pillar_views.kpi_table_partial, name='kpi_table_partial'),

    # HTMX partial: save a single KPI row inline
    path('department/<int:dept_id>/pillar/<str:pillar_id>/save-row/',
         pillar_views.save_kpi_row, name='save_kpi_row'),

    # HTMX partial: submit full pillar entry (lock it)
    path('department/<int:dept_id>/pillar/<str:pillar_id>/submit/',
         pillar_views.submit_pillar_entry, name='submit_pillar_entry'),

    # HTMX partial: analytics tab (swaps #analytics-container)
    path('department/<int:dept_id>/pillar/<str:pillar_id>/analytics/',
         pillar_views.analytics_partial, name='analytics_partial'),

    # Reports
    path('department/<int:dept_id>/report/',
         report_views.report_page, name='report_page'),
    path('department/<int:dept_id>/report/pdf/',
         report_views.export_pdf, name='export_pdf'),
    path('department/<int:dept_id>/report/excel/',
         report_views.export_excel, name='export_excel'),

    # Admin
    path('admin-panel/users/',       admin_views.users_list,    name='admin_users'),
    path('admin-panel/users/add/',   admin_views.add_user,      name='admin_add_user'),
    path('admin-panel/users/<int:user_id>/edit/',
         admin_views.edit_user,      name='admin_edit_user'),
    path('admin-panel/departments/', admin_views.departments,   name='admin_departments'),

    # HTMX: admin unlock a locked entry
    path('admin-panel/unlock-entry/<int:entry_id>/',
         admin_views.unlock_entry,   name='unlock_entry'),
]
