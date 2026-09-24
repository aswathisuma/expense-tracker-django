from datetime import date
from decimal import Decimal

from django.core.management.base import BaseCommand

from expenses.models import Expense

# (title, amount, category, date, description)
SAMPLE_EXPENSES = [
    ('Lunch', '250', 'Food', date(2026, 9, 24), 'Lunch with colleagues'),
    ('Petrol', '1500', 'Travel', date(2026, 9, 23), 'Full tank'),
    ('Movie', '500', 'Entertainment', date(2026, 9, 20), 'Weekend movie tickets'),
    ('Groceries', '2000', 'Shopping', date(2026, 9, 18), 'Monthly groceries'),
    ('Electricity', '1200', 'Bills', date(2026, 9, 15), 'Electricity bill for August'),
    ('Pharmacy', '350', 'Health', date(2026, 9, 12), 'Cold medicine'),
    ('Coffee', '180', 'Food', date(2026, 9, 10), ''),
    ('Auto rickshaw', '120', 'Travel', date(2026, 9, 8), 'Office commute'),
    ('Internet', '799', 'Bills', date(2026, 9, 5), 'Broadband monthly plan'),
    ('Dinner', '1250', 'Food', date(2026, 8, 29), 'Family dinner'),
    ('Shoes', '2499', 'Shopping', date(2026, 8, 25), 'Running shoes'),
    ('Train tickets', '1850', 'Travel', date(2026, 8, 20), 'Trip to Kochi'),
    ('Water bill', '400', 'Bills', date(2026, 8, 14), ''),
    ('Gym membership', '1500', 'Health', date(2026, 8, 3), 'Monthly membership'),
    ('Birthday gift', '1000', 'Other', date(2026, 7, 27), 'Gift for a friend'),
    ('Concert', '1800', 'Entertainment', date(2026, 7, 19), 'Live music night'),
]


class Command(BaseCommand):
    help = 'Add sample expenses for testing. Safe to run more than once.'

    def add_arguments(self, parser):
        parser.add_argument(
            '--clear',
            action='store_true',
            help='Delete ALL existing expenses before adding the samples.',
        )

    def handle(self, *args, **options):
        if options['clear']:
            deleted, _ = Expense.objects.all().delete()
            self.stdout.write(self.style.WARNING(f'Deleted {deleted} existing expense(s).'))

        created_count = 0
        for title, amount, category, expense_date, description in SAMPLE_EXPENSES:
            # get_or_create avoids duplicates if the command is run twice
            _, created = Expense.objects.get_or_create(
                title=title,
                date=expense_date,
                defaults={
                    'amount': Decimal(amount),
                    'category': category,
                    'description': description,
                },
            )
            created_count += created

        self.stdout.write(self.style.SUCCESS(f'Added {created_count} sample expense(s).'))
