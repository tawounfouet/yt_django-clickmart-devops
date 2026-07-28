from django.urls import path
from orders.api.views import PlaceOrderView, MyOrdersView, OrderDetailView


urlpatterns = [
    path('orders/place/', PlaceOrderView.as_view(), name='order-place'),
    path('orders/', MyOrdersView.as_view(), name='my-orders'),
    path('orders/<int:pk>/', OrderDetailView.as_view(), name='order-detail'),
]
