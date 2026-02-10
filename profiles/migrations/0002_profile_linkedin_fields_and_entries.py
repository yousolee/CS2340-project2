import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("profiles", "0001_initial"),
    ]

    operations = [
        migrations.CreateModel(
            name="Education",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                ("school", models.CharField(max_length=120)),
                ("degree", models.CharField(blank=True, max_length=120)),
                ("field_of_study", models.CharField(blank=True, max_length=120)),
                (
                    "enrollment_type",
                    models.CharField(
                        blank=True,
                        choices=[
                            ("FULL_TIME", "Full-time"),
                            ("PART_TIME", "Part-time"),
                            ("ONLINE", "Online"),
                            ("BOOTCAMP", "Bootcamp"),
                            ("OTHER", "Other"),
                        ],
                        max_length=20,
                    ),
                ),
                ("start_date", models.DateField(blank=True, null=True)),
                ("end_date", models.DateField(blank=True, null=True)),
                ("is_current", models.BooleanField(default=False)),
                ("grade", models.CharField(blank=True, max_length=40)),
                ("activities", models.TextField(blank=True, max_length=600)),
                ("description", models.TextField(blank=True, max_length=1000)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                (
                    "profile",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="educations",
                        to="profiles.profile",
                    ),
                ),
            ],
            options={
                "ordering": ["-is_current", "-end_date", "-start_date", "-id"],
            },
        ),
        migrations.CreateModel(
            name="Experience",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                ("company", models.CharField(max_length=120)),
                ("title", models.CharField(max_length=120)),
                (
                    "employment_type",
                    models.CharField(
                        blank=True,
                        choices=[
                            ("FULL_TIME", "Full-time"),
                            ("PART_TIME", "Part-time"),
                            ("CONTRACT", "Contract"),
                            ("INTERNSHIP", "Internship"),
                            ("FREELANCE", "Freelance"),
                            ("OTHER", "Other"),
                        ],
                        max_length=20,
                    ),
                ),
                ("location", models.CharField(blank=True, max_length=120)),
                (
                    "location_type",
                    models.CharField(
                        blank=True,
                        choices=[
                            ("ONSITE", "On-site"),
                            ("HYBRID", "Hybrid"),
                            ("REMOTE", "Remote"),
                        ],
                        max_length=10,
                    ),
                ),
                ("start_date", models.DateField()),
                ("end_date", models.DateField(blank=True, null=True)),
                ("is_current", models.BooleanField(default=False)),
                ("description", models.TextField(blank=True, max_length=1000)),
                ("activities", models.TextField(blank=True, max_length=600)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                (
                    "profile",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="experiences",
                        to="profiles.profile",
                    ),
                ),
            ],
            options={
                "ordering": ["-is_current", "-end_date", "-start_date", "-id"],
            },
        ),
        migrations.RemoveField(
            model_name="profile",
            name="education",
        ),
        migrations.RemoveField(
            model_name="profile",
            name="work_experience",
        ),
        migrations.AddField(
            model_name="profile",
            name="location",
            field=models.CharField(blank=True, max_length=120),
        ),
        migrations.AddField(
            model_name="profile",
            name="summary",
            field=models.TextField(blank=True, max_length=1000),
        ),
        migrations.AlterField(
            model_name="profile",
            name="headline",
            field=models.CharField(blank=True, max_length=160),
        ),
        migrations.AlterField(
            model_name="profile",
            name="links",
            field=models.TextField(
                blank=True,
                help_text="One link per line (LinkedIn, GitHub, portfolio, etc.)",
                max_length=1000,
            ),
        ),
        migrations.AlterField(
            model_name="profile",
            name="skills",
            field=models.TextField(
                blank=True,
                help_text="Comma-separated or bullet-style skills",
                max_length=600,
            ),
        ),
    ]
