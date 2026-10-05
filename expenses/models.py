import uuid
from decimal import Decimal

from django.core.validators import MinValueValidator
from django.db import models
from django.db.models.functions import Lower
from django.utils import timezone


def generate_id():
    return str(uuid.uuid4())


class Category(models.Model):
    """A label for transactions, e.g. Food or Salary."""

    class Type(models.TextChoices):
        # Decides which transactions the category can be used for.
        EXPENSE = 'expense', 'Expense'
        INCOME = 'income', 'Income'
        BOTH = 'both', 'Income & Expense'

    # The React app creates ids itself (so it can show a new row instantly),
    # which is why this is a string instead of Django's usual auto number.
    id = models.CharField(primary_key=True, max_length=36, default=generate_id)
    name = models.CharField(max_length=30)
    type = models.CharField(max_length=7, choices=Type.choices)
    # Monthly budget for this category. 0 means "no budget set".
    budget_limit = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=Decimal('0'),
        validators=[MinValueValidator(Decimal('0'))],
    )
    # Keeps categories in the order they were added.
    position = models.PositiveIntegerField(editable=False)

    class Meta:
        ordering = ['position']
        verbose_name_plural = 'categories'
        constraints = [
            # "Food" and "food" count as the same name
            models.UniqueConstraint(Lower('name'), name='unique_category_name'),
        ]

    def __str__(self):
        return self.name

    def save(self, *args, **kwargs):
        if self.position is None:
            last_position = Category.objects.aggregate(last=models.Max('position'))['last'] or 0
            self.position = last_position + 1
        super().save(*args, **kwargs)

    def allows(self, transaction_types):
        """Can this category hold every transaction type in `transaction_types`?"""
        return self.type == self.Type.BOTH or all(
            transaction_type == self.type for transaction_type in transaction_types
        )


class Transaction(models.Model):
    """A single income or expense entry."""

    class Type(models.TextChoices):
        EXPENSE = 'expense', 'Expense'
        INCOME = 'income', 'Income'

    class PaymentMethod(models.TextChoices):
        CASH = 'Cash', 'Cash'
        UPI = 'UPI', 'UPI'
        CREDIT_CARD = 'Credit Card', 'Credit Card'
        DEBIT_CARD = 'Debit Card', 'Debit Card'
        BANK_TRANSFER = 'Bank Transfer', 'Bank Transfer'
        OTHER = 'Other', 'Other'

    id = models.CharField(primary_key=True, max_length=36, default=generate_id)
    type = models.CharField(max_length=7, choices=Type.choices)
    amount = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        validators=[MinValueValidator(Decimal('0.01'), message='Amount must be greater than 0.')],
    )
    # PROTECT: a category that still has transactions cannot be deleted
    category = models.ForeignKey(Category, on_delete=models.PROTECT, related_name='transactions')
    date = models.DateField()
    payment_method = models.CharField(max_length=20, choices=PaymentMethod.choices)
    description = models.CharField(max_length=100, blank=True)
    created_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        # Newest transactions first
        ordering = ['-date', '-created_at']

    def __str__(self):
        return f'{self.get_type_display()}: {self.category} - {self.amount}'


class Budget(models.Model):
    """The overall monthly budget. There is only ever one row (pk=1)."""

    # 0 means "no budget set"
    monthly_limit = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=Decimal('0'),
        validators=[MinValueValidator(Decimal('0'))],
    )

    def __str__(self):
        return f'Monthly budget: {self.monthly_limit}'

    @classmethod
    def load(cls):
        budget, _ = cls.objects.get_or_create(pk=1)
        return budget
