# Generated for GHL services catalog (resolve service_id from service_name)

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("ghl_accounts", "0002_add_import_models"),
    ]

    operations = [
        migrations.CreateModel(
            name="GHLService",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("location_id", models.CharField(db_index=True, max_length=255)),
                ("service_id", models.CharField(max_length=255)),
                ("name", models.CharField(max_length=255)),
                ("updated_at", models.DateTimeField(auto_now=True)),
            ],
            options={
                "ordering": ["location_id", "name"],
                "verbose_name": "GHL service (catalog)",
                "verbose_name_plural": "GHL services (catalog)",
            },
        ),
        migrations.AddConstraint(
            model_name="ghlservice",
            constraint=models.UniqueConstraint(
                fields=("location_id", "service_id"),
                name="unique_location_ghl_service",
            ),
        ),
    ]
