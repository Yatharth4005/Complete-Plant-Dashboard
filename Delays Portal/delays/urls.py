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
    path('department/<int:dept_id>/records/<int:record_id>/edit/', views.edit_record, name='edit_record'),
    path('department/<int:dept_id>/records/<int:record_id>/delete/', views.delete_record, name='delete_record'),
    path('department/<int:dept_id>/records/<int:record_id>/update-inline/', views.update_record_inline, name='update_record_inline'),
    path('department/<int:dept_id>/report/pdf/', views.download_pdf_report, name='download_pdf_report'),
    
    # Pareto Analysis dynamic drilldown APIs
    path('department/<int:dept_id>/pareto/overall/', views.pareto_overall, name='pareto_overall'),
    path('department/<int:dept_id>/pareto/agency/', views.pareto_agency, name='pareto_agency'),
    
    # Custom Option Management
    path('department/<int:dept_id>/manage-options/', views.manage_options, name='manage_options'),
]

