from rest_framework import serializers
from images.models import Image


class ImageSerializer(serializers.ModelSerializer):
    class Meta:
        model = Image
        fields = [
            'id', 'title', 'file', 'original_filename',
            'file_size', 'mime_type', 'width', 'height',
            'thumbnail', 'uploaded_at',
        ]
        read_only_fields = [
            'id', 'original_filename', 'file_size', 'mime_type',
            'width', 'height', 'thumbnail', 'uploaded_at',
        ]
