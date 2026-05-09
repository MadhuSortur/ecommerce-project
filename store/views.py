from django.shortcuts import render
from .models import Product,ProductImage,ProductVariant
from .models import Order,OrderItem
from django.contrib.auth.models import User
from django.contrib.auth import authenticate, login, logout
from django.shortcuts import redirect
from django.contrib.auth.decorators import login_required
import json
from django.views.decorators.csrf import csrf_exempt
from .models import Profile
from .models import Wishlist
from django.http import JsonResponse
from django.shortcuts import get_object_or_404
from .models import Review
from .models import Address
from .models import ReturnRequest
from datetime import timedelta
from django.utils import timezone


# ================= LANDING =================
def landing(request):
    return render(request, 'store/landing.html')



# ================= HOME =================
def home(request):
    return render(request, 'store/home.html')



# ================= PRODUCTS =================
from django.db.models import Q, Case, When, IntegerField, Value

def products(request):
    query = request.GET.get('q')
    category = request.GET.get('category')

    items = Product.objects.all()

    if query:
        query = query.strip()

        items = Product.objects.annotate(
            priority=Case(
                # 🔥 Highest priority → exact name match
                When(name__iexact=query, then=Value(5)),

                # 🔥 Starts with (very strong match)
                When(name__istartswith=query, then=Value(4)),

                # 🔥 Contains in name
                When(name__icontains=query, then=Value(3)),

                # 🔥 Category match
                When(category__icontains=query, then=Value(2)),

                # 🔥 Description match
                When(description__icontains=query, then=Value(1)),

                default=Value(0),
                output_field=IntegerField()
            )
        ).filter(priority__gt=0).order_by('-priority')

    if category:
        items = items.filter(category=category)

    return render(request, 'store/products.html', {
        'items': items.distinct(),
        'selected_category': category
    })



# ================= PRODUCT DETAIL =================
from django.db.models import Avg
from .models import Review

def product_detail(request, id):
    product = get_object_or_404(Product, id=id)
    images = ProductImage.objects.filter(product=product)
    variants = ProductVariant.objects.filter(product=product).select_related()

    variant_data = []

    for v in variants:
        variant_data.append({
            "id": v.id,
            "color": v.color,
            "size": v.size,
            "price": float(v.price),
            "image": v.image.url if v.image else product.image.url,
            "stock": v.stock
        })

    # ⭐ Wishlist check
    is_wishlisted = False
    if request.user.is_authenticated:
        is_wishlisted = Wishlist.objects.filter(
            user=request.user,
            product=product
        ).exists()

    # ⭐ REVIEWS (NEW PART)
    reviews = Review.objects.filter(product=product).order_by('-created_at')

    avg_rating = reviews.aggregate(Avg('rating'))['rating__avg']
    avg_rating = avg_rating if avg_rating else 0

    from collections import Counter

    rating_counts = Counter(reviews.values_list('rating', flat=True))

    total_reviews = reviews.count() or 1  # avoid division by zero

    rating_data = {
        5: (rating_counts.get(5, 0) / total_reviews) * 100,
        4: (rating_counts.get(4, 0) / total_reviews) * 100,
        3: (rating_counts.get(3, 0) / total_reviews) * 100,
        2: (rating_counts.get(2, 0) / total_reviews) * 100,
        1: (rating_counts.get(1, 0) / total_reviews) * 100,
    }

    return render(request, 'store/product_detail.html', {
        'product': product,
        'images': images,
        'variant_json': json.dumps(variant_data),
        'is_wishlisted': is_wishlisted,

        # ⭐ NEW ADDED
        'reviews': reviews,
        'avg_rating': avg_rating,

        'rating_data': rating_data,
    })


# ================= WISHLIST PAGE =================

@login_required
def wishlist_page(request):
    items = Wishlist.objects.filter(user=request.user).select_related('product')

    return render(request, 'store/wishlist.html', {
        'items': items
    })

# ================= TOGGLE-WISHLIST =================

@login_required
def toggle_wishlist(request, id):
    product = get_object_or_404(Product, id=id)

    item = Wishlist.objects.filter(user=request.user, product=product)

    if item.exists():
        item.delete()
        status = 'removed'
    else:
        Wishlist.objects.create(user=request.user, product=product)
        status = 'added'

    # ⭐ NEW: get updated count
    count = Wishlist.objects.filter(user=request.user).count()

    return JsonResponse({
        'status': status,
        'count': count
    })


# ================= WISHLIST_COUNT =================

def wishlist_count(request):
    if request.user.is_authenticated:
        count = Wishlist.objects.filter(user=request.user).count()
    else:
        count = 0

    return {'wishlist_count': count}


# ================= CART =================

def cart(request):
    return render(request, 'store/cart.html')


# ================= CHECKOUT =================

@csrf_exempt
@login_required
def checkout(request):
    profile, created = Profile.objects.get_or_create(user=request.user)

    # ✅ GET ALL USER ADDRESSES
    addresses = request.user.addresses.all().order_by('-is_default', '-id')
    default_address = addresses.filter(is_default=True).first()

    if request.method == 'POST':

        # ✅ SELECTED ADDRESS ID
        address_id = request.POST.get('address_id')

        # 👉 If user selects existing address
        if address_id and address_id.strip():
            selected_address = Address.objects.get(id=address_id, user=request.user)

        # 👉 If user adds new address
        else:
            selected_address = Address.objects.create(
                user=request.user,
                full_name=request.POST.get('full_name'),
                phone=request.POST.get('phone'),
                address_line=request.POST.get('address_line'),
                city=request.POST.get('city'),
                state=request.POST.get('state'),
                pincode=request.POST.get('pincode'),
                is_default = not Address.objects.filter(user=request.user, is_default=True).exists()
            )

        total = request.POST.get('total')
        cart_data = request.POST.get('cart')

        # ✅ CREATE ORDER USING SELECTED ADDRESS
        order = Order.objects.create(
            user=request.user,
            name=selected_address.full_name,
            address=f"{selected_address.address_line}, {selected_address.city}, {selected_address.state} - {selected_address.pincode}",
            total_price=total
        )

        cart = json.loads(cart_data)

        for item in cart:

            variant = None
            product = None

            if item.get('variant_id'):
                variant = ProductVariant.objects.get(id=item['variant_id'])
                product = variant.product

                if variant.stock < item.get('quantity', 1):
                    return JsonResponse({'error': 'Out of stock'})

                variant.stock -= item.get('quantity', 1)
                variant.save()

            elif item.get('product_id'):
                product = Product.objects.get(id=item['product_id'])

            OrderItem.objects.create(
                order=order,
                product=product,
                variant=variant,
                price=item['price'],
                quantity=item.get('quantity', 1)
            )

        return JsonResponse({
            "success": True,
            "redirect_url": f"/success/?order_id={order.id}"
        })

    return render(request, 'store/checkout.html', {
        'profile': profile,
        'addresses': addresses,
        'default_address': default_address
    })


# ================= SUCCESS =================

@csrf_exempt
@login_required
def success(request):
    order_id = request.GET.get('order_id')

    order = get_object_or_404(Order, id=order_id, user=request.user)

    return render(request, 'store/success.html', {
        'order': order
    })

# ================= USER LOGIN =================

def user_login(request):
    error = None

    if request.method == 'POST':
        username = request.POST.get('username')
        password = request.POST.get('password')

        user = authenticate(request, username=username, password=password)

        if user is not None:
            login(request, user)
            return redirect('home')
        else:
            error = "Invalid username or password"

    return render(request, 'store/login.html', {
        'hide_navbar': True,
        'error': error
    })




# ================= USER LOGOUT =================

def user_logout(request):
    logout(request)
    return redirect('landing')


# ================= MY_ORDERS =================

@login_required
def my_orders(request):
    orders = Order.objects.filter(user=request.user).order_by('-created_at')

    return render(request, 'store/my_orders.html', {
        'orders': orders
    })


# ================= CANCEL_ORDER =================

from django.http import JsonResponse
from django.contrib.auth.decorators import login_required

@login_required
def cancel_order(request, order_id):
    try:
        order = Order.objects.get(id=order_id, user=request.user)

        # ✅ Only allow cancel if not shipped yet
        if order.status in ['Placed', 'Processing']:
            order.status = 'Cancelled'
            order.save()
            return JsonResponse({'success': True})

        else:
            return JsonResponse({'error': 'Order cannot be cancelled now'})

    except Order.DoesNotExist:
        return JsonResponse({'error': 'Order not found'})


# ================= REGISTER =================


from django.contrib import messages
from django.shortcuts import render, redirect
from .models import Profile, Address   # ✅ ADD THIS

def register(request):
    if request.method == 'POST':
        username = request.POST.get('username')
        password = request.POST.get('password')
        confirm_password = request.POST.get('confirm_password')
        email = request.POST.get('email')

        phone = request.POST.get('phone')

        # NEW ADDRESS FIELDS
        full_name = request.POST.get('full_name')
        address_line = request.POST.get('address_line')
        city = request.POST.get('city')
        state = request.POST.get('state')
        pincode = request.POST.get('pincode')

        # ✅ PASSWORD MATCH CHECK
        if password != confirm_password:
            messages.error(request, "Passwords do not match")
            return redirect('register')

        # ✅ USERNAME EXISTS CHECK
        if User.objects.filter(username=username).exists():
            messages.error(request, "Username already exists")
            return redirect('register')

        # ✅ PASSWORD LENGTH CHECK
        if len(password) < 6:
            messages.error(request, "Password must be at least 6 characters")
            return redirect('register')

        # CREATE USER
        user = User.objects.create_user(
            username=username,
            password=password,
            email=email
        )

        # CREATE PROFILE
        Profile.objects.create(
            user=user,
            phone=phone
        )

        # ✅ CREATE DEFAULT ADDRESS
        Address.objects.create(
            user=user,
            full_name=full_name,
            phone=phone,
            address_line=address_line,
            city=city,
            state=state,
            pincode=pincode,
            is_default=True
        )

        messages.success(request, "Account created successfully!")
        return redirect('login')

    return render(request, 'store/register.html', {'hide_navbar': True})

# ================= PROFILE =================

@login_required
def profile(request):
    profile, created = Profile.objects.get_or_create(user=request.user)

    return render(request, 'store/profile.html', {
        'profile': profile
    })


# ================= EDIT_PROFILE =================

@login_required
def edit_profile(request):
    profile, created = Profile.objects.get_or_create(user=request.user)

    if request.method == 'POST':
        profile.phone = request.POST.get('phone')
        profile.address = request.POST.get('address')
        profile.save()

        return redirect('profile')

    return render(request, 'store/edit_profile.html', {
        'profile': profile
    })



def has_purchased(user, product):
    return OrderItem.objects.filter(
        order__user=user,
        product=product
    ).exists()


# ================= ADD_REVIEW =================
@login_required
def add_review(request, id):
    product = get_object_or_404(Product, id=id)

    if request.method == "POST":
        rating = int(request.POST.get("rating"))
        comment = request.POST.get("comment")

        image = request.FILES.get('image')

        verified = has_purchased(request.user, product)

        # ✅ CHECK IF REVIEW ALREADY EXISTS
        review, created = Review.objects.get_or_create(
            product=product,
            user=request.user,
            defaults={
                'rating': rating,
                'comment': comment,
                'image': image,
                'is_verified': verified
            }
        )

        # ✅ IF ALREADY EXISTS → UPDATE IT
        if not created:
            review.rating = rating
            review.comment = comment
            review.is_verified = verified
            if image:
                review.image = image
            review.save()

    return redirect('product_detail', id=id)


# ================= EDIT_REVIEW =================


@login_required
def edit_review(request, id):
    review = get_object_or_404(Review, id=id, user=request.user)

    if request.method == "POST":
        review.rating = request.POST.get("rating")
        review.comment = request.POST.get("comment")
        review.save()

        return redirect('product_detail', id=review.product.id)

    return render(request, 'store/edit_review.html', {'review': review})


# ================= DELETE_REVIEW =================

@login_required
def delete_review(request, id):
    review = get_object_or_404(Review, id=id, user=request.user)
    product_id = review.product.id
    review.delete()

    return redirect('product_detail', id=product_id)



# ================= TRACK_ORDER =================
from django.shortcuts import render, get_object_or_404
from django.contrib.auth.decorators import login_required
from .models import Order

@login_required
def track_order(request, order_id):
    order = get_object_or_404(Order, id=order_id, user=request.user)

    steps = [
        'Placed',
        'Processing',
        'Shipped',
        'Out for Delivery',
        'Delivered'
    ]

    # ✅ FIX: handle cancelled orders
    if order.status == 'Cancelled':
        current_step = -1
    else:
        current_step = steps.index(order.status)

    return render(request, 'store/track_order.html', {
        'order': order,
        'steps': steps,
        'current_step': current_step
    })


# ================= SET_DEFAULT_ADDRESS =================

from django.contrib.auth.decorators import login_required

@login_required
def set_default_address(request, id):
    try:
        address = Address.objects.get(id=id, user=request.user)

        # remove old default
        Address.objects.filter(user=request.user, is_default=True).update(is_default=False)

        # set new default
        address.is_default = True
        address.save()

        return JsonResponse({"status": "ok"})

    except Address.DoesNotExist:
        return JsonResponse({"error": "Address not found"})
    


# ================= PLACE_ORDER =================
from django.http import JsonResponse
from django.shortcuts import get_object_or_404
import json

@login_required
def place_order(request):

    if request.method == "POST":

        data = json.loads(request.body)

        total = data.get("total")
        address_id = data.get("address_id")
        cart_data = data.get("cart")

        selected_address = get_object_or_404(
            Address,
            id=address_id,
            user=request.user
        )

        order = Order.objects.create(
            user=request.user,
            name=selected_address.full_name,
            address=f"{selected_address.address_line}, {selected_address.city}, {selected_address.state} - {selected_address.pincode}",
            total_price=total
        )

        for item in cart_data:

            variant = None
            product = None

            if item.get('variant_id'):
                variant = ProductVariant.objects.get(id=item['variant_id'])
                product = variant.product

            elif item.get('product_id'):
                product = Product.objects.get(id=item['product_id'])

            OrderItem.objects.create(
                order=order,
                product=product,
                variant=variant,
                price=item['price'],
                quantity=item.get('quantity', 1)
            )

        return JsonResponse({
            "success": True,
            "order_id": order.id
        })

    return JsonResponse({
        "success": False,
        "error": "Invalid request method"
    })


# ================= PAYMENT =================

@login_required
def payment(request):
    total = request.GET.get('total')
    address_id = request.GET.get('address_id')
    cart = request.GET.get('cart')

    return render(request, 'store/payment.html', {
        'total': total,
        'address_id': address_id,
        'cart': cart
    })

# ================= RETURN_ORDER =================

@login_required
def return_order(request, item_id):

    order_item = OrderItem.objects.get(id=item_id)

    delivery_date = order_item.order.created_at

    last_return_date = delivery_date + timedelta(days=7)

    if timezone.now() > last_return_date:
        return redirect('my_orders')

    already_requested = ReturnRequest.objects.filter(
        order_item=order_item
    ).exists()

    if already_requested:
        return redirect('my_orders')

    if request.method == "POST":

        reason = request.POST.get('reason')
        return_image = request.FILES.get('return_image')
        description = request.POST.get('description')

        ReturnRequest.objects.create(
            order=order_item.order,
            order_item=order_item,
            user=request.user,
            reason=reason,
            return_image=return_image,
            description=description
        )

        return redirect('my_orders')

    return render(request, 'store/return_order.html', {
        'item': order_item
    })