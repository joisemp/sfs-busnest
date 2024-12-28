import csv
import os
from celery import shared_task
from django.conf import settings
import logging
import time
from django.core.mail import send_mail

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
def process_uploaded_csv(file_path):
    try:
        logger.info(f"Processing file: {file_path}")
        full_path = os.path.join(settings.MEDIA_ROOT, file_path)

        with open(full_path, 'r') as csvfile:
            reader = csv.reader(csvfile)
            for row in reader:
                logger.info(f"Row: {row}")

        logger.info("CSV PROCESSING COMPLETED SUCCESSFULLY!")
    except Exception as e:
        logger.error(f"Error while processing CSV: {e}")
        raise