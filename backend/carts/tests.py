from decimal import Decimal
import pytest
from django.urls import reverse
from rest_framework import status
from model_bakery import baker

from .models import Cart, CartItem
from products.models import Product


class TestCartModel:
    @pytest.fixture
    def cart_item(self, user, db):
        product = baker.make(Product, name="Cart Item", price=10.00, stock=5, tax_percent=20.00)
        cart = baker.make(Cart, user=user)
        return baker.make(CartItem, cart=cart, product=product, quantity=2)

    def test_cart_str(self, cart):
        assert "cart" in str(cart).lower()

    def test_cart_subtotal(self, cart_item):
        assert cart_item.cart.subtotal == Decimal("20.00")

    def test_cart_tax_amount(self, cart_item):
        assert cart_item.cart.tax_amount == Decimal("4.00")

    def test_cart_grand_total(self, cart_item):
        assert cart_item.cart.grand_total == Decimal("24.00")

    def test_cart_empty_subtotal(self, cart_item):
        cart_item.delete()
        assert cart_item.cart.subtotal == Decimal("0.00")

    def test_cart_empty_grand_total(self, cart_item):
        cart_item.delete()
        assert cart_item.cart.grand_total == Decimal("0.00")

    def test_cart_multiple_items(self, cart_item):
        p2 = baker.make(Product, name="Second", price=5.00, stock=10)
        baker.make(CartItem, cart=cart_item.cart, product=p2, quantity=3)
        assert cart_item.cart.subtotal == Decimal("35.00")

    def test_cart_item_total_price(self, cart_item):
        assert cart_item.total_price == Decimal("20.00")

    def test_cart_item_str(self, cart_item):
        assert "Cart Item" in str(cart_item)
        assert "2" in str(cart_item)


class TestCartView:
    URL = reverse("cart")

    def test_get_cart_unauthenticated(self, api_client):
        response = api_client.get(self.URL)
        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_get_cart_creates_if_missing(self, db, authenticated_client):
        response = authenticated_client.get(self.URL)
        assert response.status_code == status.HTTP_200_OK
        assert "items" in response.data

    def test_get_cart_with_items(self, db, authenticated_client, user):
        cart = baker.make(Cart, user=user)
        product = baker.make(Product, name="In Cart", price=25.00, stock=3)
        baker.make(CartItem, cart=cart, product=product, quantity=1)
        response = authenticated_client.get(self.URL)
        assert len(response.data["items"]) == 1
        assert response.data["items"][0]["product_name"] == "In Cart"


class TestAddToCartView:
    URL = reverse("cart-add")

    @pytest.fixture
    def product(self, db):
        return baker.make(Product, name="Addable", price=15.00, stock=10)

    def test_add_item_success(self, db, authenticated_client, product):
        response = authenticated_client.post(
            self.URL, {"product_id": product.id, "quantity": 2}, format="json"
        )
        assert response.status_code == status.HTTP_200_OK

    def test_add_item_increments_existing(self, db, authenticated_client, product, user):
        cart = baker.make(Cart, user=user)
        baker.make(CartItem, cart=cart, product=product, quantity=1)
        response = authenticated_client.post(
            self.URL, {"product_id": product.id, "quantity": 3}, format="json"
        )
        assert response.status_code == status.HTTP_200_OK
        assert cart.items.first().quantity == 4

    def test_add_item_missing_product_id(self, authenticated_client):
        response = authenticated_client.post(self.URL, {"quantity": 1}, format="json")
        assert response.status_code == status.HTTP_400_BAD_REQUEST

    def test_add_item_nonexistent_product(self, db, authenticated_client):
        response = authenticated_client.post(
            self.URL, {"product_id": "00000000-0000-0000-0000-000000000000", "quantity": 1},
            format="json",
        )
        assert response.status_code == status.HTTP_404_NOT_FOUND

    def test_add_item_unauthenticated(self, db, api_client, product):
        response = api_client.post(
            self.URL, {"product_id": product.id, "quantity": 1}, format="json"
        )
        assert response.status_code == status.HTTP_401_UNAUTHORIZED


class TestManageCartItemView:
    @pytest.fixture
    def item(self, db, user):
        product = baker.make(Product, name="Manageable", price=10.00, stock=5)
        cart = baker.make(Cart, user=user)
        return baker.make(CartItem, cart=cart, product=product, quantity=3)

    @pytest.fixture
    def url(self, item):
        return reverse("cart-item-manage", args=[item.id])

    def test_increase_quantity(self, authenticated_client, item, url):
        response = authenticated_client.patch(url, {"change": 1}, format="json")
        assert response.status_code == status.HTTP_200_OK
        item.refresh_from_db()
        assert item.quantity == 4

    def test_decrease_quantity(self, authenticated_client, item, url):
        response = authenticated_client.patch(url, {"change": -1}, format="json")
        assert response.status_code == status.HTTP_200_OK
        item.refresh_from_db()
        assert item.quantity == 2

    def test_decrease_to_zero_removes_item(self, authenticated_client, item, url):
        response = authenticated_client.patch(url, {"change": -3}, format="json")
        assert response.status_code == status.HTTP_200_OK
        assert not CartItem.objects.filter(pk=item.id).exists()

    def test_increase_beyond_stock(self, authenticated_client, url):
        response = authenticated_client.patch(url, {"change": 10}, format="json")
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert "error" in response.data

    def test_missing_change_field(self, authenticated_client, url):
        response = authenticated_client.patch(url, {}, format="json")
        assert response.status_code == status.HTTP_400_BAD_REQUEST

    def test_delete_item(self, authenticated_client, item, url):
        response = authenticated_client.delete(url)
        assert response.status_code == status.HTTP_204_NO_CONTENT
        assert not CartItem.objects.filter(pk=item.id).exists()

    def test_manage_other_users_item(self, db, authenticated_client, url):
        other = baker.make("users.User", email="other@example.com")
        client = authenticated_client
        client.force_authenticate(user=other)
        response = client.patch(url, {"change": 1}, format="json")
        assert response.status_code == status.HTTP_404_NOT_FOUND
