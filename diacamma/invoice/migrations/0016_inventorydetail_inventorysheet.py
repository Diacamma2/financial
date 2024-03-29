# Generated by Django 3.0.9 on 2020-08-17 12:13

import django.core.validators
from django.db import migrations, models
import django.db.models.deletion
import django_fsm


class Migration(migrations.Migration):

    dependencies = [
        ('invoice', '0015_articles_indexes'),
    ]

    operations = [
        migrations.CreateModel(
            name='InventorySheet',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('date', models.DateField(verbose_name='date')),
                ('comment', models.TextField(verbose_name='comment')),
                ('status', django_fsm.FSMIntegerField(choices=[(0, 'building'), (1, 'valid')], db_index=True, default=0, verbose_name='status')),
                ('stockexit', models.ForeignKey(null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='exit_storagesheet', to='invoice.StorageSheet', verbose_name='stock exit')),
                ('stockreceipt', models.ForeignKey(null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='receipt_storagesheet', to='invoice.StorageSheet', verbose_name='stock receipt')),
                ('storagearea', models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, to='invoice.StorageArea', verbose_name='storage area')),
            ],
            options={
                'verbose_name': 'inventory sheet',
                'verbose_name_plural': 'inventory sheets',
                'ordering': ['-date', 'status'],
            },
        ),
        migrations.CreateModel(
            name='InventoryDetail',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('quantity', models.DecimalField(decimal_places=3, default=None, max_digits=12, null=True, validators=[django.core.validators.MinValueValidator(0.0), django.core.validators.MaxValueValidator(9999999.999)], verbose_name='counted quantity')),
                ('article', models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, to='invoice.Article', verbose_name='article')),
                ('inventorysheet', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='invoice.InventorySheet', verbose_name='inventory sheet')),
            ],
            options={
                'verbose_name': 'inventory detail',
                'verbose_name_plural': 'inventory details',
                'default_permissions': [],
            },
        ),
    ]
