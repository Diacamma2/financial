# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations
from django.conf import settings

from lucterios.framework.tools import set_locale_lang
from lucterios.CORE.models import PrintModel


def print_values(*args):
    set_locale_lang(settings.LANGUAGE_CODE)
    PrintModel().load_model('diacamma.invoice', "ArticleSituation_0001", is_default=True)
    PrintModel().load_model('diacamma.invoice', "ArticleSituation_0002", is_default=False)


class Migration(migrations.Migration):

    dependencies = [
        ('invoice', '0016_inventorydetail_inventorysheet'),
    ]

    operations = [
        migrations.RunPython(print_values),
    ]
