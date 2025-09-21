from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from django.contrib.sites.models import Site
from .models import CustomUser


@admin.register(CustomUser)
class CustomUserAdmin(UserAdmin):
    """
    Настройка админки для пользователей
    """
    list_display = ('email', 'username', 'first_name', 'last_name', 'is_verified', 'is_staff', 'is_active', 'created_at')
    list_filter = ('is_verified', 'is_staff', 'is_superuser', 'is_active', 'created_at')
    search_fields = ('email', 'username', 'first_name', 'last_name', 'phone_number')
    ordering = ('-created_at',)
    
    fieldsets = (
        (None, {'fields': ('username', 'password')}),
        ('Личная информация', {'fields': ('first_name', 'last_name', 'email', 'phone_number', 'date_of_birth', 'avatar')}),
        ('Права доступа', {'fields': ('is_active', 'is_staff', 'is_superuser', 'groups', 'user_permissions')}),
        ('Важные даты', {'fields': ('last_login', 'date_joined', 'created_at', 'updated_at')}),
        ('Подтверждение', {'fields': ('is_verified',)}),
    )
    
    add_fieldsets = (
        (None, {
            'classes': ('wide',),
            'fields': ('username', 'email', 'first_name', 'last_name', 'password1', 'password2'),
        }),
    )
    
    readonly_fields = ('created_at', 'updated_at', 'date_joined', 'last_login')


admin.site.unregister(Site)