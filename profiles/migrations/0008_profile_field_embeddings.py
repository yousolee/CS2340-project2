from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ("profiles", "0007_profileembedding"),
    ]

    operations = [
        migrations.CreateModel(
            name="ProfileExperienceEmbedding",
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
                    "profile",
                    models.OneToOneField(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="experience_embedding_record",
                        to="profiles.profile",
                    ),
                ),
            ],
        ),
        migrations.CreateModel(
            name="ProfileSummarySkillsEmbedding",
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
                    "profile",
                    models.OneToOneField(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="summary_skills_embedding_record",
                        to="profiles.profile",
                    ),
                ),
            ],
        ),
        migrations.CreateModel(
            name="ProfileTitleEmbedding",
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
                    "profile",
                    models.OneToOneField(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="title_embedding_record",
                        to="profiles.profile",
                    ),
                ),
            ],
        ),
    ]
