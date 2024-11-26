from django.urls import path
from services.views import institution_admin

app_name = 'institution_admin'


urlpatterns = [
     path('registrations/', institution_admin.RegistrationListView.as_view(), name='registration_list'),
     path('receipts/', institution_admin.ReceiptListView.as_view(), name='receipt_list'),
     path('receipts/add/', institution_admin.ReceiptCreateView.as_view(), name='receipt_create'),
     path('student-groups/', institution_admin.StudentGroupListView.as_view(), name='student_group_list'),
]