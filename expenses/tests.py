from datetime import date, timedelta
from decimal import Decimal

from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from .forms import ExpenseForm
from .models import Expense
from .templatetags.expense_extras import format_inr


def make_expense(**kwargs):
    data = {
        'title': 'Lunch',
        'amount': Decimal('250'),
        'category': Expense.Category.FOOD,
        'date': date(2026, 9, 24),
        'description': '',
    }
    data.update(kwargs)
    return Expense.objects.create(**data)


class FormatInrTests(TestCase):
    def test_formats_with_indian_grouping(self):
        self.assertEqual(format_inr(0), '₹0.00')
        self.assertEqual(format_inr(100), '₹100.00')
        self.assertEqual(format_inr(Decimal('1250')), '₹1,250.00')
        self.assertEqual(format_inr(Decimal('25450.5')), '₹25,450.50')
        self.assertEqual(format_inr(Decimal('1234567.89')), '₹12,34,567.89')
        self.assertEqual(format_inr(None), '₹0.00')


class ExpenseFormTests(TestCase):
    def valid_data(self, **overrides):
        data = {
            'title': 'Lunch',
            'amount': '250',
            'category': 'Food',
            'date': '2026-09-24',
            'description': '',
        }
        data.update(overrides)
        return data

    def test_valid_form(self):
        self.assertTrue(ExpenseForm(data=self.valid_data()).is_valid())

    def test_amount_must_be_greater_than_zero(self):
        for amount in ('0', '-5'):
            form = ExpenseForm(data=self.valid_data(amount=amount))
            self.assertFalse(form.is_valid())
            self.assertIn('Amount must be greater than 0.', form.errors['amount'])

    def test_required_fields(self):
        form = ExpenseForm(data={'description': 'only a description'})
        self.assertFalse(form.is_valid())
        for field in ('title', 'amount', 'category', 'date'):
            self.assertIn(field, form.errors)
        self.assertNotIn('description', form.errors)

    def test_invalid_category(self):
        form = ExpenseForm(data=self.valid_data(category='Rent'))
        self.assertFalse(form.is_valid())
        self.assertIn('category', form.errors)


class ExpenseCrudTests(TestCase):
    def test_create_expense(self):
        response = self.client.post(reverse('expense_create'), {
            'title': 'Petrol',
            'amount': '1500',
            'category': 'Travel',
            'date': '2026-09-23',
            'description': 'Full tank',
        }, follow=True)
        self.assertRedirects(response, reverse('expense_list'))
        self.assertEqual(Expense.objects.count(), 1)
        self.assertContains(response, 'was added successfully')

    def test_create_invalid_shows_errors(self):
        response = self.client.post(reverse('expense_create'), {'title': '', 'amount': '0'})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(Expense.objects.count(), 0)
        self.assertContains(response, 'Amount must be greater than 0.')
        self.assertContains(response, 'Please correct the errors below.')

    def test_detail_page(self):
        expense = make_expense(description='With friends')
        response = self.client.get(reverse('expense_detail', args=[expense.pk]))
        self.assertContains(response, 'With friends')
        self.assertContains(response, '₹250.00')

    def test_detail_404(self):
        response = self.client.get(reverse('expense_detail', args=[999]))
        self.assertEqual(response.status_code, 404)

    def test_update_expense(self):
        expense = make_expense()
        edit_url = reverse('expense_update', args=[expense.pk])

        response = self.client.get(edit_url)
        self.assertContains(response, 'value="Lunch"')

        response = self.client.post(edit_url, {
            'title': 'Team lunch',
            'amount': '600',
            'category': 'Food',
            'date': '2026-09-24',
            'description': '',
        })
        self.assertRedirects(response, reverse('expense_list'))
        expense.refresh_from_db()
        self.assertEqual(expense.title, 'Team lunch')
        self.assertEqual(expense.amount, Decimal('600'))

    def test_delete_get_only_shows_confirmation(self):
        expense = make_expense()
        response = self.client.get(reverse('expense_delete', args=[expense.pk]))
        self.assertContains(response, 'Confirm Delete')
        self.assertTrue(Expense.objects.filter(pk=expense.pk).exists())

    def test_delete_post_removes_expense(self):
        expense = make_expense()
        response = self.client.post(reverse('expense_delete', args=[expense.pk]), follow=True)
        self.assertRedirects(response, reverse('expense_list'))
        self.assertFalse(Expense.objects.filter(pk=expense.pk).exists())
        self.assertContains(response, 'was deleted successfully')


class ExpenseListFilterTests(TestCase):
    def setUp(self):
        make_expense(title='Lunch', amount=Decimal('250'), category='Food', date=date(2026, 9, 24))
        make_expense(title='Dinner', amount=Decimal('800'), category='Food', date=date(2026, 8, 10),
                     description='lunch leftovers')
        make_expense(title='Petrol', amount=Decimal('1500'), category='Travel', date=date(2026, 9, 23))

    def get_titles(self, params):
        response = self.client.get(reverse('expense_list'), params)
        return response, {expense.title for expense in response.context['page_obj']}

    def test_search_title_and_description(self):
        _, titles = self.get_titles({'search': 'LUNCH'})
        self.assertEqual(titles, {'Lunch', 'Dinner'})

    def test_category_filter(self):
        _, titles = self.get_titles({'category': 'Travel'})
        self.assertEqual(titles, {'Petrol'})

    def test_month_filter(self):
        _, titles = self.get_titles({'month': '2026-09'})
        self.assertEqual(titles, {'Lunch', 'Petrol'})

    def test_combined_filters_and_filtered_total(self):
        response, titles = self.get_titles({'search': 'lunch', 'category': 'Food', 'month': '2026-09'})
        self.assertEqual(titles, {'Lunch'})
        self.assertEqual(response.context['filtered_total'], Decimal('250'))

    def test_invalid_filters_are_ignored(self):
        response, titles = self.get_titles({'category': 'Nope', 'month': 'bad'})
        self.assertEqual(len(titles), 3)
        self.assertFalse(response.context['is_filtered'])


class PaginationTests(TestCase):
    def setUp(self):
        for day in range(1, 26):
            make_expense(title=f'Item {day}', date=date(2026, 9, day))

    def test_ten_per_page(self):
        response = self.client.get(reverse('expense_list'))
        self.assertEqual(len(response.context['page_obj']), 10)
        self.assertEqual(response.context['page_obj'].paginator.num_pages, 3)

    def test_pagination_keeps_filters(self):
        response = self.client.get(reverse('expense_list'), {'category': 'Food', 'page': 2})
        self.assertEqual(response.context['page_obj'].number, 2)
        self.assertContains(response, 'href="?category=Food&page=3"')


class DashboardTests(TestCase):
    def test_dashboard_calculations(self):
        today = timezone.localdate()
        last_month = today.replace(day=1) - timedelta(days=1)
        make_expense(title='This month A', amount=Decimal('100'), category='Food', date=today)
        make_expense(title='This month B', amount=Decimal('50.50'), category='Bills', date=today)
        make_expense(title='Last month', amount=Decimal('1000'), category='Food', date=last_month)

        response = self.client.get(reverse('dashboard'))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context['total_amount'], Decimal('1150.50'))
        self.assertEqual(response.context['expense_count'], 3)
        self.assertEqual(response.context['month_total'], Decimal('150.50'))

        summary = {item['value']: item['total'] for item in response.context['category_summary']}
        self.assertEqual(summary, {'Food': Decimal('1100'), 'Bills': Decimal('50.50')})
        self.assertContains(response, '₹1,150.50')

    def test_empty_dashboard(self):
        response = self.client.get(reverse('dashboard'))
        self.assertEqual(response.context['total_amount'], Decimal('0'))
        self.assertContains(response, 'No expenses yet.')
