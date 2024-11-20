from django.contrib import admin
from django.urls import path, include
from django.views.generic import TemplateView

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', TemplateView.as_view(template_name='index.html'), name='landing_page'),
    path('core/', include('core.urls', namespace='core')),
    path('central_admin/', include('services.urls.central_admin', namespace='central_admin')),
    path('institution_admin/', include('services.urls.institution_admin', namespace='institution_admin')),
    path('students/', include('services.urls.students', namespace='students')),
]

