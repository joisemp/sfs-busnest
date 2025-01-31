from celery import shared_task
from django.shortcuts import get_object_or_404
import openpyxl
from openpyxl.styles import Font
from io import BytesIO
from django.conf import settings
import logging, time, os
from django.core.mail import send_mail
from services.models import Organisation, Receipt, Stop, Route, Institution, Registration, StudentGroup, Ticket, ExportedFile, BusFile, Bus
from django.db import transaction
from django.contrib.auth import get_user_model
from django.core.files import File
from django.urls import reverse
from django.utils.timezone import now
from datetime import timedelta


User = get_user_model()

logger = logging.getLogger(__name__)

@shared_task(name='count_to_10')
def count_task():
    logger.info("Task started: Count to 10")
    for i in range(1, 11):
        logger.info(i)
        time.sleep(1)
    logger.info("Task compeleted!!!!")
    return "TASK DONE!!"

@shared_task(name='send_newsletter')
def send_newsletter():
    logger.info("Task started : sending newsletters")
    for i in range(1, 11):
        logger.info(f'{i}. Newsletter')
        time.sleep(1)
    logger.info("All Newsletter sent!!")
    return 'COMPLETED!!!!!'

@shared_task(name='send_email_task')
def send_email_task(subject, message, recipient_list, from_email=None):
    try:
        logger.info(f"Starting email task: Sending email to {recipient_list}")
        send_mail(
            subject=subject,
            message=message,
            from_email=from_email,
            recipient_list=recipient_list,
            fail_silently=False,
        )
        logger.info(f"Email successfully sent to {recipient_list}")
        return "Email sent successfully"
    except Exception as e:
        logger.error(f"Failed to send email to {recipient_list}: {e}")
        raise


@shared_task(name='process_uploaded_route_excel')
def process_uploaded_route_excel(file_path, org_id, registration_id):
    try:
        logger.info(f"Task Started: Processing file: {file_path}")
        full_path = os.path.join(settings.MEDIA_ROOT, file_path)

        with transaction.atomic():
            try:
                org = Organisation.objects.get(id=org_id)
                logger.info(f"Organisation fetched successfully: {org.name} (ID: {org_id})")
            except Organisation.DoesNotExist:
                logger.error(f"Organisation with ID {org_id} does not exist.")
                return
            
            try:
                registration_obj = Registration.objects.get(id=registration_id)
                logger.info(f"Registration fetched successfully: {registration_obj.name} (ID: {registration_id})")
            except Registration.DoesNotExist:
                logger.error(f"Registration with ID {registration_id} does not exist.")
                return

            # Open the Excel file
            try:
                from openpyxl import load_workbook
                workbook = load_workbook(full_path)
                sheet = workbook.active
                logger.info(f"Excel file opened successfully: {full_path}")
            except Exception as e:
                logger.error(f"Failed to open the Excel file: {e}")
                raise

            # Process the sheet headers and data
            headers = [cell.value for cell in sheet[1]]  # First row as headers
            logger.info(f"Extracted headers (route names): {headers}")

            for col_index, route_name in enumerate(headers, start=1):
                if not route_name:
                    logger.warning(f"Skipping empty header in column {col_index}.")
                    continue

                try:
                    route = Route.objects.create(org=org, registration=registration_obj, name=route_name.strip())
                    logger.info(f"Created Route: {route.name} (ID: {route.id})")

                    # Iterate over the rows below the header in the same column
                    for row_number, row in enumerate(sheet.iter_rows(min_row=2, min_col=col_index, max_col=col_index), start=2):
                        stop_name = row[0].value
                        if not stop_name:
                            logger.warning(f"Row {row_number} in column {col_index} is empty. Skipping.")
                            continue

                        stop_name = stop_name.strip().upper()

                        try:
                            stop, created = Stop.objects.get_or_create(
                                org=org,
                                name=stop_name,
                                registration = registration_obj
                            )

                            if created:
                                logger.info(f"Row {row_number}: Stop created - {stop.name} (ID: {stop.id})")
                            else:
                                logger.info(f"Row {row_number}: Stop already exists - {stop.name} (ID: {stop.id})")

                            route.stops.add(stop)
                            logger.info(f"Row {row_number}: Stop {stop.name} added to Route {route.name} (ID: {route.id})")
                        except Exception as e:
                            logger.error(f"Error processing Row {row_number} in column {col_index}: {e}")
                            raise

                except Exception as e:
                    logger.error(f"Error creating Route {route_name}: {e}")
                    raise

            logger.info("Excel processing completed successfully.")

    except Exception as e:
        logger.error(f"Error while processing Excel file: {e}")
        raise
    finally:
        logger.info("Task Ended: process_uploaded_route_excel")

        
        

@shared_task(name='process_uploaded_receipt_data_excel')
def process_uploaded_receipt_data_excel(file_path, org_id, institution_id, reg_id):
    try:
        logger.info(f"Task Started: Processing file: {file_path}")
        full_path = os.path.join(settings.MEDIA_ROOT, file_path)

        with transaction.atomic():
            # Fetch Organisation and Institution
            try:
                org = Organisation.objects.get(id=org_id)
                logger.info(f"Organisation fetched successfully: {org.name} (ID: {org_id})")
            except Organisation.DoesNotExist:
                logger.error(f"Organisation with ID {org_id} does not exist.")
                return

            try:
                institution = Institution.objects.get(id=institution_id)
                logger.info(f"Institution fetched successfully: {institution.name} (ID: {institution_id})")
            except Institution.DoesNotExist:
                logger.error(f"Institution with ID {institution_id} does not exist.")
                return

            # Ensure Registration exists (optional, based on your use case)
            try:
                registration = Registration.objects.get(id=reg_id)
            except Registration.DoesNotExist:
                logger.error(f"Registration with ID {reg_id} does not exist.")

            # Process Excel File
            try:
                import openpyxl
                workbook = openpyxl.load_workbook(full_path)
                sheet = workbook.active

                logger.info(f"Opened file: {full_path}")

                # Validate headings
                headings = [cell.value.strip().lower() for cell in next(sheet.iter_rows(min_row=1, max_row=1))]
                expected_headings = ['receipt id', 'student id', 'class', 'section']

                if headings != expected_headings:
                    logger.error(f"Invalid headings in Excel file. Expected: {expected_headings}, Found: {headings}")
                    raise ValueError("Invalid headings in Excel file.")

                # Process rows
                for row_number, row in enumerate(sheet.iter_rows(min_row=2, values_only=True), start=2):
                    try:
                        logger.info(f"Processing Row {row_number}: {row}")

                        # Extract data from row
                        receipt_id, student_id, class_name, class_section = [
                            str(cell).strip() if cell is not None else '' for cell in row
                        ]

                        if not (receipt_id and student_id and class_name and class_section):
                            logger.warning(f"Row {row_number} is incomplete: {row}")
                            raise ValueError(f"Incomplete data in row {row_number}. Rolling back the operation.")

                        group_name = f"{class_name} - {class_section}"

                        logger.info(f"Row {row_number} - Receipt ID: {receipt_id}, Student ID: {student_id}, Group: {group_name}")

                        # Create or Get StudentGroup
                        student_group, created = StudentGroup.objects.get_or_create(
                            org=org,
                            institution=institution,
                            name=group_name.upper(),
                        )

                        if created:
                            logger.info(f"Row {row_number}: Student Group created - {student_group.name} (ID: {student_group.id})")
                        else:
                            logger.info(f"Row {row_number}: Student Group already exists - {student_group.name} (ID: {student_group.id})")

                        # Create Receipt
                        receipt, created = Receipt.objects.get_or_create(
                            org=org,
                            institution=institution,
                            registration=registration,
                            receipt_id=receipt_id,
                            student_id=student_id.upper(),
                            student_group=student_group,
                        )

                        if created:
                            logger.info(f"Row {row_number}: Receipt created - {receipt.receipt_id} (ID: {receipt.id})")
                        else:
                            logger.info(f"Row {row_number}: Receipt already exists - {receipt.receipt_id} (ID: {receipt.id})")

                    except Exception as e:
                        logger.error(f"Error processing Row {row_number}: {row}. Error: {e}")
                        raise

                logger.info("Excel processing completed successfully.")

            except Exception as e:
                logger.error(f"Error while processing Excel file: {e}")
                raise

    except Exception as e:
        logger.error(f"Error while processing Excel: {e}")
        raise
    finally:
        logger.info("Task Ended: process_uploaded_receipt_data_excel")



def send_export_email(user, exported_file):
    download_url = reverse('central_admin:exported_file_download', kwargs={'file_id': exported_file.id})
    email_subject = 'Your Ticket Export is Ready'
    email_message = f"Hello {user.profile.first_name} {user.profile.last_name},\n\nYour ticket export is ready. You can download the file using the following link:\n{settings.SITE_URL}{download_url}\n\nBest regards,\nYour Team"
    
    send_mail(
        email_subject,
        email_message,
        settings.DEFAULT_FROM_EMAIL,
        [user.email]
    )


@shared_task(name='export_tickets_to_excel')
def export_tickets_to_excel(user_id, registration_slug, search_term='', filters=None):
    user = User.objects.get(id=user_id)
    registration = get_object_or_404(Registration, slug=registration_slug)
    
    # Base queryset filtered by registration and institution
    queryset = Ticket.objects.filter(org=user.profile.org, registration=registration).order_by('-created_at')
    
    
    if filters:
        if filters.get('institution'):
            queryset = queryset.filter(institution_id=filters['institution'])
        if filters.get('pickup_points'):
            queryset = queryset.filter(pickup_point_id__in=filters['pickup_points'])
        if filters.get('drop_points'):
            queryset = queryset.filter(drop_point_id__in=filters['drop_points'])
        if filters.get('schedule'):
            queryset = queryset.filter(schedule_id=filters['schedule'])
        if filters.get('pickup_buses'):
            queryset = queryset.filter(pickup_bus_record_id__in=filters['pickup_buses'])
        if filters.get('drop_buses'):
            queryset = queryset.filter(drop_bus_record_id__in=filters['drop_buses'])
        if filters.get('student_group'):
            queryset = queryset.filter(student_group_id__in=filters['student_group'])

    # Creating Excel file
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "Tickets"

    # Set headers
    headers = ['Ticket ID', 'Student Name', 'Class', 'Section', 'Student Email', 'Contact No', 'Alternative No', 'Pickup Point', 'Drop Point', 'Pickup Bus', 'Drop Bus', 'Schedule', 'Status', 'Created At']
    ws.append(headers)
    for cell in ws[1]:
        cell.font = Font(bold=True)
    
    # Add ticket data
    for ticket in queryset:
        std_class, section = str(ticket.student_group.name).split('-')
        ws.append([
            ticket.ticket_id,
            ticket.student_name,
            std_class.strip(),
            section.strip(),
            ticket.student_email,
            ticket.contact_no,
            ticket.alternative_contact_no,
            ticket.pickup_point.name if ticket.pickup_point else '',
            ticket.drop_point.name if ticket.drop_point else '',
            ticket.pickup_bus_record.label if ticket.pickup_bus_record else '',
            ticket.drop_bus_record.label if ticket.drop_bus_record else '',
            ticket.schedule.name if ticket.schedule else '',
            'Confirmed' if ticket.status else 'Pending',
            ticket.created_at.strftime('%Y-%m-%d %H:%M:%S')
        ])
    
    # Save to BytesIO and create the exported file in one step
    file_stream = BytesIO()
    wb.save(file_stream)
    file_stream.seek(0)

    # Directly create and save the ExportedFile instance
    exported_file = ExportedFile.objects.create(user=user, file=File(file_stream, name=f"{registration_slug}_export.xlsx"))

    # Now that the file is saved, we can send the email
    send_export_email(user, exported_file)
    
    return f"Excel export completed for {user.profile.first_name} {user.profile.last_name} {user.email}"


@shared_task(name='process_uploaded_bus_excel')
def process_uploaded_bus_excel(file_path, org_id):
    try:
        logger.info(f"Task Started: Processing file: {file_path}")
        full_path = os.path.join(settings.MEDIA_ROOT, file_path)

        with transaction.atomic():
            try:
                org = Organisation.objects.get(id=org_id)
                logger.info(f"Organisation fetched successfully: {org.name} (ID: {org_id})")
            except Organisation.DoesNotExist:
                logger.error(f"Organisation with ID {org_id} does not exist.")
                return
            
            try:
                bus_file = BusFile.objects.get(file=file_path)
                logger.info(f"BusFile entry fetched: {bus_file.name}")
            except BusFile.DoesNotExist:
                logger.error(f"BusFile with path {file_path} does not exist.")
                return

            try:
                workbook = openpyxl.load_workbook(full_path)
                sheet = workbook.active
                logger.info(f"Excel file opened successfully: {full_path}")
            except Exception as e:
                logger.error(f"Failed to open the Excel file: {e}")
                raise

            headers = [cell.value for cell in sheet[1]]  # First row as headers
            if headers != ["Registration", "Driver", "Capacity"]:
                logger.error("Invalid headers in the Excel file.")
                return

            for row in sheet.iter_rows(min_row=2, values_only=True):
                registration, driver, capacity = row

                if not registration or not driver or not capacity:
                    logger.warning(f"Skipping incomplete row: {row}")
                    continue

                try:
                    bus, created = Bus.objects.get_or_create(
                        org=org,
                        registration_no=registration.strip(),
                        driver = driver.strip(),
                        capacity = int(capacity)
                    )

                    if created:
                        logger.info(f"Bus created: {registration}, Driver: {driver}, Capacity: {capacity}")
                    else:
                        bus.driver = driver.strip()
                        bus.capacity = int(capacity)
                        bus.save()
                        logger.info(f"Bus updated: {registration}, Driver: {driver}, Capacity: {capacity}")

                except Exception as e:
                    logger.error(f"Error processing bus {registration}: {e}")
                    raise

            bus_file.added = True
            bus_file.save()
            logger.info("Excel processing completed successfully.")

    except Exception as e:
        logger.error(f"Error while processing Excel file: {e}")
        raise
    finally:
        logger.info("Task Ended: process_uploaded_bus_excel")


@shared_task
def mark_expired_receipts():
    expiry_days = 7 
    expiry_date = now() - timedelta(days=expiry_days)

    updated_count = Receipt.objects.filter(created_at__lt=expiry_date, is_expired=False).update(is_expired=True)

    log_message = f"Marked {updated_count} receipts as expired."
    logger.info(log_message)
    return log_message

