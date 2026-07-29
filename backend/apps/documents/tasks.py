import hashlib
import logging

from celery import shared_task

from .models import Document

logger = logging.getLogger(__name__)


@shared_task
def process_document(document_id):
    try:
        doc = Document.objects.get(id=document_id)
    except Document.DoesNotExist:
        logger.error(f"Document {document_id} not found")
        return

    doc.file.seek(0)
    raw = doc.file.read()
    doc.sha256 = hashlib.sha256(raw).hexdigest()
    doc.file_size = len(raw)

    # TODO: extract metadata
    # from .processors import extract_metadata
    # meta = extract_metadata(doc.file.path)
    # doc.page_count = meta['page_count']
    # doc.author = meta.get('author', '')

    doc.save(update_fields=['sha256', 'file_size'])
    logger.info(f"Document {document_id} processed")
