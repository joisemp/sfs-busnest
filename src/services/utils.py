from django.db.models import Prefetch
from services.models import BusRecord, Trip
from io import BytesIO
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from PIL import Image
from datetime import datetime
from django.contrib.staticfiles import finders

TEMPLATE_PATH = finders.find("images/id_img.png")  # Use finders to locate the static file

def generate_ids_pdf(students):
    """
    Generates a PDF containing ID cards for a list of students.
    """
    if not TEMPLATE_PATH:
        raise FileNotFoundError("Template image not found. Ensure 'images/id_img.png' exists in the static files directory.")

    buffer = BytesIO()
    c = canvas.Canvas(buffer, pagesize=A4)

    # Load the template image
    template_img = Image.open(TEMPLATE_PATH)
    template_width, template_height = template_img.size

    # Resize template image for better fit
    template_width, template_height = 280 + 5, 160 + 5

    # A4 page size
    page_width, page_height = A4

    # Margin and positioning
    margin_x, margin_y = 10, 40
    card_spacing_x, card_spacing_y = 0, 15

    # Calculate number of cards per row dynamically
    cards_per_row = (page_width - 2 * margin_x + card_spacing_x) // (template_width + card_spacing_x)

    x_offset = margin_x
    y_offset = page_height - template_height - margin_y

    for index, student in enumerate(students):
        # Handle NoneType for schedule names
        pickup_schedule_name = student['pickup_schedule__name']
        drop_schedule_name = student['drop_schedule__name']
        if pickup_schedule_name and drop_schedule_name:
            schedule_text = f"{pickup_schedule_name.upper()} - {drop_schedule_name.upper()}"
        elif pickup_schedule_name:
            schedule_text = f"{pickup_schedule_name.upper()}"
        elif drop_schedule_name:
            schedule_text = f"{drop_schedule_name.upper()}"
        else:
            schedule_text = ""

        # Check if a new page is needed
        if y_offset < margin_y:
            # Add footer before moving to the next page
            footer_text = f"Generated on {datetime.now().strftime('%Y-%m-%d')}"
            c.setFont("Helvetica", 8)
            text_width = c.stringWidth(footer_text, "Helvetica", 8)
            c.drawString((page_width - text_width) / 2, margin_y - 10, footer_text)
            c.showPage()
            x_offset = margin_x
            y_offset = page_height - template_height - margin_y

        # Draw the template image
        c.drawImage(TEMPLATE_PATH, x_offset, y_offset, width=template_width, height=template_height, preserveAspectRatio=True, mask='auto')

        # Add text data
        c.setFont("Helvetica-Bold", 12)
        c.setFillColor(colors.blue)
        c.drawString(x_offset + 20, y_offset + 100 - 10, student['student_name'].upper())

        c.setFont("Helvetica-Bold", 9)
        c.setFillColor(colors.black)
        schedule_text_width = c.stringWidth(schedule_text, "Helvetica-Bold", 9)
        student_id_text_width = c.stringWidth(student['ticket_id'], "Helvetica-Bold", 9)
        max_text_width = max(schedule_text_width, student_id_text_width)
        c.drawString(x_offset + template_width - max_text_width - 20, y_offset + 105 + 35, f"{student['ticket_id']}")
        c.drawString(x_offset + template_width - max_text_width - 20, y_offset + 90 + 35, schedule_text)

        c.setFont("Helvetica-Bold", 9)
        c.setFillColor(colors.black)
        pickup_label = student['pickup_bus_record__label']
        drop_label = student['drop_bus_record__label']
        
        if pickup_label:
            c.drawString(x_offset + 20, y_offset + 81 - 10, f"PICKUP : {pickup_label}")
        else:
            c.drawString(x_offset + 20, y_offset + 81 - 10, f"PICKUP : -")
        
        if drop_label:
            c.drawString(x_offset + 20, y_offset + 65 - 10, f"DROP : {drop_label}")
        else:
            c.drawString(x_offset + 20, y_offset + 65 - 10, f"DROP : -")

        c.setFont("Helvetica-Bold", 10)
        c.setFillColor(colors.gray)
        c.drawString(x_offset + 20, y_offset + 45 - 10, student['institution__name'])
        c.drawString(x_offset + 20, y_offset + 30 - 10, student['student_id'])

        c.setFont("Helvetica-Bold", 12)
        c.setFillColor(colors.black)
        student_class_section = student['student_group__name']
        text_width = c.stringWidth(student_class_section, "Helvetica-Bold", 12)
        c.drawString(x_offset + template_width - text_width - 20, y_offset + 45 - 10, student_class_section)

        current_year = datetime.now().year
        c.setFont("Helvetica", 8)
        year_width = c.stringWidth(str(current_year), "Helvetica", 8)
        c.drawString(x_offset + template_width - year_width - 20, y_offset + 30 - 10, str(current_year))

        c.setFillColor(colors.black)

        # Move position for the next card
        x_offset += template_width + card_spacing_x

        # If the row is full, move to the next row
        if (index + 1) % cards_per_row == 0:
            x_offset = margin_x
            y_offset -= template_height + card_spacing_y

    # Add footer to the last page
    footer_text = f"Generated on {datetime.now().strftime('%Y-%m-%d')}"
    c.setFont("Helvetica", 8)
    text_width = c.stringWidth(footer_text, "Helvetica", 8)
    c.drawString((page_width - text_width) / 2, margin_y - 10, footer_text)

    c.save()
    buffer.seek(0)  # Reset the buffer position to the beginning
    return buffer


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
