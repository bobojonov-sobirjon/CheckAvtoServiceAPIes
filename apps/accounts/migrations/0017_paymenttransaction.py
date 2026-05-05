from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('order', '0014_order_chat_room'),
        ('master', '0004_remove_master_completed_orders_and_more'),
        ('accounts', '0016_userdevice'),
    ]

    operations = [
        migrations.CreateModel(
            name='PaymentTransaction',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('kind', models.CharField(choices=[('order', 'Оплата заказа'), ('master_topup', 'Пополнение баланса мастера')], max_length=32, verbose_name='Тип')),
                ('status', models.CharField(choices=[('pending', 'Ожидает оплаты'), ('paid', 'Оплачено'), ('failed', 'Ошибка')], db_index=True, default='pending', max_length=20)),
                ('amount', models.DecimalField(decimal_places=2, max_digits=12, verbose_name='Сумма, ₽')),
                ('alfa_order_id', models.CharField(blank=True, db_index=True, default='', max_length=64)),
                ('alfa_order_number', models.CharField(blank=True, db_index=True, default='', max_length=64)),
                ('form_url', models.TextField(blank=True, default='')),
                ('gateway_last_response', models.JSONField(blank=True, null=True, verbose_name='Последний ответ шлюза')),
                ('last_checked_at', models.DateTimeField(blank=True, null=True)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('beneficiary', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='beneficiary_payments', to='accounts.customuser', verbose_name='Получатель')),
                ('initiated_by', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='initiated_payments', to='accounts.customuser', verbose_name='Инициатор')),
                ('intent', models.OneToOneField(on_delete=django.db.models.deletion.CASCADE, related_name='payment_tx', to='accounts.sbppaymentintent', verbose_name='Intent')),
                ('master', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='payment_transactions', to='master.master', verbose_name='Мастер')),
                ('order', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='payment_transactions', to='order.order', verbose_name='Заказ')),
            ],
            options={
                'verbose_name': 'Платёж',
                'verbose_name_plural': 'Платежи',
                'ordering': ['-created_at'],
            },
        ),
        migrations.AddIndex(
            model_name='paymenttransaction',
            index=models.Index(fields=['status', '-created_at'], name='accounts_pa_status_0bcd2d_idx'),
        ),
        migrations.AddIndex(
            model_name='paymenttransaction',
            index=models.Index(fields=['kind', 'status', '-created_at'], name='accounts_pa_kind_7b0c5d_idx'),
        ),
    ]

