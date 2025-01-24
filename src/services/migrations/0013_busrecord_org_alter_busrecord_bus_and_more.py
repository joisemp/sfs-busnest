# Generated by Django 4.2 on 2025-01-21 16:34

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('services', '0012_busrecord_alter_bus_registration_no_and_more'),
    ]

    operations = [
        migrations.AddField(
            model_name='busrecord',
            name='org',
            field=models.ForeignKey(default=1, on_delete=django.db.models.deletion.CASCADE, related_name='bus_records', to='services.organisation'),
            preserve_default=False,
        ),
        migrations.AlterField(
            model_name='busrecord',
            name='bus',
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='records', to='services.bus'),
        ),
        migrations.AlterField(
            model_name='busrecord',
            name='registration',
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='bus_records', to='services.registration'),
        ),
    ]
