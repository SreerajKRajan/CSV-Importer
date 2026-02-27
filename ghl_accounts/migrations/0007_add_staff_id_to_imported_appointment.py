from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("ghl_accounts", "0006_add_staff_name_to_imported_appointment"),
    ]

    operations = [
        migrations.AddField(
            model_name="importedappointment",
            name="staff_id",
            field=models.CharField(blank=True, default="", max_length=255),
        ),
    ]
