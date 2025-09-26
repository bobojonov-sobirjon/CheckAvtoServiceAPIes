from site import venv
from django.db import models
from apps.accounts.models import CustomUser
from django.core.exceptions import ValidationError


class Car(models.Model):
    class TypeCar(models.TextChoices):
        Passengercar = 'Легковой', 'Легковой'
        Motorcycle = 'Мото', 'Мото'
        Truck = 'Грузовой', 'Грузовой'
        Bus = 'Автобус', 'Автобус'
        Technique = 'Техника', 'Техника'
        Hydro = 'Гидро', 'Гидро'

    type_car = models.CharField(max_length=255, null=True, blank=True, verbose_name='Тип машины', choices=TypeCar.choices)
    
    brand = models.CharField(max_length=255, null=True, blank=True, verbose_name='Марка машины')
    model = models.CharField(max_length=255, null=True, blank=True, verbose_name='Модель машины')
    year = models.IntegerField(null=True, blank=True, verbose_name='Год выпуска машины')
    
    user = models.ForeignKey(CustomUser, on_delete=models.CASCADE, null=True, blank=True, verbose_name='Пользователь')
    
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='Дата создания')
    updated_at = models.DateTimeField(auto_now=True, verbose_name='Дата обновления')

    def __str__(self):
        return f"{self.brand} {self.model} ({self.year})" if self.brand and self.model else f"Car {self.id}"

    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)
        
    class Meta:
        verbose_name = 'Машина'
        verbose_name_plural = 'Машины'
        ordering = ['-created_at']
