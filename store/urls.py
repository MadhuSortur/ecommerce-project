from django.urls import path
from . import views
from django.conf import settings
from django.conf.urls.static import static

urlpatterns = [
    path('', views.landing, name='landing'),
    
    path('home/', views.home, name='home'), 
    path('products/', views.products, name='products'),
    path('cart/', views.cart, name='cart'),
    path('checkout/', views.checkout, name='checkout'),
    path('login/', views.user_login, name='login'),
    path('register/', views.register, name='register'),
    path('logout/', views.user_logout, name='logout'),
    path('my-orders/', views.my_orders, name='my_orders'),
    path('profile/', views.profile, name='profile'),
    path('edit-profile/', views.edit_profile, name='edit_profile'),
    path('product/<int:id>/', views.product_detail, name='product_detail'),
    path('wishlist/toggle/<int:id>/', views.toggle_wishlist, name='toggle_wishlist'),
    path('wishlist/', views.wishlist_page, name='wishlist'),
    path('product/<int:id>/review/', views.add_review, name='add_review'),
    path('review/edit/<int:id>/', views.edit_review, name='edit_review'),
    path('review/delete/<int:id>/', views.delete_review, name='delete_review'),
    path('review/edit/<int:id>/', views.edit_review, name='edit_review'),
    path('review/delete/<int:id>/', views.delete_review, name='delete_review'),
    path('track-order/<int:order_id>/', views.track_order, name='track_order'),
    path('cancel-order/<int:order_id>/', views.cancel_order, name='cancel_order'),
    path('set-default-address/<int:id>/', views.set_default_address, name='set_default_address'),
    path('place-order/', views.place_order, name='place_order'),
    path('payment/', views.payment, name='payment'),
    path('success/', views.success, name='success'),
    path('return-order/<int:item_id>/', views.return_order, name='return_order'),
]

urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
