"""Root URL configuration for the expense_tracker project."""
from django.contrib import admin
from django.urls import include, path
from django.views.generic import RedirectView

urlpatterns = [
    # There are no HTML pages here, so the bare address goes to the API
    path('', RedirectView.as_view(url='/api/')),
    path('admin/', admin.site.urls),
    path('api/', include('expenses.urls')),
]
