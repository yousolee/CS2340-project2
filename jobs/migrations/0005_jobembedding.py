from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ("jobs", "0004_jobapplication"),
    ]

    operations = [
        migrations.CreateModel(
            name="JobEmbedding",
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
                ("embedding", models.JSONField(blank=True, default=list)),
                ("source_hash", models.CharField(db_index=True, max_length=64)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                (
                    "job",
                    models.OneToOneField(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="embedding_record",
                        to="jobs.job",
                    ),
                ),
            ],
        ),
    ]
