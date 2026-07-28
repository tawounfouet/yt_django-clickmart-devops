from rest_framework import serializers
from .models import Product


class ProductSerializer(serializers.ModelSerializer):
    class Meta:
        model = Product
        fields = [
            'id', 'name', 'description', 'image', 'price',
            'stock', 'tax_percent', 'created_at', 'updated_at',
        ]