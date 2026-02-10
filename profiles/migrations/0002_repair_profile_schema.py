from django.db import migrations, models


def add_missing_profile_columns(apps, schema_editor):
    Profile = apps.get_model('profiles', 'Profile')
    table_name = Profile._meta.db_table

    with schema_editor.connection.cursor() as cursor:
        existing_columns = {
            column.name
            for column in schema_editor.connection.introspection.get_table_description(
                cursor,
                table_name,
            )
        }

    for field_name in ['education', 'work_experience']:
        if field_name in existing_columns:
            continue
        field = Profile._meta.get_field(field_name)
        schema_editor.add_field(Profile, field)


class Migration(migrations.Migration):
    dependencies = [
        ('profiles', '0001_initial'),
    ]

    operations = [
        migrations.RunPython(
            add_missing_profile_columns,
            reverse_code=migrations.RunPython.noop,
        ),
    ]
