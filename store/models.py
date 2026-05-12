from django.db import models
from django.contrib.auth.models import User


# ================= PRODUCT =================
class Product(models.Model):
    name = models.CharField(max_length=200)
    description = models.TextField()
    brand = models.CharField(max_length=100, blank=True)

    category = models.CharField(max_length=100)

    base_price = models.DecimalField(max_digits=10, decimal_places=2, default=0)

    stock = models.IntegerField(default=0)

    has_variants = models.BooleanField(default=False)

    image = models.ImageField(upload_to='products/')
    is_active = models.BooleanField(default=True)

    slug = models.SlugField(unique=True, null=True, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.name
    
    def get_price(self, variant_id=None):
        if self.has_variants:
            if variant_id:
                variant = self.variants.filter(id=variant_id).first()
                if variant:
                    return variant.price

            # fallback only
            variant = self.variants.first()
            if variant:
                return variant.price

        return self.base_price
    


# ================= PRODUCT IMAGES =================
class ProductImage(models.Model):
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name="images")
    image = models.ImageField(upload_to='products/')

    def __str__(self):
        return self.product.name


# ================= PRODUCT VARIANT =================
class ProductVariant(models.Model):
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name="variants")

    color = models.CharField(max_length=50, blank=True, null=True)
    size = models.CharField(max_length=10, blank=True, null=True)

    price = models.DecimalField(max_digits=10, decimal_places=2)
    stock = models.IntegerField(default=0)

    image = models.ImageField(upload_to='variants/', null=True, blank=True)

    def __str__(self):
        return f"{self.product.name} - {self.color} - {self.size}"


# ================= ORDER =================
class Order(models.Model):
    STATUS_CHOICES = (
        ('Placed', 'Order Placed'),
        ('Processing', 'Processing'),
        ('Shipped', 'Shipped'),
        ('Out for Delivery', 'Out for Delivery'),
        ('Delivered', 'Delivered'),
    )

    user = models.ForeignKey(User, on_delete=models.CASCADE, null=True)
    name = models.CharField(max_length=200)
    address = models.TextField()

    total_price = models.DecimalField(max_digits=10, decimal_places=2)

    payment_method = models.CharField(max_length=20, default='COD')

    status = models.CharField(max_length=30, choices=STATUS_CHOICES, default='Placed')

    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.name


# ================= ORDER ITEM =================
class OrderItem(models.Model):
    order = models.ForeignKey(Order, on_delete=models.CASCADE)

    product = models.ForeignKey(Product, on_delete=models.CASCADE, null=True)
    variant = models.ForeignKey(ProductVariant, on_delete=models.SET_NULL, null=True, blank=True)

    price = models.FloatField()
    quantity = models.IntegerField()

    def __str__(self):
        return self.product.name


# ================= PROFILE =================
class Profile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    phone = models.CharField(max_length=15)
    address = models.TextField(blank=True)

    def __str__(self):
        return self.user.username


# ================= ADDRESS =================
class Address(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="addresses")

    full_name = models.CharField(max_length=200)
    phone = models.CharField(max_length=15)

    address_line = models.TextField()
    city = models.CharField(max_length=100)
    state = models.CharField(max_length=100)
    pincode = models.CharField(max_length=10)

    is_default = models.BooleanField(default=False)

    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.full_name} - {self.city}"


# ================= WISHLIST =================
class Wishlist(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    product = models.ForeignKey(Product, on_delete=models.CASCADE)

    class Meta:
        unique_together = ('user', 'product')


# ================= REVIEW =================
from django.core.validators import MinValueValidator, MaxValueValidator

class Review(models.Model):
    product = models.ForeignKey('Product', on_delete=models.CASCADE, related_name="reviews")
    user = models.ForeignKey(User, on_delete=models.CASCADE)

    rating = models.IntegerField(
        validators=[MinValueValidator(1), MaxValueValidator(5)]
    )

    comment = models.TextField()

    image = models.ImageField(upload_to='reviews/', null=True, blank=True)

    is_verified = models.BooleanField(default=False)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)  # ⭐ NEW

    def __str__(self):
        return f"{self.user.username} - {self.product.name}"

    class Meta:
        unique_together = ['product', 'user']  # ⭐ NEW



# ================= REVIEW =================
class ReturnRequest(models.Model):

    RETURN_STATUS = (
        ('Pending','Pending'),
        ('Approved', 'Approved'),
        ('Rejected', 'Rejected'),
        ('Completed', 'Completed'),
    )

    REASON_CHOICES = (
        ('Damaged', 'Damaged'),
        ('Wrong Product', 'Wrong Product'),
        ('Size Issue', 'Size Issue'),
        ('Quality Issue', 'Quality Issue'),
        ('Other', 'Other'),
    )

    order = models.ForeignKey(Order, on_delete=models.CASCADE)
    order_item = models.ForeignKey(OrderItem, on_delete=models.CASCADE)

    user = models.ForeignKey(User, on_delete=models.CASCADE)

    reason = models.CharField(max_length=100, choices=REASON_CHOICES)

    description = models.TextField(blank=True, null=True)

    status = models.CharField(
        max_length=20,
        choices=RETURN_STATUS,
        default='Pending'
    )

    return_image = models.ImageField(
        upload_to='return_images/',
        blank=True,
        null=True
    )

    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Return #{self.id}"