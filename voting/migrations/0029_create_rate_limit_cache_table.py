from django.db import migrations
from django.core.management import call_command


def create_cache_table(apps, schema_editor):
    try:
        call_command('createcachetable')
    except Exception as e:
        print(f"Notice: createcachetable call during migration: {e}")


class Migration(migrations.Migration):

    dependencies = [
        ("voting", "0028_votingrecord_created_at_and_more"),
    ]

    operations = [
        migrations.RunPython(create_cache_table, reverse_code=migrations.RunPython.noop),
    ]
