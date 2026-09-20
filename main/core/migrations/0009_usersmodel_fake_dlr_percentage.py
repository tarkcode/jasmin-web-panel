# Generated migration for adding fake_dlr_percentage to UsersModel

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0008_wallet'),
    ]

    operations = [
        migrations.AddField(
            model_name='usersmodel',
            name='fake_dlr_percentage',
            field=models.IntegerField(
                default=0,
                help_text='Percentage of messages to route to Fake DLR (0-100). 0=all real, 20=20% fake delivery reports, 100=all fake.',
                verbose_name='Fake DLR %'
            ),
        ),
    ]
