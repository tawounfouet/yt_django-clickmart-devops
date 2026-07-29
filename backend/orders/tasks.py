from celery import shared_task
from django.core.mail import send_mail
from django.conf import settings
import logging

logger = logging.getLogger(__name__)


@shared_task
def send_order_confirmation_email(order_id, user_email):
    logger.info(f"[Celery] Envoi confirmation commande #{order_id} à {user_email}")
    try:
        send_mail(
            subject=f'ClickMart - Confirmation de commande #{order_id}',
            message=f'Votre commande #{order_id} a bien été enregistrée.',
            from_email=settings.EMAIL_HOST_USER,
            recipient_list=[user_email],
            fail_silently=True,
        )
        logger.info(f"[Celery] Email envoyé pour commande #{order_id}")
        return f"Email sent for order #{order_id}"
    except Exception as e:
        logger.error(f"[Celery] Échec email commande #{order_id}: {e}")
        raise


@shared_task
def cleanup_expired_carts():
    logger.info("[Celery] Nettoyage des paniers expirés...")
    from carts.models import Cart
    from django.utils import timezone
    from datetime import timedelta

    expired = timezone.now() - timedelta(hours=24)
    count, _ = Cart.objects.filter(created_at__lt=expired).delete()
    logger.info(f"[Celery] {count} paniers expirés supprimés")
    return f"Cleaned {count} expired carts"
