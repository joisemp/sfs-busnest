from django.db.models import Prefetch
from services.models import BusRecord, Trip

def get_filtered_bus_records(schedule_ids, stop_id):
    
    if not schedule_ids:
        raise ValueError("At least one schedule ID is required.")
    
    # Prefetch trips that belong to any of the given schedules.
    # For each trip, load its route and the stops for that route.
    bus_records = BusRecord.objects.prefetch_related(
        Prefetch(
            'trips',
            queryset=Trip.objects.filter(schedule_id__in=schedule_ids)
                .select_related('route')
                .prefetch_related('route__stops'),
            to_attr='prefetched_trips'
        )
    )
    
    filtered_records = []
    
    for record in bus_records:
        # Skip records that have no associated bus
        if not record.bus:
            continue
        
        total_capacity = record.bus.capacity
        
        # Using our prefetched trips (only those with a schedule in schedule_ids)
        trips = record.prefetched_trips
        
        valid_for_all = True
        
        # For each required schedule, check that there is at least one valid trip.
        for schedule in schedule_ids:
            valid_trip_found = False
            
            for trip in trips:
                # Consider only trips for the current schedule
                if trip.schedule_id != schedule:
                    continue
                
                # Check the booking condition: booking_count must be <= total_capacity - 1
                if trip.booking_count > total_capacity - 1:
                    continue
                
                # Check if the trip's route contains the given stop.
                stops_list = list(trip.route.stops.all())
                if any(stop.id == stop_id for stop in stops_list):
                    valid_trip_found = True
                    break  # Found a valid trip for this schedule
            
            if not valid_trip_found:
                valid_for_all = False
                break  # No need to check further schedules
        
        if valid_for_all:
            filtered_records.append(record)
    return filtered_records
