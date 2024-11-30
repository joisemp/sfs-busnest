from django import forms
from django.contrib.auth import get_user_model
from django.contrib.auth.forms import AuthenticationForm, UserCreationForm
from config.mixins import form_mixin

User = get_user_model()



class CustomAuthenticationForm(form_mixin.BootstrapFormMixin, AuthenticationForm):
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
    org_name = forms.CharField(max_length=200, required=True, label='Organisation')
    first_name = forms.CharField(max_length=200, required=True)
    last_name = forms.CharField(max_length=200, required=True)

    class Meta:
        model = User
        fields = ['org_name', 'first_name', 'last_name', 'email',]  
        
        