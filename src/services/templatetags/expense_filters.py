from django import template

register = template.Library()

@register.filter(name='sum_field')
def sum_field(queryset, field_name):
    """
    Sum a specific field in a queryset.
    Usage: {{ queryset|sum_field:'field_name' }}
    """
    try:
        return sum(getattr(obj, field_name, 0) for obj in queryset)
    except (TypeError, AttributeError):
        return 0

@register.filter(name='get_item')
def get_item(dictionary, key):
    """
    Get an item from a dictionary using a key.
    Usage: {{ dictionary|get_item:key }}
    Useful for integer keys that can't be accessed with dot notation.
    """
    return dictionary.get(key)
