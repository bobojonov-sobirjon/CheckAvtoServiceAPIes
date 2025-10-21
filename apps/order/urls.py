from django.urls import path
from . import views

app_name = 'order'

urlpatterns = [
    # Основные CRUD операции
    path('', views.OrderListCreateView.as_view(), name='order-list-create'),
    path('<int:id>/', views.OrderDetailView.as_view(), name='order-detail'),
    
    # Фильтрация и поиск
    path('by-user/', views.orders_by_user, name='orders-by-user'),
    path('by-master/', views.orders_by_master, name='orders-by-master'),
    
    # Дополнительные операции
    path('<int:order_id>/status/', views.update_order_status, name='update-status'),
    path('<int:order_id>/accept/', views.accept_order, name='accept-order'),
]

