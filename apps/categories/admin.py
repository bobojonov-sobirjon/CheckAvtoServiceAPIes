from django.contrib import admin
from apps.categories.models import Category
from django.utils.html import mark_safe


@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    def get_icon(self, obj):
        return mark_safe(f'<img src="{obj.icon.url}" width="50" height="50" />')
    
    get_icon.short_description = 'Иконка'
    
    list_display = [ 'get_icon', 'name', 'type_category', 'service_type', 'created_at']
    list_filter = ['type_category', 'service_type', 'created_at']
    search_fields = ['name', 'service_type']
    ordering = ['-created_at']
    
    fieldsets = (
        ('Основная информация', {
            'fields': ('name', 'type_category', 'icon')
        }),
        ('Связь между категориями', {
            'fields': ('service_type',),
            'description': 'Используйте service_type для связи между by_order и by_master категориями. Например: "remont", "diagnostika", "zamena"'
        }),
    )
