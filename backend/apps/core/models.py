import uuid
from django.db import models


class AbstractMedia(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    title = models.CharField(max_length=255, blank=True)
    file = models.FileField(upload_to="uploads/%Y/%m/%d/")
    original_filename = models.CharField(max_length=255)
    file_size = models.BigIntegerField(null=True, blank=True, help_text="Taille en octets")
    mime_type = models.CharField(max_length=100, blank=True)
    sha256 = models.CharField(max_length=64, blank=True, db_index=True)
    uploaded_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        abstract = True
        ordering = ['-uploaded_at']

    def __str__(self):
        return self.title or self.original_filename
