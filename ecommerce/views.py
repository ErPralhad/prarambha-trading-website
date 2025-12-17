from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.db.models import Sum, Count
from django.db.models.functions import TruncMonth
from django.utils.safestring import mark_safe
from django.contrib import messages
import json

from .models import Product, Order, OrderItem
from ai_engine.models import ProductView
from ai_engine.recommender import get_recommendations

from django.shortcuts import render

def home(request):
    return render(request, 'ecommerce/home.html')

# =========================
# PRODUCT LIST
# =========================
def product_list(request):
    products = Product.objects.all()
    return render(request, 'ecommerce/product_list.html', {
        'products': products
    })


# =========================
# PRODUCT DETAIL + AI TRACKING
# =========================
def product_detail(request, pk):
    product = get_object_or_404(Product, pk=pk)

    if request.user.is_authenticated:
        ProductView.objects.create(
            user=request.user,
            product=product
        )
        recommended_products = get_recommendations(request.user, product)
    else:
        recommended_products = []

    return render(request, 'ecommerce/product_detail.html', {
        'product': product,
        'recommended_products': recommended_products
    })


# =========================
# ADD TO CART
# =========================
def add_to_cart(request, product_id):
    product = get_object_or_404(Product, id=product_id)

    if product.stock <= 0:
        messages.error(request, "This product is out of stock")
        return redirect('product_detail', pk=product.id)

    cart = request.session.get('cart', {})
    product_id = str(product_id)

    if cart.get(product_id, 0) >= product.stock:
        messages.warning(request, "No more stock available")
        return redirect('view_cart')

    cart[product_id] = cart.get(product_id, 0) + 1
    request.session['cart'] = cart
    request.session.modified = True

    messages.success(request, "Product added to cart")
    return redirect('view_cart')

# =========================
# VIEW CART
# =========================
def view_cart(request):
    cart = request.session.get('cart', {})
    cart_items = []
    grand_total = 0

    for product_id, quantity in cart.items():
        product = get_object_or_404(Product, id=product_id)
        total_price = product.price * quantity

        cart_items.append({
            'id': product.id,
            'product': product,
            'quantity': quantity,
            'total_price': total_price
        })

        grand_total += total_price

    return render(request, 'ecommerce/cart.html', {
        'cart_items': cart_items,
        'grand_total': grand_total
    })


from django.contrib.auth.decorators import login_required

@login_required
def order_history(request):
    # Fetch all orders for the logged-in user
    orders = Order.objects.filter(email=request.user.email).order_by('-id')
    
    context = {
        'orders': orders
    }
    
    return render(request, 'ecommerce/order_history.html', context)

@login_required
def order_detail(request, order_id):
    order = get_object_or_404(Order, id=order_id, email=request.user.email)
    order_items = OrderItem.objects.filter(order=order)

    context = {
        'order': order,
        'order_items': order_items
    }
    return render(request, 'ecommerce/order_detail.html', context)


# =========================
# UPDATE CART QUANTITY (+ / -)
# =========================
def update_cart_quantity(request, product_id):
    cart = request.session.get('cart', {})
    product_id = str(product_id)
    action = request.GET.get('action')

    if product_id in cart:
        if action == 'increase':
            cart[product_id] += 1
        elif action == 'decrease':
            cart[product_id] -= 1
            if cart[product_id] <= 0:
                del cart[product_id]

    request.session['cart'] = cart
    request.session.modified = True
    return redirect('view_cart')


# =========================
# REMOVE FROM CART
# =========================
def remove_from_cart(request, product_id):
    cart = request.session.get('cart', {})
    product_id = str(product_id)

    if product_id in cart:
        del cart[product_id]

    request.session['cart'] = cart
    request.session.modified = True
    return redirect('view_cart')


def order_success(request, order_id):
    order = get_object_or_404(Order, id=order_id)
    return render(request, 'ecommerce/order_success.html', {'order': order})


# =========================
# CHECKOUT
# =========================
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from .models import Product, Order, OrderItem


@login_required(login_url='login')
def checkout(request):
    cart = request.session.get('cart', {})

    if not cart:
        messages.warning(request, "Your cart is empty")
        return redirect('view_cart')

    total = 0
    products = []

    # STEP 1: STOCK VALIDATION
    for product_id, qty in cart.items():
        product = get_object_or_404(Product, id=product_id)

        if qty > product.stock:
            messages.error(
                request,
                f"Not enough stock for {product.name}. Available: {product.stock}"
            )
            return redirect('view_cart')

        total += product.price * qty
        products.append((product, qty))

    # STEP 2: CREATE ORDER
    order = Order.objects.create(
        user=request.user,
        total_amount=total
    )

    # STEP 3: CREATE ORDER ITEMS + REDUCE STOCK
    for product, qty in products:
        OrderItem.objects.create(
            order=order,
            product=product,
            quantity=qty,
            price=product.price
        )

        # 🔥 CRITICAL PART — STOCK REDUCTION
        product.stock -= qty
        product.save()

    # STEP 4: CLEAR CART
    request.session['cart'] = {}
    request.session.modified = True

    messages.success(request, "Order placed successfully")
    return redirect('order_success', order_id=order.id)

# =========================
# DASHBOARD (OWNER / ADMIN)
# =========================
@login_required
def dashboard(request):
    total_products = Product.objects.count()
    total_orders = Order.objects.count()
    total_revenue = Order.objects.aggregate(
        total=Sum('total_amount')
    )['total'] or 0
    total_views = ProductView.objects.count()

    # Top-selling products
    top_products_qs = OrderItem.objects.values(
        'product__name'
    ).annotate(
        total_sold=Sum('quantity')
    ).order_by('-total_sold')[:5]

    # Most viewed products
    top_views_qs = ProductView.objects.values(
        'product__name'
    ).annotate(
        views_count=Count('id')
    ).order_by('-views_count')[:5]

    # Monthly sales
    monthly_sales_qs = (
        Order.objects.annotate(month=TruncMonth('created_at'))
        .values('month')
        .annotate(total_sales=Sum('total_amount'))
        .order_by('month')
    )

    monthly_sales = [
        {
            'month': item['month'].strftime('%Y-%m'),
            'total_sales': float(item['total_sales'] or 0)
        }
        for item in monthly_sales_qs
    ]

    recent_views = ProductView.objects.select_related(
        'product'
    ).order_by('-viewed_at')[:5]

    context = {
        'total_products': total_products,
        'total_orders': total_orders,
        'total_revenue': total_revenue,
        'total_views': total_views,
        'recent_views': recent_views,
        'top_products_json': mark_safe(json.dumps(list(top_products_qs))),
        'top_views_json': mark_safe(json.dumps(list(top_views_qs))),
        'monthly_sales_json': mark_safe(json.dumps(monthly_sales)),
    }

    return render(request, 'ecommerce/dashboard.html', context)

from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.models import User
from django.contrib import messages
from django.shortcuts import render, redirect

def signup_view(request):
    if request.method == 'POST':
        username = request.POST['username']
        email = request.POST['email']
        password = request.POST['password']
        password2 = request.POST['password2']

        if password != password2:
            messages.error(request, "Passwords do not match")
            return redirect('signup')

        if User.objects.filter(username=username).exists():
            messages.error(request, "Username already exists")
            return redirect('signup')

        user = User.objects.create_user(username=username, email=email, password=password)
        login(request, user)
        return redirect('product_list')

    return render(request, 'ecommerce/signup.html')


def login_view(request):
    if request.method == 'POST':
        username = request.POST['username']
        password = request.POST['password']

        user = authenticate(request, username=username, password=password)
        if user:
            login(request, user)
            return redirect('product_list')
        else:
            messages.error(request, "Invalid username or password")
            return redirect('login')

    return render(request, 'ecommerce/login.html')


def logout_view(request):
    logout(request)
    return redirect('product_list')


from django.shortcuts import render, get_object_or_404
from django.http import HttpResponse
from django.template.loader import get_template
from xhtml2pdf import pisa
from .models import Order, OrderItem

def generate_invoice_pdf(request, order_id):
    order = get_object_or_404(Order, id=order_id)
    order_items = OrderItem.objects.filter(order=order)

    template_path = 'ecommerce/invoice.html'
    context = {
        'order': order,
        'order_items': order_items,
        'total': sum(item.price * item.quantity for item in order_items),
    }

    response = HttpResponse(content_type='application/pdf')
    response['Content-Disposition'] = f'attachment; filename="invoice_{order.id}.pdf"'

    template = get_template(template_path)
    html = template.render(context)

    # Create PDF
    pisa_status = pisa.CreatePDF(html, dest=response)
    if pisa_status.err:
        return HttpResponse('We had some errors while generating the PDF <pre>' + html + '</pre>')

    return response
