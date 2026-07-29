import logging
from django.conf import settings
from django.core.mail.backends.base import BaseEmailBackend

logger = logging.getLogger(__name__)


class ResendEmailBackend(BaseEmailBackend):
    def __init__(self, fail_silently=False, **kwargs):
        super().__init__(fail_silently=fail_silently, **kwargs)
        try:
            import resend as resend_lib
            self._resend = resend_lib
            self._resend.api_key = getattr(settings, "RESEND_API_KEY", None)
            if not self._resend.api_key:
                logger.error("ResendEmailBackend: RESEND_API_KEY missing.")
        except ImportError:
            logger.error("ResendEmailBackend: pip install resend")
            self._resend = None

    def send_messages(self, email_messages):
        if not email_messages or self._resend is None:
            return 0
        return sum(1 for msg in email_messages if self._send(msg))

    def _send(self, message):
        try:
            payload = {
                "from": message.from_email,
                "to": message.to,
                "subject": message.subject,
            }
            if message.cc:
                payload["cc"] = message.cc
            if message.bcc:
                payload["bcc"] = message.bcc
            if message.reply_to:
                payload["reply_to"] = message.reply_to
            if message.extra_headers:
                payload["headers"] = message.extra_headers

            html_body = None
            if hasattr(message, "alternatives"):
                for content, mimetype in message.alternatives:
                    if mimetype == "text/html":
                        html_body = content
                        break
            if html_body:
                payload["html"] = html_body
            if message.body:
                payload["text"] = message.body

            response = self._resend.Emails.send(payload)
            logger.info("Resend: id=%s subject=%r", response.get("id"), message.subject)
            return True
        except Exception as exc:
            logger.error("Resend failed: subject=%r error=%s", message.subject, exc)
            if not self.fail_silently:
                raise
            return False
