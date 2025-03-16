# Generated by Django 4.2 on 2025-03-15 06:03

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('services', '0027_rename_progress_notification_notification_priority'),
    ]

    operations = [
        migrations.AlterField(
            model_name='notification',
            name='type',
            field=models.CharField(choices=[('info', 'Info'), ('warning', 'Warning'), ('danger', 'Error'), ('success', 'Success')], default='info', max_length=10),
        ),
    ]
