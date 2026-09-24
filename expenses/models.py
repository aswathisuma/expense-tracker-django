from decimal import Decimal

from django.core.validators import MinValueValidator
from django.db import models
from django.urls import reverse


class Expense(models.Model):
    """A single expense entry."""

    class Category(models.TextChoices):
        # The first value is stored in the database, the second is shown to users.
        FOOD = 'Food', 'Food'
        TRAVEL = 'Travel', 'Travel'
        SHOPPING = 'Shopping', 'Shopping'
        BILLS = 'Bills', 'Bills'
        ENTERTAINMENT = 'Entertainment', 'Entertainment'
        HEALTH = 'Health', 'Health'
        OTHER = 'Other', 'Other'

    title = models.CharField(max_length=200)
    amount = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        validators=[MinValueValidator(Decimal('0.01'), message='Amount must be greater than 0.')],
    )
    category = models.CharField(max_length=20, choices=Category.choices)
    date = models.DateField()
    description = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        # Newest expenses first
        ordering = ['-date', '-created_at']

    def __str__(self):
        return f'{self.title} - {self.amount}'

    def get_absolute_url(self):
        return reverse('expense_detail', args=[self.pk])
