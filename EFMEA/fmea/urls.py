from django.urls import path
from . import views

app_name = 'fmea'

urlpatterns = [
    path('department/<int:dept_id>/', views.fmea_dashboard, name='dashboard'),
    path('department/<int:dept_id>/identification/', views.risk_identification, name='identification'),
    path('department/<int:dept_id>/register/', views.risk_register, name='register'),
    path('department/<int:dept_id>/report/', views.risk_report, name='report'),
    path('department/<int:dept_id>/history/', views.risk_history, name='history'),
    path('department/<int:dept_id>/checklist/', views.health_checklist, name='checklist'),
    path('department/<int:dept_id>/monsoon/', views.monsoon_report, name='monsoon'),
    
    # Action endpoints
    path('department/<int:dept_id>/save-risk/', views.save_risk, name='save_risk'),
    path('department/<int:dept_id>/save-risk/<int:record_id>/', views.save_risk, name='save_risk_id'),
    path('department/<int:dept_id>/save-mitigation/<int:record_id>/', views.save_mitigation, name='save_mitigation'),
    path('department/<int:dept_id>/download-excel/', views.download_excel, name='download_excel'),
    path('department/<int:dept_id>/upload-excel/', views.upload_excel, name='upload_excel'),
    path('department/<int:dept_id>/save-report-rows/', views.save_report_rows, name='save_report_rows'),
    path('department/<int:dept_id>/delete-upload/<int:upload_id>/', views.delete_upload, name='delete_upload'),
    path('department/<int:dept_id>/clear-manual/', views.clear_manual_records, name='clear_manual_records'),
]
