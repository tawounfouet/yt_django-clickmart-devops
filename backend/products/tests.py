from decimal import Decimal
import pytest
from django.urls import reverse
from rest_framework import status
from model_bakery import baker

from .models import Product


class TestProductModel:
    def test_product_str_returns_name(self, product):
        assert str(product) == "Test Product"

    def test_product_default_is_active(self, product):
        assert product.is_active

    def test_product_created_at_auto_set(self, product):
        assert product.created_at is not None

    def test_product_updated_at_auto_set(self, product):
        assert product.updated_at is not None

    def test_product_inactive_not_listed(self, db):
        baker.make(Product, is_active=False)
        baker.make(Product, is_active=True)
        assert Product.objects.filter(is_active=True).count() == 1


class TestProductList:
    URL = reverse("product-list")

    def test_list_returns_only_active(self, db, api_client):
        baker.make(Product, name="Active", is_active=True)
        baker.make(Product, name="Inactive", is_active=False)
        response = api_client.get(self.URL)
        assert response.status_code == status.HTTP_200_OK
        assert len(response.data["results"]) == 1
        assert response.data["results"][0]["name"] == "Active"

    def test_list_returns_empty_when_no_active(self, db, api_client):
        baker.make(Product, is_active=False)
        response = api_client.get(self.URL)
        assert len(response.data["results"]) == 0


class TestProductDetail:
    @pytest.fixture
    def product(self, db):
        return baker.make(Product, name="Detail Item", price=15.50, stock=7)

    @pytest.fixture
    def url(self, product):
        return reverse("product-detail", args=[product.pk])

    def test_detail_returns_product(self, api_client, url):
        response = api_client.get(url)
        assert response.status_code == status.HTTP_200_OK
        assert response.data["name"] == "Detail Item"

    def test_detail_inactive_returns_404(self, api_client, product, url):
        product.is_active = False
        product.save()
        response = api_client.get(url)
        assert response.status_code == status.HTTP_404_NOT_FOUND

    def test_detail_nonexistent_returns_404(self, db, api_client):
        url = reverse("product-detail", args=["00000000-0000-0000-0000-000000000000"])
        response = api_client.get(url)
        assert response.status_code == status.HTTP_404_NOT_FOUND

    def test_detail_includes_all_fields(self, api_client, url):
        response = api_client.get(url)
        expected_keys = {
            "id", "name", "description", "image", "price",
            "stock", "tax_percent", "created_at", "updated_at",
        }
        assert set(response.data.keys()) == expected_keys
