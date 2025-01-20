from django import forms


class BootstrapFormMixin:
    """
    A mixin to automatically add Bootstrap classes to form fields based on their type,
    show errors below fields without list styling, and display help text.
    """
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field_name, field in self.fields.items():
            widget = field.widget

            # Add 'form-control' class to all fields except Checkboxes and RadioSelect
            if isinstance(widget, forms.CheckboxInput):
                widget.attrs['class'] = widget.attrs.get('class', '') + ' form-check-input'
            elif isinstance(widget, forms.RadioSelect):
                widget.attrs['class'] = widget.attrs.get('class', '') + ' form-check-input'
            else:
                widget.attrs['class'] = widget.attrs.get('class', '') + ' form-control'

            # Special handling for select elements
            if isinstance(widget, forms.Select):
                widget.attrs['class'] += ' form-select'

            # Add Bootstrap class for error styling
            if field_name in self.errors:
                widget.attrs['class'] += ' is-invalid'

    def as_p(self):
        """
        Render the form fields as <p> elements with Bootstrap styling, error messages,
        and help text. Non-field errors are displayed at the top of the form.
        """
        output = []

        # Add non-field errors at the top
        if self.non_field_errors():
            output.append(f"""
            <div class="alert alert-danger" role="alert">
                { " ".join(self.non_field_errors()) }
            </div>
            """)

        # Render each field
        for field_name, field in self.fields.items():
            # Field widget, errors, and help_text
            bound_field = self[field_name]
            field_errors = bound_field.errors
            is_invalid = 'is-invalid' if field_errors else ''

            error_html = ''
            if field_errors:
                error_html = f'<p class="text-danger" style="margin-top: -15px;">{ " ".join(field_errors) }</p>'

            # Help text (if any)
            help_text_html = ''
            if field.help_text:
                help_text_html = f'<small class="form-text text-muted">{field.help_text}</small>'

            # Check if the field should be rendered as a switch
            is_switch = getattr(field, 'is_switch', False)

            if isinstance(bound_field.field.widget, forms.CheckboxInput) and is_switch:
                # Render as a switch
                output.append(f"""
                <div class="form-check form-switch mb-3">
                    {bound_field}
                    <label class="form-check-label" for="{bound_field.id_for_label}">
                        {bound_field.label}
                    </label>
                    {error_html}
                    {help_text_html}
                </div>
                """)
            elif isinstance(bound_field.field.widget, forms.CheckboxInput):
                # Render as a regular checkbox
                output.append(f"""
                <div class="form-check mb-3">
                    {bound_field}
                    <label class="form-check-label" for="{bound_field.id_for_label}">
                        {bound_field.label}
                    </label>
                    {error_html}
                    {help_text_html}
                </div>
                """)
            else:
                # Render other fields normally
                label_html = ''
                if bound_field.label:  # Only add the label if it is not an empty string
                    label_html = f'<label for="{bound_field.id_for_label}" class="mb-1 ps-1">{bound_field.label}</label>'

                output.append(f"""
                <p class="form-group">
                    {label_html}
                    {bound_field}
                    {error_html}
                    {help_text_html}
                </p>
                """)

        return ''.join(output)
