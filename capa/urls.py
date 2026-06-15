from django.urls import path
from . import views

app_name = 'capa'

urlpatterns = [
    path('department/<int:dept_id>/', views.capa_dashboard, name='dashboard'),
    path('department/<int:dept_id>/identification/', views.capa_identification, name='identification'),
    path('department/<int:dept_id>/report/', views.capa_report, name='report'),
    path('department/<int:dept_id>/history/', views.capa_history, name='history'),
    
    # Actions
    path('department/<int:dept_id>/save-capa/', views.save_capa, name='save_capa'),
    path('department/<int:dept_id>/save-capa/<int:record_id>/', views.save_capa, name='save_capa_id'),
    path('department/<int:dept_id>/upload-file/', views.upload_file, name='upload_file'),
    path('department/<int:dept_id>/download-pdf/<int:capa_id>/', views.download_pdf, name='download_pdf'),
    path('department/<int:dept_id>/delete-upload/<int:upload_id>/', views.delete_upload, name='delete_upload'),
]
