from django.urls import path
from .views import (
    MasterProfileView, MasterDetailsView, MasterListView,
    MasterEmployeeView, MasterFilterChoicesView, MastersByUserView
)

urlpatterns = [
    # Masters endpoints
    path('masters/', MasterProfileView.as_view(), name='master-profile'),
    path('masters/list/', MasterListView.as_view(), name='master-list'),
    path('masters/by-user/', MastersByUserView.as_view(), name='masters-by-user'),
    path('masters/filter-choices/', MasterFilterChoicesView.as_view(), name='master-filter-choices'),
    path('masters/<int:master_id>/', MasterDetailsView.as_view(), name='master-details'),
    
    # Master Employees endpoints
    path('masters/employees/', MasterEmployeeView.as_view(), name='master-employees'),
]
