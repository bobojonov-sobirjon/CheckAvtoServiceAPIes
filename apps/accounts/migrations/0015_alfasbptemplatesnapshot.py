# Generated manually

import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('accounts', '0014_sbppaymentintent'),
    ]

    operations = [
        migrations.CreateModel(
            name='AlfaSbpTemplateSnapshot',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('template_id', models.CharField(max_length=40, verbose_name='templateId шлюза')),
                ('gateway_response', models.JSONField(verbose_name='Ответ шлюза (create)')),
                ('generated_meta', models.JSONField(blank=True, null=True, verbose_name='Поля quick-create')),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('user', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='alfa_sbp_template_snapshots', to=settings.AUTH_USER_MODEL, verbose_name='Пользователь')),
            ],
            options={
                'verbose_name': 'Снимок шаблона СБП (Альфа)',
                'verbose_name_plural': 'Снимки шаблонов СБП',
                'ordering': ['-created_at'],
            },
        ),
        migrations.AddConstraint(
            model_name='alfasbptemplatesnapshot',
            constraint=models.UniqueConstraint(fields=('user', 'template_id'), name='alfa_sbp_snapshot_user_template'),
        ),
    ]
