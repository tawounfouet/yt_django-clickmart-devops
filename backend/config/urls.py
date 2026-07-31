from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from drf_spectacular.views import SpectacularAPIView, SpectacularSwaggerView

urlpatterns = [
    path('admin/', admin.site.urls),
    path('api/v1/', include('users.api.urls')),
    path('api/v1/', include('products.api.urls')),
    path('api/v1/', include('carts.api.urls')),
    path('api/v1/', include('orders.api.urls')),
    path('api/v1/media/', include('images.api.urls')),
    path('api/v1/media/', include('audio.api.urls')),
    path('api/v1/media/', include('video.api.urls')),
    path('api/v1/media/', include('documents.api.urls')),
    path('api/schema/', SpectacularAPIView.as_view(), name='schema'),
    path('api/docs/', SpectacularSwaggerView.as_view(url_name='schema'), name='swagger-ui'),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)

handler404 = 'core.views.handler404'
handler500 = 'core.views.handler500'
