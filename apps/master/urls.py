from django.urls import path
from .views import (
    MasterProfileView, MasterDetailsView, MasterListView,
    MasterServiceView, MasterServiceDetailView, MasterServicesByMasterView,
    MasterServiceItemsView, MasterServiceItemsDetailView,
    MasterInMasterView, MasterInMasterDetailView, MasterInMasterByMasterView
)

urlpatterns = [
    # Master API endpoints
    path('masters/', MasterProfileView.as_view(), name='master-profile'),
    path('masters/list/', MasterListView.as_view(), name='master-list'),
    path('masters/<int:master_id>/', MasterDetailsView.as_view(), name='master-details'),
    
    # Master Services API endpoints
    path('masters/services/', MasterServiceView.as_view(), name='master-services'),
    path('masters/<int:master_id>/services/', MasterServicesByMasterView.as_view(), name='master-services-by-master'),
    path('masters/services/<int:service_id>/', MasterServiceDetailView.as_view(), name='master-service-detail'),
    
    # Master Service Items API endpoints
    path('masters/services/<int:master_service_id>/items/', MasterServiceItemsView.as_view(), name='master-service-items'),
    path('masters/services/items/<int:item_id>/', MasterServiceItemsDetailView.as_view(), name='master-service-item-detail'),
    
    # Master In Master API endpoints
    path('masters/in-master/', MasterInMasterView.as_view(), name='master-in-master'),
    path('masters/<int:master_id>/in-master/', MasterInMasterByMasterView.as_view(), name='master-in-master-by-master'),
    path('masters/in-master/<int:master_in_master_id>/', MasterInMasterDetailView.as_view(), name='master-in-master-detail'),
]
