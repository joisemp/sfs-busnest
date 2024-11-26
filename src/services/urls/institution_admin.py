from django.urls import path
from services.views import institution_admin

app_name = 'institution_admin'


urlpatterns = [
     path('registrations/', institution_admin.RegistrationListView.as_view(), name='registration_list'),
     path('recipts/', institution_admin.ReciptListView.as_view(), name='recipt_list'),
     path('student-groups/', institution_admin.StudentGroupListView.as_view(), name='student_group_list'),
]