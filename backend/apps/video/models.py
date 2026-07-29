from django.db import models
from core.models import AbstractMedia


class Video(AbstractMedia):
    duration = models.FloatField(null=True, blank=True, help_text="Durée en secondes")
    width = models.PositiveIntegerField(null=True, blank=True)
    height = models.PositiveIntegerField(null=True, blank=True)
    fps = models.FloatField(null=True, blank=True)
    codec = models.CharField(max_length=50, blank=True)
    thumbnail = models.ImageField(upload_to="thumbnails/", null=True, blank=True)

    class Meta(AbstractMedia.Meta):
        verbose_name_plural = "videos"
