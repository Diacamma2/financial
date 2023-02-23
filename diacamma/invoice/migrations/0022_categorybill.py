# Generated by Django 3.2.16 on 2023-02-02 10:04

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('CORE', '0006_preference'),
        ('invoice', '0021_bill_order'),
    ]

    operations = [
        migrations.CreateModel(
            name='CategoryBill',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(max_length=100, verbose_name='name')),
                ('designation', models.TextField(verbose_name='designation')),
                ('titles', models.TextField(verbose_name='titles')),
                ('emailsubject', models.CharField(max_length=100, verbose_name='email subject')),
                ('emailmessage', models.TextField(verbose_name='email message')),
                ('printmodel', models.ForeignKey(default=None, null=True, on_delete=django.db.models.deletion.SET_NULL, to='CORE.printmodel', verbose_name='print patern')),
                ('is_default', models.BooleanField(default=False, verbose_name='default')),
                ('special_numbering', models.BooleanField(default=False, verbose_name='special_numbering')),
                ('prefix_numbering', models.CharField(verbose_name='prefix numbering', max_length=20, blank=True)),
                ('workflow_order', models.IntegerField(verbose_name='workflow_order', choices=((0, 'on choice'), (1, 'always order'), (2, 'never order')), null=False, default=0, db_index=True)),
            ],
            options={
                'verbose_name': 'Category',
                'verbose_name_plural': 'Categories',
                'default_permissions': [],
            },
        ),
        migrations.AddField(
            model_name='bill',
            name='categoryBill',
            field=models.ForeignKey(default=None, null=True, on_delete=django.db.models.deletion.SET_NULL, to='invoice.categorybill', verbose_name='category'),
        ),
    ]
