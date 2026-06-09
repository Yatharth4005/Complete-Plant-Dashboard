from django.contrib import admin
from django.urls import path, include
from django.shortcuts import redirect
from django.conf import settings
from django.conf.urls.static import static

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', lambda r: redirect('cmc:dept_overview', dept_id=2)), # default redirect to BF-2/selected overview
    path('', include('cmc.urls', namespace='cmc')),
    path('', include('portal.urls', namespace='portal')),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
