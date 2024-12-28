import csv
import os
from celery import shared_task
from django.conf import settings
import logging
import time
from django.core.mail import send_mail
from services.models import Organisation, Stop, Route
from django.db import transaction

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


@shared_task(name='process_uploaded_csv')
def process_uploaded_csv(file_path, org_id, route_name):
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

            route = Route.objects.create(org=org, name=route_name)
            logger.info(f"Created Route: {route.name} (ID: {route.id})")

            with open(full_path, 'r') as csvfile:
                logger.info(f"Opened file: {full_path}")
                reader = csv.reader(csvfile)
                for row_number, row in enumerate(reader, start=1):
                    try:
                        logger.info(f"Processing Row {row_number}: {row}")

                        stop_name = row[0].strip().upper()
                        map_link = row[1].strip()
                        logger.info(f"Row {row_number} - Stop Name: {stop_name}, Map Link: {map_link}")

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
        logger.info("Task Ended: process_uploaded_csv")
