from django.urls import path
from . import views

app_name = 'order'

urlpatterns = [
    # Order creation (NEW: separate endpoints for different order types)
    path('scheduled/', views.ScheduledOrderCreateView.as_view(), name='scheduled-order-create'),
    path('sos/', views.SOSOrderCreateView.as_view(), name='sos-order-create'),
    
    # Available time slots
    path('available-slots/', views.AvailableTimeSlotsView.as_view(), name='available-time-slots'),
    
    # Order CRUD operations
    path('', views.OrderListCreateView.as_view(), name='order-list-create'),
    path('<int:id>/', views.OrderDetailView.as_view(), name='order-detail'),
    
    # Order filtering
    path('by-user/', views.OrdersByUserView.as_view(), name='orders-by-user'),
    path('by-master/', views.OrdersByMasterView.as_view(), name='orders-by-master'),
    path('available/', views.AvailableOrdersForMasterView.as_view(), name='available-orders'),
    
    # Order status management
    path('<int:order_id>/status/', views.UpdateOrderStatusView.as_view(), name='update-status'),
    path('<int:order_id>/accept/', views.AcceptOrderView.as_view(), name='accept-order'),
    
    # Rating endpoints
    path('ratings/', views.RatingCreateView.as_view(), name='rating-create'),
    path('ratings/list/', views.RatingListView.as_view(), name='rating-list'),
]

