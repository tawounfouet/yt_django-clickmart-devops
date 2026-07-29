import hashlib
import logging

from celery import shared_task

from .models import Video

logger = logging.getLogger(__name__)


@shared_task
def process_video(video_id):
    try:
        video = Video.objects.get(id=video_id)
    except Video.DoesNotExist:
        logger.error(f"Video {video_id} not found")
        return

    video.file.seek(0)
    raw = video.file.read()
    video.sha256 = hashlib.sha256(raw).hexdigest()
    video.file_size = len(raw)

    # TODO: extract metadata + thumbnail
    # from .processors import extract_metadata, extract_thumbnail
    # meta = extract_metadata(video.file.path)
    # video.duration = meta['duration']
    # thumb = extract_thumbnail(video.file.path, ...)
    # video.thumbnail.save(...)

    video.save(update_fields=['sha256', 'file_size'])
    logger.info(f"Video {video_id} processed")
