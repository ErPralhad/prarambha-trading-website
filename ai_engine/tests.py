from ecommerce.models import Product

def recommend_products(current_product, limit=4):
    """
    Simple AI logic:
    Recommend products from the same category
    """

    recommendations = Product.objects.filter(
        category=current_product.category
    ).exclude(id=current_product.id)[:limit]

    return recommendations
