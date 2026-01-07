"""
Script to create tickets and fill one trip's seats to capacity.
This script mimics a full seat scenario for testing purposes.

Usage:
    python manage.py shell < fill_trip_seats.py
    Or:
    python fill_trip_seats.py (after setting up Django environment)
"""

import os
import sys
import django
from django.utils.text import slugify

# Add parent directory to Python path to find config module
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Setup Django environment
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from services.models import (
    BusRecord, Trip, Ticket, Receipt, StudentGroup, 
    Stop, Schedule, Registration, Institution, Organisation
)
from django.db import transaction


def fill_trip_with_tickets(bus_record_label=None, schedule_name=None):
    """
    Fill one trip with tickets to reach full capacity.
    
    Args:
        bus_record_label: Label of the bus record to fill (e.g., "Bus A")
        schedule_name: Name of the schedule (e.g., "Morning")
    """
    
    # Get a bus record with trips
    if bus_record_label:
        bus_record = BusRecord.objects.filter(label__icontains=bus_record_label).first()
    else:
        bus_record = BusRecord.objects.filter(bus__isnull=False).first()
    
    if not bus_record:
        print("❌ No bus record found. Please create a bus record first.")
        return
    
    if not bus_record.bus:
        print(f"❌ Bus record '{bus_record.label}' has no bus assigned.")
        return
    
    print(f"✅ Found bus record: {bus_record.label}")
    print(f"   Bus: {bus_record.bus.registration_no}")
    print(f"   Capacity: {bus_record.bus.capacity}")
    
    # Get a trip from this bus record
    if schedule_name:
        trip = bus_record.trips.filter(schedule__name__icontains=schedule_name).first()
    else:
        trip = bus_record.trips.first()
    
    if not trip:
        print(f"❌ No trips found for bus record '{bus_record.label}'")
        return
    
    print(f"✅ Found trip: {trip.schedule.name} - {trip.route.name}")
    print(f"   Current booking count: {trip.booking_count}")
    
    # Calculate how many tickets we need to create
    capacity = bus_record.bus.capacity
    current_bookings = trip.booking_count
    tickets_needed = capacity - current_bookings
    
    if tickets_needed <= 0:
        print(f"✅ Trip is already full! ({current_bookings}/{capacity})")
        return
    
    print(f"📝 Need to create {tickets_needed} tickets to fill the trip")
    
    # Get necessary data for ticket creation
    registration = trip.registration
    org = bus_record.org
    
    # Get an institution (prefer one from the same org)
    institution = Institution.objects.filter(org=org).first()
    if not institution:
        print("❌ No institution found. Please create an institution first.")
        return
    
    # Get a student group
    student_group = StudentGroup.objects.filter(
        org=org, 
        institution=institution
    ).first()
    
    if not student_group:
        print("❌ No student group found. Creating one...")
        student_group = StudentGroup.objects.create(
            org=org,
            institution=institution,
            registration=registration,
            class_name="10",
            section="A"
        )
        print(f"✅ Created student group: {student_group}")
    
    # Get a pickup stop from the route
    pickup_stop = trip.route.stops.first()
    if not pickup_stop:
        print("❌ No stops found on the route. Please add stops first.")
        return
    
    # Find the highest existing student number to avoid conflicts
    existing_receipts = Receipt.objects.filter(
        receipt_id__startswith='REC'
    ).values_list('receipt_id', flat=True)
    
    existing_numbers = []
    for rec_id in existing_receipts:
        try:
            num = int(rec_id.replace('REC', ''))
            existing_numbers.append(num)
        except ValueError:
            continue
    
    if existing_numbers:
        start_number = max(existing_numbers) + 1
    else:
        start_number = 10000
    
    print(f"📋 Starting from student number: {start_number}")
    print(f"\n🎫 Creating {tickets_needed} tickets...")
    
    created_count = 0
    
    # Don't use atomic transaction - create tickets one by one
    for i in range(tickets_needed):
        student_number = start_number + i
        student_id = f"STU{student_number}"
        
        # Create receipt first (required for ticket)
        try:
            with transaction.atomic():
                receipt = Receipt.objects.create(
                    org=org,
                    institution=institution,
                    registration=registration,
                    receipt_id=f"REC{student_number}",
                    student_id=student_id,
                    student_group=student_group,
                    is_expired=False
                )
                
                # Determine if this is pickup or drop based on schedule name
                # Check if schedule name contains "pickup" or if it's a morning/afternoon schedule
                schedule_name_lower = trip.schedule.name.lower()
                is_pickup = 'pickup' in schedule_name_lower or 'morning' in schedule_name_lower
                
                # Create the ticket
                ticket = Ticket.objects.create(
                    org=org,
                    registration=registration,
                    institution=institution,
                    student_group=student_group,
                    recipt=receipt,
                    student_id=student_id,
                    student_name=f"Test Student {student_number}",
                    student_email=f"student{student_number}@test.com",
                    contact_no=f"98765{str(43210 + i).zfill(5)}",
                    alternative_contact_no=f"98765{str(43210 + i).zfill(5)}",
                    pickup_bus_record=bus_record if is_pickup else None,
                    drop_bus_record=None if is_pickup else bus_record,
                    pickup_point=pickup_stop if is_pickup else None,
                    drop_point=None if is_pickup else pickup_stop,
                    pickup_schedule=trip.schedule if is_pickup else None,
                    drop_schedule=None if is_pickup else trip.schedule,
                    ticket_type="one_way",
                    status=True
                )
                
                created_count += 1
                
                # Update trip booking count
                trip.booking_count += 1
                trip.save()
                
                if (i + 1) % 10 == 0:
                    print(f"   Created {i + 1}/{tickets_needed} tickets...")
                    
        except Exception as e:
            print(f"❌ Error creating ticket {i+1}: {e}")
            continue

    
    print(f"\n✅ Successfully created {created_count} tickets!")
    print(f"✅ Trip is now at {trip.booking_count}/{capacity} capacity")
    print(f"   Filled percentage: {trip.total_filled_seats_percentage}%")


if __name__ == "__main__":
    print("=" * 60)
    print("🚌 Fill Trip Seats Script")
    print("=" * 60)
    print()
    
    # You can customize these parameters:
    # - Leave None to automatically pick the first available
    # - Or specify exact values
    
    BUS_RECORD_LABEL = "Bus Record 1"  # e.g., "Bus A" or None for first available
    SCHEDULE_NAME = "Morning Pickup"      # e.g., "Morning" or None for first available
    
    fill_trip_with_tickets(
        bus_record_label=BUS_RECORD_LABEL,
        schedule_name=SCHEDULE_NAME
    )
    
    print()
    print("=" * 60)
    print("✅ Script completed!")
    print("=" * 60)
