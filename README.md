# Expense Tracker API (Django)

The backend for the React app in `expense-tracker-react-app`. It stores transactions, categories and budgets in SQLite and serves them as JSON with Django REST Framework. It's designed to help you learn Django models, the ORM, serializers and REST APIs.

**Features:** create/read/update/delete for transactions and categories, monthly and per-category budgets, server-side validation, safe category deletion (transactions are moved first), sample data, Django Admin, and a browsable API.

There are no HTML pages here any more: the React app is the user interface.

---

## Setup and running (Windows)

You need Python 3.10 or newer. Get it from https://www.python.org/downloads/ and tick **"Add python.exe to PATH"** during install.

```bash
cd expense-tracker-django

python -m venv venv
venv\Scripts\activate            # macOS/Linux: source venv/bin/activate

pip install -r requirements.txt

python manage.py migrate         # creates the tables and the default categories

python manage.py createsuperuser # optional, for /admin/
python manage.py seed_expenses   # optional: replaces ALL transactions and budgets with 6 months of samples

python manage.py runserver
```

Then start the React app in a second terminal:

```bash
cd ../expense-tracker-react-app
npm install
npm run dev
```

Open http://localhost:5173/ for the app. The React dev server forwards every `/api` request to Django on port 8000, so both must be running.

Open http://127.0.0.1:8000/api/ to explore the API in the browser, and http://127.0.0.1:8000/admin/ for Django Admin.

Other useful commands:

```bash
python manage.py test expenses   # run the automated tests
```

### Environment variables (optional)

| Variable | Default | Purpose |
|---|---|---|
| `DJANGO_SECRET_KEY` | an insecure development key | **Set this for any real deployment** |
| `DJANGO_DEBUG` | `True` | Set to `False` in production |
| `DJANGO_ALLOWED_HOSTS` | `127.0.0.1,localhost` | Comma-separated host names |

> **No login yet.** Anyone who can reach the server can read and change the data. That's fine on your own machine; add authentication before putting it online.

---

## API

All URLs start with `/api/`. Requests and responses are JSON, with camelCase field names to match the React app.

| Method and URL | What it does |
|---|---|
| `GET /api/data/` | Everything at once: `{ transactions, categories, budgets }` |
| `DELETE /api/data/` | Delete everything and restore the default categories |
| `POST /api/data/sample/` | Replace transactions and budgets with 6 months of sample data |
| `GET /api/transactions/` | List transactions, newest first |
| `POST /api/transactions/` | Create a transaction |
| `GET` `PUT` `PATCH` `DELETE /api/transactions/<id>/` | Read, update or delete one |
| `GET /api/categories/` | List categories |
| `POST /api/categories/` | Create a category |
| `GET` `PUT` `PATCH` `DELETE /api/categories/<id>/` | Read, update or delete one. Deleting a category that has transactions needs `?replacement=<category name>` |
| `GET /api/budgets/` | Read the budgets |
| `PATCH /api/budgets/` | Change the budgets. Send only what changed; a limit of 0 removes it |

Shapes:

```json
// transaction
{ "id": "8a0c…", "type": "expense", "amount": 250.5, "category": "Food",
  "date": "2026-09-24", "paymentMethod": "UPI", "description": "Lunch",
  "createdAt": "2026-09-24T08:00:00Z" }

// category ("type" is "expense", "income" or "both")
{ "id": "cat-food", "name": "Food", "type": "expense" }

// budgets ("categoryLimits" is keyed by category id)
{ "monthlyLimit": 40000, "categoryLimits": { "cat-food": 6000 } }
```

Errors come back with status 400 and a message per field, for example `{ "amount": ["Amount must be greater than 0."] }`.

---

## How it works

### 1. Project structure

```text
expense-tracker-django/
├── manage.py                  # command-line entry point
├── expense_tracker/           # project package: settings and root URLs
│   ├── settings.py
│   └── urls.py                # sends /admin/ to the admin and /api/ to expenses.urls
└── expenses/                  # the app
    ├── models.py              # Category, Transaction, Budget (database tables)
    ├── serializers.py         # model <-> JSON, plus validation
    ├── views.py               # the API endpoints
    ├── urls.py                # URL → view mapping
    ├── app_data.py            # default categories, sample data, "clear everything"
    ├── admin.py               # Django Admin configuration
    ├── tests.py               # automated tests
    ├── migrations/            # database changes (0002 adds the default categories)
    └── management/commands/seed_expenses.py  # sample data command
```

### 2. Models

- **`Category`** has a `name`, a `type` (`expense`, `income` or `both`), and its monthly `budget_limit` (0 means no budget). A `UniqueConstraint` on `Lower('name')` makes "Food" and "food" the same name.
- **`Transaction`** has a `type`, `amount`, `date`, `payment_method`, `description` and a **foreign key** to `Category`. `on_delete=models.PROTECT` stops a category being deleted while transactions still use it.
- **`Budget`** holds the overall monthly limit. There is only ever one row, fetched with `Budget.load()`.
- `amount` is a `DecimalField`, which stores money exactly (floats would cause rounding errors).
- `Category` and `Transaction` use a **text `id`** instead of Django's usual auto number. The React app creates the id itself (a UUID), which lets it show a new row instantly without waiting for the server.

### 3. Serializers

A serializer does for an API what a `ModelForm` does for an HTML page: it turns a model into JSON, and validates incoming JSON before saving.

- `source='payment_method'` lets the JSON say `paymentMethod` while the model keeps Python-style names.
- `SlugRelatedField(slug_field='name')` shows a transaction's category as its name (`"Food"`) even though the database stores a foreign key. Renaming a category therefore updates every transaction for free.
- `validate_<field>()` checks one field (e.g. the category name is unique); `validate()` checks fields together (e.g. an income transaction can't use an expense-only category).

### 4. Views and URLs

- `TransactionViewSet` and `CategoryViewSet` are `ModelViewSet`s: one class gives list, create, detail, update and delete. The `DefaultRouter` in `urls.py` builds their URLs.
- `CategoryViewSet.destroy()` is overridden to move a category's transactions to the replacement before deleting it, inside `transaction.atomic()` so it either all happens or none of it does.
- `budgets`, `app_data` and `sample_data` are small function views using `@api_view`.

### 5. How the React app uses it

1. On start it calls `GET /api/data/` and keeps the result in React state.
2. Every change (add, edit, delete) updates the screen immediately and sends one request in the background.
3. If a request fails, the app shows the error and reloads `GET /api/data/` so the screen matches the database again.

### 6. Adding new features

- **New field** (for example `notes`): add it to the model, run `makemigrations` and `migrate`, add it to the serializer's `fields`, then use it in the React app.
- **New payment method:** add a line to `Transaction.PaymentMethod`, run `makemigrations` and `migrate`, and add it to `PAYMENT_METHODS` in the React app's `constants/transactions.js`.
- **User accounts:** add `user = models.ForeignKey(settings.AUTH_USER_MODEL, ...)` to each model, turn on authentication in `REST_FRAMEWORK`, and filter every queryset with `.filter(user=request.user)`.
- **Other ideas:** CSV export, server-side monthly reports (`TruncMonth` + `Sum`), and filtering the list with query parameters (`?month=2026-09`).
