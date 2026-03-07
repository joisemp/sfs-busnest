"""
Dummy data creation script for BusRequest and BusRequestComment.

This script creates realistic bus requests with comments for testing purposes.
It uses existing organizations, institutions, registrations, and receipts.

Run this script to populate the database with sample bus requests.
"""

import os
import sys
import django
from datetime import datetime, timedelta
from decimal import Decimal
import random

# Add parent directory to Python path to find config module
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from django.db import transaction
from django.contrib.auth import get_user_model
from services.models import (
    Organisation, Institution, Registration, Receipt, 
    StudentGroup, BusRequest, BusRequestComment
)
from core.models import UserProfile

User = get_user_model()


# Sample data for realistic dummy content
STUDENT_NAMES = [
    "Aarav Kumar", "Vivaan Singh", "Aditya Sharma", "Vihaan Patel", "Arjun Reddy",
    "Sai Kumar", "Krishna Rao", "Reyansh Gupta", "Ayaan Khan", "Arnav Mishra",
    "Saanvi Sharma", "Ananya Patel", "Diya Singh", "Aadhya Kumar", "Ishaan Verma",
    "Kavya Reddy", "Priya Nair", "Riya Joshi", "Aarohi Desai", "Navya Kapoor",
    "Ayush Malhotra", "Rohan Iyer", "Kabir Mehta", "Aryan Chatterjee", "Shaurya Bansal"
]

PICKUP_ADDRESSES = [
    "Plot 23, Sunrise Apartments, Jubilee Hills, Hyderabad",
    "House 45, Green Valley Colony, Banjara Hills, Hyderabad",
    "Flat 302, Silver Oak Towers, Gachibowli, Hyderabad",
    "Villa 12, Lotus Gardens, Kondapur, Hyderabad",
    "Apartment 504, Rainbow Residency, Miyapur, Hyderabad",
    "House 78, Golden Heights, Kukatpally, Hyderabad",
    "Flat 201, Emerald Plaza, Madhapur, Hyderabad",
    "Plot 34, Diamond Enclave, Manikonda, Hyderabad",
    "Bungalow 9, Palm Meadows, Kompally, Hyderabad",
    "Apartment 701, Blue Ridge, HITEC City, Hyderabad",
    "House 56, Vasant Vihar, Road No 12, Banjara Hills",
    "Flat 403, Cyber Towers, Gachibowli, Hyderabad",
    "Villa 23, Lake View Residency, Madhapur, Hyderabad",
    "Plot 67, Shanti Nagar, Borabanda, Hyderabad",
    "Apartment 302, Meridian Splendor, Financial District"
]

DROP_ADDRESSES = [
    "School Main Gate, Road No 5, Jubilee Hills, Hyderabad",
    "School Campus Entrance, Gachibowli, Hyderabad",
    "Institute Main Block, SR Nagar, Hyderabad",
    "Academy Front Gate, Ameerpet, Hyderabad",
    "College Administrative Block, Kukatpally, Hyderabad",
    "School Primary Wing, Banjara Hills, Hyderabad",
    "Institute Reception Area, Madhapur, Hyderabad",
    "School Sports Ground Gate, Kondapur, Hyderabad",
    "College Library Entrance, Miyapur, Hyderabad",
    "Academy Auditorium Gate, HITEC City, Hyderabad"
]

NOTES = [
    "Please ensure the bus reaches on time as I have morning classes.",
    "My child has asthma, please ensure good ventilation in the bus.",
    "Prefer a seat near the front as my child gets motion sickness.",
    "Request for a female conductor if possible.",
    "My child is new to the school, please assign a friendly conductor.",
    "Need GPS tracking access for the bus route.",
    "Prefer morning pickup time between 7:00 AM - 7:30 AM.",
    "My child has a medical condition, keep emergency contact handy.",
    "Request for air-conditioned bus if available.",
    "Prefer a seat near the window for better air circulation.",
    "",  # Some requests without notes
    "",
    ""
]

COMMENT_TEMPLATES = [
    "Thank you for your request. We will review and get back to you soon.",
    "Your request has been received. Our team is working on route allocation.",
    "We are currently reviewing bus availability for your area.",
    "Your pickup location has been noted. We will assign the nearest route.",
    "Request acknowledged. Expected response time: 2-3 business days.",
    "We are checking bus capacity for your requested area.",
    "Your contact details have been verified. Awaiting route assignment.",
    "Thank you for providing detailed location information.",
    "Request is under review by our transportation coordinator.",
    "We will contact you via email once the route is confirmed."
]


def get_random_phone():
    """Generate a random 10-digit Indian phone number"""
    return f"{random.randint(6, 9)}{random.randint(100000000, 999999999)}"


def get_random_email(name):
    """Generate a random email based on student name"""
    domains = ["gmail.com", "yahoo.com", "outlook.com", "hotmail.com"]
    name_part = name.lower().replace(" ", ".")
    return f"{name_part}@{random.choice(domains)}"


def get_google_maps_link(address):
    """Generate a Google Maps link for an address"""
    encoded_address = address.replace(" ", "+").replace(",", "%2C")
    return f"https://www.google.com/maps/search/?api=1&query={encoded_address}"


def clear_bus_requests():
    """Clear all existing bus requests and comments"""
    print("\n🗑️  Clearing existing bus request data...")
    
    with transaction.atomic():
        BusRequestComment.objects.all().delete()
        print("   ✓ Cleared bus request comments")
        
        BusRequest.objects.all().delete()
        print("   ✓ Cleared bus requests")


def create_bus_requests(num_requests=20, create_comments=True):
    """
    Create dummy bus requests with optional comments.
    
    Args:
        num_requests (int): Number of bus requests to create (default: 20)
        create_comments (bool): Whether to create comments on some requests (default: True)
    """
    print(f"\n🚌 Creating {num_requests} dummy bus requests...")
    
    # Get required existing data
    organisations = list(Organisation.objects.all())
    if not organisations:
        print("   ❌ No organisations found. Please run create_dummy_data.py first.")
        return
    
    institutions = list(Institution.objects.all())
    if not institutions:
        print("   ❌ No institutions found. Please run create_dummy_data.py first.")
        return
    
    registrations = list(Registration.objects.all())
    if not registrations:
        print("   ❌ No registrations found. Please run create_dummy_data.py first.")
        return
    
    receipts = list(Receipt.objects.all())
    if not receipts:
        print("   ❌ No receipts found. Please run create_dummy_data.py first.")
        return
    
    student_groups = list(StudentGroup.objects.all())
    
    # Get users for creating comments
    admin_users = list(User.objects.filter(
        profile__role__in=[UserProfile.CENTRAL_ADMIN, UserProfile.INSTITUTION_ADMIN]
    ))
    
    requests_created = 0
    comments_created = 0
    
    with transaction.atomic():
        for i in range(num_requests):
            # Select random entities
            org = random.choice(organisations)
            institution = random.choice([inst for inst in institutions if inst.org == org])
            registration = random.choice([reg for reg in registrations if reg.org == org])
            receipt = random.choice([rec for rec in receipts if rec.org == org])
            student_group = random.choice(student_groups) if student_groups and random.random() > 0.2 else None
            
            # Generate student data
            student_name = random.choice(STUDENT_NAMES)
            pickup_address = random.choice(PICKUP_ADDRESSES)
            drop_address = random.choice(DROP_ADDRESSES)
            
            # Create bus request
            bus_request = BusRequest.objects.create(
                org=org,
                institution=institution,
                registration=registration,
                receipt=receipt,
                student_group=student_group,
                student_name=student_name,
                pickup_address=pickup_address,
                pickup_location_map_link=get_google_maps_link(pickup_address),
                drop_address=drop_address,
                drop_location_map_link=get_google_maps_link(drop_address),
                contact_no=get_random_phone(),
                contact_email=get_random_email(student_name),
                note=random.choice(NOTES),
                status=random.choice(['open', 'open', 'open', 'closed'])  # 75% open, 25% closed
            )
            requests_created += 1
            
            # Create comments on some requests (60% chance)
            if create_comments and admin_users and random.random() > 0.4:
                num_comments = random.randint(1, 3)
                for _ in range(num_comments):
                    BusRequestComment.objects.create(
                        bus_request=bus_request,
                        comment=random.choice(COMMENT_TEMPLATES),
                        created_by=random.choice(admin_users)
                    )
                    comments_created += 1
    
    print(f"   ✓ Created {requests_created} bus requests")
    if create_comments:
        print(f"   ✓ Created {comments_created} comments")


def print_summary():
    """Print a summary of created bus requests"""
    print("\n📊 Bus Request Summary:")
    print(f"   Total Bus Requests: {BusRequest.objects.count()}")
    print(f"   Open Requests: {BusRequest.objects.filter(status='open').count()}")
    print(f"   Closed Requests: {BusRequest.objects.filter(status='closed').count()}")
    print(f"   Total Comments: {BusRequestComment.objects.count()}")
    print(f"   Requests with StudentGroup: {BusRequest.objects.filter(student_group__isnull=False).count()}")
    print(f"   Requests without StudentGroup: {BusRequest.objects.filter(student_group__isnull=True).count()}")


def main():
    """Main function to orchestrate dummy data creation"""
    print("=" * 60)
    print("  SFS BusNest - Bus Request Dummy Data Creation")
    print("=" * 60)
    
    try:
        # Ask user for confirmation
        response = input("\n⚠️  This will delete all existing bus requests. Continue? (y/n): ")
        if response.lower() != 'y':
            print("\n❌ Operation cancelled.")
            return
        
        # Ask for number of requests
        num_input = input("\n📝 How many bus requests to create? (default: 20): ")
        num_requests = int(num_input) if num_input.strip() else 20
        
        # Ask about comments
        comments_input = input("💬 Create comments on requests? (y/n, default: y): ")
        create_comments = comments_input.lower() != 'n' if comments_input.strip() else True
        
        # Clear existing data
        clear_bus_requests()
        
        # Create new dummy data
        create_bus_requests(num_requests=num_requests, create_comments=create_comments)
        
        # Print summary
        print_summary()
        
        print("\n" + "=" * 60)
        print("  ✅ Bus request dummy data creation completed successfully!")
        print("=" * 60)
        
    except KeyboardInterrupt:
        print("\n\n❌ Operation cancelled by user.")
    except Exception as e:
        print(f"\n\n❌ Error: {str(e)}")
        import traceback
        traceback.print_exc()


if __name__ == '__main__':
    main()
