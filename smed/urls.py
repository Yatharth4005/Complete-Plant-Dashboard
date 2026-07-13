from django.urls import path
from smed import views

app_name = 'smed'

urlpatterns = [
    path('department/<int:dept_id>/', views.smed_dashboard, name='smed_dashboard'),
    path('department/<int:dept_id>/template/<int:template_id>/data/', views.get_smed_run_data, name='get_smed_run_data'),
    path('department/<int:dept_id>/template/<int:template_id>/save/', views.save_smed_run, name='save_smed_run'),
    path('department/<int:dept_id>/template/<int:template_id>/history/', views.smed_history, name='smed_history'),
    path('department/<int:dept_id>/run/<int:run_id>/delete/', views.delete_smed_run, name='delete_smed_run'),
]
