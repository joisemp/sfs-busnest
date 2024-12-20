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


def generate_unique_code(model):
    """Generates a unique code with a 5-character alphanumeric code."""
    def generate_code():
        return ''.join(random.choices(string.ascii_lowercase + string.digits, k=6))
    
    code = f"{generate_code()}"
    model_class = model
    while model_class.objects.filter(code=code).exists():
        code = f"{generate_code()}"
    return code