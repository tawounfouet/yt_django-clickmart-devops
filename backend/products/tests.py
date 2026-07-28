from decimal import Decimal
from django.test import TestCase
from rest_framework.test import APITestCase
from rest_framework import status
from django.urls import reverse

from .models import Product


class ProductModelTests(TestCase):
    def setUp(self):
        self.product = Product.objects.create(
            name="Test Product",
            description="A test product",
            price=Decimal("29.99"),
            stock=10,
            tax_percent=Decimal("10.00"),
        )

    def test_product_creation(self):
        self.assertEqual(self.product.name, "Test Product")
        self.assertEqual(self.product.price, Decimal("29.99"))
        self.assertEqual(self.product.stock, 10)

    def test_product_str_returns_name(self):
        self.assertEqual(str(self.product), "Test Product")

    def test_product_default_is_active(self):
        self.assertTrue(self.product.is_active)

    def test_product_default_tax_percent(self):
        product = Product.objects.create(
            name="No Tax",
            price=Decimal("9.99"),
            stock=5,
        )
        self.assertEqual(product.tax_percent, Decimal("0.00"))

    def test_product_created_at_auto_set(self):
        self.assertIsNotNone(self.product.created_at)

    def test_product_updated_at_auto_set(self):
        self.assertIsNotNone(self.product.updated_at)

    def test_product_inactive_not_listed_by_default(self):
        Product.objects.create(
            name="Inactive",
            price=Decimal("5.00"),
            stock=1,
            is_active=False,
        )
        active_count = Product.objects.filter(is_active=True).count()
        self.assertEqual(active_count, 1)


class ProductListTests(APITestCase):
    def setUp(self):
        self.url = reverse("product-list")
        self.p1 = Product.objects.create(
            name="Active",
            price=Decimal("10.00"),
            stock=5,
        )
        self.p2 = Product.objects.create(
            name="Inactive",
            price=Decimal("20.00"),
            stock=3,
            is_active=False,
        )

    def test_list_returns_only_active(self):
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)
        self.assertEqual(response.data[0]["name"], "Active")

    def test_list_returns_empty_when_no_active(self):
        self.p1.is_active = False
        self.p1.save()
        response = self.client.get(self.url)
        self.assertEqual(len(response.data), 0)


class ProductDetailTests(APITestCase):
    def setUp(self):
        self.product = Product.objects.create(
            name="Detail Item",
            price=Decimal("15.50"),
            stock=7,
        )
        self.url = reverse("product-detail", args=[self.product.pk])

    def test_detail_returns_product(self):
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["name"], "Detail Item")

    def test_detail_inactive_returns_404(self):
        self.product.is_active = False
        self.product.save()
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_detail_nonexistent_returns_404(self):
        url = reverse("product-detail", args=[9999])
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_detail_includes_all_fields(self):
        response = self.client.get(self.url)
        expected_keys = {
            "id", "name", "description", "image", "price",
            "stock", "tax_percent", "created_at",
            "updated_at",
        }
        self.assertEqual(set(response.data.keys()), expected_keys)
