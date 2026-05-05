from django.db import models
from apps.categories.manager.managers import ByMasterManager, ByCarManager, ByOrderManager


class Category(models.Model):
    
    class TypeCategory(models.TextChoices):
        BY_MASTER = 'by_master', 'По категории мастера'
        BY_CAR = 'by_car', 'По категории машины'
        BY_ORDER = 'by_order', 'По категории заказа'
    
    name = models.CharField(max_length=255, verbose_name='Название категории')
    type_category = models.CharField(max_length=255, verbose_name='Тип категории', choices=TypeCategory.choices)
    service_type = models.CharField(
        max_length=100,
        blank=True,
        default='',
        verbose_name='Тип услуги',
        help_text=(
            'Нужно для группировки похожих категорий и связи категорий для заказов (by_order) '
            'с категориями для мастеров (by_master). '
            'Заполняйте коротким названием услуги в одном стиле. '
            'Примеры: «Ремонт», «Диагностика», «Замена масла», «Шиномонтаж», «Электрика». '
            'Если не используется — оставьте пустым.'
        )
    )
    icon = models.FileField(upload_to='categories/icons/', verbose_name='Иконка категории', null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='Дата создания')
    updated_at = models.DateTimeField(auto_now=True, verbose_name='Дата обновления')
    
    objects = models.Manager()
    by_master = ByMasterManager()
    by_car = ByCarManager()
    by_order = ByOrderManager()
    
    class Meta:
        verbose_name = 'Категория'
        verbose_name_plural = 'Категории'
        ordering = ['-created_at']
    
    def __str__(self):
        return self.name