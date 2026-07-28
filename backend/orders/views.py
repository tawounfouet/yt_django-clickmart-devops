from django.db import transaction
from django.shortcuts import get_object_or_404
from rest_framework.views import APIView
from rest_framework.permissions import IsAuthenticated
from carts.models import Cart, CartItem
from rest_framework.response import Response
from products.models import Product
from .models import Order, OrderItem
from .serializers import OrderSerializer
from rest_framework import status
from .utils import send_order_notification
from rest_framework.generics import ListAPIView, RetrieveAPIView


class PlaceOrderView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        try:
            cart = Cart.objects.get(user=request.user)
        except Cart.DoesNotExist:
            return Response(
                {'error': 'No cart found'},
                status=status.HTTP_400_BAD_REQUEST
            )

        if cart.items.count() == 0:
            return Response(
                {'error': 'Cart is empty'},
                status=status.HTTP_400_BAD_REQUEST
            )

        shipping_address = request.data.get("shippingAddress")
        if not shipping_address:
            return Response(
                {'error': 'Shipping address is required'},
                status=status.HTTP_400_BAD_REQUEST
            )

        with transaction.atomic():
            order = Order.objects.create(
                user=request.user,
                subtotal=cart.subtotal,
                tax_amount=cart.tax_amount,
                grand_total=cart.grand_total,
                address=shipping_address.get("address"),
                phone=shipping_address.get("phone"),
                city=shipping_address.get("city"),
                state=shipping_address.get("state"),
                zip_code=shipping_address.get("zipCode"),
            )

            for item in cart.items.select_related('product').all():
                product = Product.objects.select_for_update().get(
                    pk=item.product.pk
                )

                if product.stock < item.quantity:
                    raise ValueError(
                        f'Stock insuffisant pour {product.name}. '
                        f'Disponible : {product.stock}'
                    )

                product.stock -= item.quantity
                product.save()

                OrderItem.objects.create(
                    order=order,
                    product=product,
                    quantity=item.quantity,
                    price=product.price,
                    total_price=item.total_price
                )

            cart.items.all().delete()

        try:
            send_order_notification(order)
        except Exception:
            pass

        serializer = OrderSerializer(order)
        return Response(serializer.data, status=status.HTTP_201_CREATED)


class MyOrdersView(ListAPIView):
    permission_classes = [IsAuthenticated]
    serializer_class = OrderSerializer

    def get_queryset(self):
        return Order.objects.filter(user=self.request.user)


class OrderDetailView(RetrieveAPIView):
    permission_classes = [IsAuthenticated]
    serializer_class = OrderSerializer

    def get_object(self):
        pk = self.kwargs.get('pk')
        return get_object_or_404(Order, pk=pk, user=self.request.user)
