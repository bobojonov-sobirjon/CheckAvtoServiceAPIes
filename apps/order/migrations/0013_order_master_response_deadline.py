from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('order', '0012_order_alfa_form_url'),
    ]

    operations = [
        migrations.AddField(
            model_name='order',
            name='master_response_deadline',
            field=models.DateTimeField(blank=True, db_index=True, help_text='Если мастер не ответит до этого времени, заказ автоматически отклоняется', null=True, verbose_name='Дедлайн ответа мастера'),
        ),
    ]

