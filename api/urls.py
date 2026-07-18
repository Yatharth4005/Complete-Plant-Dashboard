from django.urls import path
from rest_framework_simplejwt.views import (
    TokenObtainPairView,
    TokenRefreshView,
)
from api.views import (
    MeView, DashboardView, 
    ChecklistSchedulesView, ChecklistsListView, 
    ChecklistDetailView, ChecklistInitializeView, ChecklistSaveView,
    FuguaiTagListView, FuguaiTagCreateView, FuguaiTagUpdateView,
    auto_login_view, webview_token_view
)

urlpatterns = [
    # Authentication endpoints
    path('auth/login/', TokenObtainPairView.as_view(), name='token_obtain_pair'),
    path('auth/auto-login/', auto_login_view, name='auto_login'),
    path('auth/webview-token/', webview_token_view, name='webview_token'),
    path('auth/refresh/', TokenRefreshView.as_view(), name='token_refresh'),
    path('auth/me/', MeView.as_view(), name='user_me'),
    
    # Dashboard configuration
    path('dashboard/', DashboardView.as_view(), name='dashboard'),
    
    # Checklist API endpoints
    path('checklist/schedules/', ChecklistSchedulesView.as_view(), name='checklist_schedules'),
    path('checklist/list/', ChecklistsListView.as_view(), name='checklist_list'),
    path('checklist/detail/<int:checklist_id>/', ChecklistDetailView.as_view(), name='checklist_detail'),
    path('checklist/initialize/', ChecklistInitializeView.as_view(), name='checklist_initialize'),
    path('checklist/save/<int:checklist_id>/', ChecklistSaveView.as_view(), name='checklist_save'),

    # Fuguai Register endpoints (TPM Abnormality tracking)
    path('tpm/fuguai/list/', FuguaiTagListView.as_view(), name='tpm_fuguai_list'),
    path('tpm/fuguai/create/', FuguaiTagCreateView.as_view(), name='tpm_fuguai_create'),
    path('tpm/fuguai/update/<int:tag_id>/', FuguaiTagUpdateView.as_view(), name='tpm_fuguai_update'),
]
