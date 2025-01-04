from celery import shared_task
from django.shortcuts import get_object_or_404
import openpyxl
from openpyxl.styles import Font
from io import BytesIO
from django.conf import settings
import logging, time, os, csv
from django.core.mail import send_mail
from services.models import Organisation, Receipt, Stop, Route, Institution, Registration, StudentGroup, Ticket, ExportedFile
from django.db import transaction
from django.contrib.auth import get_user_model
from django.core.files import File
from django.urls import reverse

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
def process_uploaded_route_excel(file_path, org_id):
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
                    route = Route.objects.create(org=org, name=route_name.strip())
                    logger.info(f"Created Route: {route.name} (ID: {route.id})")

                    # Iterate over the rows below the header in the same column
                    for row_number, row in enumerate(sheet.iter_rows(min_row=2, min_col=col_index, max_col=col_index), start=2):
                        stop_name = row[0].value
                        if not stop_name:
                            logger.warning(f"Row {row_number} in column {col_index} is empty. Skipping.")
                            continue

                        stop_name = stop_name.strip().upper()
                        map_link = None  # Modify if a map link is expected elsewhere in the Excel structure

                        try:
                            stop, created = Stop.objects.get_or_create(
                                org=org,
                                name=stop_name,
                                defaults={'map_link': map_link},
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

        
        

@shared_task(name='process_uploaded_receipt_data_csv')
def process_uploaded_receipt_data_csv(file_path, org_id, institution_id, reg_id):
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

            # Process CSV File
            with open(full_path, 'r') as csvfile:
                logger.info(f"Opened file: {full_path}")
                reader = csv.reader(csvfile)
                for row_number, row in enumerate(reader, start=1):
                    try:
                        logger.info(f"Processing Row {row_number}: {row}")

                        # Extract data from row
                        receipt_id = row[0].strip()
                        student_id = row[1].strip()
                        class_name = row[2].strip()
                        class_section = row[3].strip()
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
                    except IndexError:
                        logger.warning(f"Row {row_number} is malformed or incomplete: {row}")
                        raise ValueError(f"Malformed row at line {row_number}. Rolling back the operation.")
                    except Exception as e:
                        logger.error(f"Error processing Row {row_number}: {row}. Error: {e}")
                        raise

            logger.info("CSV processing completed successfully.")

    except Exception as e:
        logger.error(f"Error while processing CSV: {e}")
        raise
    finally:
        logger.info("Task Ended: process_uploaded_receipts_csv")


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
        if filters.get('buses'):
            queryset = queryset.filter(bus_id__in=filters['buses'])

    # Creating Excel file
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "Tickets"

    # Set headers
    headers = ['Ticket ID', 'Student Name', 'Student Email', 'Contact No', 'Alternative No', 'Bus', 'Pickup Point', 'Drop Point', 'Schedule', 'Status', 'Created At']
    ws.append(headers)
    for cell in ws[1]:
        cell.font = Font(bold=True)
    
    # Add ticket data
    for ticket in queryset:
        ws.append([
            ticket.ticket_id,
            ticket.student_name,
            ticket.student_email,
            ticket.contact_no,
            ticket.alternative_contact_no,
            ticket.bus.label,
            ticket.pickup_point.name if ticket.pickup_point else '',
            ticket.drop_point.name if ticket.drop_point else '',
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
