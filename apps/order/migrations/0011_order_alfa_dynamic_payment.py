# Generated manually

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('order', '0010_order_payment_sbp'),
    ]

    operations = [
        migrations.AddField(
            model_name='order',
            name='alfa_order_id',
            field=models.CharField(
                blank=True,
                default='',
                help_text='orderId из payment/rest/register.do для getOrderStatusExtended',
                max_length=64,
                verbose_name='Alfa orderId (dynamic)',
            ),
        ),
        migrations.AddField(
            model_name='order',
            name='alfa_order_number',
            field=models.CharField(
                blank=True,
                default='',
                help_text='orderNumber отправленный в register.do (обычно order_id или intent_id)',
                max_length=64,
                verbose_name='Alfa orderNumber (dynamic)',
            ),
        ),
    ]

