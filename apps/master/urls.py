from django.urls import path
from .views import (
    MasterProfileView, MasterServiceTypesView, MasterAddServiceView, 
    MasterRemoveServiceView, MasterStatsView
)

urlpatterns = [
    # Master API endpoints
    path('masters/', MasterProfileView.as_view(), name='master-profile'),
    path('masters/service-types/', MasterServiceTypesView.as_view(), name='master-service-types'),
    path('masters/add-service/', MasterAddServiceView.as_view(), name='master-add-service'),
    path('masters/remove-service/', MasterRemoveServiceView.as_view(), name='master-remove-service'),
    path('masters/stats/', MasterStatsView.as_view(), name='master-stats'),
]
