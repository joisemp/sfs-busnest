from django.contrib import admin
from django.urls import path, include
from config.views import LandingPageView, count_to_10

"""
URL configuration for the BMS-SFS Institutions project.
This module defines the URL patterns for the project, mapping URLs to their
corresponding views or including other URL configurations.
Routes:
- 'admin/': Admin site URLs.
- '': Landing page view.
- 'count/': View to count to 10.
- 'core/': Includes the URL patterns from the 'core' app.
- 'central_admin/': Includes the URL patterns for central administration services.
- 'institution_admin/': Includes the URL patterns for institution administration services.
- 'students/': Includes the URL patterns for student-related services.
Namespaces:
- 'core': Namespace for the 'core' app.
- 'central_admin': Namespace for central administration services.
- 'institution_admin': Namespace for institution administration services.
- 'students': Namespace for student-related services.
"""

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', LandingPageView.as_view(), name='landing_page'),
    path('count/', count_to_10, name='count'),
    path('core/', include('core.urls', namespace='core')),
    path('central_admin/', include('services.urls.central_admin', namespace='central_admin')),
    path('institution_admin/', include('services.urls.institution_admin', namespace='institution_admin')),
    path('students/', include('services.urls.students', namespace='students')),
]

