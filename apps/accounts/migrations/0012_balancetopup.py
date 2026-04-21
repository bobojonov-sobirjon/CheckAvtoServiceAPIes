# Generated manually

from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('accounts', '0011_alter_carowner_options_alter_faq_options_and_more'),
    ]

    operations = [
        migrations.CreateModel(
            name='BalanceTopUp',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('order_number', models.CharField(max_length=36, unique=True, verbose_name='Номер заказа (мерчант)')),
                ('alfa_order_id', models.CharField(blank=True, default='', max_length=64, verbose_name='orderId шлюза')),
                ('amount', models.DecimalField(decimal_places=2, max_digits=12, verbose_name='Сумма, ₽')),
                ('status', models.CharField(default='pending', max_length=20, verbose_name='Статус')),
                ('error_message', models.TextField(blank=True, default='', verbose_name='Ошибка')),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('completed_at', models.DateTimeField(blank=True, null=True)),
                ('user', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='balance_top_ups', to=settings.AUTH_USER_MODEL, verbose_name='Пользователь')),
            ],
            options={
                'verbose_name': 'Пополнение баланса',
                'verbose_name_plural': 'Пополнения баланса',
                'ordering': ['-created_at'],
            },
        ),
    ]
