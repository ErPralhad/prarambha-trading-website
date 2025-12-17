from django import template

register = template.Library()

@register.filter
def multiply(value, arg):
    """Multiply two numbers."""
    return value * arg

@register.filter
def sum_total(items):
    """Calculate the sum of item totals: price * quantity."""
    total = sum(item.price * item.quantity for item in items)
    return total
