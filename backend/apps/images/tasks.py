import hashlib
import logging
from io import BytesIO

from celery import shared_task
from django.core.files.base import ContentFile

from .models import Image
from .processors import extract_metadata, generate_thumbnail

logger = logging.getLogger(__name__)


@shared_task
def process_image(image_id):
    try:
        image = Image.objects.get(id=image_id)
    except Image.DoesNotExist:
        logger.error(f"Image {image_id} not found")
        return

    image.file.seek(0)
    raw = image.file.read()

    # SHA256
    image.sha256 = hashlib.sha256(raw).hexdigest()

    # Metadata
    meta = extract_metadata(BytesIO(raw))
    image.width = meta['width']
    image.height = meta['height']
    image.exif_data = meta['exif_data']
    image.file_size = len(raw)

    # Thumbnail
    image.file.seek(0)
    thumb_buf = generate_thumbnail(image.file)
    image.thumbnail.save(
        f"thumb_{image.id}.jpg",
        ContentFile(thumb_buf.read()),
        save=False,
    )

    image.save(update_fields=[
        'sha256', 'width', 'height', 'exif_data',
        'file_size', 'thumbnail',
    ])
    logger.info(f"Image {image_id} processed: {image.width}x{image.height}")
