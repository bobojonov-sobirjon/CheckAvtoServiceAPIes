from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('accounts', '0015_alfasbptemplatesnapshot'),
    ]

    operations = [
        migrations.CreateModel(
            name='UserDevice',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('device_token', models.TextField(verbose_name='FCM token')),
                ('device_type', models.CharField(choices=[('android', 'Android'), ('ios', 'iOS'), ('web', 'Web')], default='android', max_length=20, verbose_name='Тип устройства')),
                ('is_active', models.BooleanField(default=True, verbose_name='Активен')),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('user', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='devices', to='accounts.customuser', verbose_name='Пользователь')),
            ],
            options={
                'verbose_name': 'Устройство пользователя',
                'verbose_name_plural': 'Устройства пользователей',
                'ordering': ['-updated_at'],
            },
        ),
        migrations.AddIndex(
            model_name='userdevice',
            index=models.Index(fields=['user', 'is_active', '-updated_at'], name='accounts_us_user_id_a540cd_idx'),
        ),
        migrations.AddConstraint(
            model_name='userdevice',
            constraint=models.UniqueConstraint(fields=('user', 'device_token'), name='uniq_user_device_token'),
        ),
    ]

