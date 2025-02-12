import os
from uuid import uuid4
from django.db import models
from django.forms import ValidationError
from django.utils.text import slugify
from django.core.validators import RegexValidator
from config.validators import validate_excel_file
from config.utils import generate_unique_slug, generate_unique_code
from django.conf import settings
from django.db.models.signals import post_delete
from django.dispatch import receiver


class Organisation(models.Model):
    name = models.CharField(max_length=200, db_index=True)
    contact_no = models.CharField(
        max_length=12,
        validators=[RegexValidator(r'^\d{10,12}$', 'Enter a valid contact number')],
        db_index=True,
        null=True
    )
    email = models.EmailField(unique=True, db_index=True, null=True)
    area = models.CharField(max_length=200)
    city = models.CharField(max_length=200)
    slug = models.SlugField(unique=True, db_index=True, max_length=255)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def save(self, *args, **kwargs):
        if not self.slug:
            base_slug = slugify(self.name)
            self.slug = generate_unique_slug(self, base_slug)
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.name}"
    

class Institution(models.Model):
    org = models.ForeignKey(Organisation, on_delete=models.CASCADE, related_name='institutions')
    name = models.CharField(max_length=200, db_index=True)
    label = models.CharField(max_length=50, unique=True)
    contact_no = models.CharField(
        max_length=12,
        validators=[RegexValidator(r'^\d{10,12}$', 'Enter a valid contact number')],
        db_index=True
    )
    email = models.EmailField(unique=True, db_index=True)
    slug = models.SlugField(unique=True, db_index=True, max_length=255)
    incharge = models.OneToOneField('core.UserProfile', max_length=200, null=True, on_delete=models.SET_NULL, related_name='institution')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def save(self, *args, **kwargs):
        if not self.slug:
            base_slug = slugify(self.name)
            self.slug = generate_unique_slug(self, base_slug)
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.name} - {self.label}"


class Route(models.Model):
    org = models.ForeignKey(Organisation, on_delete=models.CASCADE, related_name='routes')
    registration = models.ForeignKey('services.Registration', on_delete=models.CASCADE, related_name='routes')
    name = models.CharField(max_length=200)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    slug = models.SlugField(unique=True, db_index=True, max_length=255)

    def save(self, *args, **kwargs):
        if not self.slug:
            base_slug = slugify(f"{self.org}-{self.name}")
            self.slug = generate_unique_slug(self, base_slug)
        super().save(*args, **kwargs)
        
    def __str__(self):
        return f"{self.name}"
    

class Stop(models.Model):
    org = models.ForeignKey(Organisation, on_delete=models.CASCADE, related_name='stops')
    registration = models.ForeignKey('services.Registration', on_delete=models.CASCADE, related_name='stops')
    route = models.ForeignKey(Route, on_delete=models.CASCADE, related_name='stops')
    name = models.CharField(max_length=200)
    slug = models.SlugField(unique=True, db_index=True, max_length=255)
    
    def save(self, *args, **kwargs):
        if not self.slug:
            base_slug = slugify(f"{self.org}-{self.name}")
            self.slug = generate_unique_slug(self, base_slug)
        super().save(*args, **kwargs)
        
    def __str__(self):
        return f"{self.name}"
    
    
def rename_uploaded_file(instance, filename):
    base_name = os.path.splitext(filename)[0]
    ext = os.path.splitext(filename)[1]
    return f"{instance.org.slug}/route_files/{slugify(base_name)}-{uuid4()}{ext}"


def rename_bus_uploaded_file(instance, filename):
    base_name = os.path.splitext(filename)[0]
    ext = os.path.splitext(filename)[1]
    return f"{instance.org.slug}/bus_files/{slugify(base_name)}-{uuid4()}{ext}"


class RouteFile(models.Model):
    org = models.ForeignKey(Organisation, on_delete=models.CASCADE, related_name='route_files')
    name = models.CharField(max_length=200)
    file = models.FileField(upload_to=rename_uploaded_file, validators=[validate_excel_file])
    added = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    slug = models.SlugField(unique=True, db_index=True, max_length=255)

    def save(self, *args, **kwargs):
        if not self.slug:
            base_slug = slugify(f"{self.org}-{self.name}")
            self.slug = generate_unique_slug(self, base_slug)
        super().save(*args, **kwargs)
        
    def __str__(self):
        return f"{self.name}"


class Registration(models.Model):
    org = models.ForeignKey(Organisation, on_delete=models.CASCADE, related_name='registrations')
    name = models.CharField(max_length=200)
    instructions = models.TextField()
    status = models.BooleanField(default=False)
    code = models.CharField(max_length=100, unique=True, null=True)
    slug = models.SlugField(unique=True, db_index=True, max_length=255)

    def save(self, *args, **kwargs):
        if not self.slug:
            base_slug = slugify(f"{self.org}-{self.name}")
            self.slug = generate_unique_slug(self, base_slug)
        if not self.code:
            self.code = generate_unique_code(self, unique_field='code')
        super().save(*args, **kwargs)
    
    def __str__(self):
        return f"{self.org}{self.name}"
    

class Schedule(models.Model):
    org = models.ForeignKey(Organisation, on_delete=models.CASCADE, related_name='schedules')
    registration = models.ForeignKey('services.Registration', on_delete=models.CASCADE, related_name='schedules')
    name = models.CharField(max_length=50)  # Example: "Morning", "Afternoon", "Evening"
    start_time = models.TimeField()  # Example: 08:00 AM
    end_time = models.TimeField()    # Example: 11:00 AM
    slug = models.SlugField(unique=True, db_index=True, max_length=255)

    def save(self, *args, **kwargs):
        if not self.slug:
            base_slug = slugify(f"{self.org}-{self.name}")
            self.slug = generate_unique_slug(self, base_slug)
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.name} ({self.start_time} - {self.end_time})"
    

class ScheduleGroup(models.Model):
    registration = models.ForeignKey(Registration, on_delete=models.CASCADE, related_name='schedule_groups')
    pick_up_schedule = models.ForeignKey(Schedule, on_delete=models.CASCADE, related_name='pickup_groups')
    drop_schedule = models.ForeignKey(Schedule, on_delete=models.CASCADE, related_name='drop_groups')
    allow_one_way = models.BooleanField(default=False)
    description = models.CharField(max_length=500)
    
    def __str__(self):
        return f"{self.pick_up_schedule.name}-{self.drop_schedule.name}"
    

class Bus(models.Model):
    org = models.ForeignKey(Organisation, on_delete=models.CASCADE, related_name='buses')
    registration_no = models.CharField(max_length=100)
    driver = models.CharField(max_length=255)
    capacity = models.PositiveIntegerField(blank=False, null=False)
    is_available = models.BooleanField(default=True)
    slug = models.SlugField(unique=True, db_index=True, max_length=255)

    def save(self, *args, **kwargs):
        if not self.slug:
            base_slug = slugify(f"bus-{self.registration_no}")
            self.slug = generate_unique_slug(self, base_slug)
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.registration_no} (Capacity : {self.capacity})"
    

class BusRecord(models.Model):
    org = models.ForeignKey(Organisation, on_delete=models.CASCADE, related_name='bus_records')
    bus = models.ForeignKey(Bus, on_delete=models.SET_NULL, null=True, related_name='records')
    registration = models.ForeignKey(Registration, on_delete=models.CASCADE, related_name='bus_records')
    label = models.CharField(max_length=20)
    min_required_capacity = models.PositiveIntegerField(default=0)
    slug = models.SlugField(unique=True, db_index=True, max_length=255)

    class Meta:
        unique_together = ('bus', 'registration')
        
    def clean(self):
        if self.bus:
            if self.min_required_capacity > self.bus.capacity:
                raise ValidationError(
                    f"The bus cpacity ({self.bus.capacity}) is less than the minimum capacity of ({self.min_required_capacity})."
                )

    def save(self, *args, **kwargs):
        if not self.slug:
            base_slug = slugify(f"record-{self.bus.registration_no}-{self.registration.name}")
            self.slug = generate_unique_slug(self, base_slug)
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.label}"
    

class Trip(models.Model):
    registration = models.ForeignKey(Registration, on_delete=models.CASCADE, related_name='trips')
    record = models.ForeignKey(BusRecord, on_delete=models.CASCADE, related_name='trips')
    schedule = models.ForeignKey(Schedule, on_delete=models.CASCADE, related_name='trips')
    route = models.ForeignKey(Route, on_delete=models.CASCADE, related_name='trips')
    booking_count = models.PositiveIntegerField(default=0)
    
    class Meta:
        unique_together = ('registration', 'record', 'schedule')
    
    @property
    def total_filled_seats_percentage(self):
        if not self.record or not self.record.bus or self.record.bus.capacity == 0:
            return 0
        return round((self.booking_count * 100) / self.record.bus.capacity, 2)
    
    def __str__(self):
        return f"{self.schedule} | {self.route}"


TICKET_TYPES = ( 
    ("one_way", "One way"), 
    ("two_way", "Two way"),  
)


class Ticket(models.Model):
    org = models.ForeignKey(Organisation, on_delete=models.CASCADE, related_name='tickets')
    registration = models.ForeignKey(Registration, on_delete=models.CASCADE, related_name='tickets')
    institution = models.ForeignKey(Institution, on_delete=models.CASCADE, related_name='tickets')
    student_group = models.ForeignKey('services.StudentGroup', on_delete=models.CASCADE, related_name='tickets')
    recipt = models.OneToOneField('services.Receipt', on_delete=models.CASCADE, related_name='ticket')
    ticket_id = models.CharField(max_length=300, unique=True)
    student_id = models.CharField(max_length=100)
    student_name = models.CharField(max_length=200)
    student_email = models.EmailField()
    contact_no = models.CharField(
        max_length=12,
        validators=[RegexValidator(r'^\d{10,12}$', 'Enter a valid contact number')],
    )
    alternative_contact_no = models.CharField(
        max_length=12,
        validators=[RegexValidator(r'^\d{10,12}$', 'Enter a valid contact number')],
    )
    pickup_bus_record = models.ForeignKey(BusRecord, on_delete=models.CASCADE, null=True, default=None, blank=True, related_name='pickup_tickets')
    drop_bus_record = models.ForeignKey(BusRecord, on_delete=models.CASCADE, null=True, default=None, blank=True, related_name='drop_tickets')
    pickup_point = models.ForeignKey(Stop, on_delete=models.SET_NULL, null=True, default=None, blank=True, related_name='ticket_pickups')
    drop_point = models.ForeignKey(Stop, on_delete=models.SET_NULL, null=True, default=None, blank=True, related_name='ticket_drops')
    pickup_schedule = models.ForeignKey(Schedule, on_delete=models.SET_NULL, null=True, default=None, related_name='pickup_tickets')
    drop_schedule = models.ForeignKey(Schedule, on_delete=models.SET_NULL, null=True, default=None, related_name='drop_tickets')
    ticket_type = models.CharField(max_length=300, choices=TICKET_TYPES, default='twoway')
    status = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    slug = models.SlugField(unique=True, db_index=True, max_length=255)

    def save(self, *args, **kwargs):
        if not self.slug:
            base_slug = slugify(f"{self.registration.name}-{self.ticket_id}")
            self.slug = generate_unique_slug(self, base_slug)
        if not self.ticket_id:
            self.ticket_id = generate_unique_code(self, no_of_char=12, unique_field='ticket_id')
        super().save(*args, **kwargs)

    def __str__(self):
        return f"Ticket for {self.student_name}"


class StudentGroup(models.Model):
    org = models.ForeignKey(Organisation, on_delete=models.CASCADE, related_name='groups')
    institution = models.ForeignKey(Institution, on_delete=models.CASCADE, related_name='groups')
    name = models.CharField(max_length=20)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    slug = models.SlugField(unique=True, db_index=True, max_length=255)

    def save(self, *args, **kwargs):
        if not self.slug:
            base_slug = slugify(f"{self.org}-{self.name}")
            self.slug = generate_unique_slug(self, base_slug)
        super().save(*args, **kwargs)
    
    def __str__(self):
        return f"{self.name}"


class Receipt(models.Model):
    org = models.ForeignKey(Organisation, on_delete=models.CASCADE, related_name='recipts')
    institution = models.ForeignKey(Institution, on_delete=models.CASCADE, related_name='recipts')
    registration = models.ForeignKey(Registration, on_delete=models.CASCADE, related_name='recipts')
    receipt_id = models.CharField(max_length=500)
    student_id = models.CharField(max_length=20)
    student_group = models.ForeignKey(StudentGroup, on_delete=models.CASCADE)
    is_expired = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    slug = models.SlugField(unique=True, db_index=True, max_length=255)

    def save(self, *args, **kwargs):
        if self.student_id:
            self.student_id = self.student_id.upper()
        if not self.slug:
            base_slug = slugify(f"{self.student_id}-{self.created_at}")
            self.slug = generate_unique_slug(self, base_slug)
        super().save(*args, **kwargs)
        
    def __str__(self):
        return f"{self.receipt_id}"
    

def rename_uploaded_file_receipt(instance, filename):
    base_name = os.path.splitext(filename)[0]
    ext = os.path.splitext(filename)[1]
    return f"{instance.org.slug}/{instance.institution.slug}/receipt_files/{slugify(base_name)}-{uuid4()}{ext}"


class ReceiptFile(models.Model):
    org = models.ForeignKey(Organisation, on_delete=models.CASCADE, related_name='recipt_files')
    institution = models.ForeignKey(Institution, on_delete=models.CASCADE, related_name='recipt_files')
    registration = models.ForeignKey(Registration, on_delete=models.CASCADE, related_name='recipt_files')
    file = models.FileField(upload_to=rename_uploaded_file_receipt, validators=[validate_excel_file])
    added = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    slug = models.SlugField(unique=True, db_index=True, max_length=255)

    def save(self, *args, **kwargs):
        if not self.slug:
            base_slug = slugify(f"{self.org}-{self.institution.name}")
            self.slug = generate_unique_slug(self, base_slug)
        super().save(*args, **kwargs)
        
    def __str__(self):
        return f"{self.name}"
    

class FAQ(models.Model):
    org = models.ForeignKey(Organisation, on_delete=models.CASCADE, related_name='faqs')
    registration = models.ForeignKey(Registration, on_delete=models.CASCADE, related_name='faqs')
    question = models.CharField(max_length=500)
    answer = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    slug = models.SlugField(unique=True, db_index=True, max_length=255)

    def save(self, *args, **kwargs):
        if not self.slug:
            base_slug = slugify(f"faq-{self.question}")
            self.slug = generate_unique_slug(self, base_slug)
        super().save(*args, **kwargs)
        
    def __str__(self):
        return f"{self.receipt_id}"
    

class BusRequest(models.Model):
    org = models.ForeignKey(Organisation, on_delete=models.CASCADE, related_name='bus_requests')
    institution = models.ForeignKey(Institution, on_delete=models.CASCADE, related_name='bus_requests')
    registration = models.ForeignKey(Registration, on_delete=models.CASCADE, related_name='bus_requests')
    receipt = models.ForeignKey(Receipt, on_delete=models.CASCADE)
    student_group = models.ForeignKey(StudentGroup, null=True, on_delete=models.SET_NULL)
    student_name = models.CharField(max_length=300)
    pickup_address = models.CharField(max_length=500)
    drop_address = models.CharField(max_length=500)
    contact_no = models.CharField(
        max_length=12,
        validators=[RegexValidator(r'^\d{10,12}$', 'Enter a valid contact number')],
    )
    contact_email = models.EmailField()
    created_at = models.DateTimeField(auto_now_add=True)
    slug = models.SlugField(unique=True, db_index=True, max_length=255)
    
    def save(self, *args, **kwargs):
        if not self.slug:
            base_slug = slugify(f"faq-{self.registration}-{self.student_name}")
            self.slug = generate_unique_slug(self, base_slug)
        super().save(*args, **kwargs)
        
    def __str__(self):
        return self.student_name
    

class ExportedFile(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)  # User who requested the export
    file = models.FileField(upload_to='exports/')  # Path to the file
    created_at = models.DateTimeField(auto_now_add=True)
    
    def __str__(self):
        return f"Exported File for {self.user.username} - {self.created_at}"


class BusFile(models.Model):
    org = models.ForeignKey(Organisation, on_delete=models.CASCADE)
    user=models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    file = models.FileField(upload_to=rename_bus_uploaded_file, validators=[validate_excel_file])
    name = models.CharField(max_length=255)
    added = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    slug = models.SlugField(unique=True, db_index=True, max_length=255)

    def save(self, *args, **kwargs):
        if not self.slug:
            base_slug = slugify(f"{self.org}-{self.name}")
            self.slug = generate_unique_slug(self, base_slug)
        super().save(*args, **kwargs)
        
    def __str__(self):
        return f"{self.created_at}"
    

class OrganisationActivity(models.Model):
    org = models.ForeignKey(Organisation, on_delete=models.CASCADE)
    user=models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True)
    action = models.CharField(max_length=200)
    created_at = models.DateTimeField(auto_now_add=True)
    slug = models.SlugField(unique=True, db_index=True, max_length=255)
    
    def save(self, *args, **kwargs):
        if not self.slug:
            base_slug = slugify(f"{self.org}-{self.user}")
            self.slug = generate_unique_slug(self, base_slug)
        super().save(*args, **kwargs)
        
    def __str__(self):
        return f"{self.created_at}"
    

# @receiver(post_delete, sender=Ticket)
# def increment_bus_capacity_on_ticket_delete(sender, instance, **kwargs):
#     try:
#         # Find the associated BusCapacity instance
#         bus_capacity = BusCapacity.objects.get(bus=instance.bus, registration=instance.registration)
#         # Increment the available seats
#         bus_capacity.available_seats += 1
#         bus_capacity.save()
#     except BusCapacity.DoesNotExist:
#         pass