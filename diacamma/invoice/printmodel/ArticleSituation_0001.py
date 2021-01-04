# -*- coding: utf-8 -*-
'''
Printmodel django module for accounting

@author: Laurent GAY
@organization: sd-libre.fr
@contact: info@sd-libre.fr
@copyright: 2021 sd-libre.fr
@license: This file is part of Lucterios.

Lucterios is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.

Lucterios is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with Lucterios.  If not, see <http://www.gnu.org/licenses/>.
'''

from __future__ import unicode_literals

from django.utils.translation import ugettext_lazy as _

from diacamma.invoice.models import ArticleSituation

name = _("listing")
kind = 0
modelname = ArticleSituation.get_long_name()
value = """210
297
15//%s//#article
45//%s//#designation
15//%s//#storagearea
10//%s//#quantity_txt
15//%s//#amount
10//%s//#mean
""" % (_('article'), _('designation'), _('Area'), _('Quantity'), _('Amount'), _('Mean price'))
