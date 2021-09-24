# Generated by Django 3.1.7 on 2021-09-24 08:56

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('accounting', '0015_multilink'),
    ]

    operations = [
        migrations.AlterField(
            model_name='costaccounting',
            name='year',
            field=models.ForeignKey(default=None, null=True, on_delete=django.db.models.deletion.CASCADE, to='accounting.fiscalyear', verbose_name='fiscal year'),
        ),
    ]
