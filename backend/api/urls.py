from django.urls import path
from rest_framework.throttling import ScopedRateThrottle
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView
from users import views as UserViews
from products import views as ProductViews
from carts import views as CartViews
from orders import views as OrderViews


class ThrottledTokenObtainPairView(TokenObtainPairView):
    throttle_classes = [ScopedRateThrottle]
    throttle_scope = 'auth'


urlpatterns = [
    path('register/', UserViews.RegisterView.as_view(), name='register'),

    # USER APIs
    path('token/', ThrottledTokenObtainPairView.as_view(), name='token_obtain_pair'),
    path('token/refresh/', TokenRefreshView.as_view(), name='token_refresh'),
    path('profile/', UserViews.ProfileView.as_view(), name='profile'),

    # Products APIs
    path('products/', ProductViews.ProductListView.as_view(), name='product-list'),
    path('products/<int:pk>/', ProductViews.ProductDetailView.as_view(), name='product-detail'),

    # Cart API
    path('cart/', CartViews.CartView.as_view(), name='cart'),
    path('cart/add/', CartViews.AddToCartView.as_view(), name='cart-add'),
    path('cart/items/<int:item_id>/', CartViews.ManageCartItemView.as_view(), name='cart-item-manage'),

    # Orders
    path('orders/place/', OrderViews.PlaceOrderView.as_view(), name='order-place'),
    path('orders/', OrderViews.MyOrdersView.as_view(), name='my-orders'),
    path('orders/<int:pk>/', OrderViews.OrderDetailView.as_view(), name='order-detail'),
]
