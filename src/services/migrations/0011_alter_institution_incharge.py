# Generated by Django 4.2 on 2024-11-24 11:09

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0001_initial'),
        ('services', '0010_ticket_alternative_contact_no_ticket_recipt_id_and_more'),
    ]

    operations = [
        migrations.AlterField(
            model_name='institution',
            name='incharge',
            field=models.OneToOneField(max_length=200, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='institution', to='core.userprofile'),
        ),
    ]
