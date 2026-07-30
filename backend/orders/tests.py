from decimal import Decimal
import pytest
from unittest.mock import patch
from django.urls import reverse
from rest_framework import status
from model_bakery import baker

from .models import Order, OrderItem
from products.models import Product
from carts.models import Cart, CartItem


class TestOrderModel:
    @pytest.fixture
    def order(self, db, user):
        return baker.make(Order, user=user, subtotal=100.00, tax_amount=10.00, grand_total=110.00)

    def test_order_creation(self, order, user):
        assert order.user == user
        assert order.grand_total == Decimal("110.00")

    def test_order_default_status(self, order):
        assert order.status == "PENDING"

    def test_order_str(self, order, user):
        assert "Order #" in str(order)
        assert user.email in str(order)

    def test_order_status_choices(self, order):
        for choice, _ in Order.STATUS_CHOICES:
            order.status = choice
            order.save()
            assert order.status == choice


class TestPlaceOrderView:
    URL = reverse("order-place")

    @pytest.fixture
    def setup_cart(self, db, user):
        product = baker.make(Product, name="Order Item", price=20.00, stock=5, tax_percent=10.00)
        cart = baker.make(Cart, user=user)
        baker.make(CartItem, cart=cart, product=product, quantity=2)
        return cart, product

    @pytest.fixture
    def shipping(self):
        return {"shippingAddress": {"address": "456 Oak Ave", "phone": "555-0200",
                "city": "Portland", "state": "OR", "zipCode": "97201"}}

    @patch("orders.api.views.send_order_notification")
    def test_place_order_success(self, mock_notify, authenticated_client, setup_cart, shipping):
        response = authenticated_client.post(self.URL, shipping, format="json")
        assert response.status_code == status.HTTP_201_CREATED
        assert Order.objects.count() == 1
        assert OrderItem.objects.count() == 1
        order = Order.objects.first()
        assert order.grand_total == Decimal("44.00")
        assert order.address == "456 Oak Ave"
        mock_notify.assert_called_once()

    @patch("orders.api.views.send_order_notification")
    def test_place_order_deducts_stock(self, mock_notify, authenticated_client, setup_cart, shipping):
        _, product = setup_cart
        authenticated_client.post(self.URL, shipping, format="json")
        product.refresh_from_db()
        assert product.stock == 3

    @patch("orders.api.views.send_order_notification")
    def test_place_order_clears_cart(self, mock_notify, authenticated_client, setup_cart, shipping):
        cart, _ = setup_cart
        authenticated_client.post(self.URL, shipping, format="json")
        cart.refresh_from_db()
        assert cart.items.count() == 0

    def test_place_order_empty_cart(self, authenticated_client, setup_cart, shipping):
        cart, _ = setup_cart
        cart.items.all().delete()
        response = authenticated_client.post(self.URL, shipping, format="json")
        assert response.status_code == status.HTTP_400_BAD_REQUEST

    def test_place_order_unauthenticated(self, api_client, shipping):
        response = api_client.post(self.URL, shipping, format="json")
        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    @patch("orders.api.views.send_order_notification")
    def test_place_order_insufficient_stock(self, mock_notify, authenticated_client, setup_cart, shipping):
        _, product = setup_cart
        product.stock = 1
        product.save()
        response = authenticated_client.post(self.URL, shipping, format="json")
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        product.refresh_from_db()
        assert product.stock == 1


class TestMyOrdersView:
    URL = reverse("my-orders")

    def test_my_orders_only_own(self, db, authenticated_client, user):
        other = baker.make("users.User", email="other@example.com")
        baker.make(Order, user=other, subtotal=50.00, tax_amount=5.00, grand_total=55.00)
        baker.make(Order, user=user, subtotal=30.00, tax_amount=3.00, grand_total=33.00)
        response = authenticated_client.get(self.URL)
        assert response.status_code == status.HTTP_200_OK
        assert len(response.data) == 1

    def test_my_orders_unauthenticated(self, api_client):
        response = api_client.get(self.URL)
        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_my_orders_empty(self, authenticated_client):
        response = authenticated_client.get(self.URL)
        assert len(response.data) == 0


class TestOrderDetailView:
    @pytest.fixture
    def order(self, db, user):
        return baker.make(Order, user=user, subtotal=75.00, tax_amount=7.50, grand_total=82.50)

    @pytest.fixture
    def url(self, order):
        return reverse("order-detail", args=[order.id])

    def test_order_detail_own(self, authenticated_client, url):
        response = authenticated_client.get(url)
        assert response.status_code == status.HTTP_200_OK
        assert response.data["grand_total"] == "82.50"

    def test_order_detail_other_user(self, db, authenticated_client, url):
        other = baker.make("users.User", email="other2@example.com")
        authenticated_client.force_authenticate(user=other)
        response = authenticated_client.get(url)
        assert response.status_code == status.HTTP_404_NOT_FOUND

    def test_order_detail_nonexistent(self, authenticated_client):
        url = reverse("order-detail", args=["00000000-0000-0000-0000-000000000000"])
        response = authenticated_client.get(url)
        assert response.status_code == status.HTTP_404_NOT_FOUND
