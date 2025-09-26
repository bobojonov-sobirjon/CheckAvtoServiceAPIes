from django.contrib import admin
from .models import Car


@admin.register(Car)
class CarAdmin(admin.ModelAdmin):
    """Админка для машин"""
    list_display = [
        'brand', 'model', 'type_car', 'year', 'user', 'created_at'
    ]
    list_filter = [
        'type_car', 'brand', 'year', 'created_at'
    ]
    search_fields = [
        'brand', 'model', 'user__phone_number', 'user__first_name', 'user__last_name'
    ]
    ordering = ['-created_at']
    
    fieldsets = (
        ('Основная информация', {
            'fields': ('brand', 'model', 'type_car', 'year')
        }),
        ('Пользователь', {
            'fields': ('user',)
        }),
        ('Даты', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    readonly_fields = ['created_at', 'updated_at']
    
    def get_queryset(self, request):
        """Оптимизация запросов"""
        return super().get_queryset(request).select_related('user')