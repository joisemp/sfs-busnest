from django.core.exceptions import ValidationError

def validate_excel_file(value):
    if not value.name.endswith(('.xlsx', '.xls')):
        raise ValidationError("Only Excel files (.xlsx, .xls) are allowed.")
