from django.db import migrations


def add_missing_profile_columns(apps, schema_editor):
    Profile = apps.get_model("profiles", "Profile")
    table_name = Profile._meta.db_table

    with schema_editor.connection.cursor() as cursor:
        existing_columns = {
            column.name
            for column in schema_editor.connection.introspection.get_table_description(
                cursor,
                table_name,
            )
        }

    for field_name in ["summary", "location"]:
        if field_name in existing_columns:
            continue
        schema_editor.add_field(Profile, Profile._meta.get_field(field_name))


class Migration(migrations.Migration):
    dependencies = [
        ("profiles", "0003_merge_20260210_2036"),
    ]

    operations = [
        migrations.RunPython(
            add_missing_profile_columns,
            reverse_code=migrations.RunPython.noop,
        ),
    ]
