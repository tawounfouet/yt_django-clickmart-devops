from django.db import transaction
from django.db.models.signals import post_save
from django.dispatch import receiver

from .models import Image
from .tasks import process_image


@receiver(post_save, sender=Image)
def trigger_image_processing(sender, instance, created, **kwargs):
    if created and not instance.sha256:
        transaction.on_commit(lambda: process_image.delay(str(instance.id)))
