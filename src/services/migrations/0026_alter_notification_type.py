# Generated by Django 4.2 on 2025-03-14 18:14

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('services', '0025_notification'),
    ]

    operations = [
        migrations.AlterField(
            model_name='notification',
            name='type',
            field=models.CharField(choices=[('info', 'Info'), ('warning', 'Warning'), ('error', 'Error'), ('success', 'Success')], default='info', max_length=10),
        ),
    ]
