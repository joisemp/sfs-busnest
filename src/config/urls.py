from django.contrib import admin
from django.urls import path, include
from config.views import LandingPageView, count_to_10

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', LandingPageView.as_view(), name='landing_page'),
    path('count/', count_to_10, name='count'),
    path('core/', include('core.urls', namespace='core')),
    path('central_admin/', include('services.urls.central_admin', namespace='central_admin')),
    path('institution_admin/', include('services.urls.institution_admin', namespace='institution_admin')),
    path('students/', include('services.urls.students', namespace='students')),
]

