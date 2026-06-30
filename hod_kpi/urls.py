from django.urls import path
from . import views

app_name = 'hod_kpi'

urlpatterns = [
    path('dashboard/', views.hod_kpi_dashboard, name='dashboard'),
    path('upload/', views.upload_excel, name='upload_excel'),
    path('save/kpi-feedback/', views.save_kpi_feedback, name='save_kpi_feedback'),
    path('save/delay-explanation/', views.save_delay_explanation, name='save_delay_explanation'),
    path('save/monthly-inputs/', views.save_monthly_inputs, name='save_monthly_inputs'),
    path('ai-insights/', views.generate_ai_insights, name='generate_ai_insights'),
    path('submit/', views.submit_review, name='submit_review'),
    path('history/', views.review_history, name='review_history'),
]
