# Generated by Django 4.2 on 2025-01-20 09:05

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('services', '0005_stop_registration_alter_stop_org'),
    ]

    operations = [
        migrations.AlterField(
            model_name='stop',
            name='org',
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='org_stops', to='services.organisation'),
        ),
        migrations.AlterField(
            model_name='stop',
            name='registration',
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='registration_stops', to='services.registration'),
        ),
    ]
