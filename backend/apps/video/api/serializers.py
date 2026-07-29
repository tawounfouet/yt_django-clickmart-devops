from rest_framework.serializers import ModelSerializer
from video.models import Video


class VideoSerializer(ModelSerializer):
    class Meta:
        model = Video
        fields = '__all__'
        read_only_fields = [
            'id', 'original_filename', 'file_size', 'mime_type',
            'duration', 'width', 'height', 'fps', 'codec',
            'thumbnail', 'uploaded_at',
        ]
