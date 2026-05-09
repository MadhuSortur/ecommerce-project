from django.contrib import admin
from .models import *
from .models import Product, ProductVariant, ProductImage, Order, OrderItem, Profile, Wishlist 
from .models import ReturnRequest
from django.utils.html import format_html
# Variant inside Product
class ProductVariantInline(admin.TabularInline):
    model = ProductVariant
    extra = 1


# Multiple images inside Product
class ProductImageInline(admin.TabularInline):
    model = ProductImage
    extra = 1


@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = ['name', 'category', 'base_price', 'stock', 'is_active']
    prepopulated_fields = {"slug": ("name",)}

    inlines = [ProductVariantInline, ProductImageInline]


@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    list_display = ['id', 'user', 'total_price', 'status', 'created_at']


@admin.register(OrderItem)
class OrderItemAdmin(admin.ModelAdmin):
    list_display = ['order', 'product', 'variant', 'price', 'quantity']


@admin.register(Profile)
class ProfileAdmin(admin.ModelAdmin):
    list_display = ['user', 'phone']


@admin.register(Wishlist)
class WishlistAdmin(admin.ModelAdmin):
    list_display = ['user', 'product']


@admin.register(ReturnRequest)
class ReturnRequestAdmin(admin.ModelAdmin):

    list_display = (
        'id',
        'user',
        'order',
        'reason',
        'status',
        'return_image_preview',
        'created_at'
    )

    def return_image_preview(self, obj):

        if obj.return_image:
            return format_html(
                '<img src="{}" width="70" height="70" style="border-radius:8px;" />',
                obj.return_image.url
            )

        return "No Image"