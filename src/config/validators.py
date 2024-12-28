from django.core.exceptions import ValidationError

def validate_csv_file(value):
    if not value.name.endswith('.csv'):
        raise ValidationError("Only CSV files are allowed.")
