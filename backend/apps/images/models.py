from django.db import models
from core.models import AbstractMedia


class Image(AbstractMedia):
    width = models.PositiveIntegerField(null=True, blank=True)
    height = models.PositiveIntegerField(null=True, blank=True)
    thumbnail = models.ImageField(upload_to="thumbnails/", null=True, blank=True)
    exif_data = models.JSONField(default=dict, blank=True)

    class Meta(AbstractMedia.Meta):
        pass
