# Gestion des Emails — ClickMart

> **Date** : 2026-07-29
> **Version** : 1.0
> **Contexte** : Backend email tiers (console/smtp/resend) + auto admin creation

---

## Architecture

```
┌──────────────────────────────────────────────────────────┐
│                  EMAIL_BACKEND_TYPE                       │
│                        │                                  │
│         ┌──────────────┼──────────────┐                   │
│         │              │              │                   │
│      console         smtp          resend                │
│    (dev / CI)     (staging)     (production)             │
│         │              │              │                   │
│    stdout         Gmail SMTP    Resend API                │
│    (zéro coût)    (dummy)      (hello@webtech-dev.info)  │
└──────────────────────────────────────────────────────────┘
```

| Environnement | Backend | Envoi réel | Config |
|---|---|---|---|
| Dev local | `console` | Non (stdout) | `EMAIL_BACKEND_TYPE=console` |
| CI (GitHub Actions) | `console` | Non (stdout) | (défaut) |
| Staging | `smtp` | Oui (Gmail dummy) | `EMAIL_BACKEND_TYPE=smtp` |
| Production | `resend` | Oui (Resend API) | `EMAIL_BACKEND_TYPE=resend` |

---

## Configuration Django

```python
# backend/config/settings.py

EMAIL_BACKEND_TYPE = config('EMAIL_BACKEND_TYPE', default='console')
DEFAULT_FROM_EMAIL = config('DEFAULT_FROM_EMAIL', default='noreply@clickmart.local')
ADMIN_EMAIL = config('ADMIN_EMAIL', default='admin@clickmart.local')

if EMAIL_BACKEND_TYPE == 'resend':
    EMAIL_BACKEND = 'core.mail.ResendEmailBackend'
    RESEND_API_KEY = config('RESEND_API_KEY')
elif EMAIL_BACKEND_TYPE == 'smtp':
    EMAIL_BACKEND = 'django.core.mail.backends.smtp.EmailBackend'
    EMAIL_HOST = 'smtp.gmail.com'
    EMAIL_PORT = 587
    EMAIL_USE_TLS = True
    EMAIL_HOST_USER = config('EMAIL_HOST_USER')
    EMAIL_HOST_PASSWORD = config('EMAIL_HOST_PASSWORD')
else:
    EMAIL_BACKEND = 'django.core.mail.backends.console.EmailBackend'
```

---

## ResendEmailBackend custom

```python
# backend/apps/core/mail.py
class ResendEmailBackend(BaseEmailBackend):
    def _send(self, message):
        payload = {
            "from": message.from_email,
            "to": message.to,
            "subject": message.subject,
        }
        if message.cc: payload["cc"] = message.cc
        if message.bcc: payload["bcc"] = message.bcc
        if message.reply_to: payload["reply_to"] = message.reply_to
        # HTML support (EmailMultiAlternatives)
        for content, mimetype in getattr(message, 'alternatives', []):
            if mimetype == 'text/html':
                payload["html"] = content
        if message.body: payload["text"] = message.body
        response = self._resend.Emails.send(payload)
        return True
```

**Fonctionnalités supportées** :
- `send_mail()` — email texte simple
- `EmailMultiAlternatives` — HTML + texte
- CC, BCC, Reply-To, Headers personnalisés
- Logging (ID Resend, sujet)
- Graceful fallback (`fail_silently`)

---

## Fichiers d'environnement

### `.envs/.local` — Dev Docker

```bash
EMAIL_BACKEND_TYPE=console
```

### `.envs/.staging` — Staging

```bash
EMAIL_BACKEND_TYPE=smtp
EMAIL_HOST_USER=dummy@gmail.com
EMAIL_HOST_PASSWORD=dummypassword
```

### `.envs/.prod` — Production

```bash
EMAIL_BACKEND_TYPE=resend
RESEND_API_KEY=re_xxxxx
DEFAULT_FROM_EMAIL=hello@webtech-dev.info
ADMIN_EMAIL=thomas.awounfouet@yahoo.com
ADMIN_PASSWORD=changeme
```

---

## Admin auto-création

Commande `create_admin` exécutée au démarrage du backend :

```python
# backend/users/management/commands/create_admin.py
class Command(BaseCommand):
    def handle(self, *args, **options):
        email = config('ADMIN_EMAIL', default='admin@clickmart.local')
        password = config('ADMIN_PASSWORD', default='changeme')
        if User.objects.filter(email=email).exists():
            user = User.objects.get(email=email)
            user.set_password(password)
            user.save()
        else:
            User.objects.create_superuser(email=email, password=password, username=email)
```

Exécutée dans `docker-compose.yml` après `migrate` :
```bash
sh -c "python manage.py collectstatic --noinput &&
       python manage.py migrate &&
       python manage.py create_admin &&
       gunicorn ..."
```

---

## Tests d'envoi

| Date | Environnement | Resend ID | Statut |
|---|---|---|---|
| 2026-07-29 | Dev local | `e1febfb8` | delivered ✅ |
| 2026-07-29 | Production | `71df6527` | delivered ✅ |
| 2026-07-29 | Production | `8bd0c386` | delivered ✅ |

---

## Dépendances

```
resend==2.9.0
```

---

## Opérations courantes

### Tester l'envoi d'email

```bash
docker compose exec backend python3 -c "
import django; django.setup()
from django.core.mail import send_mail
send_mail('Test', 'Body', 'hello@webtech-dev.info', ['thomas.awounfouet@yahoo.com'])
"
```

### Changement de provider

| Pour passer à... | Modifier `.env` |
|---|---|
| Console (dev) | `EMAIL_BACKEND_TYPE=console` |
| SMTP (Gmail) | `EMAIL_BACKEND_TYPE=smtp` + `EMAIL_HOST_USER/PASSWORD` |
| Resend | `EMAIL_BACKEND_TYPE=resend` + `RESEND_API_KEY` |

Aucun changement de code — `send_mail()` continue de fonctionner.

### Vérifier le statut d'un email Resend

```python
import resend
resend.api_key = 're_...'
email = resend.Emails.get('email_id')
print(email['last_event'])  # delivered, bounced, opened...
```
