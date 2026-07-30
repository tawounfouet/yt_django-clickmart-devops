import os

from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model

User = get_user_model()


class Command(BaseCommand):
    help = "Create default superuser from .env (ADMIN_EMAIL, ADMIN_PASSWORD)"

    def handle(self, *args, **options):
        email = os.environ.get('ADMIN_EMAIL', 'admin@clickmart.local')
        password = os.environ.get('ADMIN_PASSWORD', 'admin123')

        if User.objects.filter(email=email).exists():
            user = User.objects.get(email=email)
            user.set_password(password)
            user.is_staff = True
            user.is_superuser = True
            user.save()
            self.stdout.write(self.style.WARNING(f"Admin {email} exists — password updated"))
        else:
            User.objects.create_superuser(email=email, password=password, username=email)
            self.stdout.write(self.style.SUCCESS(f"Admin {email} created"))
