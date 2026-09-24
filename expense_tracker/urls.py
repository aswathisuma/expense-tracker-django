"""Root URL configuration for the expense_tracker project."""
from django.contrib import admin
from django.urls import include, path

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', include('expenses.urls')),
]
