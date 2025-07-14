from django import template

register = template.Library()

@register.filter
def get_item(obj, key):
    return getattr(obj, key, '')

@register.filter
def floatval(value):
    try:
        return float(value)
    except (ValueError, TypeError):
        return 0