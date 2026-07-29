from django.db import models
from core.models import AbstractMedia


class Document(AbstractMedia):
    page_count = models.PositiveIntegerField(null=True, blank=True)
    author = models.CharField(max_length=255, blank=True)
    is_encrypted = models.BooleanField(default=False)

    class Meta(AbstractMedia.Meta):
        verbose_name_plural = "documents"
