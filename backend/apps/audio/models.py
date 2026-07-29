from django.db import models
from core.models import AbstractMedia


class Audio(AbstractMedia):
    duration = models.FloatField(null=True, blank=True, help_text="Durée en secondes")
    sample_rate = models.IntegerField(null=True, blank=True)
    bitrate = models.IntegerField(null=True, blank=True)
    channels = models.IntegerField(null=True, blank=True)

    class Meta(AbstractMedia.Meta):
        verbose_name_plural = "audio"
