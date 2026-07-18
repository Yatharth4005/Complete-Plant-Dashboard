# tpm/urls.py

from django.urls import path
from tpm.views import auth_views, dashboard_views, department_views, governance_views
from tpm.views import pillar_views, ws_kpi_views, report_views, admin_views, kaizen_views, capa_views, jh_master_views, opl_views

urlpatterns = [
    # Auth
    path('',             auth_views.redirect_root,   name='root'),
    path('logout/',      auth_views.logout_view,      name='logout'),

    # Admin plant-wide dashboard
    path('dashboard/',   dashboard_views.plant_dashboard, name='tpm_dashboard'),

    # Department
    path('department/<int:dept_id>/',
         department_views.dept_overview, name='dept_overview'),
    path('department/<int:dept_id>/upload/',
         department_views.upload_tpm_excel, name='upload_tpm_excel'),

    # Workstation KPI
    path('department/<int:dept_id>/pillar/ws-kpi/',
         ws_kpi_views.ws_kpi_page, name='ws_kpi_page'),
    path('department/<int:dept_id>/pillar/ws-kpi/add-workstation/',
         ws_kpi_views.add_workstation, name='add_workstation'),
    path('department/<int:dept_id>/pillar/ws-kpi/save/<int:ws_id>/',
         ws_kpi_views.save_workstation, name='save_workstation'),
    path('department/<int:dept_id>/pillar/ws-kpi/delete-workstation/<int:ws_id>/',
         ws_kpi_views.delete_workstation, name='delete_workstation'),

    path('department/<int:dept_id>/pillar/ws-kpi/delete/<int:ws_id>/',
         ws_kpi_views.delete_workstation_values, name='delete_workstation_values'),

    # HTMX partial: add/delete custom workstation KPIs
    path('department/<int:dept_id>/pillar/ws-kpi/add-kpi/<int:ws_id>/',
         ws_kpi_views.add_workstation_kpi, name='add_workstation_kpi'),
    path('department/<int:dept_id>/pillar/ws-kpi/add-kpi-placeholder/',
         ws_kpi_views.add_workstation_kpi_placeholder, name='add_workstation_kpi_placeholder'),
    path('department/<int:dept_id>/pillar/ws-kpi/delete-kpi/<int:ws_id>/<int:kpi_id>/',
         ws_kpi_views.delete_workstation_kpi, name='delete_workstation_kpi'),

    # Fuguai modal & list (above standard pillar URL to prevent string parameter clash)
    path('department/<int:dept_id>/pillar/fuguai-modal/',
         pillar_views.fuguai_modal_partial, name='fuguai_modal_partial'),
    path('department/<int:dept_id>/pillar/fuguai-list/',
         pillar_views.fuguai_list_partial, name='fuguai_list_partial'),

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

    # HTMX partial: delete/clear full pillar entry
    path('department/<int:dept_id>/pillar/<str:pillar_id>/delete/',
         pillar_views.delete_pillar_entry, name='delete_pillar_entry'),

    # HTMX partial: add/delete custom KPI definitions for standard pillars
    path('department/<int:dept_id>/pillar/<str:pillar_id>/add-custom-kpi/',
         pillar_views.add_custom_kpi, name='add_custom_kpi'),
    path('department/<int:dept_id>/pillar/<str:pillar_id>/delete-custom-kpi/<int:custom_id>/',
         pillar_views.delete_custom_kpi, name='delete_custom_kpi'),

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

    # Governance
    path('governance/structure/', governance_views.tpm_governance_structure, name='tpm_governance_structure'),
    path('governance/structure/assign/', governance_views.assign_role, name='assign_role'),
    path('governance/structure/unassign/', governance_views.unassign_role, name='unassign_role'),
    path('governance/structure/save-role-description/', governance_views.save_role_description, name='save_role_description'),
    path('governance/users/',     governance_views.tpm_governance_users,     name='tpm_governance_users'),

    # Admin
    path('admin-panel/users/',       admin_views.users_list,    name='admin_users'),
    path('admin-panel/users/add/',   admin_views.add_user,      name='admin_add_user'),
    path('admin-panel/users/<int:user_id>/edit/',
         admin_views.edit_user,      name='admin_edit_user'),
    path('admin-panel/users/<int:user_id>/delete/',
         admin_views.admin_delete_user, name='admin_delete_user'),
    path('admin-panel/departments/', admin_views.departments,   name='admin_departments'),

    # HTMX: admin unlock a locked entry
    path('admin-panel/unlock-entry/<int:entry_id>/',
         admin_views.unlock_entry,   name='unlock_entry'),

    # Kaizen Sheets
    path('department/<int:dept_id>/pillar/<str:pillar_id>/kaizen/',
         kaizen_views.kaizen_list_partial, name='kaizen_list_partial'),
    path('department/<int:dept_id>/pillar/<str:pillar_id>/kaizen/upload/',
         kaizen_views.kaizen_upload_partial, name='kaizen_upload_partial'),
    path('department/<int:dept_id>/pillar/<str:pillar_id>/kaizen/save-upload/',
         kaizen_views.kaizen_save_upload, name='kaizen_save_upload'),
    path('department/<int:dept_id>/pillar/<str:pillar_id>/kaizen/new/',
         kaizen_views.kaizen_edit_partial, name='kaizen_new_partial'),
    path('department/<int:dept_id>/pillar/<str:pillar_id>/kaizen/<int:kaizen_id>/edit/',
         kaizen_views.kaizen_edit_partial, name='kaizen_edit_partial'),
    path('department/<int:dept_id>/pillar/<str:pillar_id>/kaizen/save/',
         kaizen_views.kaizen_save, name='kaizen_save'),
    path('department/<int:dept_id>/pillar/<str:pillar_id>/kaizen/save/<int:kaizen_id>/',
         kaizen_views.kaizen_save, name='kaizen_save_id'),
    path('department/<int:dept_id>/pillar/<str:pillar_id>/kaizen/<int:kaizen_id>/delete/',
         kaizen_views.kaizen_delete, name='kaizen_delete'),
    path('kaizen/<int:kaizen_id>/download/excel/',
         kaizen_views.download_excel, name='kaizen_download_excel'),
    path('kaizen/<int:kaizen_id>/download/pdf/',
         kaizen_views.download_pdf, name='kaizen_download_pdf'),

    # OPL Sheets
    path('department/<int:dept_id>/pillar/<str:pillar_id>/opl/',
         opl_views.opl_list_partial, name='opl_list_partial'),
    path('department/<int:dept_id>/pillar/<str:pillar_id>/opl/new/',
         opl_views.opl_edit_partial, name='opl_new_partial'),
    path('department/<int:dept_id>/pillar/<str:pillar_id>/opl/<int:opl_id>/edit/',
         opl_views.opl_edit_partial, name='opl_edit_partial'),
    path('department/<int:dept_id>/pillar/<str:pillar_id>/opl/save/',
         opl_views.opl_save, name='opl_save'),
    path('department/<int:dept_id>/pillar/<str:pillar_id>/opl/save/<int:opl_id>/',
         opl_views.opl_save, name='opl_save_id'),
    path('department/<int:dept_id>/pillar/<str:pillar_id>/opl/<int:opl_id>/delete/',
         opl_views.opl_delete, name='opl_delete'),

    # Plant Dashboard Overview Tab partial
    path('dashboard/overview/',
         dashboard_views.plant_overview_partial, name='plant_overview_partial'),

    # CAPA Sheets
    path('dashboard/capa/',
         capa_views.capa_list_partial, name='capa_list_partial'),
    path('dashboard/capa/new/',
         capa_views.capa_edit_partial, name='capa_new_partial'),
    path('dashboard/capa/<int:capa_id>/edit/',
         capa_views.capa_edit_partial, name='capa_edit_partial'),
    path('dashboard/capa/save/',
         capa_views.capa_save, name='capa_save'),
    path('dashboard/capa/save/<int:capa_id>/',
         capa_views.capa_save, name='capa_save_id'),
    path('dashboard/capa/<int:capa_id>/delete/',
         capa_views.capa_delete, name='capa_delete'),
    path('capa/<int:capa_id>/download/excel/',
         capa_views.download_excel, name='capa_download_excel'),
    path('capa/<int:capa_id>/download/pdf/',
         capa_views.download_pdf, name='capa_download_pdf'),

    # JH Master List & Plan
    path('department/<int:dept_id>/jh-master-list/equipments/',
         jh_master_views.jh_master_equipments, name='jh_master_equipments'),
    path('department/<int:dept_id>/jh-master-list/machines/',
         jh_master_views.jh_machine_list, name='jh_machine_list'),
    path('department/<int:dept_id>/jh-master-list/plan/',
         jh_master_views.jh_master_plan, name='jh_master_plan'),
    path('department/<int:dept_id>/jh-master-list/save/',
         jh_master_views.save_jh_machine, name='save_jh_machine'),
    path('department/<int:dept_id>/jh-master-list/save/<int:machine_id>/',
         jh_master_views.save_jh_machine, name='save_jh_machine_id'),
    path('department/<int:dept_id>/jh-master-list/delete/<int:machine_id>/',
         jh_master_views.delete_jh_machine, name='delete_jh_machine'),
    path('department/<int:dept_id>/jh-master-list/settings/',
         jh_master_views.save_jh_settings, name='save_jh_settings'),
    path('department/<int:dept_id>/jh-master-plan/save-cell/',
         jh_master_views.save_jh_plan_cell, name='save_jh_plan_cell'),
]
