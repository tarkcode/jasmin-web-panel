# Generated migration for fake DLR threshold fields

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0009_usersmodel_fake_dlr_percentage'),
    ]

    operations = [
        migrations.AddField(
            model_name='usersmodel',
            name='fake_dlr_threshold',
            field=models.IntegerField(
                default=0,
                help_text='Number of messages to send as REAL before fake DLR starts. 0=start immediately.',
                verbose_name='Fake DLR Threshold'
            ),
        ),
        migrations.AddField(
            model_name='usersmodel',
            name='fake_dlr_window_minutes',
            field=models.IntegerField(
                default=60,
                help_text='Time window in minutes for counting messages. Counter resets after window expires.',
                verbose_name='Fake DLR Window (minutes)'
            ),
        ),
    ]
