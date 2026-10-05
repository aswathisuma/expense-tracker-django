from datetime import date
from decimal import Decimal
from io import StringIO

from django.core.management import call_command
from django.urls import reverse
from django.utils import timezone
from rest_framework import status
from rest_framework.test import APITestCase

from .app_data import DEFAULT_CATEGORIES, get_recent_months
from .models import Budget, Category, Transaction

# The default categories are created by a migration, so they exist in every test.


def make_transaction(**kwargs):
    data = {
        'type': 'expense',
        'amount': Decimal('250'),
        'category': Category.objects.get(name='Food'),
        'date': date(2026, 9, 24),
        'payment_method': 'UPI',
        'description': 'Lunch',
    }
    data.update(kwargs)
    return Transaction.objects.create(**data)


def transaction_payload(**overrides):
    data = {
        'type': 'expense',
        'amount': 250,
        'category': 'Food',
        'date': '2026-09-24',
        'paymentMethod': 'UPI',
        'description': 'Lunch',
    }
    data.update(overrides)
    return data


class TransactionApiTests(APITestCase):
    def test_list_is_newest_first_in_the_react_shape(self):
        make_transaction(date=date(2026, 9, 1), description='Older')
        newer = make_transaction(date=date(2026, 9, 24), amount=Decimal('99.50'), description='Newer')

        response = self.client.get(reverse('transaction-list'))

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        rows = response.json()
        self.assertEqual([row['description'] for row in rows], ['Newer', 'Older'])
        self.assertEqual(
            set(rows[0]),
            {'id', 'type', 'amount', 'category', 'date', 'paymentMethod', 'description', 'createdAt'},
        )
        self.assertEqual(rows[0]['id'], newer.pk)
        self.assertEqual(rows[0]['amount'], 99.5)  # a JSON number, not the string "99.50"
        self.assertEqual(rows[0]['category'], 'Food')
        self.assertTrue(rows[0]['createdAt'].endswith('Z'))

    def test_create_keeps_the_id_sent_by_the_client(self):
        response = self.client.post(
            reverse('transaction-list'),
            transaction_payload(id='11111111-2222-3333-4444-555555555555'),
            format='json',
        )

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        saved = Transaction.objects.get(pk='11111111-2222-3333-4444-555555555555')
        self.assertEqual(saved.amount, Decimal('250'))
        self.assertEqual(saved.category.name, 'Food')
        self.assertEqual(saved.payment_method, 'UPI')

    def test_create_without_id_generates_one(self):
        response = self.client.post(reverse('transaction-list'), transaction_payload(), format='json')

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertTrue(response.json()['id'])

    def test_create_rejects_a_duplicate_id(self):
        existing = make_transaction()
        response = self.client.post(
            reverse('transaction-list'), transaction_payload(id=existing.pk), format='json',
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('id', response.json())

    def test_create_validation(self):
        invalid_payloads = {
            'amount': transaction_payload(amount=0),
            'category': transaction_payload(category='Rent'),
            'paymentMethod': transaction_payload(paymentMethod='Cheque'),
            'type': transaction_payload(type='transfer'),
            'description': transaction_payload(description='x' * 101),
            'date': transaction_payload(date='24-09-2026'),
        }
        for field, payload in invalid_payloads.items():
            with self.subTest(field=field):
                response = self.client.post(reverse('transaction-list'), payload, format='json')
                self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
                self.assertIn(field, response.json())
        self.assertEqual(Transaction.objects.count(), 0)

    def test_category_must_allow_the_transaction_type(self):
        response = self.client.post(
            reverse('transaction-list'), transaction_payload(type='income', category='Food'), format='json',
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('category', response.json())

        # "Other" is a "both" category, so it accepts income
        response = self.client.post(
            reverse('transaction-list'), transaction_payload(type='income', category='Other'), format='json',
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

    def test_update_cannot_change_the_id(self):
        transaction = make_transaction()
        response = self.client.put(
            reverse('transaction-detail', args=[transaction.pk]),
            transaction_payload(id='something-else', amount=600.75, category='Travel'),
            format='json',
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        transaction.refresh_from_db()
        self.assertEqual(transaction.amount, Decimal('600.75'))
        self.assertEqual(transaction.category.name, 'Travel')
        self.assertFalse(Transaction.objects.filter(pk='something-else').exists())

    def test_delete(self):
        transaction = make_transaction()
        response = self.client.delete(reverse('transaction-detail', args=[transaction.pk]))

        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        self.assertFalse(Transaction.objects.exists())

    def test_detail_404(self):
        response = self.client.get(reverse('transaction-detail', args=['missing']))
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)


class CategoryApiTests(APITestCase):
    def test_list_returns_the_defaults_in_order(self):
        response = self.client.get(reverse('category-list'))

        self.assertEqual(
            [(row['id'], row['name'], row['type']) for row in response.json()],
            DEFAULT_CATEGORIES,
        )

    def test_create_is_added_at_the_end(self):
        response = self.client.post(
            reverse('category-list'), {'id': 'cat-rent', 'name': '  Rent ', 'type': 'expense'}, format='json',
        )

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.json(), {'id': 'cat-rent', 'name': 'Rent', 'type': 'expense'})
        self.assertEqual(Category.objects.last().name, 'Rent')

    def test_name_must_be_unique_ignoring_case(self):
        response = self.client.post(reverse('category-list'), {'name': 'food', 'type': 'expense'}, format='json')

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('name', response.json())

    def test_rename_is_seen_by_its_transactions(self):
        transaction = make_transaction()
        response = self.client.put(
            reverse('category-detail', args=['cat-food']), {'name': 'Meals', 'type': 'expense'}, format='json',
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        detail = self.client.get(reverse('transaction-detail', args=[transaction.pk])).json()
        self.assertEqual(detail['category'], 'Meals')

    def test_type_must_keep_allowing_existing_transactions(self):
        make_transaction()
        url = reverse('category-detail', args=['cat-food'])

        response = self.client.put(url, {'name': 'Food', 'type': 'income'}, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('type', response.json())

        response = self.client.put(url, {'name': 'Food', 'type': 'both'}, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_delete_unused_category(self):
        response = self.client.delete(reverse('category-detail', args=['cat-education']))

        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        self.assertFalse(Category.objects.filter(pk='cat-education').exists())

    def test_delete_used_category_needs_a_replacement(self):
        transaction = make_transaction()
        url = reverse('category-detail', args=['cat-food'])

        response = self.client.delete(url)
        self.assertEqual(response.status_code, status.HTTP_409_CONFLICT)

        for bad_replacement in ('Nope', 'Food', 'Salary'):  # unknown, itself, income-only
            response = self.client.delete(f'{url}?replacement={bad_replacement}')
            self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertTrue(Category.objects.filter(pk='cat-food').exists())

        response = self.client.delete(f'{url}?replacement=Other')
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        transaction.refresh_from_db()
        self.assertEqual(transaction.category.name, 'Other')
        self.assertFalse(Category.objects.filter(pk='cat-food').exists())


class BudgetApiTests(APITestCase):
    def test_empty_budgets(self):
        response = self.client.get(reverse('budgets'))
        self.assertEqual(response.json(), {'monthlyLimit': 0, 'categoryLimits': {}})

    def test_patch_changes_only_what_is_sent(self):
        url = reverse('budgets')

        response = self.client.patch(url, {'monthlyLimit': 40000}, format='json')
        self.assertEqual(response.json(), {'monthlyLimit': 40000, 'categoryLimits': {}})

        response = self.client.patch(
            url, {'categoryLimits': {'cat-food': 6000, 'cat-travel': 4500.5}}, format='json',
        )
        self.assertEqual(
            response.json(),
            {'monthlyLimit': 40000, 'categoryLimits': {'cat-food': 6000, 'cat-travel': 4500.5}},
        )

        # 0 removes a category's budget
        response = self.client.patch(url, {'categoryLimits': {'cat-food': 0}}, format='json')
        self.assertEqual(response.json()['categoryLimits'], {'cat-travel': 4500.5})

    def test_patch_validation(self):
        url = reverse('budgets')

        response = self.client.patch(url, {'monthlyLimit': -1}, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

        response = self.client.patch(url, {'categoryLimits': {'cat-missing': 100}}, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_deleting_a_category_removes_its_budget(self):
        self.client.patch(reverse('budgets'), {'categoryLimits': {'cat-food': 6000}}, format='json')
        self.client.delete(reverse('category-detail', args=['cat-food']))

        self.assertEqual(self.client.get(reverse('budgets')).json()['categoryLimits'], {})


class AppDataApiTests(APITestCase):
    def test_get_returns_everything(self):
        make_transaction()
        data = self.client.get(reverse('app_data')).json()

        self.assertEqual(set(data), {'transactions', 'categories', 'budgets'})
        self.assertEqual(len(data['transactions']), 1)
        self.assertEqual(len(data['categories']), len(DEFAULT_CATEGORIES))

    def test_delete_clears_everything_and_restores_default_categories(self):
        make_transaction()
        Category.objects.create(name='Rent', type='expense', budget_limit=Decimal('500'))
        Category.objects.filter(pk='cat-food').update(name='Meals')
        self.client.patch(reverse('budgets'), {'monthlyLimit': 40000}, format='json')

        data = self.client.delete(reverse('app_data')).json()

        self.assertEqual(data['transactions'], [])
        self.assertEqual(data['budgets'], {'monthlyLimit': 0, 'categoryLimits': {}})
        self.assertEqual(
            [(row['id'], row['name'], row['type']) for row in data['categories']],
            DEFAULT_CATEGORIES,
        )

    def test_sample_data(self):
        make_transaction(description='Replaced by the samples')
        # A renamed default category keeps its id, so "Food" must come back under a new one.
        Category.objects.filter(pk='cat-food').update(name='Meals')

        response = self.client.post(reverse('sample_data'))

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        data = response.json()
        today = timezone.localdate().isoformat()
        self.assertGreater(len(data['transactions']), 60)
        self.assertFalse(any(row['description'] == 'Replaced by the samples' for row in data['transactions']))
        self.assertTrue(all(row['date'] <= today for row in data['transactions']))

        names = [row['name'] for row in data['categories']]
        self.assertIn('Meals', names)
        self.assertIn('Food', names)
        food_id = Category.objects.get(name='Food').pk
        self.assertEqual(data['budgets']['monthlyLimit'], 40000)
        self.assertEqual(data['budgets']['categoryLimits'][food_id], 6000)
        self.assertEqual(len(data['budgets']['categoryLimits']), 4)

    def test_seed_command(self):
        call_command('seed_expenses', stdout=StringIO())

        self.assertTrue(Transaction.objects.exists())
        self.assertEqual(Budget.load().monthly_limit, Decimal('40000'))


class RecentMonthsTests(APITestCase):
    def test_wraps_around_the_year(self):
        self.assertEqual(
            get_recent_months(3, date(2026, 1, 15)),
            [(2025, 11), (2025, 12), (2026, 1)],
        )
