# Add location_id to ImportedAppointment so imports and past-appointments are scoped by location from URL

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("ghl_accounts", "0004_add_notes_to_imported_appointment"),
    ]

    operations = [
        migrations.AddField(
            model_name="importedappointment",
            name="location_id",
            field=models.CharField(blank=True, db_index=True, default="", max_length=255),
        ),
    ]
