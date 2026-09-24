# Expense Tracker (Django)

A simple expense tracker built with Django, SQLite and Django templates. It's designed to help you learn Django CRUD, the ORM, forms and templates.

**Features:** dashboard with summary cards, add/view/edit/delete expenses, search, category and month filters that work together, filtered totals, pagination (10 per page), amounts formatted as Indian Rupees, Django Admin, and Django messages.

---

## Setup and running (Windows)

You need Python 3.10 or newer. Get it from https://www.python.org/downloads/ and tick **"Add python.exe to PATH"** during install.

```bash
cd expense_tracker

python -m venv venv
venv\Scripts\activate            # macOS/Linux: source venv/bin/activate

pip install django               # or: pip install -r requirements.txt

python manage.py makemigrations
python manage.py migrate

python manage.py createsuperuser # for /admin/
python manage.py seed_expenses   # optional: adds 16 sample expenses

python manage.py runserver
```

Open http://127.0.0.1:8000/ for the app and http://127.0.0.1:8000/admin/ for Django Admin.

Other useful commands:

```bash
python manage.py test expenses          # run the automated tests
python manage.py seed_expenses --clear  # delete all expenses, then re-add the samples
```

### Environment variables (optional)

| Variable | Default | Purpose |
|---|---|---|
| `DJANGO_SECRET_KEY` | an insecure development key | **Set this for any real deployment** |
| `DJANGO_DEBUG` | `True` | Set to `False` in production |
| `DJANGO_ALLOWED_HOSTS` | `127.0.0.1,localhost` | Comma-separated host names |

---

## URLs

| URL | View | Name |
|---|---|---|
| `/` | `dashboard` | `dashboard` |
| `/expenses/` | `expense_list` | `expense_list` |
| `/expenses/add/` | `expense_create` | `expense_create` |
| `/expenses/<id>/` | `expense_detail` | `expense_detail` |
| `/expenses/<id>/edit/` | `expense_update` | `expense_update` |
| `/expenses/<id>/delete/` | `expense_delete` | `expense_delete` |
| `/admin/` | Django Admin | — |

---

## How it works

### 1. Project structure

```text
expense_tracker/
├── manage.py                  # command-line entry point
├── expense_tracker/           # project package: settings and root URLs
│   ├── settings.py
│   └── urls.py                # sends /admin/ to the admin and everything else to expenses.urls
├── templates/
│   └── base.html              # shared layout: navbar, messages, footer
└── expenses/                  # the app
    ├── models.py              # Expense model (database table)
    ├── forms.py               # ExpenseForm (ModelForm)
    ├── views.py               # one function per page
    ├── urls.py                # URL → view mapping
    ├── admin.py               # Django Admin configuration
    ├── tests.py               # automated tests
    ├── templatetags/expense_extras.py        # the |inr currency filter
    ├── management/commands/seed_expenses.py  # sample data command
    ├── templates/expenses/    # page templates, plus includes/ for reusable pieces
    └── static/expenses/       # style.css and script.js
```

A Django **project** holds settings and configuration. An **app** (`expenses`) holds one feature's models, views, templates and static files.

### 2. The Expense model

`Expense` in `models.py` becomes a database table. Each attribute is a column:

- `amount` is a `DecimalField`, which stores money exactly (floats would cause rounding errors). Its `MinValueValidator` rejects 0 and negative amounts.
- `category` uses `choices=Category.choices`. `Category` is a `TextChoices` class, so only the seven allowed values can be saved, and the form shows them as a dropdown.
- `description` has `blank=True`, which makes it optional.
- `created_at` uses `auto_now_add=True`, so it's set once when the row is created. `updated_at` uses `auto_now=True`, so it's refreshed on every save.
- `Meta.ordering = ['-date', '-created_at']` sorts expenses newest first by default.

### 3. ModelForm

`ExpenseForm` builds its fields from the model, so labels, required fields and the category choices come for free. The `widgets` add the browser date picker and number step. `clean_amount()` shows how to add custom validation: any `clean_<field>()` method runs automatically when `form.is_valid()` is called. Errors are shown under each field by `includes/form_field.html`.

### 4. Views

All views are plain functions:

- `expense_create` and `expense_update` follow the standard pattern:
  1. **GET:** show an empty form (create) or a form filled with the expense's values (`instance=expense`).
  2. **POST:** bind `request.POST` to the form and call `is_valid()`.
  3. If valid, call `form.save()`, add a success message, and **redirect**. Redirecting after a POST stops the browser from re-submitting the form on refresh.
  4. If invalid, render the same template again with the errors.
- `expense_delete` shows a confirmation page on GET and deletes only on POST. The form includes `{% csrf_token %}`, and `@require_http_methods` rejects any other method.
- `get_object_or_404` returns a 404 page instead of crashing when an id doesn't exist.

### 5. URLs

`expenses/urls.py` gives every route a `name`. Templates use `{% url 'expense_update' expense.pk %}` and views use `redirect('expense_list')` instead of hard-coded paths, so a URL can be changed in one place.

### 6. Templates

Every page starts with `{% extends 'base.html' %}` and fills in `{% block title %}` and `{% block content %}`. Reusable pieces live in `templates/expenses/includes/` and are pulled in with `{% include %}`:

- `form_field.html`: a label, an input and its errors
- `category_badge.html`: a coloured category label
- `expense_facts.html`: an expense's details, used on both the detail and delete pages

Amounts are formatted with the custom filter `{{ amount|inr }}`. For example, 1234567.5 becomes `₹12,34,567.50`, using Indian digit grouping.

### 7. Database flow

1. The browser submits a form, which sends a POST request.
2. The view validates the data with `ExpenseForm`.
3. `form.save()` runs an SQL `INSERT` or `UPDATE` through the ORM.
4. The view redirects to the expense list.
5. The list view runs `Expense.objects.all()` (a `SELECT` query) and the template shows the rows.

You never write SQL. The ORM builds safe, parameterised queries, which protects against SQL injection.

### 8. Search and filters

The filter form uses `method="get"`, so its values appear in the URL, for example `/expenses/?search=lunch&category=Food&month=2026-09`. The view starts from `Expense.objects.all()` and narrows it one step at a time:

```python
expenses = expenses.filter(Q(title__icontains=search) | Q(description__icontains=search))
expenses = expenses.filter(category=category)
expenses = expenses.filter(date__year=2026, date__month=9)
```

Each `.filter()` adds an `AND` condition, which is why the filters combine. Querysets are lazy, so only one SQL query runs, when the results are needed.

The active filters are URL-encoded into `querystring` and added to every pagination link (`?search=lunch&category=Food&page=2`), so they're kept when you change page. The month dropdown is built from `Expense.objects.dates('date', 'month')`, which lists only months that have expenses.

### 9. Dashboard calculations

All sums are done by the database through aggregation:

```python
Expense.objects.aggregate(total=Sum('amount'))                 # total spent
Expense.objects.count()                                        # number of expenses
Expense.objects.filter(date__year=..., date__month=...)        # this month, then aggregate
Expense.objects.values('category').annotate(total=Sum('amount'))  # one row per category (GROUP BY)
```

`aggregate()` returns `None` for an empty table, so `get_total()` falls back to `0`. The list page's filtered total uses the same `get_total()` on the filtered queryset.

### 10. Adding new features

- **New field** (for example `payment_method`): add it to the model, run `makemigrations` and `migrate`, add it to `ExpenseForm.Meta.fields`, and show it in the templates.
- **New category:** add a line to `Expense.Category`, then run `makemigrations` and `migrate`. Add a `.badge-<name>` colour in `style.css` if you want one.
- **New page:** write a view, add a `path()` with a name, create a template that extends `base.html`, and add a navbar link.
- **User accounts:** add `user = models.ForeignKey(settings.AUTH_USER_MODEL, ...)`, protect the views with `@login_required`, and filter every queryset with `Expense.objects.filter(user=request.user)`.
- **Other ideas:** CSV export (using `HttpResponse` with `csv.writer`), monthly budgets (a `Budget` model compared against the monthly `Sum`), and a date-range filter (`date__range`).

---

## Sample data through Django Admin

If you prefer not to use `seed_expenses`:

1. Log in at `/admin/` with your superuser.
2. Open **Expenses** and choose **Add expense**.
3. Add a few expenses, for example:

   | Title | Amount | Category | Date |
   |---|---|---|---|
   | Lunch | 250 | Food | 2026-09-24 |
   | Petrol | 1500 | Travel | 2026-09-23 |
   | Movie | 500 | Entertainment | 2026-09-20 |
   | Groceries | 2000 | Shopping | 2026-09-18 |
   | Electricity | 1200 | Bills | 2026-09-15 |
