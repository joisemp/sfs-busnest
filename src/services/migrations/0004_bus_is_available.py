# Generated by Django 4.2 on 2025-01-20 08:43

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('services', '0003_rename_bus_no_bus_registration_no_remove_bus_label_and_more'),
    ]

    operations = [
        migrations.AddField(
            model_name='bus',
            name='is_available',
            field=models.BooleanField(default=True),
        ),
    ]
