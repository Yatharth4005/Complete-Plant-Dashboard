from django.urls import path
from delays import views

app_name = 'delays'

urlpatterns = [
    # Delays Main Dashboard & Analytics
    path('department/<int:dept_id>/', views.dept_overview, name='dept_overview'),
    
    # Excel Upload & Management
    path('department/<int:dept_id>/upload/', views.upload_file, name='upload_file'),
    path('department/<int:dept_id>/upload/<int:upload_id>/delete/', views.delete_upload, name='delete_upload'),
    
    # Log Table Search/Filter
    path('department/<int:dept_id>/records/', views.records_table, name='records_table'),
    
    # Manual Delay Entries
    path('department/<int:dept_id>/records/new/', views.new_record, name='new_record'),
    path('department/<int:dept_id>/records/lock/', views.lock_records, name='lock_records'),
    path('department/<int:dept_id>/records/<int:record_id>/edit/', views.edit_record, name='edit_record'),
    path('department/<int:dept_id>/records/<int:record_id>/delete/', views.delete_record, name='delete_record'),
    path('department/<int:dept_id>/records/<int:record_id>/update-inline/', views.update_record_inline, name='update_record_inline'),
    path('department/<int:dept_id>/report/pdf/', views.download_pdf_report, name='download_pdf_report'),
    path('department/<int:dept_id>/notifications/mark-all-read/', views.mark_all_read, name='mark_all_read'),
    path('department/<int:dept_id>/notifications/<int:notification_id>/mark-read/', views.mark_read, name='mark_read'),
    path('department/<int:dept_id>/notifications/<int:notification_id>/submit-reason/', views.submit_reason, name='submit_reason'),

    
    # Pareto Analysis dynamic drilldown APIs
    path('department/<int:dept_id>/pareto/overall/', views.pareto_overall, name='pareto_overall'),
    path('department/<int:dept_id>/pareto/agency/', views.pareto_agency, name='pareto_agency'),
    path('department/<int:dept_id>/mttr-mtbf/overall/', views.mttr_mtbf_overall, name='mttr_mtbf_overall'),
    
    # Custom Option Management
    path('department/<int:dept_id>/manage-options/', views.manage_options, name='manage_options'),
    path('department/<int:dept_id>/checklist/new/', views.create_checklist, name='create_checklist'),
    path('department/<int:dept_id>/checklist/<int:item_id>/delete/', views.delete_checklist_item, name='delete_checklist_item'),
    path('department/<int:dept_id>/checklist/<int:checklist_id>/reschedule/', views.reschedule_checklist, name='reschedule_checklist'),
    path('department/<int:dept_id>/checklist/schedule/update/', views.update_checklist_schedule, name='update_checklist_schedule'),
    path('department/<int:dept_id>/checklist/schedule/<int:schedule_id>/update-incharge/', views.update_checklist_schedule_incharge, name='update_checklist_schedule_incharge'),
    path('department/<int:dept_id>/checklist/<int:checklist_id>/edit/', views.edit_checklist, name='edit_checklist'),
]


