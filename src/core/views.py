from django.shortcuts import redirect, render
from django.contrib.auth.views import LoginView
from django.contrib.auth import login
from . forms import CustomAuthenticationForm


class LoginView(LoginView):
    form_class = CustomAuthenticationForm
    template_name = 'core/login.html'

    def form_valid(self, form):
        login(self.request, form.get_user())
        return redirect('landing_page')