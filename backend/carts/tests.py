from decimal import Decimal
from django.test import TestCase
from django.contrib.auth import get_user_model
from rest_framework.test import APITestCase
from rest_framework import status
from django.urls import reverse

from .models import Cart, CartItem
from products.models import Product

User = get_user_model()


class CartModelTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            email="cart@example.com",
            username="cartuser",
            password="pass123",
        )
        self.cart = Cart.objects.create(user=self.user)
        self.product = Product.objects.create(
            name="Cart Item",
            price=Decimal("10.00"),
            stock=5,
            tax_percent=Decimal("20.00"),
        )
        self.item = CartItem.objects.create(
            cart=self.cart,
            product=self.product,
            quantity=2,
        )

    def test_cart_creation(self):
        self.assertEqual(self.cart.user, self.user)

    def test_cart_str(self):
        self.assertIn("cart", str(self.cart).lower())

    def test_cart_subtotal(self):
        self.assertEqual(self.cart.subtotal, Decimal("20.00"))

    def test_cart_tax_amount(self):
        self.assertEqual(self.cart.tax_amount, Decimal("4.00"))

    def test_cart_grand_total(self):
        self.assertEqual(self.cart.grand_total, Decimal("24.00"))

    def test_cart_empty_subtotal(self):
        self.item.delete()
        self.assertEqual(self.cart.subtotal, Decimal("0.00"))

    def test_cart_empty_grand_total(self):
        self.item.delete()
        self.assertEqual(self.cart.grand_total, Decimal("0.00"))

    def test_cart_multiple_items(self):
        p2 = Product.objects.create(
            name="Second",
            price=Decimal("5.00"),
            stock=10,
        )
        CartItem.objects.create(cart=self.cart, product=p2, quantity=3)
        self.assertEqual(self.cart.subtotal, Decimal("35.00"))

    def test_cart_item_total_price(self):
        self.assertEqual(self.item.total_price, Decimal("20.00"))

    def test_cart_item_str(self):
        self.assertIn("Cart Item", str(self.item))
        self.assertIn("2", str(self.item))


class CartViewTests(APITestCase):
    def setUp(self):
        self.url = reverse("cart")
        self.user = User.objects.create_user(
            email="view@example.com",
            username="viewuser",
            password="pass123",
        )

    def test_get_cart_unauthenticated(self):
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_get_cart_creates_if_missing(self):
        self.client.force_authenticate(user=self.user)
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn("items", response.data)

    def test_get_cart_with_items(self):
        self.client.force_authenticate(user=self.user)
        cart = Cart.objects.create(user=self.user)
        product = Product.objects.create(
            name="In Cart",
            price=Decimal("25.00"),
            stock=3,
        )
        CartItem.objects.create(cart=cart, product=product, quantity=1)
        response = self.client.get(self.url)
        self.assertEqual(len(response.data["items"]), 1)
        self.assertEqual(response.data["items"][0]["product_name"], "In Cart")


class AddToCartViewTests(APITestCase):
    def setUp(self):
        self.url = reverse("cart-add")
        self.user = User.objects.create_user(
            email="add@example.com",
            username="adduser",
            password="pass123",
        )
        self.product = Product.objects.create(
            name="Addable",
            price=Decimal("15.00"),
            stock=10,
        )
        self.client.force_authenticate(user=self.user)

    def test_add_item_success(self):
        response = self.client.post(
            self.url, {"product_id": self.product.id, "quantity": 2},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        cart = Cart.objects.get(user=self.user)
        self.assertEqual(cart.items.count(), 1)
        self.assertEqual(cart.items.first().quantity, 2)

    def test_add_item_increments_existing(self):
        cart = Cart.objects.create(user=self.user)
        CartItem.objects.create(cart=cart, product=self.product, quantity=1)
        response = self.client.post(
            self.url, {"product_id": self.product.id, "quantity": 3},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(cart.items.first().quantity, 4)

    def test_add_item_missing_product_id(self):
        response = self.client.post(
            self.url, {"quantity": 1}, format="json"
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_add_item_nonexistent_product(self):
        response = self.client.post(
            self.url, {"product_id": 9999, "quantity": 1},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_add_item_unauthenticated(self):
        self.client.force_authenticate(user=None)
        response = self.client.post(
            self.url, {"product_id": self.product.id, "quantity": 1},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)


class ManageCartItemViewTests(APITestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            email="manage@example.com",
            username="manageuser",
            password="pass123",
        )
        self.product = Product.objects.create(
            name="Manageable",
            price=Decimal("10.00"),
            stock=5,
        )
        self.cart = Cart.objects.create(user=self.user)
        self.item = CartItem.objects.create(
            cart=self.cart, product=self.product, quantity=3,
        )
        self.url = reverse("cart-item-manage", args=[self.item.id])
        self.client.force_authenticate(user=self.user)

    def test_increase_quantity(self):
        response = self.client.patch(
            self.url, {"change": 1}, format="json"
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.item.refresh_from_db()
        self.assertEqual(self.item.quantity, 4)

    def test_decrease_quantity(self):
        response = self.client.patch(
            self.url, {"change": -1}, format="json"
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.item.refresh_from_db()
        self.assertEqual(self.item.quantity, 2)

    def test_decrease_to_zero_removes_item(self):
        response = self.client.patch(
            self.url, {"change": -3}, format="json"
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertFalse(CartItem.objects.filter(pk=self.item.id).exists())

    def test_increase_beyond_stock(self):
        response = self.client.patch(
            self.url, {"change": 10}, format="json"
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("error", response.data)

    def test_missing_change_field(self):
        response = self.client.patch(self.url, {}, format="json")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_delete_item(self):
        response = self.client.delete(self.url)
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        self.assertFalse(CartItem.objects.filter(pk=self.item.id).exists())

    def test_manage_other_users_item(self):
        other = User.objects.create_user(
            email="other@example.com",
            username="other",
            password="pass123",
        )
        self.client.force_authenticate(user=other)
        response = self.client.patch(
            self.url, {"change": 1}, format="json"
        )
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
