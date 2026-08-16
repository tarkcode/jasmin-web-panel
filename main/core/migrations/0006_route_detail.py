from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0005_fake_dlr_models'),
    ]

    operations = [
        migrations.CreateModel(
            name='RouteDetail',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('created', models.DateTimeField(auto_now_add=True)),
                ('modified', models.DateTimeField(auto_now=True)),
                ('name', models.CharField(help_text='A label for this route', max_length=100, verbose_name='Route Name')),
                ('country', models.CharField(blank=True, help_text='Destination country', max_length=64, verbose_name='Country')),
                ('route_type', models.CharField(choices=[('transactional', 'Transactional'), ('promotional', 'Promotional'), ('otp', 'OTP'), ('other', 'Other')], default='transactional', max_length=20, verbose_name='Route Type')),
                ('smpp_connector', models.CharField(help_text='The connector (cid) that supplies this route', max_length=64, verbose_name='SMPP Connector / Provider')),
                ('buy_price', models.DecimalField(decimal_places=5, default=0, max_digits=12, verbose_name='Buy Price')),
                ('currency', models.CharField(default='USD', max_length=8, verbose_name='Currency')),
                ('tps', models.IntegerField(default=0, help_text='Messages per second allowed on this route', verbose_name='TPS')),
                ('status', models.CharField(choices=[('active', 'Active'), ('inactive', 'Inactive'), ('testing', 'Testing')], default='active', max_length=12, verbose_name='Status')),
            ],
            options={
                'verbose_name': 'Route Detail',
                'verbose_name_plural': 'Route Details',
                'db_table': 'tbl_route_details',
                'ordering': ['-created'],
            },
        ),
    ]
