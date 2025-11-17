"""
Utility for moving a stop to a new route and updating all related tickets and bus records.

This module provides a function to safely transfer a stop from one route to another, ensuring that all tickets referencing the stop are updated to reference the new route, and that bus record assignments and trip booking counts are adjusted accordingly. The operation is performed atomically to maintain data integrity.

Functions:
    move_stop_and_update_tickets(stop_to_move, new_route):
        Moves a stop to a new route, updates all tickets and bus records referencing the stop, and ensures trip booking counts and assignments remain valid.
"""

from collections import defaultdict
from django.db import transaction
from django.db import models
from services.models import Ticket, BusRecord

def move_stop_and_update_tickets(stop_to_move, new_route):
    """
    Moves a stop to a new route and updates all tickets and bus records referencing the stop.
    Ensures that all tickets referencing the stop are reassigned to valid bus records and trips on the new route, and that trip booking counts are updated accordingly.
    The operation is performed atomically to maintain data integrity.

    Args:
        stop_to_move: The Stop instance to move.
        new_route: The Route instance to assign the stop to.
    Raises:
        ValueError: If no suitable bus record or capacity is found for any ticket.
    """
    # Store the old route before making any changes
    old_route = stop_to_move.route
    
    # Step 1: Tickets referencing the stop
    tickets = Ticket.objects.filter(
        models.Q(pickup_point=stop_to_move) | models.Q(drop_point=stop_to_move)
    )

    # Step 2: Available bus records that have trips for the new_route
    bus_records = BusRecord.objects.filter(
        trips__route=new_route
    ).distinct()

    if not bus_records.exists():
        raise ValueError(f"No bus records found with trips for the new route '{new_route.name}'")

    # Prepare to track how many tickets move to each bus record + schedule
    # Key: (bus_record_id, schedule_id), value: count of tickets moving
    ticket_counts = defaultdict(int)

    # Step 3: Map tickets to bus records and schedules, validate trips exist for the new route
    ticket_assignments = []

    for ticket in tickets:
        pickup_sched = ticket.pickup_schedule
        drop_sched = ticket.drop_schedule
        
        # Determine which stop type(s) are being transferred for this ticket
        is_transferring_pickup = (ticket.pickup_point == stop_to_move)
        is_transferring_drop = (ticket.drop_point == stop_to_move)

        # Filter bus_records with trips matching BOTH the ticket's schedules AND the new route
        # Only check for schedules that are being transferred
        possible_bus_records = []

        for br in bus_records:
            # Get trips that are specifically for the new route
            br_trips_on_new_route = br.trips.filter(route=new_route)
            
            # Check trips exist for the schedules being transferred on the NEW ROUTE
            has_pickup_trip = False
            has_drop_trip = False
            
            if is_transferring_pickup and pickup_sched:
                has_pickup_trip = br_trips_on_new_route.filter(schedule=pickup_sched).exists()
            
            if is_transferring_drop and drop_sched:
                has_drop_trip = br_trips_on_new_route.filter(schedule=drop_sched).exists()

            # Validate based on what's being transferred
            is_valid = False
            if is_transferring_pickup and is_transferring_drop:
                # Both stops being transferred - need both schedules
                if pickup_sched and drop_sched:
                    is_valid = has_pickup_trip and has_drop_trip
                elif pickup_sched:
                    is_valid = has_pickup_trip
                elif drop_sched:
                    is_valid = has_drop_trip
            elif is_transferring_pickup:
                # Only pickup being transferred
                if pickup_sched:
                    is_valid = has_pickup_trip
                else:
                    is_valid = True  # No schedule to validate
            elif is_transferring_drop:
                # Only drop being transferred
                if drop_sched:
                    is_valid = has_drop_trip
                else:
                    is_valid = True  # No schedule to validate
            
            if is_valid:
                possible_bus_records.append(br)

        if not possible_bus_records:
            schedule_info = []
            if is_transferring_pickup and pickup_sched:
                schedule_info.append(f"pickup schedule '{pickup_sched.name}'")
            if is_transferring_drop and drop_sched:
                schedule_info.append(f"drop schedule '{drop_sched.name}'")
            
            stop_type = []
            if is_transferring_pickup:
                stop_type.append("pickup")
            if is_transferring_drop:
                stop_type.append("drop")
            
            raise ValueError(
                f"No bus record found with trips for route '{new_route.name}' and {' and '.join(schedule_info)} "
                f"for ticket {ticket.ticket_id} ({' and '.join(stop_type)} stop). "
                f"Please ensure bus records have trips configured for this route and schedule combination."
            )

        # Assign to the first bus record with enough capacity
        assigned_br = None
        for br in possible_bus_records:
            # Get trips specifically for the new route
            br_trips_on_new_route = br.trips.filter(route=new_route)
            can_assign = True

            # Check capacity for pickup trip on the new route (only if transferring pickup)
            if is_transferring_pickup and pickup_sched:
                pickup_trip = br_trips_on_new_route.filter(schedule=pickup_sched).first()
                if not pickup_trip:
                    can_assign = False
                elif pickup_trip.booking_count + ticket_counts[(br.id, pickup_sched.id)] + 1 > br.bus.capacity:
                    can_assign = False

            # Check capacity for drop trip on the new route (only if transferring drop)
            if can_assign and is_transferring_drop and drop_sched:
                drop_trip = br_trips_on_new_route.filter(schedule=drop_sched).first()
                if not drop_trip:
                    can_assign = False
                elif drop_trip.booking_count + ticket_counts[(br.id, drop_sched.id)] + 1 > br.bus.capacity:
                    can_assign = False

            if can_assign:
                assigned_br = br
                break

        if not assigned_br:
            raise ValueError(
                f"Capacity exceeded for all bus records on route '{new_route.name}' for ticket {ticket.ticket_id}. "
                f"Please add more buses or increase capacity."
            )

        # Record this assignment
        if is_transferring_pickup and pickup_sched:
            ticket_counts[(assigned_br.id, pickup_sched.id)] += 1
        if is_transferring_drop and drop_sched:
            ticket_counts[(assigned_br.id, drop_sched.id)] += 1

        ticket_assignments.append((ticket, assigned_br, is_transferring_pickup, is_transferring_drop))

    # Step 4: All tickets can fit; now update in DB atomically
    with transaction.atomic():
        for ticket, new_br, is_transferring_pickup, is_transferring_drop in ticket_assignments:
            old_pickup_br = ticket.pickup_bus_record
            old_drop_br = ticket.drop_bus_record

            pickup_sched = ticket.pickup_schedule
            drop_sched = ticket.drop_schedule

            # Decrement old trips (from old route) - only for stops being transferred
            if is_transferring_pickup and old_pickup_br and pickup_sched:
                old_pickup_trip = old_pickup_br.trips.filter(schedule=pickup_sched, route=old_route).first()
                if old_pickup_trip:
                    old_pickup_trip.booking_count = max(old_pickup_trip.booking_count - 1, 0)
                    old_pickup_trip.save()

            if is_transferring_drop and old_drop_br and drop_sched:
                old_drop_trip = old_drop_br.trips.filter(schedule=drop_sched, route=old_route).first()
                if old_drop_trip:
                    old_drop_trip.booking_count = max(old_drop_trip.booking_count - 1, 0)
                    old_drop_trip.save()

            # Increment new trips (on new route) and update ticket - only for stops being transferred
            new_trips_on_new_route = new_br.trips.filter(route=new_route)
            
            if is_transferring_pickup and pickup_sched:
                new_pickup_trip = new_trips_on_new_route.filter(schedule=pickup_sched).first()
                if new_pickup_trip:
                    new_pickup_trip.booking_count += 1
                    new_pickup_trip.save()
                    ticket.pickup_bus_record = new_br
                else:
                    raise ValueError(
                        f"Trip not found for bus record {new_br.label}, route '{new_route.name}', "
                        f"and schedule '{pickup_sched.name}'"
                    )

            if is_transferring_drop and drop_sched:
                new_drop_trip = new_trips_on_new_route.filter(schedule=drop_sched).first()
                if new_drop_trip:
                    new_drop_trip.booking_count += 1
                    new_drop_trip.save()
                    ticket.drop_bus_record = new_br
                else:
                    raise ValueError(
                        f"Trip not found for bus record {new_br.label}, route '{new_route.name}', "
                        f"and schedule '{drop_sched.name}'"
                    )

            ticket.save()

        # Finally, update the stop's route itself
        stop_to_move.route = new_route
        stop_to_move.save()
