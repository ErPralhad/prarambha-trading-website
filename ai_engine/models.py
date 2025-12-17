from django.db import models
from django.contrib.auth.models import User
from ecommerce.models import Product

class ProductView(models.Model):
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name="ai_product_views"
    )
    product = models.ForeignKey(
        Product,
        on_delete=models.CASCADE,
        related_name="ai_views"
    )
    viewed_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.user} viewed {self.product}"
