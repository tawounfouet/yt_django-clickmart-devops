from decimal import Decimal
from django.test import TestCase
from django.contrib.auth import get_user_model
from rest_framework.test import APITestCase
from rest_framework import status
from django.urls import reverse
from unittest.mock import patch

from .models import Order, OrderItem
from products.models import Product
from carts.models import Cart, CartItem

User = get_user_model()


class OrderModelTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            email="order@example.com",
            username="orderuser",
            password="pass123",
        )
        self.order = Order.objects.create(
            user=self.user,
            subtotal=Decimal("100.00"),
            tax_amount=Decimal("10.00"),
            grand_total=Decimal("110.00"),
            address="123 Main St",
            phone="555-0100",
            city="Springfield",
            state="IL",
            zip_code="62701",
        )

    def test_order_creation(self):
        self.assertEqual(self.order.user, self.user)
        self.assertEqual(self.order.grand_total, Decimal("110.00"))

    def test_order_default_status(self):
        self.assertEqual(self.order.status, "PENDING")

    def test_order_str(self):
        self.assertIn("Order #", str(self.order))
        self.assertIn("order@example.com", str(self.order))

    def test_order_status_choices(self):
        for choice, _ in Order.STATUS_CHOICES:
            self.order.status = choice
            self.order.save()
            self.assertEqual(self.order.status, choice)


class PlaceOrderViewTests(APITestCase):
    def setUp(self):
        self.url = reverse("order-place")
        self.user = User.objects.create_user(
            email="buyer@example.com",
            username="buyer",
            password="pass123",
        )
        self.product = Product.objects.create(
            name="Order Item",
            price=Decimal("20.00"),
            stock=5,
            tax_percent=Decimal("10.00"),
        )
        self.cart = Cart.objects.create(user=self.user)
        self.cart_item = CartItem.objects.create(
            cart=self.cart, product=self.product, quantity=2,
        )
        self.shipping = {
            "shippingAddress": {
                "address": "456 Oak Ave",
                "phone": "555-0200",
                "city": "Portland",
                "state": "OR",
                "zipCode": "97201",
            }
        }
        self.client.force_authenticate(user=self.user)

    @patch("orders.views.send_order_notification")
    def test_place_order_success(self, mock_notify):
        response = self.client.post(
            self.url, self.shipping, format="json"
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(Order.objects.count(), 1)
        self.assertEqual(OrderItem.objects.count(), 1)
        order = Order.objects.first()
        self.assertEqual(order.grand_total, Decimal("44.00"))
        self.assertEqual(order.address, "456 Oak Ave")
        mock_notify.assert_called_once()

    @patch("orders.views.send_order_notification")
    def test_place_order_deducts_stock(self, mock_notify):
        self.client.post(self.url, self.shipping, format="json")
        self.product.refresh_from_db()
        self.assertEqual(self.product.stock, 3)

    @patch("orders.views.send_order_notification")
    def test_place_order_clears_cart(self, mock_notify):
        self.client.post(self.url, self.shipping, format="json")
        self.cart.refresh_from_db()
        self.assertEqual(self.cart.items.count(), 0)

    def test_place_order_empty_cart(self):
        self.cart.items.all().delete()
        response = self.client.post(
            self.url, self.shipping, format="json"
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_place_order_unauthenticated(self):
        self.client.force_authenticate(user=None)
        response = self.client.post(
            self.url, self.shipping, format="json"
        )
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    @patch("orders.views.send_order_notification")
    def test_place_order_insufficient_stock(self, mock_notify):
        self.product.stock = 1
        self.product.save()
        response = self.client.post(
            self.url, self.shipping, format="json"
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.product.refresh_from_db()
        self.assertEqual(self.product.stock, 1)


class MyOrdersViewTests(APITestCase):
    def setUp(self):
        self.url = reverse("my-orders")
        self.user = User.objects.create_user(
            email="my@example.com",
            username="myuser",
            password="pass123",
        )
        other = User.objects.create_user(
            email="other@example.com",
            username="other",
            password="pass123",
        )
        Order.objects.create(
            user=other, subtotal=Decimal("50.00"),
            tax_amount=Decimal("5.00"), grand_total=Decimal("55.00"),
        )
        self.client.force_authenticate(user=self.user)

    def test_my_orders_only_own(self):
        Order.objects.create(
            user=self.user, subtotal=Decimal("30.00"),
            tax_amount=Decimal("3.00"), grand_total=Decimal("33.00"),
        )
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)

    def test_my_orders_unauthenticated(self):
        self.client.force_authenticate(user=None)
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_my_orders_empty(self):
        response = self.client.get(self.url)
        self.assertEqual(len(response.data), 0)


class OrderDetailViewTests(APITestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            email="detail@example.com",
            username="detailuser",
            password="pass123",
        )
        self.order = Order.objects.create(
            user=self.user, subtotal=Decimal("75.00"),
            tax_amount=Decimal("7.50"), grand_total=Decimal("82.50"),
        )
        self.url = reverse("order-detail", args=[self.order.id])
        self.client.force_authenticate(user=self.user)

    def test_order_detail_own(self):
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["grand_total"], "82.50")

    def test_order_detail_other_user(self):
        other = User.objects.create_user(
            email="other2@example.com",
            username="other2",
            password="pass123",
        )
        self.client.force_authenticate(user=other)
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_order_detail_nonexistent(self):
        url = reverse("order-detail", args=[9999])
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
