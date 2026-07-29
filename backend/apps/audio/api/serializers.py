from rest_framework.serializers import ModelSerializer
from audio.models import Audio


class AudioSerializer(ModelSerializer):
    class Meta:
        model = Audio
        fields = '__all__'
        read_only_fields = [
            'id', 'original_filename', 'file_size', 'mime_type',
            'duration', 'sample_rate', 'bitrate', 'channels', 'uploaded_at',
        ]
