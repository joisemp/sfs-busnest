# Generated manually on 2025-10-31

from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


def delete_assignments_without_drivers(apps, schema_editor):
    """
    Delete all bus reservation assignments that don't have a driver assigned.
    This is necessary before making the driver field required.
    """
    BusReservationAssignment = apps.get_model('services', 'BusReservationAssignment')
    deleted_count = BusReservationAssignment.objects.filter(driver__isnull=True).delete()[0]
    if deleted_count > 0:
        print(f"Deleted {deleted_count} bus assignment(s) without drivers.")


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('services', '0039_add_driver_to_bus_reservation_assignment'),
    ]

    operations = [
        # First, delete any assignments without drivers
        migrations.RunPython(delete_assignments_without_drivers, migrations.RunPython.noop),
        
        # Then make the driver field required
        migrations.AlterField(
            model_name='busreservationassignment',
            name='driver',
            field=models.ForeignKey(
                help_text='Driver assigned to this bus',
                limit_choices_to={'profile__is_driver': True},
                on_delete=django.db.models.deletion.PROTECT,
                related_name='driver_assignments',
                to=settings.AUTH_USER_MODEL
            ),
        ),
    ]
