from rest_framework import viewsets
from audio.models import Audio
from audio.api.serializers import AudioSerializer


class AudioViewSet(viewsets.ModelViewSet):
    queryset = Audio.objects.all()
    serializer_class = AudioSerializer
