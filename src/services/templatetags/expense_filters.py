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
