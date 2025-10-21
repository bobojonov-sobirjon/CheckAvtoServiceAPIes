from django.contrib import admin
from django import forms
from .models import Master, ServiceType, MasterService


class MasterAdminForm(forms.ModelForm):
    """Форма для мастера"""
    # services field removed - now handled by MasterService model
    
    class Meta:
        model = Master
        fields = '__all__'
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # services field removed - now handled by MasterService model
    
    def save(self, commit=True):
        instance = super().save(commit=False)
        if commit:
            instance.save()
        return instance


class MasterServiceInline(admin.TabularInline):
    """Инлайн для услуг мастера"""
    model = MasterService
    extra = 1
    fields = ['name', 'price_from', 'price_to']
    ordering = ['name']


@admin.register(Master)
class MasterAdmin(admin.ModelAdmin):
    """Админка для мастеров"""
    form = MasterAdminForm
    
    list_display = [
        'full_name', 'phone_number', 'city', 'services_display', 'created_at'
    ]
    list_filter = [
        'city', 'created_at'
    ]
    search_fields = [
        'user__phone_number', 'user__first_name', 'user__last_name', 
        'city'
    ]
    ordering = ['-created_at']
    inlines = [MasterServiceInline]
    
    fieldsets = (
        ('Пользователь', {
            'fields': ('service_type', 'user',)
        }),
        ('Местоположение', {
            'fields': ('city', 'address', 'latitude', 'longitude')
        }),
        ('Контактная информация', {
            'fields': ('phone', 'working_time')
        }),
        # Services section removed - now handled by MasterService model
        ('Банковские данные', {
            'fields': ('card_number', 'card_expiry_month', 'card_expiry_year', 'card_cvv'),
            'classes': ('collapse',)
        }),
        ('Финансы', {
            'fields': ('balance',),
            'classes': ('collapse',)
        }),
        ('Временные метки', {
            'fields': ('created_at', 'updated_at', 'last_activity'),
            'classes': ('collapse',)
        }),
    )
    
    readonly_fields = ['created_at', 'updated_at', 'last_activity']
    
    def full_name(self, obj):
        return obj.full_name
    full_name.short_description = 'Полное имя'
    
    def phone_number(self, obj):
        return obj.phone_number
    phone_number.short_description = 'Телефон'
    
    def services_display(self, obj):
        """Отображение услуг в списке"""
        from .models import MasterService
        master_services = MasterService.objects.filter(master=obj)
        return ', '.join([service.name for service in master_services])
    services_display.short_description = 'Услуги'
