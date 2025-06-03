"""
forms.py - Custom authentication and registration forms for the core app

This module defines Django forms for user authentication and registration, extending Django's built-in forms
with additional fields and Bootstrap styling. It includes:

- CustomAuthenticationForm: A login form with Bootstrap styling for username and password fields.
- UserRegisterForm: A registration form that collects user and organization details, also styled for Bootstrap.
"""

from django import forms
from django.contrib.auth import get_user_model
from django.contrib.auth.forms import AuthenticationForm, UserCreationForm
from config.mixins import form_mixin

User = get_user_model()



class CustomAuthenticationForm(form_mixin.BootstrapFormMixin, AuthenticationForm):
    """
    A custom authentication form that extends BootstrapFormMixin and Django's AuthenticationForm.
    This form customizes the username and password fields to use Bootstrap-compatible widgets
    and ensures that both fields are marked as required in the HTML. It also removes the default
    label suffix and applies the 'form-control' CSS class to both fields for consistent styling.
    Attributes:
        username (forms.CharField): The username field, rendered as a required text input with Bootstrap styling.
        password (forms.CharField): The password field, rendered as a required password input with Bootstrap styling.
    Methods:
        __init__(*args, **kwargs): Initializes the form, removes the label suffix, and updates widget attributes for styling.
    """
    username = forms.CharField(
        widget=forms.TextInput(attrs={'required': True}))
    password = forms.CharField(
        widget=forms.PasswordInput(attrs={'required': True}))
    
    def __init__(self, *args, **kwargs):
        super(CustomAuthenticationForm, self).__init__(*args, **kwargs)
        self.label_suffix = ''

        self.fields['username'].widget.attrs.update({'class': 'form-control'})
        self.fields['password'].widget.attrs.update({'class': 'form-control'})
        

class UserRegisterForm(form_mixin.BootstrapFormMixin, UserCreationForm):
    """
    A Django form for registering a new user with additional organization-related fields.
    Inherits from:
        form_mixin.BootstrapFormMixin: Adds Bootstrap styling to the form.
        UserCreationForm: Provides user creation functionality.
    Fields:
        org_name (CharField): The name of the organisation. Required.
        area (CharField): The area, sector, or locality of the organisation. Required.
        city (CharField): The city where the organisation is located. Required.
        first_name (CharField): The first name of the user. Required.
        last_name (CharField): The last name of the user. Required.
    Meta:
        model (User): The user model associated with this form.
        fields (list): Specifies the fields to include in the form: 
            ['org_name', 'area', 'city', 'first_name', 'last_name', 'email']
    """
    org_name = forms.CharField(max_length=200, required=True, label='Organisation name')
    area = forms.CharField(max_length=200, required=True, label='Area / Sector / Locality')
    city = forms.CharField(max_length=200, required=True)
    first_name = forms.CharField(max_length=200, required=True)
    last_name = forms.CharField(max_length=200, required=True)

    class Meta:
        model = User
        fields = ['org_name', 'area', 'city', 'first_name', 'last_name', 'email',] 

