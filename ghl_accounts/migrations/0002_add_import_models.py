# Generated manually for CSV importer

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("ghl_accounts", "0001_initial"),
    ]

    operations = [
        migrations.CreateModel(
            name="ServiceCalendarMapping",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("location_id", models.CharField(db_index=True, max_length=255)),
                ("service_name", models.CharField(max_length=255)),
                ("service_id", models.CharField(max_length=255)),
                ("staff_id", models.CharField(max_length=255)),
                ("calendar_id", models.CharField(max_length=255)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
            ],
            options={
                "ordering": ["location_id", "service_name"],
            },
        ),
        migrations.CreateModel(
            name="ImportedAppointment",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("name", models.CharField(max_length=255)),
                ("email", models.EmailField(max_length=254)),
                ("phone", models.CharField(blank=True, max_length=50)),
                ("service_name", models.CharField(max_length=255)),
                ("start_time", models.DateTimeField()),
                ("end_time", models.DateTimeField()),
                ("is_past", models.BooleanField(default=False)),
                ("ghl_booking_id", models.CharField(blank=True, max_length=255, null=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
            ],
            options={
                "ordering": ["-created_at"],
            },
        ),
        migrations.AddConstraint(
            model_name="servicecalendarmapping",
            constraint=models.UniqueConstraint(
                fields=("location_id", "service_name"),
                name="unique_location_service",
            ),
        ),
    ]
