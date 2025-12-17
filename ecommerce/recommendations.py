# ecommerce/recommendations.py
import pandas as pd
from sklearn.metrics.pairwise import cosine_similarity

def get_product_recommendations(user, num_recommendations=5):
    from .models import ProductView, Product

    # Get all product views
    views = ProductView.objects.all().values('user_id', 'product_id')

    if not views:
        # fallback: return random products if no data
        return Product.objects.order_by('?')[:num_recommendations]

    df = pd.DataFrame(views)

    # Create user-product matrix
    user_product_matrix = df.pivot_table(index='user_id', columns='product_id', aggfunc='size', fill_value=0)

    # Compute product similarity (cosine)
    product_sim = cosine_similarity(user_product_matrix.T)
    product_sim_df = pd.DataFrame(product_sim, index=user_product_matrix.columns, columns=user_product_matrix.columns)

    # Get products the user has viewed
    user_views = user_product_matrix.loc[user.id] if user.id in user_product_matrix.index else pd.Series(dtype=int)
    if user_views.empty:
        return Product.objects.order_by('?')[:num_recommendations]

    # Find similar products
    similar_scores = product_sim_df[user_views[user_views > 0].index].sum(axis=1)
    similar_scores = similar_scores.drop(user_views[user_views > 0].index, errors='ignore')  # remove already viewed

    recommended_ids = similar_scores.sort_values(ascending=False).head(num_recommendations).index.tolist()
    return Product.objects.filter(id__in=recommended_ids)
