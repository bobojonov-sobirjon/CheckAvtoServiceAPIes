from django.urls import path
from .views import CarListCreateView, CarDetailView, CarStatsView

urlpatterns = [
    # Car API endpoints
    path('cars/', CarListCreateView.as_view(), name='car-list-create'),
    path('cars/<int:pk>/', CarDetailView.as_view(), name='car-detail'),
    path('cars/stats/', CarStatsView.as_view(), name='car-stats'),
]
