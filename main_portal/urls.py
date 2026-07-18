from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static

urlpatterns = [
    path('', include('portal.urls')),
    path('tpm/', include('tpm.urls')),
    path('cmc/', include('cmc.urls', namespace='cmc')),
    path('delays/', include('delays.urls', namespace='delays')),
    path('fmea/', include('fmea.urls', namespace='fmea')),
    path('capa/', include('capa.urls', namespace='capa')),
    path('safety/', include('Safety.urls', namespace='safety')),
    path('hod-kpi/', include('hod_kpi.urls', namespace='hod_kpi')),
    path('quality/', include('quality.urls', namespace='quality')),
    path('smed/', include('smed.urls', namespace='smed')),
    path('api/', include('api.urls')),
    path('admin/', admin.site.urls),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
