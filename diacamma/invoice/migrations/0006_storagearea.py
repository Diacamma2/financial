# -*- coding: utf-8 -*-
# Generated by Django 1.10.7 on 2017-05-02 15:03
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('invoice', '0005_custom_article'),
    ]

    operations = [
        migrations.CreateModel(
            name='StorageArea',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(max_length=50, verbose_name='name')),
                ('designation', models.TextField(verbose_name='designation')),
            ],
            options={
                'verbose_name': 'Storage area',
                'default_permissions': [],
                'verbose_name_plural': 'Storage areas',
            },
        ),
    ]
