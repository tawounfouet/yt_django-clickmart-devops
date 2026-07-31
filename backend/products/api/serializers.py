from apps.core.mixins import ValidateFieldsMixin
from rest_framework import serializers
from products.models import Product


class ProductSerializer(ValidateFieldsMixin, serializers.ModelSerializer):
    class Meta:
        model = Product
        fields = [
            'id', 'name', 'description', 'image', 'price',
            'stock', 'tax_percent', 'created_at', 'updated_at',
        ]
