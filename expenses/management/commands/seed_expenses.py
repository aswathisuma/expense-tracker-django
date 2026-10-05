from django.core.management.base import BaseCommand

from expenses.app_data import load_sample_data


class Command(BaseCommand):
    help = 'Replace ALL transactions and budgets with 6 months of sample data.'

    def handle(self, *args, **options):
        count = load_sample_data()
        self.stdout.write(self.style.SUCCESS(f'Added {count} sample transaction(s).'))
