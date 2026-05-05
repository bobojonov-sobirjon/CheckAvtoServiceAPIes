from django.contrib import admin
from apps.categories.models import Category
from django.utils.html import mark_safe


@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    def get_icon(self, obj):
        if obj.icon:
            return mark_safe(f'<img src="{obj.icon.url}" width="50" height="50" />')
        return '-'
    
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
            'description': mark_safe(
                'Поле <b>«Тип услуги»</b> помогает группировать похожие категории и связывать категории '
                'для <b>заказов</b> (by_order) с категориями для <b>мастеров</b> (by_master).<br><br>'
                '<b>Как заполнять:</b> укажите короткое название услуги в одном стиле (лучше по‑русски).<br>'
                '<b>Примеры:</b> «Ремонт», «Диагностика», «Замена масла», «Шиномонтаж», «Электрика».<br><br>'
                'Если связь не нужна — оставьте поле пустым.'
            )
        }),
    )
