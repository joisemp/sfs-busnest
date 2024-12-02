from django.views.generic import TemplateView
from config.mixins.access_mixin import RedirectLoggedInUsersMixin

class LandingPageView(RedirectLoggedInUsersMixin, TemplateView):
    template_name = 'index.html'