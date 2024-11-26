from django.urls import path
from services.views import institution_admin

app_name = 'institution_admin'


urlpatterns = [
     path('registrations/', institution_admin.RegistrationListView.as_view(), name='registration_list'),
     path('receipts/', institution_admin.ReceiptListView.as_view(), name='receipt_list'),
     path('receipts/add/', institution_admin.ReceiptCreateView.as_view(), name='receipt_create'),
     path('receipts/<slug:receipt_slug>/delete/', institution_admin.ReceiptDeleteView.as_view(), name='receipt_delete'),
     path('student-groups/', institution_admin.StudentGroupListView.as_view(), name='student_group_list'),
     path('student-groups/create/', institution_admin.StudentGroupCreateView.as_view(), name='student_group_create'),
     path('student-groups/<slug:student_group_slug>/update/', institution_admin.StudentGroupUpdateView.as_view(), name='student_group_update'),
]