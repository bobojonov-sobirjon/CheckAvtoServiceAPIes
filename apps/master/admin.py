from django.contrib import admin
from django import forms
from .models import Master, ServiceType


class MasterAdminForm(forms.ModelForm):
    """Форма для мастера с множественным выбором услуг"""
    services = forms.MultipleChoiceField(
        choices=ServiceType.choices,
        widget=forms.CheckboxSelectMultiple,
        required=False,
        label='Предоставляемые услуги'
    )
    
    class Meta:
        model = Master
        fields = '__all__'
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if self.instance and self.instance.pk:
            self.fields['services'].initial = self.instance.services
    
    def save(self, commit=True):
        instance = super().save(commit=False)
        instance.services = self.cleaned_data.get('services', [])
        if commit:
            instance.save()
        return instance


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
    
    fieldsets = (
        ('Пользователь', {
            'fields': ('user',)
        }),
        ('Местоположение', {
            'fields': ('city',)
        }),
        ('Услуги', {
            'fields': ('services',),
            'description': 'Выберите услуги, которые предоставляет мастер'
        }),
        ('Банковские данные', {
            'fields': ('card_number', 'card_expiry_month', 'card_expiry_year', 'card_cvv'),
            'classes': ('collapse',)
        }),
        ('Финансы', {
            'fields': ('reserved_amount',),
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
        return ', '.join(obj.get_services_display())
    services_display.short_description = 'Услуги'