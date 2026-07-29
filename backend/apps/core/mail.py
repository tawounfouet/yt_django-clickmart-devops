import resend
from django.core.mail.backends.base import BaseEmailBackend
from django.conf import settings


class ResendBackend(BaseEmailBackend):
    def __init__(self, fail_silently=False, **kwargs):
        super().__init__(fail_silently=fail_silently)
        resend.api_key = getattr(settings, 'RESEND_API_KEY', '')

    def send_messages(self, email_messages):
        sent = 0
        for message in email_messages:
            try:
                params = {
                    'from': message.from_email or settings.DEFAULT_FROM_EMAIL,
                    'to': message.to,
                    'subject': message.subject,
                }
                if message.body:
                    params['text'] = message.body
                if hasattr(message, 'alternatives') and message.alternatives:
                    for alt_content, alt_type in message.alternatives:
                        if alt_type == 'text/html':
                            params['html'] = alt_content
                            break
                resend.Emails.send(params)
                sent += 1
            except Exception:
                if not self.fail_silently:
                    raise
        return sent
