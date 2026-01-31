from django.contrib import admin
from django.utils.html import format_html
from django.urls import reverse
from django.utils.safestring import mark_safe
from .models import Order, OrderStatus, OrderPriority, OrderType, ScheduledOrder, SOSOrder, OrderService


class BaseOrderAdmin(admin.ModelAdmin):
    """Базовая админка для заказов"""
    
    list_per_page = 25
    list_max_show_all = 100
    readonly_fields = ['id', 'created_at', 'updated_at', 'user_link', 'master_link', 'order_type']
    filter_horizontal = ['masters', 'car', 'category']
    
    search_fields = [
        'id', 'text', 'location', 'user__first_name', 'user__last_name', 
        'user__email', 'master__user__first_name', 'master__user__last_name'
    ]
    
    def user_link(self, obj):
        """Ссылка на пользователя"""
        if obj.user:
            url = reverse('admin:accounts_customuser_change', args=[obj.user.id])
            return format_html('<a href="{}">{}</a>', url, obj.user.get_full_name() or obj.user.email)
        return '-'
    user_link.short_description = 'Пользователь'
    user_link.admin_order_field = 'user__first_name'
    
    def master_link(self, obj):
        """Ссылка на мастера"""
        if obj.master:
            url = reverse('admin:master_master_change', args=[obj.master.id])
            return format_html('<a href="{}">{}</a>', url, obj.master.full_name)
        return '-'
    master_link.short_description = 'Мастер'
    master_link.admin_order_field = 'master__user__first_name'
    
    def status_badge(self, obj):
        """Статус с цветовой индикацией"""
        colors = {
            OrderStatus.PENDING: '#ffc107',      # Желтый
            OrderStatus.IN_PROGRESS: '#17a2b8',  # Синий
            OrderStatus.COMPLETED: '#28a745',    # Зеленый
            OrderStatus.CANCELLED: '#6c757d',    # Серый
            OrderStatus.REJECTED: '#dc3545',     # Красный
        }
        color = colors.get(obj.status, '#6c757d')
        return format_html(
            '<span style="background-color: {}; color: white; padding: 3px 8px; '
            'border-radius: 3px; font-size: 11px;">{}</span>',
            color, obj.get_status_display()
        )
    status_badge.short_description = 'Статус'
    status_badge.admin_order_field = 'status'
    
    def priority_badge(self, obj):
        """Приоритет с цветовой индикацией"""
        colors = {
            OrderPriority.LOW: '#28a745',    # Зеленый
            OrderPriority.HIGH: '#dc3545',   # Красный
        }
        color = colors.get(obj.priority, '#6c757d')
        return format_html(
            '<span style="background-color: {}; color: white; padding: 3px 8px; '
            'border-radius: 3px; font-size: 11px;">{}</span>',
            color, obj.get_priority_display()
        )
    priority_badge.short_description = 'Приоритет'
    priority_badge.admin_order_field = 'priority'
    
    def location_short(self, obj):
        """Краткое описание местоположения"""
        if obj.location:
            return obj.location[:50] + '...' if len(obj.location) > 50 else obj.location
        return '-'
    location_short.short_description = 'Местоположение'
    
    def get_queryset(self, request):
        """Оптимизация запросов"""
        return super().get_queryset(request).select_related(
            'user', 'master', 'master__user'
        )
    
    def has_add_permission(self, request):
        """Разрешить создание заказов только суперпользователям"""
        return request.user.is_superuser
    
    def has_change_permission(self, request, obj=None):
        """Разрешить изменение заказов"""
        return True
    
    def has_delete_permission(self, request, obj=None):
        """Разрешить удаление заказов только суперпользователям"""
        return request.user.is_superuser
    
    def get_readonly_fields(self, request, obj=None):
        """Поля только для чтения"""
        readonly_fields = list(self.readonly_fields)
        
        # Обычные пользователи не могут изменять некоторые поля
        if not request.user.is_superuser:
            readonly_fields.extend(['user', 'master'])
        
        return readonly_fields


@admin.register(ScheduledOrder)
class ScheduledOrderAdmin(BaseOrderAdmin):
    """Админка для запланированных заказов (Order by Date)"""
    
    list_display = [
        'id', 'user_link', 'master_link', 'scheduled_date', 'time_slot',
        'status_badge', 'priority_badge', 'created_at'
    ]
    
    list_filter = [
        'status', 'priority', 'scheduled_date', 'created_at',
        'master__city', 'master'
    ]
    
    fieldsets = (
        ('Основная информация', {
            'fields': ('id', 'order_type', 'user_link', 'text', 'status', 'priority')
        }),
        ('Дата и время визита', {
            'fields': ('scheduled_date', 'scheduled_time_start', 'scheduled_time_end'),
            'classes': ('wide',)
        }),
        ('Мастер и услуги', {
            'fields': ('master_link', 'category', 'car')
        }),
        ('Местоположение мастера', {
            'fields': ('location', 'latitude', 'longitude'),
            'classes': ('collapse',)
        }),
        ('Временные метки', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    def time_slot(self, obj):
        """Временной слот"""
        if obj.scheduled_time_start and obj.scheduled_time_end:
            return f"{obj.scheduled_time_start.strftime('%H:%M')}-{obj.scheduled_time_end.strftime('%H:%M')}"
        return '-'
    time_slot.short_description = 'Время визита'
    time_slot.admin_order_field = 'scheduled_time_start'


@admin.register(SOSOrder)
class SOSOrderAdmin(BaseOrderAdmin):
    """Админка для SOS заказов (экстренная помощь)"""
    
    list_display = [
        'id', 'user_link', 'master_link', 'location_short', 
        'status_badge', 'created_at', 'coordinates'
    ]
    
    list_filter = [
        'status', 'created_at', 'master__city', 'master'
    ]
    
    fieldsets = (
        ('Основная информация', {
            'fields': ('id', 'order_type', 'user_link', 'text', 'status'),
            'classes': ('wide',)
        }),
        ('Местоположение клиента (GPS)', {
            'fields': ('location', 'latitude', 'longitude'),
            'classes': ('wide',)
        }),
        ('Мастер и услуги', {
            'fields': ('master_link', 'category', 'car')
        }),
        ('Временные метки', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    def coordinates(self, obj):
        """GPS координаты"""
        if obj.latitude and obj.longitude:
            return format_html(
                '<a href="https://www.google.com/maps?q={},{}" target="_blank">{:.4f}, {:.4f}</a>',
                obj.latitude, obj.longitude, obj.latitude, obj.longitude
            )
        return '-'
    coordinates.short_description = 'GPS координаты'
    
    def get_readonly_fields(self, request, obj=None):
        """Поля только для чтения"""
        readonly_fields = list(super().get_readonly_fields(request, obj))
        # Для SOS заказов scheduled поля не нужны
        return readonly_fields


class OrderStatusFilter(admin.SimpleListFilter):
    """Фильтр по статусу заказа"""
    title = 'Статус заказа'
    parameter_name = 'status'
    
    def lookups(self, request, model_admin):
        return OrderStatus.choices
    
    def queryset(self, request, queryset):
        if self.value():
            return queryset.filter(status=self.value())
        return queryset


class OrderPriorityFilter(admin.SimpleListFilter):
    """Фильтр по приоритету заказа"""
    title = 'Приоритет заказа'
    parameter_name = 'priority'
    
    def lookups(self, request, model_admin):
        return OrderPriority.choices
    
    def queryset(self, request, queryset):
        if self.value():
            return queryset.filter(priority=self.value())
        return queryset


@admin.register(OrderService)
class OrderServiceAdmin(admin.ModelAdmin):
    """Админка для услуг в заказе"""
    
    list_display = ['id', 'order_link', 'service_name', 'service_price', 'created_at']
    list_filter = ['created_at', 'order__status']
    search_fields = [
        'order__id', 'master_service_item__name', 
        'order__user__first_name', 'order__user__last_name'
    ]
    readonly_fields = ['id', 'created_at']
    list_per_page = 25
    
    def order_link(self, obj):
        """Ссылка на заказ"""
        if obj.order:
            url = reverse('admin:order_order_change', args=[obj.order.id])
            return format_html('<a href="{}">Заказ #{}</a>', url, obj.order.id)
        return '-'
    order_link.short_description = 'Заказ'
    order_link.admin_order_field = 'order__id'
    
    def service_name(self, obj):
        """Название услуги"""
        return obj.master_service_item.name if obj.master_service_item else '-'
    service_name.short_description = 'Услуга'
    
    def service_price(self, obj):
        """Цена услуги"""
        if obj.master_service_item:
            price_from = obj.master_service_item.price_from
            price_to = obj.master_service_item.price_to
            if price_from and price_to:
                return f"{price_from} - {price_to} сум"
            elif price_from:
                return f"от {price_from} сум"
        return '-'
    service_price.short_description = 'Цена'
    
    def get_queryset(self, request):
        """Оптимизация запросов"""
        return super().get_queryset(request).select_related(
            'order', 'order__user', 'master_service_item', 
            'master_service_item__master_service'
        )


# Дополнительные настройки админки
admin.site.site_header = "CheckAvto - Администрирование"
admin.site.site_title = "CheckAvto Admin"
admin.site.index_title = "Управление заказами"
