from django.views.generic import TemplateView
from django.http import HttpResponse
from django.template.loader import render_to_string
from config.mixins.access_mixin import RedirectLoggedInUsersMixin
from django.shortcuts import redirect
from services.tasks import count_task

class LandingPageView(RedirectLoggedInUsersMixin, TemplateView):
    template_name = 'index.html'


def service_worker(request):
    """Serve the service worker JS file from root scope."""
    content = render_to_string('sw.js', request=request)
    return HttpResponse(content, content_type='application/javascript')


def manifest_json(request):
    """Serve manifest.json as same-origin to avoid CORS issues with CDN-hosted static files."""
    content = render_to_string('manifest.json', request=request)
    return HttpResponse(content, content_type='application/json')


def count_to_10(request):
    count_task.delay()
    return redirect('landing_page')