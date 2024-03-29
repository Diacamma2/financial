# -*- coding: utf-8 -*-
# Generated by Django 1.9.2 on 2016-06-02 12:49
from __future__ import unicode_literals

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('payoff', '0002_payoffmode'),
    ]

    operations = [
        migrations.CreateModel(
            name='PaymentMethod',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('paytype', models.IntegerField(choices=[(0, 'transfer'), (1, 'cheque'), (2, 'PayPal'), (3, 'online')], db_index=True, default=0, verbose_name='type')),
                ('extra_data', models.TextField(verbose_name='data')),
                ('bank_account', models.ForeignKey(default=None, on_delete=django.db.models.deletion.PROTECT, to='payoff.BankAccount', verbose_name='bank account')),
            ],
            options={
                'verbose_name': 'payment method',
                'default_permissions': [],
                'ordering': ['id'],
                'verbose_name_plural': 'payment methods',
            },
        ),
    ]
