from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static

urlpatterns = [
    path('', include('portal.urls')),
    path('tpm/', include('tpm.urls')),
    path('cmc/', include('cmc.urls', namespace='cmc')),
    path('delays/', include('delays.urls', namespace='delays')),
    path('admin/', admin.site.urls),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
