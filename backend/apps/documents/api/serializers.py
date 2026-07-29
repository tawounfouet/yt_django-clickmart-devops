from rest_framework.serializers import ModelSerializer
from documents.models import Document


class DocumentSerializer(ModelSerializer):
    class Meta:
        model = Document
        fields = '__all__'
        read_only_fields = [
            'id', 'original_filename', 'file_size', 'mime_type',
            'page_count', 'author', 'uploaded_at',
        ]
