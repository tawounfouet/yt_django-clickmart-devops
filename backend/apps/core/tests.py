import pytest
from django.core.management import call_command
from django.contrib.auth import get_user_model

User = get_user_model()

from apps.core.mixins import ValidateFieldsMixin
from rest_framework import serializers


class TestValidateFieldsMixin:
    def test_rejects_unknown_fields(self):
        class DummySerializer(ValidateFieldsMixin, serializers.Serializer):
            name = serializers.CharField()
        s = DummySerializer(data={"name": "test", "typo_field": "bad"})
        assert not s.is_valid()
        assert "Unknown field" in str(s.errors["non_field_errors"][0])

    def test_accepts_valid_fields(self):
        class DummySerializer(ValidateFieldsMixin, serializers.Serializer):
            name = serializers.CharField()
        s = DummySerializer(data={"name": "test"})
        assert s.is_valid()


class TestGetOrNone:
    def test_get_or_none_found(self, product):
        from products.models import Product
        result = Product.objects.get_or_none(pk=product.pk)
        assert result == product

    def test_get_or_none_not_found(self, db):
        from products.models import Product
        result = Product.objects.get_or_none(pk="00000000-0000-0000-0000-000000000000")
        assert result is None


class TestCreateAdmin:
    def test_create_admin_command(self, db):
        call_command("create_admin")
        admin = User.objects.get(email="admin@clickmart.local")
        assert admin.is_superuser
        assert admin.check_password("admin123")


class TestSendOrderNotification:
    def test_send_order_notification_does_not_raise(self, order):
        from orders.utils import send_order_notification
        send_order_notification(order)


class TestCartSerializer:
    def test_cart_serializer_exports_expected_fields(self, user):
        from carts.models import Cart
        from carts.serializers import CartSerializer
        cart, _ = Cart.objects.get_or_create(user=user)
        data = CartSerializer(cart).data
        assert 'id' in data
        assert 'user' in data


class TestAdminAccess:
    def test_admin_login_page_loads(self, api_client):
        response = api_client.get('/admin/login/')
        assert response.status_code == 200




        from celery import current_app
        current_app.conf.task_always_eager = True
        from orders.tasks import send_order_confirmation_email
        send_order_confirmation_email("test-id", "test@test.com")


class TestUserSerializer:
    def test_user_serializer_exports_expected_fields(self, user):
        from users.serializers import UserSerializer
        data = UserSerializer(user).data
        assert 'id' in data
        assert 'email' in data
        assert 'username' in data
