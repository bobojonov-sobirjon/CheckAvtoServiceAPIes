# Generated manually

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('accounts', '0012_balancetopup'),
    ]

    operations = [
        migrations.DeleteModel(name='BalanceTopUp'),
    ]
