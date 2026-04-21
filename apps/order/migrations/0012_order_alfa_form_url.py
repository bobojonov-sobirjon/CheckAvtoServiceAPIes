# Generated manually

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('order', '0011_order_alfa_dynamic_payment'),
    ]

    operations = [
        migrations.AddField(
            model_name='order',
            name='alfa_form_url',
            field=models.TextField(
                blank=True,
                default='',
                help_text='formUrl из payment/rest/register.do (ссылка для оплаты)',
                verbose_name='Alfa formUrl (dynamic)',
            ),
        ),
    ]

