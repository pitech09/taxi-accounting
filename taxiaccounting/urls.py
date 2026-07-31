from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from django.shortcuts import redirect
from django.views.generic import RedirectView
from django.urls import reverse_lazy

urlpatterns = [
    path('admin/', admin.site.urls),
    path('accounts/', include('accounts.urls')),
    path('owner/', include('owner.urls')),
    path('owner/cashbook/', include('cashbook.urls')),
    path('driver/', include('driver_portal.urls')),
    path('reports/', include('reports.urls')),
    path('api/', include('api.urls')),
    
    # Root: redirect to custom owner login if not authenticated, else dashboard
    path('', lambda request: redirect('owner_dashboard' if request.user.is_authenticated else 'login')),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)