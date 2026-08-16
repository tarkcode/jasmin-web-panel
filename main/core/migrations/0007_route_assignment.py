from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0006_route_detail'),
    ]

    operations = [
        migrations.CreateModel(
            name='RouteAssignment',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('created', models.DateTimeField(auto_now_add=True)),
                ('modified', models.DateTimeField(auto_now=True)),
                ('uid', models.CharField(help_text='Jasmin user this route is sold to', max_length=64, verbose_name='Customer (User)')),
                ('sell_price', models.DecimalField(decimal_places=5, default=0, max_digits=12, verbose_name='Sell Price')),
                ('status', models.CharField(choices=[('active', 'Active'), ('inactive', 'Inactive')], default='active', max_length=12, verbose_name='Status')),
                ('notes', models.CharField(blank=True, max_length=255, verbose_name='Notes')),
                ('route', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='assignments', to='core.routedetail', verbose_name='Route')),
            ],
            options={
                'verbose_name': 'Route Assignment',
                'verbose_name_plural': 'Route Assignments',
                'db_table': 'tbl_route_assignments',
                'ordering': ['-created'],
                'unique_together': {('route', 'uid')},
            },
        ),
    ]
