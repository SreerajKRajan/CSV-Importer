# Add notes column to ImportedAppointment (CSV notes stored in DB and sent to GHL contact)

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("ghl_accounts", "0003_add_ghl_service_catalog"),
    ]

    operations = [
        migrations.AddField(
            model_name="importedappointment",
            name="notes",
            field=models.TextField(blank=True, default=""),
        ),
    ]
