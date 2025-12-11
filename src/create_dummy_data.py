"""
Comprehensive dummy data creation script for testing the SFS BusNest system.
Clears existing test data and creates complete dataset including:
- Organizations, Institutions, Users
- Registrations with Installment Dates
- Routes, Stops, Buses, Schedules
- Student Groups, Receipts, Tickets
- Payments

Run this script to get a fresh, complete test environment.
"""

import os
import django
from datetime import datetime, timedelta, date
from decimal import Decimal
import random

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from django.db import connection, transaction
from django.contrib.auth import get_user_model
from services.models import (
    Organisation, Institution, Registration, Route, Stop, Bus, BusRecord,
    Schedule, ScheduleGroup, Trip, StudentGroup, Ticket, Receipt, 
    InstallmentDate, Payment
)
from core.models import UserProfile

User = get_user_model()


def reset_sequence(table_name):
    """Reset the auto-increment sequence for a table"""
    with connection.cursor() as cursor:
        cursor.execute(f"SELECT setval(pg_get_serial_sequence('{table_name}', 'id'), COALESCE(MAX(id), 1)) FROM {table_name};")


def clear_test_data():
    """Clear all test data from the database"""
    print("\n🗑️  Clearing existing test data...")
    
    with transaction.atomic():
        # Delete in reverse order of dependencies
        Payment.objects.all().delete()
        print("   ✓ Cleared payments")
        
        Ticket.objects.all().delete()
        print("   ✓ Cleared tickets")
        
        Receipt.objects.all().delete()
        print("   ✓ Cleared receipts")
        
        Trip.objects.all().delete()
        print("   ✓ Cleared trips")
        
        ScheduleGroup.objects.all().delete()
        print("   ✓ Cleared schedule groups")
        
        Schedule.objects.all().delete()
        print("   ✓ Cleared schedules")
        
        BusRecord.objects.all().delete()
        print("   ✓ Cleared bus records")
        
        Bus.objects.all().delete()
        print("   ✓ Cleared buses")
        
        Stop.objects.all().delete()
        print("   ✓ Cleared stops")
        
        Route.objects.all().delete()
        print("   ✓ Cleared routes")
        
        StudentGroup.objects.all().delete()
        print("   ✓ Cleared student groups")
        
        InstallmentDate.objects.all().delete()
        print("   ✓ Cleared installment dates")
        
        Registration.objects.all().delete()
        print("   ✓ Cleared registrations")
        
        # Clear users except superuser
        UserProfile.objects.filter(is_central_admin=False, is_institution_admin=False).delete()
        User.objects.exclude(is_superuser=True).exclude(profile__is_central_admin=True).delete()
        print("   ✓ Cleared test users")
        
        Institution.objects.all().delete()
        print("   ✓ Cleared institutions")
        
        Organisation.objects.all().delete()
        print("   ✓ Cleared organizations")
        
        # Reset all sequences
        from django.db import connection
        with connection.cursor() as cursor:
            tables = [
                'services_payment', 'services_ticket', 'services_receipt', 'services_trip',
                'services_schedulegroup', 'services_schedule', 'services_busrecord', 'services_bus',
                'services_stop', 'services_route', 'services_studentgroup', 'services_installmentdate',
                'services_registration', 'services_institution', 'services_organisation'
            ]
            for table in tables:
                cursor.execute(f"ALTER SEQUENCE {table}_id_seq RESTART WITH 1;")
        print("   ✓ Reset all sequences")
    
    print("✅ Database cleared!\n")


@transaction.atomic
def create_dummy_data():
    """Create comprehensive dummy data for testing"""
    print("🚀 Starting comprehensive dummy data creation...\n")
    
    # ========== STEP 1: Organization & Users ==========
    print("📋 Step 1: Creating Organization and Users...")
    
    org, _ = Organisation.objects.get_or_create(
        name="SFS Institutions",
        defaults={
            'area': "Jayanagar",
            'city': "Bangalore",
            'contact_no': "9876543210",
            'email': "admin@sfsinstitutions.edu"
        }
    )
    print(f"   ✓ Organization: {org.name}")
    
    # Create Central Admin
    central_admin_user, created = User.objects.get_or_create(
        email="central@sfs.edu",
        defaults={
            'first_name': "Central",
            'last_name': "Admin"
        }
    )
    if created:
        central_admin_user.set_password("password123")
        central_admin_user.save()
    
    central_profile, _ = UserProfile.objects.get_or_create(
        user=central_admin_user,
        defaults={
            'org': org,
            'is_central_admin': True
        }
    )
    print(f"   ✓ Central Admin: {central_admin_user.email}")
    
    # ========== STEP 2: Institutions ==========
    print("\n🏫 Step 2: Creating Institutions...")
    
    institutions_data = [
        {"name": "SFS High School", "code": "SFSHS", "email": "highschool@sfs.edu"},
        {"name": "SFS College", "code": "SFSCOL", "email": "college@sfs.edu"},
        {"name": "SFS Junior College", "code": "SFSJC", "email": "junior@sfs.edu"},
    ]
    
    institutions = []
    for inst_data in institutions_data:
        inst, _ = Institution.objects.get_or_create(
            org=org,
            name=inst_data['name'],
            defaults={
                'label': inst_data['code'],
                'contact_no': f"98765432{len(institutions)}",
                'email': inst_data['email']
            }
        )
        institutions.append(inst)
        
        # Create Institution Admin
        admin_user, created = User.objects.get_or_create(
            email=inst_data['email'],
            defaults={
                'first_name': inst_data['name'].split()[1],
                'last_name': "Admin"
            }
        )
        if created:
            admin_user.set_password("password123")
            admin_user.save()
        
        admin_profile, _ = UserProfile.objects.get_or_create(
            user=admin_user,
            defaults={
                'org': org,
                'first_name': admin_user.first_name,
                'last_name': admin_user.last_name,
                'is_institution_admin': True
            }
        )
        
        # Set institution incharge
        inst.incharge = admin_profile
        inst.save()
        
        print(f"   ✓ Institution: {inst.name} (Admin: {admin_user.email})")
    
    # ========== STEP 3: Registration & Installments ==========
    print("\n📅 Step 3: Creating Registration and Installment Dates...")
    
    reg, _ = Registration.objects.get_or_create(
        org=org,
        name="Registration 2026",
        defaults={
            'instructions': "Academic Year 2025-2026 Bus Service Registration. Please ensure all documents are submitted on time.",
            'status': True  # True means active
        }
    )
    print(f"   ✓ Registration: {reg.name}")
    
    # Create Installment Dates
    installments_data = [
        {"title": "First Installment", "due_date": date(2025, 12, 16), "description": "Payment for December-January"},
        {"title": "Second Installment", "due_date": date(2026, 1, 15), "description": "Payment for February"},
        {"title": "Third Installment", "due_date": date(2026, 2, 15), "description": "Payment for March"},
        {"title": "Final Installment", "due_date": date(2026, 3, 15), "description": "Final payment"},
    ]
    
    installments = []
    for inst_data in installments_data:
        installment, _ = InstallmentDate.objects.get_or_create(
            org=org,
            registration=reg,
            title=inst_data['title'],
            defaults={
                'due_date': inst_data['due_date'],
                'description': inst_data['description']
            }
        )
        installments.append(installment)
        print(f"   ✓ Installment: {installment.title} (Due: {installment.due_date})")
    
    # ========== STEP 4: Routes & Stops ==========
    print("\n🗺️  Step 4: Creating Routes and Stops...")
    
    routes_data = [
        {
            "name": "Route 1 - Electronic City",
            "stops": ["Electronic City Phase 1", "Silk Board", "BTM Layout", "Jayanagar", "SFS Campus"]
        },
        {
            "name": "Route 2 - Whitefield", 
            "stops": ["Whitefield", "Marathahalli", "Domlur", "Indiranagar", "SFS Campus"]
        },
        {
            "name": "Route 3 - Hebbal",
            "stops": ["Hebbal", "Manyata Tech Park", "Hennur", "Kalyan Nagar", "SFS Campus"]
        }
    ]
    
    routes = []
    all_stops = []
    for route_data in routes_data:
        route, _ = Route.objects.get_or_create(
            org=org,
            registration=reg,
            name=route_data['name']
        )
        routes.append(route)
        print(f"   ✓ Route: {route.name}")
        
        for idx, stop_name in enumerate(route_data['stops'], 1):
            stop, _ = Stop.objects.get_or_create(
                org=org,
                registration=reg,
                route=route,
                name=stop_name
            )
            all_stops.append(stop)
            print(f"      • Stop {idx}: {stop.name}")
    
    reset_sequence('services_route')
    reset_sequence('services_stop')
    
    # ========== STEP 5: Buses & Schedules ==========
    print("\n🚌 Step 5: Creating Buses and Schedules...")
    
    # Create Buses
    buses_data = [
        {"registration_no": "KA01AB1234", "capacity": 50},
        {"registration_no": "KA02CD5678", "capacity": 45},
        {"registration_no": "KA03EF9012", "capacity": 52},
    ]
    
    buses = []
    for bus_data in buses_data:
        bus, _ = Bus.objects.get_or_create(
            org=org,
            registration_no=bus_data['registration_no'],
            defaults={
                'capacity': bus_data['capacity'],
                'is_available': True
            }
        )
        buses.append(bus)
        print(f"   ✓ Bus: {bus.registration_no} ({bus.capacity} seats)")
    
    reset_sequence('services_bus')
    
    # Create Schedules
    schedules_data = [
        {"name": "Morning Pickup", "start_time": "07:00", "end_time": "08:30"},
        {"name": "Evening Drop", "start_time": "15:30", "end_time": "17:00"},
    ]
    
    schedules = []
    for sched_data in schedules_data:
        schedule, _ = Schedule.objects.get_or_create(
            org=org,
            registration=reg,
            name=sched_data['name'],
            defaults={
                'start_time': sched_data['start_time'],
                'end_time': sched_data['end_time']
            }
        )
        schedules.append(schedule)
        print(f"   ✓ Schedule: {schedule.name} ({schedule.start_time} - {schedule.end_time})")
    
    reset_sequence('services_schedule')
    reset_sequence('services_bus')
    
    #Create Schedule Group
    schedule_group, _ = ScheduleGroup.objects.get_or_create(
        registration=reg,
        pick_up_schedule=schedules[0],
        drop_schedule=schedules[1],
        defaults={
            'allow_one_way': False,
            'description': 'Morning pickup and evening drop schedule group'
        }
    )
    print(f"   ✓ Schedule Group created")
    
    reset_sequence('services_schedulegroup')
    
    # ========== STEP 6: Bus Records & Trips ==========
    print("\n🎫 Step 6: Creating Bus Records and Trips...")
    
    reset_sequence('services_busrecord')
    reset_sequence('services_trip')
    
    bus_records = []
    trips = []
    
    for idx, (route, bus) in enumerate(zip(routes, buses[:3])):
        bus_record, _ = BusRecord.objects.get_or_create(
            org=org,
            bus=bus,
            registration=reg,
            defaults={
                'label': f"Bus Record {idx+1}",
                'min_required_capacity': 0
            }
        )
        bus_records.append(bus_record)
        print(f"   ✓ Bus Record: {bus.registration_no} → {route.name}")
        
        # Create trips for both schedules
        for schedule in schedules:
            trip, _ = Trip.objects.get_or_create(
                registration=reg,
                record=bus_record,
                route=route,
                schedule=schedule,
                defaults={
                    'booking_count': 0
                }
            )
            trips.append(trip)
            print(f"      • Trip: {route.name} - {schedule.name}")
    
    reset_sequence('services_busrecord')
    reset_sequence('services_trip')
    
    # ========== STEP 7: Student Groups ==========
    print("\n👥 Step 7: Creating Student Groups...")
    
    student_groups_data = []
    for inst in institutions[:2]:  # Only for first 2 institutions
        for class_num in ['8', '9', '10']:
            for section in ['A', 'B']:
                group_name = f"{class_num} - {section}"
                group, _ = StudentGroup.objects.get_or_create(
                    org=org,
                    institution=inst,
                    name=group_name
                )
                student_groups_data.append(group)
                print(f"   ✓ Student Group: {inst.name} - {group.name}")
    
    reset_sequence('services_studentgroup')
    
    # ========== STEP 8: Receipts & Tickets ==========
    print("\n🎟️  Step 8: Creating Receipts and Tickets...")
    
    student_names = [
        "Rahul Kumar", "Priya Sharma", "Arjun Patel", "Sneha Reddy", "Vikram Singh",
        "Ananya Iyer", "Rohan Gupta", "Meera Nair", "Karthik Rao", "Divya Menon",
        "Aditya Verma", "Pooja Joshi", "Nikhil Shah", "Kavya Desai", "Sanjay Pillai",
        "Ritu Agarwal", "Amit Malhotra", "Shreya Kapoor", "Varun Bhat", "Neha Kulkarni"
    ]
    
    receipts = []
    tickets = []
    ticket_count = 0
    
    for idx, student_name in enumerate(student_names):
        # Select institution and student group
        inst = institutions[idx % 2]  # Alternate between first 2 institutions
        student_group = random.choice([g for g in student_groups_data if g.institution == inst])
        
        # Create receipt
        receipt, _ = Receipt.objects.get_or_create(
            org=org,
            registration=reg,
            institution=inst,
            receipt_id=f"REC{2026}{idx+1:04d}",
            defaults={
                'student_id': f"STU{2026}{idx+1:04d}",
                'student_group': student_group,
                'is_expired': False
            }
        )
        receipts.append(receipt)
        
        # Select random route and stops
        route = random.choice(routes)
        route_stops = [s for s in all_stops if s.route == route]
        pickup_stop = random.choice(route_stops[:-1])  # Not last stop
        drop_stop = route_stops[-1]  # Last stop (campus)
        
        # Find appropriate trips
        morning_trip = next((t for t in trips if t.route == route and t.schedule == schedules[0]), None)
        evening_trip = next((t for t in trips if t.route == route and t.schedule == schedules[1]), None)
        
        if morning_trip and evening_trip:
            # Create ticket
            ticket, created = Ticket.objects.get_or_create(
                org=org,
                registration=reg,
                institution=inst,
                recipt=receipt,
                defaults={
                    'student_name': student_name,
                    'student_id': receipt.student_id,
                    'student_group': student_group,
                    'contact_no': f"98765{43210 + idx}",
                    'pickup_point': pickup_stop,
                    'drop_point': drop_stop,
                    'pickup_bus_record': morning_trip.record,
                    'drop_bus_record': evening_trip.record,
                    'pickup_schedule': morning_trip.schedule,
                    'drop_schedule': evening_trip.schedule,
                    'ticket_type': 'two_way',
                    'status': True
                }
            )
            
            if created:
                # Update trip booking counts
                morning_trip.booking_count += 1
                morning_trip.save()
                evening_trip.booking_count += 1
                evening_trip.save()
                
                tickets.append(ticket)
                ticket_count += 1
                print(f"   ✓ Ticket #{ticket_count}: {student_name} ({inst.name}) - {route.name}")
    
    reset_sequence('services_receipt')
    reset_sequence('services_ticket')
    
    # ========== STEP 9: Payments ==========
    print("\n💰 Step 9: Creating Sample Payments...")
    
    payment_count = 0
    for idx, ticket in enumerate(tickets[:15]):  # Create payments for first 15 tickets
        # Some tickets have 1 payment, some have 2
        num_payments = 1 if idx % 3 == 0 else 2
        
        for payment_num in range(num_payments):
            installment = installments[payment_num]
            amount = Decimal("5777.00") if payment_num == 0 else Decimal("5000.00")
            
            payment, _ = Payment.objects.get_or_create(
                org=org,
                registration=reg,
                ticket=ticket,
                institution=ticket.institution,
                installment_date=installment,
                defaults={
                    'amount': amount,
                    'payment_date': installment.due_date - timedelta(days=random.randint(1, 5)),
                    'payment_mode': random.choice(['cash', 'online', 'upi', 'card']),
                    'transaction_reference': f"TXN{random.randint(100000, 999999)}",
                    'notes': f"Payment for {installment.title}",
                    'recorded_by': User.objects.filter(profile__is_institution_admin=True, 
                                                       profile__institution=ticket.institution).first()
                }
            )
            payment_count += 1
            print(f"   ✓ Payment #{payment_count}: {ticket.student_name} - {installment.title} - ₹{amount}")
    
    reset_sequence('services_payment')
    
    # ========== Summary ==========
    print("\n" + "="*60)
    print("✅ DUMMY DATA CREATION COMPLETE!")
    print("="*60)
    print(f"📊 Summary:")
    print(f"   • Organizations: {Organisation.objects.count()}")
    print(f"   • Institutions: {Institution.objects.count()}")
    print(f"   • Registrations: {Registration.objects.count()}")
    print(f"   • Installment Dates: {InstallmentDate.objects.count()}")
    print(f"   • Routes: {Route.objects.count()}")
    print(f"   • Stops: {Stop.objects.count()}")
    print(f"   • Buses: {Bus.objects.count()}")
    print(f"   • Schedules: {Schedule.objects.count()}")
    print(f"   • Bus Records: {BusRecord.objects.count()}")
    print(f"   • Trips: {Trip.objects.count()}")
    print(f"   • Student Groups: {StudentGroup.objects.count()}")
    print(f"   • Receipts: {Receipt.objects.count()}")
    print(f"   • Tickets: {Ticket.objects.count()}")
    print(f"   • Payments: {Payment.objects.count()}")
    print("\n🔐 Login Credentials:")
    print(f"   Central Admin: central@sfs.edu / password123")
    print(f"   Institution Admin 1: highschool@sfs.edu / password123")
    print(f"   Institution Admin 2: college@sfs.edu / password123")
    print("\n🎉 System is ready for comprehensive testing!")
    print("="*60)


if __name__ == '__main__':
    clear_test_data()
    create_dummy_data()
