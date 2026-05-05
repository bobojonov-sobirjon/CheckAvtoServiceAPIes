from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('chat', '0001_initial'),
        ('order', '0013_order_master_response_deadline'),
    ]

    operations = [
        migrations.AddField(
            model_name='order',
            name='chat_room',
            field=models.OneToOneField(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='order', to='chat.chatroom', verbose_name='Чат комната'),
        ),
    ]

