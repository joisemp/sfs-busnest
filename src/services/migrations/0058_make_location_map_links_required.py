# Generated migration to make location map link fields required

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('services', '0057_populate_location_map_links'),
    ]

    operations = [
        migrations.AlterField(
            model_name='busrequest',
            name='drop_location_map_link',
            field=models.URLField(help_text='Google Maps or other map link for the drop location', max_length=1000),
        ),
        migrations.AlterField(
            model_name='busrequest',
            name='pickup_location_map_link',
            field=models.URLField(help_text='Google Maps or other map link for the pickup location', max_length=1000),
        ),
    ]
