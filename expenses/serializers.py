"""Serializers turn model objects into JSON for the React app, and validate the JSON it sends back.

Field names are camelCase (paymentMethod, createdAt) because that is what the React app uses.
"""
from datetime import timezone as datetime_timezone
from decimal import Decimal

from django.core.validators import RegexValidator
from rest_framework import serializers

from .models import Category, Transaction

# Ids end up in URLs (/api/transactions/<id>/), so keep them to URL-safe characters.
validate_id_characters = RegexValidator(
    r'^[A-Za-z0-9_-]+$',
    message='An id can only contain letters, numbers, hyphens and underscores.',
)


class ClientIdMixin:
    """The React app may send its own `id` when creating a row. It can never be changed later."""

    def validate_id(self, value):
        if self.instance is None and self.Meta.model.objects.filter(pk=value).exists():
            raise serializers.ValidationError('This id is already in use.')
        return value

    def update(self, instance, validated_data):
        validated_data.pop('id', None)
        return super().update(instance, validated_data)


class CategorySerializer(ClientIdMixin, serializers.ModelSerializer):
    id = serializers.CharField(max_length=36, required=False, validators=[validate_id_characters])

    class Meta:
        model = Category
        fields = ['id', 'name', 'type']

    def validate_name(self, value):
        duplicates = Category.objects.filter(name__iexact=value)
        if self.instance is not None:
            duplicates = duplicates.exclude(pk=self.instance.pk)
        if duplicates.exists():
            raise serializers.ValidationError('A category with this name already exists.')
        return value

    def validate(self, attrs):
        # An "expense" category that already has expenses cannot become "income" only.
        if self.instance is not None and 'type' in attrs:
            used_types = sorted(set(self.instance.transactions.values_list('type', flat=True)))
            if not Category(type=attrs['type']).allows(used_types):
                raise serializers.ValidationError({
                    'type': f'This category already has {" and ".join(used_types)} transactions, '
                            'so it must allow them.',
                })
        return attrs


class TransactionSerializer(ClientIdMixin, serializers.ModelSerializer):
    id = serializers.CharField(max_length=36, required=False, validators=[validate_id_characters])
    # coerce_to_string=False sends the amount as a JSON number (2400.5), not a string ("2400.50")
    amount = serializers.DecimalField(
        max_digits=12,
        decimal_places=2,
        min_value=Decimal('0.01'),
        coerce_to_string=False,
        error_messages={'min_value': 'Amount must be greater than 0.'},
    )
    # The database stores a foreign key; the API shows and accepts the category's name.
    category = serializers.SlugRelatedField(slug_field='name', queryset=Category.objects.all())
    paymentMethod = serializers.ChoiceField(
        source='payment_method',
        choices=Transaction.PaymentMethod.choices,
    )
    # Always sent in UTC ("2026-09-24T08:00:00Z") so the timestamps sort correctly as text
    createdAt = serializers.DateTimeField(
        source='created_at',
        read_only=True,
        default_timezone=datetime_timezone.utc,
    )

    class Meta:
        model = Transaction
        fields = ['id', 'type', 'amount', 'category', 'date', 'paymentMethod', 'description', 'createdAt']

    def validate(self, attrs):
        # On a partial update (PATCH) a field may be missing, so fall back to the saved value.
        category = attrs.get('category', getattr(self.instance, 'category', None))
        transaction_type = attrs.get('type', getattr(self.instance, 'type', None))
        if category is not None and transaction_type and not category.allows([transaction_type]):
            raise serializers.ValidationError({
                'category': f'"{category.name}" cannot be used for {transaction_type} transactions.',
            })
        return attrs


class BudgetUpdateSerializer(serializers.Serializer):
    """Input for PATCH /api/budgets/. Both fields are optional; a limit of 0 removes that budget."""

    monthlyLimit = serializers.DecimalField(
        max_digits=12, decimal_places=2, min_value=Decimal('0'), required=False,
    )
    # { "<category id>": amount }
    categoryLimits = serializers.DictField(
        child=serializers.DecimalField(max_digits=12, decimal_places=2, min_value=Decimal('0')),
        required=False,
    )

    def validate_categoryLimits(self, value):
        known_ids = set(Category.objects.filter(pk__in=value.keys()).values_list('pk', flat=True))
        unknown_ids = sorted(set(value) - known_ids)
        if unknown_ids:
            raise serializers.ValidationError(f'Unknown category id: {", ".join(unknown_ids)}')
        return value
