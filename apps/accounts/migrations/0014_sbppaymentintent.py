# Generated manually

import uuid

import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('accounts', '0013_delete_balancetopup'),
    ]

    operations = [
        migrations.CreateModel(
            name='SbpPaymentIntent',
            fields=[
                ('id', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ('amount', models.DecimalField(decimal_places=2, max_digits=12, verbose_name='Сумма, ₽')),
                ('status', models.CharField(default='pending', max_length=20, verbose_name='Статус')),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('completed_at', models.DateTimeField(blank=True, null=True)),
                ('bank_reference', models.CharField(blank=True, default='', max_length=256, verbose_name='Референс банка')),
                ('user', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='sbp_intents', to=settings.AUTH_USER_MODEL, verbose_name='Пользователь')),
            ],
            options={
                'verbose_name': 'СБП: намерение оплаты',
                'verbose_name_plural': 'СБП: намерения оплаты',
                'ordering': ['-created_at'],
            },
        ),
        migrations.AddIndex(
            model_name='sbppaymentintent',
            index=models.Index(fields=['user', 'status', '-created_at'], name='accounts_sb_user_id_2a8fbd_idx'),
        ),
    ]
