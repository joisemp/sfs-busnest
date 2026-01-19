# Custom migration to populate default values and make fields required

from django.db import migrations


def populate_location_map_links(apps, schema_editor):
    """
    Populate existing BusRequest records with default map links.
    Uses a placeholder URL for existing records that don't have map links.
    """
    BusRequest = apps.get_model('services', 'BusRequest')
    default_url = 'https://maps.google.com'
    
    # Update all records that have null values
    BusRequest.objects.filter(pickup_location_map_link__isnull=True).update(
        pickup_location_map_link=default_url
    )
    BusRequest.objects.filter(drop_location_map_link__isnull=True).update(
        drop_location_map_link=default_url
    )


def reverse_populate(apps, schema_editor):
    """
    Reverse operation - set the fields back to null if migration is reversed.
    """
    BusRequest = apps.get_model('services', 'BusRequest')
    default_url = 'https://maps.google.com'
    
    # Set back to null for records that have the default URL
    BusRequest.objects.filter(pickup_location_map_link=default_url).update(
        pickup_location_map_link=None
    )
    BusRequest.objects.filter(drop_location_map_link=default_url).update(
        drop_location_map_link=None
    )


class Migration(migrations.Migration):

    dependencies = [
        ('services', '0056_busrequest_drop_location_map_link_and_more'),
    ]

    operations = [
        migrations.RunPython(populate_location_map_links, reverse_populate),
    ]
