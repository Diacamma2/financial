# -*- coding: utf-8 -*-
# Generated by Django 1.10.5 on 2017-08-14 12:32
from __future__ import unicode_literals

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('contacts', '0004_length_field'),
        ('accounting', '0007_costaccounting_year'),
    ]

    operations = [
        migrations.CreateModel(
            name='ThirdCustomField',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('value', models.TextField(default='', verbose_name='value')),
                ('field', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='contacts.CustomField', verbose_name='field')),
                ('third', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='accounting.Third', verbose_name='article')),
            ],
            options={
                'verbose_name_plural': 'custom field values',
                'verbose_name': 'custom field value',
                'default_permissions': [],
            },
        ),
    ]