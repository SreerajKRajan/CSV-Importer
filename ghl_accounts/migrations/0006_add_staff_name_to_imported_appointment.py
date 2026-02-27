from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("ghl_accounts", "0005_add_location_id_to_imported_appointment"),
    ]

    operations = [
        migrations.AddField(
            model_name="importedappointment",
            name="staff_name",
            field=models.CharField(max_length=255, blank=True, default=""),
        ),
    ]

