# Generated by Django 2.2.4 on 2019-10-03 13:18

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('documents', '0004_newcontainers'),
        ('accounting', '0012_entrylineaccount_reference_size'),
    ]

    operations = [
        migrations.AddField(
            model_name='fiscalyear',
            name='folder',
            field=models.ForeignKey(null=True, on_delete=django.db.models.deletion.PROTECT, to='documents.FolderContainer', verbose_name='folder'),
        ),
    ]
