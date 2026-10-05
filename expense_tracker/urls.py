"""Root URL configuration for the expense_tracker project."""
from django.contrib import admin
from django.urls import include, path
from django.views.generic import RedirectView

urlpatterns = [
    # The bare address opens Django Admin, which asks for a login first
    path('', RedirectView.as_view(pattern_name='admin:index')),
    path('admin/', admin.site.urls),
    path('api/', include('expenses.urls')),
]
