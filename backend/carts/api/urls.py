from django.urls import path
from carts.api.views import CartView, AddToCartView, ManageCartItemView


urlpatterns = [
    path('cart/', CartView.as_view(), name='cart'),
    path('cart/add/', AddToCartView.as_view(), name='cart-add'),
    path('cart/items/<int:item_id>/', ManageCartItemView.as_view(), name='cart-item-manage'),
]
