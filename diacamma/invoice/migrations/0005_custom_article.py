# -*- coding: utf-8 -*-
# Generated by Django 1.10.7 on 2017-04-18 15:26
from __future__ import unicode_literals

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('invoice', '0004_article_stockable'),
    ]

    operations = [
        migrations.CreateModel(
            name='ArticleCustomField',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('value', models.TextField(default='', verbose_name='value')),
            ],
            options={
                'default_permissions': [],
                'verbose_name_plural': 'custom field values',
                'verbose_name': 'custom field value',
            },
        ),
        migrations.AlterModelOptions(
            name='article',
            options={'ordering': ['reference'], 'verbose_name': 'article', 'verbose_name_plural': 'articles'},
        ),
        migrations.AddField(
            model_name='articlecustomfield',
            name='article',
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='invoice.Article', verbose_name='article'),
        ),
        migrations.AddField(
            model_name='articlecustomfield',
            name='field',
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='contacts.CustomField', verbose_name='field'),
        ),
    ]
