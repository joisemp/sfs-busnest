# Generated by Django 4.2 on 2025-01-26 18:56

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('services', '0001_initial'),
    ]

    operations = [
        migrations.AddField(
            model_name='organisation',
            name='area',
            field=models.CharField(default=1, max_length=200),
            preserve_default=False,
        ),
        migrations.AddField(
            model_name='organisation',
            name='city',
            field=models.CharField(default=1, max_length=200),
            preserve_default=False,
        ),
    ]
