from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ("jobs", "0005_jobembedding"),
    ]

    operations = [
        migrations.CreateModel(
            name="JobDescriptionEmbedding",
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
                        related_name="description_embedding_record",
                        to="jobs.job",
                    ),
                ),
            ],
        ),
        migrations.CreateModel(
            name="JobSkillsEmbedding",
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
                        related_name="skills_embedding_record",
                        to="jobs.job",
                    ),
                ),
            ],
        ),
        migrations.CreateModel(
            name="JobTitleEmbedding",
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
                        related_name="title_embedding_record",
                        to="jobs.job",
                    ),
                ),
            ],
        ),
    ]
