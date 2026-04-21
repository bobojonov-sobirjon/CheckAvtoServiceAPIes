from django.contrib import admin, messages
from django.contrib.auth.admin import UserAdmin
from django.contrib.sites.models import Site
from .models import (
    CustomUser,
    MasterCustomUser,
    CarOwner,
    Owner,
    UserBalance,
    UserSMSCode,
    FAQ,
    SbpPaymentIntent,
)


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
    Базовый админ для CustomUser (скрыт из меню, но доступен для ссылок)
    """
    
    def has_module_permission(self, request):
        """Скрываем из меню админки"""
        return False
    
    list_display = ('private_id', 'email', 'username', 'first_name', 'last_name', 'created_at')
    list_filter = ('groups', 'is_verified', 'is_staff', 'is_superuser', 'is_active', 'created_at')
    search_fields = ('email', 'username', 'first_name', 'last_name', 'phone_number', 'private_id')
    ordering = ('-created_at',)
    inlines = [UserBalanceInline, UserSMSCodeInline]
    
    fieldsets = (
        (None, {'fields': ('username', 'password')}),
        ('Личная информация', {'fields': ('private_id', 'first_name', 'last_name', 'email', 'phone_number', 'date_of_birth', 'avatar', 'description')}),
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
    
    readonly_fields = ('private_id', 'created_at', 'updated_at', 'date_joined', 'last_login')


@admin.register(MasterCustomUser)
class MasterCustomUserAdmin(UserAdmin):
    """
    Настройка админки для мастеров
    """
    
    def get_role_name(self, obj):
        return obj.get_role_name()
    get_role_name.short_description = 'Роль'
    
    def get_queryset(self, request):
        """Фильтруем только пользователей с группой Master"""
        qs = super().get_queryset(request)
        return qs.filter(groups__name='Master').distinct()
    
    list_display = ('private_id', 'email', 'username', 'first_name', 'last_name', 'get_role_name', 'created_at')
    list_filter = ('is_verified', 'is_staff', 'is_active', 'created_at')
    search_fields = ('email', 'username', 'first_name', 'last_name', 'phone_number')
    ordering = ('-created_at',)
    inlines = [UserBalanceInline, UserSMSCodeInline]
    
    fieldsets = (
        (None, {'fields': ('username', 'password')}),
        ('Личная информация', {'fields': ('private_id', 'first_name', 'last_name', 'email', 'phone_number', 'date_of_birth', 'avatar', 'description')}),
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


@admin.register(CarOwner)
class CarOwnerAdmin(UserAdmin):
    """
    Настройка админки для автовладельцев
    """
    
    def get_role_name(self, obj):
        return obj.get_role_name()
    get_role_name.short_description = 'Роль'
    
    def get_queryset(self, request):
        """Фильтруем только пользователей с группой Driver"""
        qs = super().get_queryset(request)
        return qs.filter(groups__name='Driver').distinct()
    
    list_display = ('private_id', 'email', 'username', 'first_name', 'last_name', 'get_role_name', 'created_at')
    list_filter = ('is_verified', 'is_staff', 'is_active', 'created_at')
    search_fields = ('email', 'username', 'first_name', 'last_name', 'phone_number')
    ordering = ('-created_at',)
    inlines = [UserBalanceInline, UserSMSCodeInline]
    
    fieldsets = (
        (None, {'fields': ('username', 'password')}),
        ('Личная информация', {'fields': ('first_name', 'last_name', 'email', 'phone_number', 'date_of_birth', 'avatar', 'description')}),
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


@admin.register(Owner)
class OwnerAdmin(UserAdmin):
    """
    Настройка админки для владельцев
    """
    
    def get_role_name(self, obj):
        return obj.get_role_name()
    get_role_name.short_description = 'Роль'
    
    def get_queryset(self, request):
        """Фильтруем только пользователей с группой Owner"""
        qs = super().get_queryset(request)
        return qs.filter(groups__name='Owner').distinct()
    
    list_display = ('private_id', 'email', 'username', 'first_name', 'last_name', 'get_role_name', 'created_at')
    list_filter = ('is_verified', 'is_staff', 'is_active', 'created_at')
    search_fields = ('email', 'username', 'first_name', 'last_name', 'phone_number')
    ordering = ('-created_at',)
    inlines = [UserBalanceInline, UserSMSCodeInline]
    
    fieldsets = (
        (None, {'fields': ('username', 'password')}),
        ('Личная информация', {'fields': ('private_id', 'first_name', 'last_name', 'email', 'phone_number', 'date_of_birth', 'avatar', 'description')}),
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


@admin.register(SbpPaymentIntent)
class SbpPaymentIntentAdmin(admin.ModelAdmin):
    """Намерения СБП: подтверждение оплаты и зачисление вручную."""

    list_display = ('id', 'user', 'amount', 'status', 'created_at', 'completed_at', 'bank_reference_short')
    list_filter = ('status', 'created_at')
    search_fields = ('id', 'user__email', 'user__username', 'bank_reference')
    readonly_fields = ('id', 'created_at', 'completed_at')
    actions = ('action_mark_paid',)

    @admin.display(description='Реф. банка')
    def bank_reference_short(self, obj):
        t = (obj.bank_reference or '')[:40]
        return f'{t}…' if len(obj.bank_reference or '') > 40 else t

    @admin.action(description='Зачислить на баланс (оплачено)')
    def action_mark_paid(self, request, queryset):
        done = 0
        skipped = 0
        for obj in queryset:
            code, _ = SbpPaymentIntent.complete_pending(
                obj.pk,
                bank_reference=f'admin:{request.user.pk}',
            )
            if code == 'ok':
                done += 1
            elif code == 'already_completed':
                skipped += 1
            else:
                skipped += 1
        self.message_user(
            request,
            f'Зачислено: {done}, пропущено (не pending / ошибка): {skipped}',
            level=messages.INFO if done else messages.WARNING,
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