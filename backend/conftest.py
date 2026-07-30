import pytest
from model_bakery import baker
from rest_framework.test import APIClient
from django.contrib.auth import get_user_model

User = get_user_model()


@pytest.fixture
def user(db):
    """A persisted user with known credentials."""
    return baker.make(User, email="test@example.com", username="testuser")


@pytest.fixture
def api_client():
    """Unauthenticated DRF test client."""
    return APIClient()


@pytest.fixture
def authenticated_client(user):
    """Authenticated DRF test client (force_authenticate bypasses JWT)."""
    client = APIClient()
    client.force_authenticate(user=user)
    return client


@pytest.fixture
def product(db):
    """A product with default values."""
    from products.models import Product
    return baker.make(Product, name="Test Product", price=29.99, stock=10)


@pytest.fixture
def cart(user, db):
    """A cart belonging to the default user."""
    from carts.models import Cart
    return baker.make(Cart, user=user)


@pytest.fixture
def cart_item(cart, product, db):
    """A cart item linking the default cart and product."""
    from carts.models import CartItem
    return baker.make(CartItem, cart=cart, product=product, quantity=2)


@pytest.fixture
def order(user, db):
    """An order belonging to the default user."""
    from orders.models import Order
    return baker.make(Order, user=user, subtotal=100.00, tax_amount=10.00, grand_total=110.00)
