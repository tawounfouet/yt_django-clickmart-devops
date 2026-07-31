from apps.core.mixins import ValidateFieldsMixin
from rest_framework import serializers
from orders.models import Order, OrderItem


class OrderItemSerializer(ValidateFieldsMixin, serializers.ModelSerializer):
    class Meta:
        model = OrderItem
        fields = '__all__'


class OrderSerializer(ValidateFieldsMixin, serializers.ModelSerializer):
    items = OrderItemSerializer(many=True, read_only=True)

    class Meta:
        model = Order
        fields = '__all__'
