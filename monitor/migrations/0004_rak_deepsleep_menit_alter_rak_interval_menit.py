# Generated migration for deepsleep_menit field

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('monitor', '0003_apikey_rak_foto_alter_rak_api_key'),
    ]

    operations = [
        migrations.AddField(
            model_name='rak',
            name='deepsleep_menit',
            field=models.IntegerField(
                choices=[(5, '5 Menit'), (10, '10 Menit'), (15, '15 Menit'), (30, '30 Menit'), (60, '1 Jam')],
                default=30
            ),
        ),
        migrations.RemoveField(
            model_name='rak',
            name='interval_menit',
        ),
    ]
