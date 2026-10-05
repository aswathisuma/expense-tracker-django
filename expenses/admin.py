from django.contrib import admin

from .models import Budget, Category, Transaction


@admin.register(Transaction)
class TransactionAdmin(admin.ModelAdmin):
    list_display = ('date', 'type', 'category', 'amount', 'payment_method', 'description')
    list_filter = ('type', 'category', 'payment_method', 'date')
    search_fields = ('description',)
    ordering = ('-date',)
    date_hierarchy = 'date'
    readonly_fields = ('id', 'updated_at')


@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ('name', 'type', 'budget_limit')
    list_filter = ('type',)
    search_fields = ('name',)
    readonly_fields = ('id',)


@admin.register(Budget)
class BudgetAdmin(admin.ModelAdmin):
    list_display = ('monthly_limit',)

    # There is only one budget row, so it can be edited but not added or deleted.
    def has_add_permission(self, request):
        return not Budget.objects.exists()

    def has_delete_permission(self, request, obj=None):
        return False
