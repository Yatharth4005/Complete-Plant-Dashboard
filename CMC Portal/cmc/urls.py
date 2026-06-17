from django.urls import path
from cmc.views import dashboard_views, schedule_views, vibration_views, oil_test_views, wda_views, notification_views, report_views, grease_report_views

app_name = 'cmc'

urlpatterns = [
    # CMC Entry Point
    path('department/<int:dept_id>/', dashboard_views.dept_overview, name='dept_overview'),

    # PM Schedule
    path('department/<int:dept_id>/schedule/', schedule_views.schedule_grid, name='schedule_grid'),
    path('department/<int:dept_id>/schedule/update-cell/', schedule_views.update_cell, name='update_cell'),

    # Vibration Monitoring
    path('department/<int:dept_id>/vibration/', vibration_views.log_list, name='vibration_list'),
    path('department/<int:dept_id>/vibration/new/', vibration_views.log_entry, name='vibration_new'),
    path('department/<int:dept_id>/vibration/<int:log_id>/', vibration_views.log_detail, name='vibration_detail'),
    path('department/<int:dept_id>/vibration/analytics/', vibration_views.analytics, name='vibration_analytics'),

    # Oil Testing
    path('department/<int:dept_id>/oil-test/', oil_test_views.log_list, name='oil_list'),
    path('department/<int:dept_id>/oil-test/new/', oil_test_views.log_entry, name='oil_new'),
    path('department/<int:dept_id>/oil-test/analytics/', oil_test_views.analytics, name='oil_analytics'),

    # Grease Report
    path('department/<int:dept_id>/grease-report/', grease_report_views.log_list, name='grease_list'),
    path('department/<int:dept_id>/grease-report/new/', grease_report_views.log_entry, name='grease_new'),
    path('department/<int:dept_id>/grease-report/analytics/', grease_report_views.analytics, name='grease_analytics'),

    # WDA
    path('department/<int:dept_id>/wda/', wda_views.log_list, name='wda_list'),
    path('department/<int:dept_id>/wda/new/', wda_views.log_entry, name='wda_new'),
    path('department/<int:dept_id>/wda/analytics/', wda_views.analytics, name='wda_analytics'),

    # SAP Notification Tracker
    path('department/<int:dept_id>/notifications/', notification_views.tracker, name='notification_tracker'),
    path('department/<int:dept_id>/notifications/<int:notif_id>/close/', notification_views.close_notif, name='close_notification'),

    # Reports
    path('department/<int:dept_id>/reports/', report_views.report_page, name='report_page'),
    path('department/<int:dept_id>/reports/pdf/', report_views.export_pdf, name='export_pdf'),
    path('department/<int:dept_id>/reports/excel/', report_views.export_excel, name='export_excel'),

    # HTMX APIS
    path('api/equipment-search/', dashboard_views.equipment_search, name='equipment_search'),
    path('api/equipment-bearing-points/', vibration_views.get_bearing_points, name='equipment_bearing_points'),
]
