from django.db import migrations

from expenses.app_data import ensure_default_categories


def add_default_categories(apps, schema_editor):
    ensure_default_categories(apps.get_model('expenses', 'Category'))


def copy_old_expenses(apps, schema_editor):
    """Turn rows of the original Expense table into transactions, so no data is lost."""
    Expense = apps.get_model('expenses', 'Expense')
    Category = apps.get_model('expenses', 'Category')
    Transaction = apps.get_model('expenses', 'Transaction')
    categories = {category.name: category for category in Category.objects.all()}

    for expense in Expense.objects.all():
        # The old title and description share the new, shorter description field.
        description = f'{expense.title}: {expense.description}' if expense.description else expense.title
        Transaction.objects.create(
            type='expense',
            amount=expense.amount,
            category=categories.get(expense.category, categories['Other']),
            date=expense.date,
            payment_method='Other',  # the old table did not record one
            description=description[:100],
            created_at=expense.created_at,
        )


class Migration(migrations.Migration):

    dependencies = [
        ('expenses', '0002_api_models'),
    ]

    operations = [
        # A new database starts with the same categories the React app expects.
        migrations.RunPython(add_default_categories, migrations.RunPython.noop),
        migrations.RunPython(copy_old_expenses, migrations.RunPython.noop),
    ]
