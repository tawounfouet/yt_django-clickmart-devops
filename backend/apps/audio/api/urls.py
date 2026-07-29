from django.urls import path, include
from rest_framework.routers import DefaultRouter
from audio.api.views import AudioViewSet

router = DefaultRouter()
router.register(r'audio', AudioViewSet)

urlpatterns = [
    path('', include(router.urls)),
]
