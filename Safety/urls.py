from django.urls import path
from Safety import views

app_name = 'safety'

urlpatterns = [
    path('department/<int:dept_id>/incident-management/', views.im_dashboard, name='im_dashboard'),
    path('department/<int:dept_id>/report-incident/', views.report_incident, name='report_incident'),
    path('department/<int:dept_id>/review-incident/<int:incident_id>/', views.review_incident, name='review_incident'),
    path('department/<int:dept_id>/delete-incident/<int:incident_id>/', views.delete_incident, name='delete_incident'),
]
