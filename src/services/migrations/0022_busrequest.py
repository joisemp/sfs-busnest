# Generated by Django 4.2 on 2024-12-21 10:18

import django.core.validators
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('services', '0021_bus_capacity_buscapacity'),
    ]

    operations = [
        migrations.CreateModel(
            name='BusRequest',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('student_name', models.CharField(max_length=300)),
                ('pickup_address', models.CharField(max_length=500)),
                ('drop_address', models.CharField(max_length=500)),
                ('contact_no', models.CharField(max_length=12, validators=[django.core.validators.RegexValidator('^\\d{10,12}$', 'Enter a valid contact number')])),
                ('contact_email', models.EmailField(max_length=254)),
                ('slug', models.SlugField(unique=True)),
                ('group', models.ForeignKey(null=True, on_delete=django.db.models.deletion.SET_NULL, to='services.studentgroup')),
                ('institution', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='bus_requests', to='services.institution')),
                ('org', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='bus_requests', to='services.organisation')),
                ('receipt', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='services.receipt')),
                ('registration', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='bus_requests', to='services.registration')),
            ],
        ),
    ]
