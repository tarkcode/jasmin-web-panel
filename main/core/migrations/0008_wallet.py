from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0007_route_assignment'),
    ]

    operations = [
        migrations.CreateModel(
            name='Wallet',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('created', models.DateTimeField(auto_now_add=True)),
                ('modified', models.DateTimeField(auto_now=True)),
                ('uid', models.CharField(max_length=64, unique=True, verbose_name='User')),
                ('currency', models.CharField(default='USD', max_length=8, verbose_name='Currency')),
            ],
            options={
                'verbose_name': 'Wallet',
                'verbose_name_plural': 'Wallets',
                'db_table': 'tbl_wallets',
                'ordering': ['-modified'],
            },
        ),
        migrations.CreateModel(
            name='WalletTransaction',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('created', models.DateTimeField(auto_now_add=True)),
                ('modified', models.DateTimeField(auto_now=True)),
                ('txn_type', models.CharField(choices=[('credit', 'Credit'), ('debit', 'Debit'), ('refund', 'Refund'), ('adjustment', 'Adjustment'), ('sms_charge', 'SMS charge')], max_length=16, verbose_name='Type')),
                ('amount', models.DecimalField(decimal_places=5, default=0, max_digits=14, verbose_name='Amount')),
                ('balance_after', models.DecimalField(blank=True, decimal_places=5, max_digits=14, null=True, verbose_name='Balance After')),
                ('description', models.CharField(blank=True, max_length=255, verbose_name='Description')),
                ('reference', models.CharField(blank=True, max_length=64, verbose_name='Reference')),
                ('created_by', models.CharField(blank=True, max_length=64, verbose_name='By')),
                ('wallet', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='transactions', to='core.wallet')),
            ],
            options={
                'verbose_name': 'Wallet Transaction',
                'verbose_name_plural': 'Wallet Transactions',
                'db_table': 'tbl_wallet_transactions',
                'ordering': ['-created'],
            },
        ),
        migrations.AddIndex(
            model_name='wallettransaction',
            index=models.Index(fields=['reference'], name='wallet_txn_ref_idx'),
        ),
    ]
