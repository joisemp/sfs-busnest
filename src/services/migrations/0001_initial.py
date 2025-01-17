# Generated by Django 4.2 on 2025-01-04 05:18

import config.validators
from django.conf import settings
import django.core.validators
from django.db import migrations, models
import django.db.models.deletion
import services.models


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        ('core', '0001_initial'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name='Bus',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('label', models.CharField(max_length=255)),
                ('bus_no', models.CharField(max_length=15)),
                ('driver', models.CharField(max_length=255)),
                ('capacity', models.PositiveIntegerField()),
                ('slug', models.SlugField(unique=True)),
            ],
        ),
        migrations.CreateModel(
            name='Institution',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(db_index=True, max_length=200)),
                ('label', models.CharField(max_length=50, unique=True)),
                ('contact_no', models.CharField(db_index=True, max_length=12, validators=[django.core.validators.RegexValidator('^\\d{10,12}$', 'Enter a valid contact number')])),
                ('email', models.EmailField(db_index=True, max_length=254, unique=True)),
                ('slug', models.SlugField(unique=True)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('incharge', models.OneToOneField(max_length=200, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='institution', to='core.userprofile')),
            ],
        ),
        migrations.CreateModel(
            name='Organisation',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(db_index=True, max_length=200)),
                ('contact_no', models.CharField(db_index=True, max_length=12, null=True, validators=[django.core.validators.RegexValidator('^\\d{10,12}$', 'Enter a valid contact number')])),
                ('email', models.EmailField(db_index=True, max_length=254, null=True, unique=True)),
                ('slug', models.SlugField(unique=True)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
            ],
        ),
        migrations.CreateModel(
            name='Receipt',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('receipt_id', models.CharField(max_length=500, unique=True)),
                ('student_id', models.CharField(max_length=20)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('slug', models.SlugField(unique=True)),
                ('institution', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='recipts', to='services.institution')),
                ('org', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='recipts', to='services.organisation')),
            ],
        ),
        migrations.CreateModel(
            name='Registration',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(max_length=200)),
                ('instructions', models.TextField()),
                ('status', models.BooleanField(default=False)),
                ('code', models.CharField(max_length=100, null=True, unique=True)),
                ('slug', models.SlugField(unique=True)),
                ('org', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='registrations', to='services.organisation')),
            ],
        ),
        migrations.CreateModel(
            name='Schedule',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(max_length=50)),
                ('start_time', models.TimeField()),
                ('end_time', models.TimeField()),
                ('slug', models.SlugField(unique=True)),
                ('org', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='schedules', to='services.organisation')),
            ],
        ),
        migrations.CreateModel(
            name='Stop',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(max_length=200)),
                ('map_link', models.CharField(max_length=255, null=True)),
                ('slug', models.SlugField(unique=True)),
                ('org', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='stops', to='services.organisation')),
            ],
        ),
        migrations.CreateModel(
            name='StudentGroup',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(max_length=20)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('slug', models.SlugField(unique=True)),
                ('institution', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='groups', to='services.institution')),
                ('org', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='groups', to='services.organisation')),
            ],
        ),
        migrations.CreateModel(
            name='Ticket',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('ticket_id', models.CharField(max_length=300, unique=True)),
                ('student_id', models.CharField(max_length=100)),
                ('student_name', models.CharField(max_length=200)),
                ('student_email', models.EmailField(max_length=254)),
                ('contact_no', models.CharField(max_length=12, validators=[django.core.validators.RegexValidator('^\\d{10,12}$', 'Enter a valid contact number')])),
                ('alternative_contact_no', models.CharField(max_length=12, validators=[django.core.validators.RegexValidator('^\\d{10,12}$', 'Enter a valid contact number')])),
                ('status', models.BooleanField(default=False)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('slug', models.SlugField(unique=True)),
                ('bus', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='tickets', to='services.bus')),
                ('drop_point', models.ForeignKey(null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='ticket_drops', to='services.stop')),
                ('institution', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='tickets', to='services.institution')),
                ('org', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='tickets', to='services.organisation')),
                ('pickup_point', models.ForeignKey(null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='ticket_pickups', to='services.stop')),
                ('recipt', models.OneToOneField(on_delete=django.db.models.deletion.CASCADE, related_name='ticket', to='services.receipt')),
                ('registration', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='tickets', to='services.registration')),
                ('schedule', models.ForeignKey(null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='tickets', to='services.schedule')),
                ('student_group', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='tickets', to='services.studentgroup')),
            ],
        ),
        migrations.CreateModel(
            name='RouteFile',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(max_length=200)),
                ('file', models.FileField(upload_to=services.models.rename_uploaded_file, validators=[config.validators.validate_excel_file])),
                ('added', models.BooleanField(default=False)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('slug', models.SlugField(unique=True)),
                ('org', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='route_files', to='services.organisation')),
            ],
        ),
        migrations.CreateModel(
            name='Route',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(max_length=200)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('slug', models.SlugField(unique=True)),
                ('org', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='routes', to='services.organisation')),
                ('stops', models.ManyToManyField(related_name='stops', to='services.stop')),
            ],
        ),
        migrations.AddField(
            model_name='registration',
            name='stops',
            field=models.ManyToManyField(related_name='registration_stops', to='services.stop'),
        ),
        migrations.CreateModel(
            name='ReceiptFile',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('file', models.FileField(upload_to=services.models.rename_uploaded_file_receipt, validators=[config.validators.validate_excel_file])),
                ('added', models.BooleanField(default=False)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('slug', models.SlugField(unique=True)),
                ('institution', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='recipt_files', to='services.institution')),
                ('org', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='recipt_files', to='services.organisation')),
                ('registration', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='recipt_files', to='services.registration')),
            ],
        ),
        migrations.AddField(
            model_name='receipt',
            name='registration',
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='recipts', to='services.registration'),
        ),
        migrations.AddField(
            model_name='receipt',
            name='student_group',
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='services.studentgroup'),
        ),
        migrations.AddField(
            model_name='institution',
            name='org',
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='institutions', to='services.organisation'),
        ),
        migrations.CreateModel(
            name='FAQ',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('question', models.CharField(max_length=500)),
                ('answer', models.TextField()),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('slug', models.SlugField(unique=True)),
                ('org', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='faqs', to='services.organisation')),
                ('registration', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='faqs', to='services.registration')),
            ],
        ),
        migrations.CreateModel(
            name='ExportedFile',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('file', models.FileField(upload_to='exports/')),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('user', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to=settings.AUTH_USER_MODEL)),
            ],
        ),
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
                ('institution', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='bus_requests', to='services.institution')),
                ('org', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='bus_requests', to='services.organisation')),
                ('receipt', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='services.receipt')),
                ('registration', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='bus_requests', to='services.registration')),
                ('student_group', models.ForeignKey(null=True, on_delete=django.db.models.deletion.SET_NULL, to='services.studentgroup')),
            ],
        ),
        migrations.AddField(
            model_name='bus',
            name='org',
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='buses', to='services.organisation'),
        ),
        migrations.AddField(
            model_name='bus',
            name='route',
            field=models.ForeignKey(null=True, on_delete=django.db.models.deletion.SET_NULL, to='services.route'),
        ),
        migrations.AddField(
            model_name='bus',
            name='schedule',
            field=models.ForeignKey(null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='buses', to='services.schedule'),
        ),
        migrations.CreateModel(
            name='BusCapacity',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('available_seats', models.PositiveIntegerField()),
                ('bus', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='capacities', to='services.bus')),
                ('registration', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='bus_capacities', to='services.registration')),
            ],
            options={
                'unique_together': {('bus', 'registration')},
            },
        ),
    ]
