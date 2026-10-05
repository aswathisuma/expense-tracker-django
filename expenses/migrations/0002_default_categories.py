from django.db import migrations

from expenses.app_data import ensure_default_categories


def add_default_categories(apps, schema_editor):
    ensure_default_categories(apps.get_model('expenses', 'Category'))


class Migration(migrations.Migration):

    dependencies = [
        ('expenses', '0001_initial'),
    ]

    operations = [
        # A new database starts with the same categories the React app expects.
        migrations.RunPython(add_default_categories, migrations.RunPython.noop),
    ]
