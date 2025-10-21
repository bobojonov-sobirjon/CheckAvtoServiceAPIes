from django.urls import path
from .views import (
    MasterProfileView, MasterDetailsView, MasterListView,
    MasterServiceView, MasterServiceDetailView
)

urlpatterns = [
    # Master API endpoints
    path('masters/', MasterProfileView.as_view(), name='master-profile'),
    path('masters/list/', MasterListView.as_view(), name='master-list'),
    path('masters/<int:master_id>/', MasterDetailsView.as_view(), name='master-details'),
    
    # Master Services API endpoints
    path('masters/services/', MasterServiceView.as_view(), name='master-services'),
    path('masters/services/<int:service_id>/', MasterServiceDetailView.as_view(), name='master-service-detail'),
]
