from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from django.contrib.sites.models import Site
from .models import CustomUser, UserBalance, UserSMSCode, FAQ


class UserBalanceInline(admin.StackedInline):
    """Inline для баланса пользователя"""
    model = UserBalance
    extra = 0
    readonly_fields = ('created_at', 'updated_at')
    fields = ('amount', 'created_at', 'updated_at')


class UserSMSCodeInline(admin.TabularInline):
    """Inline для SMS кодов пользователя"""
    model = UserSMSCode
    extra = 0
    readonly_fields = ('code', 'identifier', 'identifier_type', 'created_at', 'expires_at', 'is_used', 'used_at')
    fields = ('code', 'identifier', 'identifier_type', 'created_at', 'expires_at', 'is_used', 'used_at')
    can_delete = False
    max_num = 0  # Display only, no editing


@admin.register(CustomUser)
class CustomUserAdmin(UserAdmin):
    """
    Настройка админки для пользователей
    """
    list_display = ('email', 'username', 'first_name', 'last_name', 'is_verified', 'is_staff', 'is_active', 'created_at')
    list_filter = ('is_verified', 'is_staff', 'is_superuser', 'is_active', 'created_at')
    search_fields = ('email', 'username', 'first_name', 'last_name', 'phone_number')
    ordering = ('-created_at',)
    inlines = [UserBalanceInline, UserSMSCodeInline]
    
    fieldsets = (
        (None, {'fields': ('username', 'password')}),
        ('Личная информация', {'fields': ('first_name', 'last_name', 'email', 'phone_number', 'date_of_birth', 'avatar')}),
        ('Права доступа', {'fields': ('is_active', 'is_staff', 'is_superuser', 'groups')}),
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


@admin.register(UserBalance)
class UserBalanceAdmin(admin.ModelAdmin):
    """Админка для балансов пользователей"""
    list_display = ('user', 'amount', 'created_at', 'updated_at')
    list_filter = ('created_at', 'updated_at')
    search_fields = ('user__email', 'user__username', 'user__first_name', 'user__last_name')
    ordering = ('-updated_at',)
    readonly_fields = ('created_at', 'updated_at')
    
    fieldsets = (
        (None, {'fields': ('user', 'amount')}),
        ('Даты', {'fields': ('created_at', 'updated_at')}),
    )


# @admin.register(UserSMSCode)
class UserSMSCodeAdmin(admin.ModelAdmin):
    """Админка для SMS кодов"""
    list_display = ('code', 'identifier', 'identifier_type', 'created_by', 'is_used', 'created_at', 'expires_at')
    list_filter = ('identifier_type', 'is_used', 'created_at', 'expires_at')
    search_fields = ('code', 'identifier', 'created_by__email', 'created_by__username')
    ordering = ('-created_at',)
    readonly_fields = ('created_at', 'expires_at', 'used_at')
    
    fieldsets = (
        (None, {'fields': ('code', 'identifier', 'identifier_type')}),
        ('Пользователь', {'fields': ('created_by', 'is_used', 'used_at')}),
        ('Даты', {'fields': ('created_at', 'expires_at')}),
    )


@admin.register(FAQ)
class FAQAdmin(admin.ModelAdmin):
    """Админка для FAQ"""
    list_display = ('question_short', 'order', 'is_active', 'created_at', 'updated_at')
    list_filter = ('is_active', 'created_at', 'updated_at')
    search_fields = ('question', 'answer')
    ordering = ('order', '-created_at')
    list_editable = ('order', 'is_active')
    
    fieldsets = (
        (None, {'fields': ('question', 'answer', 'order', 'is_active')}),
        ('Даты', {'fields': ('created_at', 'updated_at')}),
    )
    
    readonly_fields = ('created_at', 'updated_at')
    
    def question_short(self, obj):
        """Короткая версия вопроса для отображения в списке"""
        return obj.question[:100] + '...' if len(obj.question) > 100 else obj.question
    question_short.short_description = 'Вопрос'


admin.site.unregister(Site)