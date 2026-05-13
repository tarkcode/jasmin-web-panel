# Generated migration for Fake DLR models

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0004_submitlog_charge_alter_moroutersmodel_type_and_more'),
    ]

    operations = [
        migrations.CreateModel(
            name='FakeDLRConnectorModel',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('created', models.DateTimeField(auto_now_add=True, verbose_name='Created')),
                ('modified', models.DateTimeField(auto_now=True, verbose_name='Modified')),
                ('cid', models.CharField(help_text='Unique identifier for the Fake DLR connector', max_length=30, unique=True, verbose_name='Connector ID')),
                ('name', models.CharField(help_text='Descriptive name for the connector', max_length=100, verbose_name='Name')),
                ('description', models.TextField(blank=True, help_text="Optional description of the connector's purpose", null=True, verbose_name='Description')),
                ('enabled', models.BooleanField(default=True, help_text='Whether this connector is active', verbose_name='Enabled')),
                ('success_rate', models.IntegerField(default=100, help_text='Percentage of messages marked as DELIVRD (0-100)', verbose_name='Success Rate (%)')),
                ('min_delay', models.IntegerField(default=0, help_text='Minimum delay before generating DLR', verbose_name='Minimum Delay (seconds)')),
                ('max_delay', models.IntegerField(default=15, help_text='Maximum delay before generating DLR', verbose_name='Maximum Delay (seconds)')),
                ('instant_response', models.BooleanField(default=False, help_text='Generate DLR immediately without delay', verbose_name='Instant Response')),
                ('error_code', models.CharField(default='000', help_text='Error code for delivery reports', max_length=10, verbose_name='Error Code')),
                ('total_messages', models.BigIntegerField(default=0, help_text='Total number of messages processed', verbose_name='Total Messages')),
                ('delivered_count', models.BigIntegerField(default=0, help_text='Number of messages marked as delivered', verbose_name='Delivered Count')),
                ('failed_count', models.BigIntegerField(default=0, help_text='Number of messages marked as failed', verbose_name='Failed Count')),
            ],
            options={
                'verbose_name': 'Fake DLR Connector',
                'verbose_name_plural': 'Fake DLR Connectors',
                'db_table': 'tbl_fake_dlr_connectors',
                'ordering': ['cid'],
            },
        ),
        migrations.CreateModel(
            name='FakeDLRRouteModel',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('created', models.DateTimeField(auto_now_add=True, verbose_name='Created')),
                ('modified', models.DateTimeField(auto_now=True, verbose_name='Modified')),
                ('order', models.IntegerField(help_text='Route priority order', unique=True, verbose_name='Order')),
                ('name', models.CharField(help_text='Descriptive name for the route', max_length=100, verbose_name='Name')),
                ('enabled', models.BooleanField(default=True, help_text='Whether this route is active', verbose_name='Enabled')),
                ('fake_dlr_percentage', models.IntegerField(default=30, help_text='Percentage of traffic to route to Fake DLR (0-100)', verbose_name='Fake DLR Percentage')),
                ('real_connector_cid', models.CharField(help_text='Real SMPP connector ID for actual traffic', max_length=30, verbose_name='Real Connector CID')),
                ('filter_user_uid', models.CharField(blank=True, help_text='Only apply to specific user (leave empty for all)', max_length=15, null=True, verbose_name='Filter by User UID')),
                ('filter_source_addr_pattern', models.CharField(blank=True, help_text='Regex pattern for source address filtering', max_length=100, null=True, verbose_name='Filter by Source Address Pattern')),
                ('filter_destination_addr_pattern', models.CharField(blank=True, help_text='Regex pattern for destination address filtering', max_length=100, null=True, verbose_name='Filter by Destination Address Pattern')),
                ('total_messages', models.BigIntegerField(default=0, help_text='Total messages processed by this route', verbose_name='Total Messages')),
                ('fake_dlr_messages', models.BigIntegerField(default=0, help_text='Messages routed to Fake DLR', verbose_name='Fake DLR Messages')),
                ('real_messages', models.BigIntegerField(default=0, help_text='Messages routed to real connector', verbose_name='Real Messages')),
                ('fake_dlr_connector', models.ForeignKey(help_text='Fake DLR connector to use for this route', on_delete=django.db.models.deletion.CASCADE, related_name='routes', to='core.fakedlrconnectormodel', verbose_name='Fake DLR Connector')),
            ],
            options={
                'verbose_name': 'Fake DLR Route',
                'verbose_name_plural': 'Fake DLR Routes',
                'db_table': 'tbl_fake_dlr_routes',
                'ordering': ['order'],
            },
        ),
    ]
