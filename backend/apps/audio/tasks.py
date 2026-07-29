import hashlib
import logging

from celery import shared_task

from .models import Audio

logger = logging.getLogger(__name__)


@shared_task
def process_audio(audio_id):
    try:
        audio = Audio.objects.get(id=audio_id)
    except Audio.DoesNotExist:
        logger.error(f"Audio {audio_id} not found")
        return

    audio.file.seek(0)
    raw = audio.file.read()
    audio.sha256 = hashlib.sha256(raw).hexdigest()
    audio.file_size = len(raw)

    # TODO: extract metadata (duration, sample_rate, bitrate)
    # from .processors import extract_metadata
    # meta = extract_metadata(audio.file)
    # audio.duration = meta['duration']
    # audio.sample_rate = meta['sample_rate']

    audio.save(update_fields=['sha256', 'file_size'])
    logger.info(f"Audio {audio_id} processed")
