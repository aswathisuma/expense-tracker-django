from django.urls import include, path
from rest_framework.routers import SimpleRouter

from . import views

# The router builds the list and detail URLs for each ViewSet.
# SimpleRouter (unlike DefaultRouter) adds no index page listing the API at /api/.
router = SimpleRouter()
router.register('transactions', views.TransactionViewSet)
router.register('categories', views.CategoryViewSet)

urlpatterns = [
    path('budgets/', views.budgets, name='budgets'),
    path('data/', views.app_data, name='app_data'),
    path('data/sample/', views.sample_data, name='sample_data'),
    path('', include(router.urls)),
]
