from django.contrib import admin
from django import forms
from .models import Master, MasterService, MasterServiceItems, MasterEmployee
from apps.categories.models import Category


class MasterAdminForm(forms.ModelForm):
    """Форма для мастера"""
    # services field removed - now handled by MasterService model
    
    class Meta:
        model = Master
        fields = '__all__'
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # services field removed - now handled by MasterService model
        # Фильтруем категории только по типу BY_MASTER
        if 'category' in self.fields:
            self.fields['category'].queryset = Category.objects.filter(type_category='by_master')
    
    def save(self, commit=True):
        instance = super().save(commit=False)
        if commit:
            instance.save()
        return instance


class MasterServiceItemsInline(admin.TabularInline):
    """Инлайн для элементов услуги мастера"""
    model = MasterServiceItems
    extra = 1
    fields = ['name', 'price_from', 'price_to', 'category']
    ordering = ['-created_at']
    
    def formfield_for_foreignkey(self, db_field, request, **kwargs):
        """Фильтруем категории только по типу BY_MASTER"""
        if db_field.name == 'category':
            kwargs['queryset'] = Category.objects.filter(type_category='by_master')
        return super().formfield_for_foreignkey(db_field, request, **kwargs)


class MasterServiceInlineForm(forms.ModelForm):
    """
    В MasterService нет редактируемых полей, но объект нужен как контейнер для MasterServiceItems.
    Делаем скрытый маркер, чтобы Django admin считал inline-форму изменённой и сохранял новый объект.
    """

    create_marker = forms.BooleanField(required=False, initial=True, widget=forms.HiddenInput())

    class Meta:
        model = MasterService
        fields = ('create_marker',)

    def has_changed(self):
        # Force create for new inline row
        if self.instance and self.instance.pk is None:
            return True
        return super().has_changed()


class MasterServiceInline(admin.TabularInline):
    """Инлайн-контейнер для услуг мастера (чтобы потом добавлять items внутри MasterService)."""
    model = MasterService
    form = MasterServiceInlineForm
    extra = 1
    show_change_link = True
    can_delete = True
    verbose_name = 'Услуга мастера'
    verbose_name_plural = 'Услуги мастера'
    fields = ('created_at',)
    readonly_fields = ('created_at',)


class MasterEmployeeInline(admin.TabularInline):
    """Инлайн для сотрудников мастерской"""
    model = MasterEmployee
    extra = 0
    autocomplete_fields = ('employee',)
    readonly_fields = ('added_at',)
    fields = ('employee', 'added_at')


@admin.register(Master)
class MasterAdmin(admin.ModelAdmin):
    """Админка для мастеров"""
    form = MasterAdminForm
    
    def get_category(self, obj):
        return ", ".join([category.name for category in obj.category.all()])
    get_category.short_description = 'Категория'
    
    list_display = [
        'full_name', 'name', 'phone_number', 'city', 'get_category', 'latitude', 'longitude', 'created_at'
    ]
    list_filter = [
        'city', 'created_at'
    ]
    search_fields = [
        'user__phone_number', 'user__first_name', 'user__last_name', 
        'name', 'city'
    ]
    ordering = ['-created_at']
    inlines = [MasterServiceInline, MasterEmployeeInline]
    
    fieldsets = (
        ('Пользователь', {
            'fields': ('user', 'name', 'category', 'description')
        }),
        ('Местоположение', {
            'fields': ('city', 'address', 'latitude', 'longitude')
        }),
        ('Контактная информация', {
            'fields': ('phone', 'working_time')
        }),
        # Services section removed - now handled by MasterService model
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
        return f"{master_services.count()} услуг"
    services_display.short_description = 'Услуги'


@admin.register(MasterService)
class MasterServiceAdmin(admin.ModelAdmin):
    """Админка для услуг мастера"""
    list_display = ['master__address', 'master__city', 'master', 'items_count', 'created_at']
    list_filter = ['created_at']
    search_fields = ['master__user__phone_number', 'master__user__first_name']
    ordering = ['-created_at']
    inlines = [MasterServiceItemsInline]
    
    def items_count(self, obj):
        return obj.master_service_items.count()
    items_count.short_description = 'Количество элементов'
    
    def has_module_permission(self, request):
        """Скрываем из меню (управляется inline в Master)."""
        return False


@admin.register(MasterServiceItems)
class MasterServiceItemsAdmin(admin.ModelAdmin):
    """
    Нужен для autocomplete_fields в OrderServiceInline.
    В меню скрыт — управляется через MasterService inline.
    """

    search_fields = ('name', 'master_service__master__user__email', 'master_service__master__name')
    list_display = ('id', 'name', 'master_service', 'category', 'price_from', 'price_to', 'created_at')
    list_filter = ('category', 'created_at')

    def has_module_permission(self, request):
        return False


@admin.register(MasterEmployee)
class MasterEmployeeAdmin(admin.ModelAdmin):
    """Админка для сотрудников мастерской"""
    list_display = ('id', 'master', 'employee', 'added_at')
    list_filter = ('added_at',)
    search_fields = ('master__user__email', 'employee__email', 'employee__phone_number')
    readonly_fields = ('added_at',)
    
    def get_readonly_fields(self, request, obj=None):
        if obj:  # При редактировании
            return self.readonly_fields + ('master', 'employee')
        return self.readonly_fields

    def has_module_permission(self, request):
        """Скрываем из меню (управляется inline в Master)."""
        return False

