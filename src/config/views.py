from django.views.generic import TemplateView
from config.mixins.access_mixin import RedirectLoggedInUsersMixin
from django.shortcuts import redirect
from services.tasks import count_task

class LandingPageView(RedirectLoggedInUsersMixin, TemplateView):
    template_name = 'index.html'
    

def count_to_10(request):
    count_task.delay()
    return redirect('landing_page')