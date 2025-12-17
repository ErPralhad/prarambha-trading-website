from ecommerce.models import Product
import numpy as np

def recommend_products(current_product, limit=4):
    """
    Simple AI logic:
    Recommend products from the same category
    """
    candidates = Product.objects.filter(
        category=current_product.category
    ).exclude(id=current_product.id)

    if not candidates.exists():
        return []  # no recommendations available

    # Randomly pick up to 'limit' products
    candidates_list = list(candidates)
    if len(candidates_list) <= limit:
        return candidates_list
    else:
        return list(np.random.choice(candidates_list, limit, replace=False))
