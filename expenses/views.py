from datetime import datetime
from decimal import Decimal
from urllib.parse import urlencode

from django.contrib import messages
from django.core.paginator import Paginator
from django.db.models import Count, Q, Sum
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.views.decorators.http import require_http_methods

from .forms import ExpenseForm
from .models import Expense

EXPENSES_PER_PAGE = 10


def get_total(queryset):
    """Return the sum of `amount` for a queryset (0 when it is empty)."""
    return queryset.aggregate(total=Sum('amount'))['total'] or Decimal('0')


def dashboard(request):
    today = timezone.localdate()
    expenses = Expense.objects.all()
    this_month = expenses.filter(date__year=today.year, date__month=today.month)
    total_amount = get_total(expenses)

    # One row per category: {'category': 'Food', 'total': Decimal(...), 'count': 3}
    category_rows = (
        expenses.values('category')
        .annotate(total=Sum('amount'), count=Count('id'))
        .order_by('-total')
    )
    category_labels = dict(Expense.Category.choices)
    category_summary = [
        {
            'value': row['category'],
            'name': category_labels.get(row['category'], row['category']),
            'total': row['total'],
            'count': row['count'],
            'percent': round(row['total'] / total_amount * 100) if total_amount else 0,
        }
        for row in category_rows
    ]

    context = {
        'today': today,
        'total_amount': total_amount,
        'expense_count': expenses.count(),
        'month_total': get_total(this_month),
        'current_month': today.strftime('%Y-%m'),
        'recent_expenses': expenses[:5],
        'category_summary': category_summary,
    }
    return render(request, 'expenses/dashboard.html', context)


def expense_list(request):
    expenses = Expense.objects.all()

    # Read the filters from the URL, e.g. /expenses/?search=lunch&category=Food&month=2026-09
    search = request.GET.get('search', '').strip()
    category = request.GET.get('category', '')
    month = request.GET.get('month', '')

    if search:
        expenses = expenses.filter(Q(title__icontains=search) | Q(description__icontains=search))

    if category in Expense.Category.values:
        expenses = expenses.filter(category=category)
    else:
        category = ''  # ignore unknown categories

    selected_month = None
    if month:
        try:
            selected_month = datetime.strptime(month, '%Y-%m').date()
        except ValueError:
            month = ''  # ignore badly formatted months
        else:
            expenses = expenses.filter(
                date__year=selected_month.year,
                date__month=selected_month.month,
            )

    filtered_total = get_total(expenses)

    paginator = Paginator(expenses, EXPENSES_PER_PAGE)
    page_obj = paginator.get_page(request.GET.get('page'))
    page_range = paginator.get_elided_page_range(page_obj.number, on_each_side=2, on_ends=1)

    # Active filters, re-used in pagination links so they survive page changes
    active_filters = {key: value for key, value in
                      {'search': search, 'category': category, 'month': month}.items() if value}

    # Months that have at least one expense, newest first, for the month dropdown
    month_choices = [
        (month_date.strftime('%Y-%m'), month_date.strftime('%B %Y'))
        for month_date in Expense.objects.dates('date', 'month', order='DESC')
    ]
    # Keep the selected month in the dropdown even if it has no expenses
    if selected_month and month not in dict(month_choices):
        month_choices.insert(0, (month, selected_month.strftime('%B %Y')))

    context = {
        'page_obj': page_obj,
        'page_range': page_range,
        'ellipsis': Paginator.ELLIPSIS,
        'filtered_total': filtered_total,
        'result_count': paginator.count,
        'search': search,
        'selected_category': category,
        'selected_month': month,
        'categories': Expense.Category.choices,
        'month_choices': month_choices,
        'querystring': urlencode(active_filters),
        'is_filtered': bool(active_filters),
    }
    return render(request, 'expenses/expense_list.html', context)


def expense_detail(request, pk):
    expense = get_object_or_404(Expense, pk=pk)
    return render(request, 'expenses/expense_detail.html', {'expense': expense})


def expense_create(request):
    if request.method == 'POST':
        form = ExpenseForm(request.POST)
        if form.is_valid():
            expense = form.save()
            messages.success(request, f'Expense "{expense.title}" was added successfully.')
            return redirect('expense_list')
        messages.error(request, 'Please correct the errors below.')
    else:
        # Pre-fill today's date to save the user a click
        form = ExpenseForm(initial={'date': timezone.localdate()})

    context = {
        'form': form,
        'page_title': 'Add Expense',
        'submit_label': 'Save Expense',
    }
    return render(request, 'expenses/expense_form.html', context)


def expense_update(request, pk):
    expense = get_object_or_404(Expense, pk=pk)

    if request.method == 'POST':
        # `instance=expense` tells the form to update this row instead of creating a new one
        form = ExpenseForm(request.POST, instance=expense)
        if form.is_valid():
            form.save()
            messages.success(request, f'Expense "{expense.title}" was updated successfully.')
            return redirect('expense_list')
        messages.error(request, 'Please correct the errors below.')
    else:
        form = ExpenseForm(instance=expense)

    context = {
        'form': form,
        'expense': expense,
        'page_title': 'Edit Expense',
        'submit_label': 'Update Expense',
    }
    return render(request, 'expenses/expense_form.html', context)


@require_http_methods(['GET', 'POST'])
def expense_delete(request, pk):
    expense = get_object_or_404(Expense, pk=pk)

    # GET only shows the confirmation page; the row is deleted on POST
    if request.method == 'POST':
        title = expense.title
        expense.delete()
        messages.success(request, f'Expense "{title}" was deleted successfully.')
        return redirect('expense_list')

    return render(request, 'expenses/expense_confirm_delete.html', {'expense': expense})
