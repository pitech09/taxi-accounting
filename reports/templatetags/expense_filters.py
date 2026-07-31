from django import template
from cashbook.models import CashTransaction

register = template.Library()

@register.filter
def category_label(category_code):
    """Return the human-readable label for a category code."""
    choices = dict(CashTransaction.CATEGORY_CHOICES)
    return choices.get(category_code, category_code)