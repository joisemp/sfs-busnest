"""
Script to delete all routes and stops for a specific registration.

Usage:
    From src/ directory:
    python manage.py shell < dev_utils/delete_routes_and_stops.py
    
    Or in Django shell:
    exec(open('dev_utils/delete_routes_and_stops.py').read())
"""

import os
import sys
import django

# Add the parent directory (src) to the Python path
current_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.dirname(current_dir)
sys.path.insert(0, parent_dir)

# Setup Django environment
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from django.db import transaction
from services.models import Registration, Route, Stop

# Registration slug to delete routes/stops from
REGISTRATION_SLUG = 'sfs-group-of-institutions-academic-year-2026-27-facp'

def delete_routes_and_stops(registration_slug):
    """
    Delete all routes and stops for a specific registration.
    
    Args:
        registration_slug: The slug of the registration
        
    Returns:
        dict: Summary of deletion operation
    """
    try:
        # Get the registration
        registration = Registration.objects.get(slug=registration_slug)
        print(f"Found registration: {registration.name}")
        print(f"Organization: {registration.org}")
        
        # Count before deletion
        routes_count = Route.objects.filter(registration=registration).count()
        stops_count = Stop.objects.filter(registration=registration).count()
        
        print(f"\nFound {routes_count} routes and {stops_count} stops")
        
        if routes_count == 0 and stops_count == 0:
            print("No routes or stops to delete.")
            return {
                'success': True,
                'routes_deleted': 0,
                'stops_deleted': 0,
                'message': 'No data to delete'
            }
        
        # Confirm deletion
        confirm = input(f"\nAre you sure you want to delete {routes_count} routes and {stops_count} stops? (yes/no): ")
        
        if confirm.lower() != 'yes':
            print("Operation cancelled.")
            return {
                'success': False,
                'message': 'User cancelled operation'
            }
        
        # Delete within transaction
        with transaction.atomic():
            # Delete routes (stops will cascade delete automatically)
            deleted_info = Route.objects.filter(registration=registration).delete()
            
            # deleted_info is a tuple: (total_deleted, {model: count})
            total_deleted = deleted_info[0]
            model_counts = deleted_info[1]
            
            routes_deleted = model_counts.get('services.Route', 0)
            stops_deleted = model_counts.get('services.Stop', 0)
            
            print(f"\n✓ Successfully deleted:")
            print(f"  - {routes_deleted} routes")
            print(f"  - {stops_deleted} stops")
            print(f"  - {total_deleted} total records (including related data)")
            
            return {
                'success': True,
                'routes_deleted': routes_deleted,
                'stops_deleted': stops_deleted,
                'total_deleted': total_deleted,
                'model_counts': model_counts,
                'message': 'Deletion successful'
            }
            
    except Registration.DoesNotExist:
        print(f"✗ Error: Registration with slug '{registration_slug}' not found.")
        return {
            'success': False,
            'message': 'Registration not found'
        }
    except Exception as e:
        print(f"✗ Error during deletion: {str(e)}")
        return {
            'success': False,
            'message': f'Error: {str(e)}'
        }

# Run the deletion
if __name__ == '__main__':
    print("=" * 70)
    print("DELETE ROUTES AND STOPS SCRIPT")
    print("=" * 70)
    print(f"\nTarget Registration Slug: {REGISTRATION_SLUG}\n")
    
    result = delete_routes_and_stops(REGISTRATION_SLUG)
    
    print("\n" + "=" * 70)
    if result['success']:
        print("OPERATION COMPLETED SUCCESSFULLY")
    else:
        print("OPERATION FAILED")
    print("=" * 70)
