from decimal import Decimal

import django.core.validators
from django.db import migrations, models


class Migration(migrations.Migration):
    """The original Expense table, from before this project became an API.

    Databases created back then already have this migration applied, so it has
    to stay here for `migrate` to upgrade them. 0004 removes the table again.
    """

    initial = True

    dependencies = [
    ]

    operations = [
        migrations.CreateModel(
            name='Expense',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('title', models.CharField(max_length=200)),
                ('amount', models.DecimalField(decimal_places=2, max_digits=12, validators=[django.core.validators.MinValueValidator(Decimal('0.01'), message='Amount must be greater than 0.')])),
                ('category', models.CharField(choices=[('Food', 'Food'), ('Travel', 'Travel'), ('Shopping', 'Shopping'), ('Bills', 'Bills'), ('Entertainment', 'Entertainment'), ('Health', 'Health'), ('Other', 'Other')], max_length=20)),
                ('date', models.DateField()),
                ('description', models.TextField(blank=True)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
            ],
            options={
                'ordering': ['-date', '-created_at'],
            },
        ),
    ]
