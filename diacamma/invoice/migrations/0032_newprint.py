# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations
from django.db.models import deletion
from django.conf import settings

from lucterios.framework.tools import set_locale_lang
from lucterios.CORE.models import PrintModel


def newprint_values(*args):
    set_locale_lang(settings.LANGUAGE_CODE)
    PrintModel().load_model('diacamma.invoice', "Bill_0003", is_default=False)


class Migration(migrations.Migration):

    dependencies = [
        ('accounting', '0019_fiscalyear_prefix'),
        ('invoice', '0031_multiprice'),
    ]

    operations = [
        migrations.RunPython(newprint_values),
    ]
