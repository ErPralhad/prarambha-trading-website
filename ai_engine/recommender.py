from django.db.models import Count
from ecommerce.models import Product
from .models import ProductView

def get_recommendations(user, current_product, limit=4):
    """
    AI Recommendation based on:
    - Same category
    - Product popularity
    - User behavior
    """

    # Get products viewed by this user
    viewed_products = ProductView.objects.filter(
        user=user
    ).values_list('product_id', flat=True)

    # Recommend products from same category
    recommendations = (
        Product.objects
        .filter(category=current_product.category)
        .exclude(id=current_product.id)
        .exclude(id__in=viewed_products)
        .annotate(views=Count('ai_views'))
        .order_by('-views')[:limit]
    )

    return recommendations
