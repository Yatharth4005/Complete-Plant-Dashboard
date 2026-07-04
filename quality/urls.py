from django.urls import path
from quality import views

app_name = 'quality'

urlpatterns = [
    path('department/<int:dept_id>/', views.quality_dashboard, name='quality_dashboard'),
    path('department/<int:dept_id>/entry/', views.quality_entry, name='quality_entry'),
    path('department/<int:dept_id>/entry/<int:entry_id>/edit/', views.quality_entry, name='edit_quality_entry'),
    path('department/<int:dept_id>/entry/<int:entry_id>/delete/', views.delete_quality_entry, name='delete_quality_entry'),
    path('department/<int:dept_id>/summary-report/', views.quality_summary_report, name='quality_summary_report'),
]
