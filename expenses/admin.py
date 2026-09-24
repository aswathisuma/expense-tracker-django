from django.contrib import admin

from .models import Expense


@admin.register(Expense)
class ExpenseAdmin(admin.ModelAdmin):
    list_display = ('title', 'amount', 'category', 'date', 'created_at')
    list_filter = ('category', 'date')
    search_fields = ('title', 'description')
    ordering = ('-date',)
    date_hierarchy = 'date'
    readonly_fields = ('created_at', 'updated_at')
