# Generated by Django 4.2 on 2025-03-16 18:20

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('services', '0029_notification_file_processing_task'),
    ]

    operations = [
        migrations.AlterUniqueTogether(
            name='receipt',
            unique_together={('registration', 'receipt_id', 'student_id')},
        ),
    ]
