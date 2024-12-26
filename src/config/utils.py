import random
import string


def generate_unique_slug(instance, base_slug):
    """Generates a unique slug with a 4-character alphanumeric code."""
    def generate_code():
        return ''.join(random.choices(string.ascii_lowercase + string.digits, k=4))
    
    slug = f"{base_slug}-{generate_code()}"
    model_class = instance.__class__
    while model_class.objects.filter(slug=slug).exists():
        slug = f"{base_slug}-{generate_code()}"
    return slug


def generate_unique_code(model, no_of_char=6, unique_field='id'):
    def generate_code():
        return ''.join(random.choices(string.ascii_lowercase + string.digits, k=no_of_char))
    
    code = generate_code()
    filter_kwargs = {unique_field: code}
    model_class = model.__class__
    while model_class.objects.filter(**filter_kwargs).exists():
        code = generate_code()
    return code
