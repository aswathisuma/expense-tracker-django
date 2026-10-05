from django.db import transaction
from rest_framework import status, viewsets
from rest_framework.decorators import api_view
from rest_framework.response import Response

from .app_data import clear_all_data, load_sample_data
from .models import Budget, Category, Transaction
from .serializers import BudgetUpdateSerializer, CategorySerializer, TransactionSerializer


class TransactionViewSet(viewsets.ModelViewSet):
    """
    GET    /api/transactions/        list
    POST   /api/transactions/        create
    GET    /api/transactions/<id>/   detail
    PUT    /api/transactions/<id>/   update (PATCH for a partial update)
    DELETE /api/transactions/<id>/   delete
    """

    # select_related fetches each transaction's category in the same SQL query
    queryset = Transaction.objects.select_related('category')
    serializer_class = TransactionSerializer


class CategoryViewSet(viewsets.ModelViewSet):
    """Same URLs as transactions, under /api/categories/."""

    queryset = Category.objects.all()
    serializer_class = CategorySerializer

    @transaction.atomic
    def destroy(self, request, *args, **kwargs):
        """A category that is still used can only be deleted if its transactions
        are moved to another one: DELETE /api/categories/<id>/?replacement=Other
        """
        category = self.get_object()

        if category.transactions.exists():
            replacement_name = request.query_params.get('replacement')
            if not replacement_name:
                return Response(
                    {'detail': 'This category still has transactions. Choose a replacement category.'},
                    status=status.HTTP_409_CONFLICT,
                )

            replacement = Category.objects.exclude(pk=category.pk).filter(name=replacement_name).first()
            if replacement is None:
                return Response(
                    {'detail': f'Replacement category "{replacement_name}" was not found.'},
                    status=status.HTTP_400_BAD_REQUEST,
                )

            used_types = set(category.transactions.values_list('type', flat=True))
            if not replacement.allows(used_types):
                return Response(
                    {'detail': f'"{replacement.name}" cannot hold this category\'s transactions.'},
                    status=status.HTTP_400_BAD_REQUEST,
                )

            category.transactions.update(category=replacement)

        category.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


def get_budgets():
    """Budgets in the shape the React app uses. Categories without a budget are left out."""
    return {
        'monthlyLimit': Budget.load().monthly_limit,
        'categoryLimits': dict(
            Category.objects.filter(budget_limit__gt=0).values_list('id', 'budget_limit')
        ),
    }


def get_app_data():
    """Everything the React app needs, in one response."""
    return {
        'transactions': TransactionSerializer(Transaction.objects.select_related('category'), many=True).data,
        'categories': CategorySerializer(Category.objects.all(), many=True).data,
        'budgets': get_budgets(),
    }


@api_view(['GET', 'PATCH'])
def budgets(request):
    """
    GET   /api/budgets/   { "monthlyLimit": 40000, "categoryLimits": { "cat-food": 6000 } }
    PATCH /api/budgets/   send only what changed; a limit of 0 removes that budget
    """
    if request.method == 'PATCH':
        serializer = BudgetUpdateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        with transaction.atomic():
            if 'monthlyLimit' in serializer.validated_data:
                budget = Budget.load()
                budget.monthly_limit = serializer.validated_data['monthlyLimit']
                budget.save()

            for category_id, limit in serializer.validated_data.get('categoryLimits', {}).items():
                Category.objects.filter(pk=category_id).update(budget_limit=limit)

    return Response(get_budgets())


@api_view(['GET', 'DELETE'])
def app_data(request):
    """
    GET    /api/data/   all transactions, categories and budgets
    DELETE /api/data/   clear everything and restore the default categories
    """
    if request.method == 'DELETE':
        clear_all_data()
    return Response(get_app_data())


@api_view(['POST'])
def sample_data(request):
    """POST /api/data/sample/   replace transactions and budgets with 6 months of demo data"""
    load_sample_data()
    return Response(get_app_data())
