"""Default categories, the sample data generator and the "clear everything" helper."""
from datetime import date, datetime, timezone as datetime_timezone
from decimal import ROUND_HALF_UP, Decimal

from django.db import transaction
from django.db.models import Max
from django.utils import timezone

from .models import Budget, Category, Transaction, generate_id

# (id, name, type)
DEFAULT_CATEGORIES = [
    ('cat-food', 'Food', 'expense'),
    ('cat-travel', 'Travel', 'expense'),
    ('cat-shopping', 'Shopping', 'expense'),
    ('cat-bills', 'Bills', 'expense'),
    ('cat-entertainment', 'Entertainment', 'expense'),
    ('cat-health', 'Health', 'expense'),
    ('cat-education', 'Education', 'expense'),
    ('cat-salary', 'Salary', 'income'),
    ('cat-freelance', 'Freelance', 'income'),
    ('cat-other', 'Other', 'both'),
]

# (day, type, category, amount, payment method, description)
MONTHLY_TEMPLATE = [
    (1, 'income', 'Salary', 55000, 'Bank Transfer', 'Monthly salary'),
    (2, 'expense', 'Bills', 15000, 'Bank Transfer', 'House rent'),
    (3, 'expense', 'Food', 2400, 'UPI', 'Groceries'),
    (5, 'expense', 'Bills', 1850, 'UPI', 'Electricity bill'),
    (7, 'expense', 'Travel', 1200, 'UPI', 'Metro card recharge'),
    (9, 'expense', 'Entertainment', 649, 'Credit Card', 'Streaming subscription'),
    (11, 'expense', 'Food', 1350, 'Credit Card', 'Dinner with friends'),
    (14, 'expense', 'Shopping', 2999, 'Credit Card', 'Clothes'),
    (16, 'expense', 'Health', 800, 'Cash', 'Pharmacy'),
    (18, 'expense', 'Food', 2100, 'UPI', 'Groceries'),
    (20, 'income', 'Freelance', 12000, 'Bank Transfer', 'Website project'),
    (22, 'expense', 'Travel', 2600, 'Debit Card', 'Weekend trip bus tickets'),
    (24, 'expense', 'Education', 1499, 'Debit Card', 'Online course'),
    (26, 'expense', 'Shopping', 1850, 'UPI', 'Home essentials'),
    (27, 'expense', 'Food', 950, 'Cash', 'Snacks and tea'),
]

# Day-to-day spending changes a little every month; rent and salary do not.
VARIABLE_CATEGORIES = {'Food', 'Travel', 'Shopping', 'Health'}
MONTH_FACTORS = [Decimal('0.9'), Decimal('1.05'), Decimal('0.95'), Decimal('1.12'), Decimal('1'), Decimal('1.08')]

SAMPLE_MONTHLY_LIMIT = Decimal('40000')
SAMPLE_CATEGORY_LIMITS = {
    'Food': Decimal('6000'),
    'Travel': Decimal('4500'),
    'Shopping': Decimal('7000'),
    'Entertainment': Decimal('1500'),
}


def ensure_default_categories(category_model=Category):
    """Add any default categories that are missing (matched by name).

    `category_model` lets a migration pass in its historical version of the model.
    """
    existing_names = {name.lower() for name in category_model.objects.values_list('name', flat=True)}
    existing_ids = set(category_model.objects.values_list('id', flat=True))
    position = category_model.objects.aggregate(last=Max('position'))['last'] or 0

    for category_id, name, category_type in DEFAULT_CATEGORIES:
        if name.lower() in existing_names:
            continue
        position += 1
        category_model.objects.create(
            # The default id may be taken by a category that was renamed
            id=generate_id() if category_id in existing_ids else category_id,
            name=name,
            type=category_type,
            position=position,
        )


def get_recent_months(count, today):
    """The last `count` months as (year, month) pairs, oldest first, ending with today's month."""
    months = []
    year, month = today.year, today.month
    for _ in range(count):
        months.append((year, month))
        year, month = (year - 1, 12) if month == 1 else (year, month - 1)
    return months[::-1]


@transaction.atomic
def clear_all_data():
    """Delete every transaction and budget, and reset the categories to the defaults."""
    Transaction.objects.all().delete()
    Category.objects.all().delete()
    Budget.objects.all().delete()
    ensure_default_categories()


@transaction.atomic
def load_sample_data():
    """Replace all transactions and budgets with 6 months of demo data."""
    ensure_default_categories()
    categories = {category.name.lower(): category for category in Category.objects.all()}
    today = timezone.localdate()

    Transaction.objects.all().delete()
    transactions = []
    for month_index, (year, month) in enumerate(get_recent_months(len(MONTH_FACTORS), today)):
        for row_index, row in enumerate(MONTHLY_TEMPLATE):
            day, transaction_type, category_name, amount, payment_method, description = row
            transaction_date = date(year, month, day)
            is_freelance_month = month_index % 2 == 1

            if transaction_date > today or (category_name == 'Freelance' and not is_freelance_month):
                continue

            factor = MONTH_FACTORS[month_index] if category_name in VARIABLE_CATEGORIES else Decimal('1')
            transactions.append(Transaction(
                type=transaction_type,
                amount=(amount * factor).quantize(Decimal('1'), rounding=ROUND_HALF_UP),
                category=categories[category_name.lower()],
                date=transaction_date,
                payment_method=payment_method,
                description=description,
                created_at=datetime(year, month, day, 8 + row_index % 12, tzinfo=datetime_timezone.utc),
            ))
    Transaction.objects.bulk_create(transactions)

    Category.objects.update(budget_limit=0)
    for category_name, limit in SAMPLE_CATEGORY_LIMITS.items():
        Category.objects.filter(pk=categories[category_name.lower()].pk).update(budget_limit=limit)

    budget = Budget.load()
    budget.monthly_limit = SAMPLE_MONTHLY_LIMIT
    budget.save()

    return len(transactions)
