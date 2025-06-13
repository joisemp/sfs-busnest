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
    # Step 1: Tickets referencing the stop
    tickets = Ticket.objects.filter(
        models.Q(pickup_point=stop_to_move) | models.Q(drop_point=stop_to_move)
    )

    # Step 2: Available bus records for new_route
    bus_records = BusRecord.objects.filter(
        trips__route=new_route
    ).distinct()

    if not bus_records.exists():
        raise ValueError("No bus records found for the new route")

    # Prepare to track how many tickets move to each bus record + schedule
    # Key: (bus_record_id, schedule_id), value: count of tickets moving
    ticket_counts = defaultdict(int)

    # Step 3: Map tickets to bus records and schedules, validate trips exist
    # We'll also track which bus record can serve each ticket's pickup/drop
    ticket_assignments = []

    for ticket in tickets:
        pickup_sched = ticket.pickup_schedule
        drop_sched = ticket.drop_schedule

        # Filter bus_records with trips matching the ticket's schedules
        possible_bus_records = []

        for br in bus_records:
            br_trips = br.trips.all()
            # Check trips exist for pickup/drop schedules as applicable
            has_pickup_trip = pickup_sched and br_trips.filter(schedule=pickup_sched).exists()
            has_drop_trip = drop_sched and br_trips.filter(schedule=drop_sched).exists()

            # Ticket must have pickup and drop both on same bus record if both schedules exist
            if pickup_sched and drop_sched:
                if has_pickup_trip and has_drop_trip:
                    possible_bus_records.append(br)
            elif pickup_sched:
                if has_pickup_trip:
                    possible_bus_records.append(br)
            elif drop_sched:
                if has_drop_trip:
                    possible_bus_records.append(br)

        if not possible_bus_records:
            raise ValueError(f"No suitable bus record with required trips found for ticket {ticket.ticket_id}")

        # Assign to the first bus record with enough capacity (will verify capacity later)
        assigned_br = None
        for br in possible_bus_records:
            br_trips = br.trips.all()
            can_assign = True

            # Check capacity for pickup trip
            if pickup_sched:
                pickup_trip = br_trips.filter(schedule=pickup_sched).first()
                if pickup_trip.booking_count + ticket_counts[(br.id, pickup_sched.id)] + 1 > br.bus.capacity:
                    can_assign = False

            # Check capacity for drop trip
            if can_assign and drop_sched:
                drop_trip = br_trips.filter(schedule=drop_sched).first()
                if drop_trip.booking_count + ticket_counts[(br.id, drop_sched.id)] + 1 > br.bus.capacity:
                    can_assign = False

            if can_assign:
                assigned_br = br
                break

        if not assigned_br:
            raise ValueError(f"Capacity exceeded for all bus records for ticket {ticket.ticket_id}")

        # Record this assignment
        if pickup_sched:
            ticket_counts[(assigned_br.id, pickup_sched.id)] += 1
        if drop_sched:
            ticket_counts[(assigned_br.id, drop_sched.id)] += 1

        ticket_assignments.append((ticket, assigned_br))

    # Step 4: All tickets can fit; now update in DB atomically
    with transaction.atomic():
        for ticket, new_br in ticket_assignments:
            old_pickup_br = ticket.pickup_bus_record
            old_drop_br = ticket.drop_bus_record

            pickup_sched = ticket.pickup_schedule
            drop_sched = ticket.drop_schedule

            # Decrement old trips
            if old_pickup_br and pickup_sched:
                old_pickup_trip = old_pickup_br.trips.filter(schedule=pickup_sched).first()
                if old_pickup_trip:
                    old_pickup_trip.booking_count = max(old_pickup_trip.booking_count - 1, 0)
                    old_pickup_trip.save()

            if old_drop_br and drop_sched:
                old_drop_trip = old_drop_br.trips.filter(schedule=drop_sched).first()
                if old_drop_trip:
                    old_drop_trip.booking_count = max(old_drop_trip.booking_count - 1, 0)
                    old_drop_trip.save()

            # Increment new trips
            new_trips = new_br.trips.all()
            if pickup_sched:
                new_pickup_trip = new_trips.filter(schedule=pickup_sched).first()
                if new_pickup_trip:
                    new_pickup_trip.booking_count += 1
                    new_pickup_trip.save()
                ticket.pickup_bus_record = new_br

            if drop_sched:
                new_drop_trip = new_trips.filter(schedule=drop_sched).first()
                if new_drop_trip:
                    new_drop_trip.booking_count += 1
                    new_drop_trip.save()
                ticket.drop_bus_record = new_br

            # Update ticket's pickup/drop stop route to new route if applicable
            if ticket.pickup_point == stop_to_move:
                ticket.pickup_point.route = new_route
                ticket.pickup_point.save()
            if ticket.drop_point == stop_to_move:
                ticket.drop_point.route = new_route
                ticket.drop_point.save()

            ticket.save()

        # Finally, update the stop's route itself
        stop_to_move.route = new_route
        stop_to_move.save()
