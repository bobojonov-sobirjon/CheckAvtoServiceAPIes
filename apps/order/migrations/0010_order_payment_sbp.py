# Generated manually

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('accounts', '0015_alfasbptemplatesnapshot'),
        ('order', '0009_review_userrating'),
    ]

    operations = [
        migrations.AddField(
            model_name='order',
            name='payment_status',
            field=models.CharField(
                choices=[('none', 'Нет'), ('pending', 'Ожидает оплаты'), ('paid', 'Оплачено')],
                default='none',
                help_text='После complete: pending — QR для клиента; paid — webhook подтвердил оплату',
                max_length=20,
                verbose_name='Оплата (СБП)',
            ),
        ),
        migrations.AddField(
            model_name='order',
            name='sbp_payment_intent',
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name='orders',
                to='accounts.sbppaymentintent',
                verbose_name='СБП intent оплаты заказа',
            ),
        ),
    ]
