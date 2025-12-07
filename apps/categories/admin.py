from django.contrib import admin
from apps.categories.models import Category
from django.utils.html import mark_safe


@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    def get_icon(self, obj):
        return mark_safe(f'<img src="{obj.icon.url}" width="50" height="50" />')
    
    get_icon.short_description = 'Иконка'
    
    list_display = [ 'get_icon', 'name', 'type_category', 'created_at', 'updated_at']
    list_filter = ['type_category', 'created_at']
    search_fields = ['name']
    ordering = ['-created_at']
