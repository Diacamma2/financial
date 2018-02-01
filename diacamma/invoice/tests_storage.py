# -*- coding: utf-8 -*-
'''
diacamma.invoice tests package

@author: Laurent GAY
@organization: sd-libre.fr
@contact: info@sd-libre.fr
@copyright: 2017 sd-libre.fr
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
from shutil import rmtree

from lucterios.framework.xfergraphic import XferContainerAcknowledge
from lucterios.framework.filetools import get_user_dir
from lucterios.framework.test import LucteriosTest

from diacamma.invoice.test_tools import InvoiceTest, default_area,\
    default_articles, insert_storage
from diacamma.accounting.test_tools import initial_thirds, default_compta
from diacamma.payoff.test_tools import default_bankaccount
from diacamma.invoice.views import ArticleShow, BillAddModify, DetailAddModify,\
    BillShow, BillTransition, ArticleList
from diacamma.invoice.views_storage import StorageSheetList,\
    StorageSheetAddModify, StorageSheetShow, StorageDetailAddModify,\
    StorageSheetTransition, StorageDetailImport, StorageDetailDel
from diacamma.payoff.views import SupportingThirdValid
from django.utils import six
from _io import StringIO


class StorageTest(InvoiceTest):

    def setUp(self):
        self.xfer_class = XferContainerAcknowledge
        initial_thirds()
        LucteriosTest.setUp(self)
        default_compta()
        default_bankaccount()
        rmtree(get_user_dir(), True)
        default_area()
        default_articles(with_storage=True)

    def test_receipt(self):
        self.factory.xfer = ArticleShow()
        self.calljson('/diacamma.invoice/articleShow', {'article': '3'}, False)
        self.assert_observer('core.custom', 'diacamma.invoice', 'articleShow')
        self.assert_count_equal('', 11)
        self.assert_json_equal('LABELFORM', 'reference', "ABC3")

        self.factory.xfer = ArticleShow()
        self.calljson('/diacamma.invoice/articleShow', {'article': '1'}, False)
        self.assert_observer('core.custom', 'diacamma.invoice', 'articleShow')
        self.assert_count_equal('', 16)
        self.assert_json_equal('LABELFORM', 'reference', "ABC1")
        self.assert_grid_equal('storage', {"area": "Lieu de stockage", "qty": "Quantité", "amount": "Montant", "mean": "Prix moyen"}, 1)
        self.assert_json_equal('', 'storage/@0/area', "{[b]}Total{[/b]}")
        self.assert_json_equal('', 'storage/@0/qty', "{[b]}0.0{[/b]}")
        self.assert_json_equal('', 'storage/@0/amount', "{[b]}0.00€{[/b]}")
        self.assert_json_equal('', 'storage/@0/mean', '')
        self.assert_count_equal('moving', 0)

        self.factory.xfer = StorageSheetList()
        self.calljson('/diacamma.invoice/storageSheetList', {}, False)
        self.assert_observer('core.custom', 'diacamma.invoice', 'storageSheetList')
        self.assert_count_equal('storagesheet', 0)

        self.factory.xfer = StorageSheetAddModify()
        self.calljson('/diacamma.invoice/storageSheetAddModify', {}, False)
        self.assert_observer('core.custom', 'diacamma.invoice', 'storageSheetAddModify')
        self.assert_count_equal('', 8)

        self.factory.xfer = StorageSheetAddModify()
        self.calljson('/diacamma.invoice/storageSheetAddModify',
                      {'sheet_type': 0, 'date': '2014-04-01', 'SAVE': 'YES', 'storagearea': 1, 'comment': "arrivage massif!"}, False)
        self.assert_observer('core.acknowledge', 'diacamma.invoice', 'storageSheetAddModify')
        self.assertEqual(self.response_json['action']['id'], "diacamma.invoice/storageSheetShow")
        self.assertEqual(len(self.response_json['action']['params']), 1)
        self.assertEqual(self.response_json['action']['params']['storagesheet'], 1)

        self.factory.xfer = StorageSheetShow()
        self.calljson('/diacamma.invoice/storageSheetShow', {'storagesheet': "1"}, False)
        self.assert_observer('core.custom', 'diacamma.invoice', 'storageSheetShow')
        self.assert_count_equal('', 11)
        self.assert_json_equal('LABELFORM', 'sheet_type', "réception de stock")
        self.assert_json_equal('LABELFORM', 'status', "en création")
        self.assert_json_equal('LABELFORM', 'storagearea', "Lieu 1")
        self.assert_count_equal('storagedetail', 0)
        self.assert_count_equal('#storagedetail/actions', 4)

        self.factory.xfer = StorageDetailAddModify()
        self.calljson('/diacamma.invoice/storageDetailAddModify', {'storagesheet': "1"}, False)
        self.assert_observer('core.custom', 'diacamma.invoice', 'storageDetailAddModify')
        self.assert_count_equal('', 5)
        self.assert_json_equal('FLOAT', 'quantity', 1.0)
        self.assert_json_equal('', '#quantity/min', 0.0)
        self.assert_json_equal('', '#quantity/max', 9999999.99)
        self.assert_json_equal('', '#quantity/prec', 2)

        self.factory.xfer = StorageDetailAddModify()
        self.calljson('/diacamma.invoice/storageDetailAddModify', {'storagesheet': "1", "article": 1}, False)
        self.assert_observer('core.custom', 'diacamma.invoice', 'storageDetailAddModify')
        self.assert_count_equal('', 5)
        self.assert_json_equal('FLOAT', 'quantity', 1.0)
        self.assert_json_equal('', '#quantity/min', 0.0)
        self.assert_json_equal('', '#quantity/max', 9999999.99)
        self.assert_json_equal('', '#quantity/prec', 2)

        self.factory.xfer = StorageDetailAddModify()
        self.calljson('/diacamma.invoice/storageDetailAddModify', {'storagesheet': "1", "article": 3}, False)
        self.assert_observer('core.custom', 'diacamma.invoice', 'storageDetailAddModify')
        self.assert_count_equal('', 5)
        self.assert_json_equal('FLOAT', 'quantity', 1.0)
        self.assert_json_equal('', '#quantity/min', 0.0)
        self.assert_json_equal('', '#quantity/max', 9999999.99)
        self.assert_json_equal('', '#quantity/prec', 0)

        self.factory.xfer = StorageDetailAddModify()
        self.calljson('/diacamma.invoice/storageDetailAddModify', {'storagesheet': "1", 'SAVE': 'YES', "article": 1, "price": 7.25, "quantity": 10}, False)
        self.assert_observer('core.acknowledge', 'diacamma.invoice', 'storageDetailAddModify')

        self.factory.xfer = StorageDetailAddModify()
        self.calljson('/diacamma.invoice/storageDetailAddModify', {'storagesheet': "1", 'SAVE': 'YES', "article": 4, "price": 1.00, "quantity": 25}, False)
        self.assert_observer('core.acknowledge', 'diacamma.invoice', 'storageDetailAddModify')

        self.factory.xfer = StorageSheetShow()
        self.calljson('/diacamma.invoice/storageSheetShow', {'storagesheet': "1"}, False)
        self.assert_observer('core.custom', 'diacamma.invoice', 'storageSheetShow')
        self.assert_count_equal('', 11)
        self.assert_json_equal('LABELFORM', 'status', "en création")
        self.assert_count_equal('storagedetail', 2)
        self.assert_json_equal('', 'storagedetail/@0/article', "ABC1")
        self.assert_json_equal('', 'storagedetail/@0/price_txt', "7.25€")
        self.assert_json_equal('', 'storagedetail/@0/quantity_txt', "10.00")
        self.assert_json_equal('', 'storagedetail/@1/article', "ABC4")
        self.assert_json_equal('', 'storagedetail/@1/price_txt', "1.00€")
        self.assert_json_equal('', 'storagedetail/@1/quantity_txt', "25.00")

        self.factory.xfer = ArticleShow()
        self.calljson('/diacamma.invoice/articleShow', {'article': '1'}, False)
        self.assert_observer('core.custom', 'diacamma.invoice', 'articleShow')
        self.assert_count_equal('', 16)
        self.assert_json_equal('LABELFORM', 'reference', "ABC1")
        self.assert_count_equal('storage', 1)
        self.assert_count_equal('moving', 0)

        self.factory.xfer = StorageSheetTransition()
        self.calljson('/diacamma.invoice/storageSheetTransition',
                      {'CONFIRME': 'YES', 'storagesheet': 1, 'TRANSITION': 'valid'}, False)
        self.assert_observer('core.acknowledge', 'diacamma.invoice', 'storageSheetTransition')

        self.factory.xfer = StorageSheetShow()
        self.calljson('/diacamma.invoice/storageSheetShow', {'storagesheet': "1"}, False)
        self.assert_observer('core.custom', 'diacamma.invoice', 'storageSheetShow')
        self.assert_count_equal('', 10)
        self.assert_json_equal('LABELFORM', 'status', "validé")
        self.assert_count_equal('storagedetail', 2)

        self.factory.xfer = ArticleShow()
        self.calljson('/diacamma.invoice/articleShow', {'article': '1'}, False)
        self.assert_observer('core.custom', 'diacamma.invoice', 'articleShow')
        self.assert_count_equal('', 16)
        self.assert_json_equal('LABELFORM', 'reference', "ABC1")
        self.assert_count_equal('storage', 2)
        self.assert_json_equal('', 'storage/@0/area', "Lieu 1")
        self.assert_json_equal('', 'storage/@0/qty', "10.0")
        self.assert_json_equal('', 'storage/@0/amount', "72.50€")
        self.assert_json_equal('', 'storage/@0/mean', "7.25€")
        self.assert_json_equal('', 'storage/@1/area', "{[b]}Total{[/b]}")
        self.assert_json_equal('', 'storage/@1/qty', "{[b]}10.0{[/b]}")
        self.assert_json_equal('', 'storage/@1/amount', "{[b]}72.50€{[/b]}")

        self.assert_count_equal('moving', 1)
        self.assert_json_equal('', 'moving/@0/storagesheet.date', "2014-04-01")
        self.assert_json_equal('', 'moving/@0/storagesheet.comment', "arrivage massif!")
        self.assert_json_equal('', 'moving/@0/quantity', "10.00")

        self.factory.xfer = StorageSheetList()
        self.calljson('/diacamma.invoice/storageSheetList', {'status': -1}, False)
        self.assert_observer('core.custom', 'diacamma.invoice', 'storageSheetList')
        self.assert_count_equal('storagesheet', 1)

    def test_exit(self):
        self.factory.xfer = ArticleShow()
        self.calljson('/diacamma.invoice/articleShow', {'article': '3'}, False)
        self.assert_observer('core.custom', 'diacamma.invoice', 'articleShow')
        self.assert_count_equal('', 11)
        self.assert_json_equal('LABELFORM', 'reference', "ABC3")

        self.factory.xfer = ArticleShow()
        self.calljson('/diacamma.invoice/articleShow', {'article': '1'}, False)
        self.assert_observer('core.custom', 'diacamma.invoice', 'articleShow')
        self.assert_count_equal('', 16)
        self.assert_json_equal('LABELFORM', 'reference', "ABC1")
        self.assert_grid_equal('storage', {"area": "Lieu de stockage", "qty": "Quantité", "amount": "Montant", "mean": "Prix moyen"}, 1)
        self.assert_json_equal('', 'storage/@0/area', "{[b]}Total{[/b]}")
        self.assert_json_equal('', 'storage/@0/qty', "{[b]}0.0{[/b]}")
        self.assert_json_equal('', 'storage/@0/amount', "{[b]}0.00€{[/b]}")
        self.assert_grid_equal('moving', {"storagesheet.date": "date", "storagesheet.comment": "commentaire", "quantity": "quantité"}, 0)  # nb=3

        self.factory.xfer = StorageSheetList()
        self.calljson('/diacamma.invoice/storageSheetList', {}, False)
        self.assert_observer('core.custom', 'diacamma.invoice', 'storageSheetList')
        self.assert_count_equal('storagesheet', 0)

        self.factory.xfer = StorageSheetAddModify()
        self.calljson('/diacamma.invoice/storageSheetAddModify', {'sheet_type': 1}, False)
        self.assert_observer('core.custom', 'diacamma.invoice', 'storageSheetAddModify')
        self.assert_count_equal('', 5)

        self.factory.xfer = StorageSheetAddModify()
        self.calljson('/diacamma.invoice/storageSheetAddModify',
                      {'sheet_type': 1, 'date': '2014-04-01', 'SAVE': 'YES', 'storagearea': 1, 'comment': "casses!"}, False)
        self.assert_observer('core.acknowledge', 'diacamma.invoice', 'storageSheetAddModify')
        self.assertEqual(self.response_json['action']['id'], "diacamma.invoice/storageSheetShow")
        self.assertEqual(len(self.response_json['action']['params']), 1)
        self.assertEqual(self.response_json['action']['params']['storagesheet'], 1)

        self.factory.xfer = StorageSheetShow()
        self.calljson('/diacamma.invoice/storageSheetShow', {'storagesheet': "1"}, False)
        self.assert_observer('core.custom', 'diacamma.invoice', 'storageSheetShow')
        self.assert_count_equal('', 8)
        self.assert_json_equal('LABELFORM', 'sheet_type', "sortie de stock")
        self.assert_json_equal('LABELFORM', 'status', "en création")
        self.assert_json_equal('LABELFORM', 'storagearea', "Lieu 1")
        self.assert_count_equal('storagedetail', 0)
        self.assert_count_equal('#storagedetail/actions', 3)

        self.factory.xfer = StorageDetailAddModify()
        self.calljson('/diacamma.invoice/storageDetailAddModify', {'storagesheet': "1"}, False)
        self.assert_observer('core.custom', 'diacamma.invoice', 'storageDetailAddModify')
        self.assert_count_equal('', 4)

        self.factory.xfer = StorageDetailAddModify()
        self.calljson('/diacamma.invoice/storageDetailAddModify', {'storagesheet': "1", 'SAVE': 'YES', "article": 1, "quantity": 7}, False)
        self.assert_observer('core.acknowledge', 'diacamma.invoice', 'storageDetailAddModify')

        self.factory.xfer = StorageDetailAddModify()
        self.calljson('/diacamma.invoice/storageDetailAddModify', {'storagesheet': "1", 'SAVE': 'YES', "article": 4, "quantity": 6}, False)
        self.assert_observer('core.acknowledge', 'diacamma.invoice', 'storageDetailAddModify')

        self.factory.xfer = StorageSheetShow()
        self.calljson('/diacamma.invoice/storageSheetShow', {'storagesheet': "1"}, False)
        self.assert_observer('core.custom', 'diacamma.invoice', 'storageSheetShow')
        self.assert_count_equal('', 8)
        self.assert_json_equal('LABELFORM', 'status', "en création")
        self.assert_count_equal('storagedetail', 2)
        self.assert_json_equal('', 'storagedetail/@0/article', "ABC1")
        self.assert_json_equal('', 'storagedetail/@0/quantity_txt', "7.00")
        self.assert_json_equal('', 'storagedetail/@1/article', "ABC4")
        self.assert_json_equal('', 'storagedetail/@1/quantity_txt', "6.00")
        self.assert_json_equal('LABELFORM', 'info',
                               "{[font color=\"red\"]}L'article ABC1 est en quantité insuffisante{[br/]}L'article ABC4 est en quantité insuffisante{[/font]}")

        self.factory.xfer = ArticleShow()
        self.calljson('/diacamma.invoice/articleShow', {'article': '1'}, False)
        self.assert_observer('core.custom', 'diacamma.invoice', 'articleShow')
        self.assert_count_equal('', 16)
        self.assert_json_equal('LABELFORM', 'reference', "ABC1")
        self.assert_count_equal('storage', 1)
        self.assert_count_equal('moving', 0)

        self.factory.xfer = StorageSheetTransition()
        self.calljson('/diacamma.invoice/storageSheetTransition',
                      {'CONFIRME': 'YES', 'storagesheet': 1, 'TRANSITION': 'valid'}, False)
        self.assert_observer('core.exception', 'diacamma.invoice', 'storageSheetTransition')

        insert_storage()

        self.factory.xfer = ArticleShow()
        self.calljson('/diacamma.invoice/articleShow', {'article': '1'}, False)
        self.assert_observer('core.custom', 'diacamma.invoice', 'articleShow')
        self.assert_count_equal('', 16)
        self.assert_json_equal('LABELFORM', 'reference', "ABC1")
        self.assert_count_equal('storage', 3)
        self.assert_json_equal('', 'storage/@0/area', "Lieu 1")
        self.assert_json_equal('', 'storage/@0/qty', "10.0")
        self.assert_json_equal('', 'storage/@0/amount', "50.00€")
        self.assert_json_equal('', 'storage/@1/area', "Lieu 2")
        self.assert_json_equal('', 'storage/@1/qty', "5.0")
        self.assert_json_equal('', 'storage/@1/amount', "20.00€")
        self.assert_json_equal('', 'storage/@2/area', "{[b]}Total{[/b]}")
        self.assert_json_equal('', 'storage/@2/qty', "{[b]}15.0{[/b]}")
        self.assert_json_equal('', 'storage/@2/amount', "{[b]}70.00€{[/b]}")
        self.assert_count_equal('moving', 2)
        self.assert_json_equal('', 'moving/@0/storagesheet.date', "2014-01-02")
        self.assert_json_equal('', 'moving/@0/storagesheet.comment', "B")
        self.assert_json_equal('', 'moving/@0/quantity', "5.00")
        self.assert_json_equal('', 'moving/@1/storagesheet.date', "2014-01-01")
        self.assert_json_equal('', 'moving/@1/storagesheet.comment', "A")
        self.assert_json_equal('', 'moving/@1/quantity', "10.00")

        self.factory.xfer = StorageSheetShow()
        self.calljson('/diacamma.invoice/storageSheetShow', {'storagesheet': "1"}, False)
        self.assert_observer('core.custom', 'diacamma.invoice', 'storageSheetShow')
        self.assert_count_equal('', 8)
        self.assert_json_equal('LABELFORM', 'status', "en création")
        self.assert_count_equal('storagedetail', 2)
        self.assert_json_equal('', 'storagedetail/@0/article', "ABC1")
        self.assert_json_equal('', 'storagedetail/@0/quantity_txt', "7.00")
        self.assert_json_equal('', 'storagedetail/@1/article', "ABC4")
        self.assert_json_equal('', 'storagedetail/@1/quantity_txt', "6.00")
        self.assert_json_equal('LABELFORM', 'info', "{[font color=\"red\"]}{[/font]}")

        self.factory.xfer = StorageSheetTransition()
        self.calljson('/diacamma.invoice/storageSheetTransition',
                      {'CONFIRME': 'YES', 'storagesheet': 1, 'TRANSITION': 'valid'}, False)
        self.assert_observer('core.acknowledge', 'diacamma.invoice', 'storageSheetTransition')

        self.factory.xfer = StorageSheetShow()
        self.calljson('/diacamma.invoice/storageSheetShow', {'storagesheet': "1"}, False)
        self.assert_observer('core.custom', 'diacamma.invoice', 'storageSheetShow')
        self.assert_count_equal('', 7)
        self.assert_json_equal('LABELFORM', 'status', "validé")
        self.assert_count_equal('storagedetail', 2)

        self.factory.xfer = ArticleShow()
        self.calljson('/diacamma.invoice/articleShow', {'article': '1'}, False)
        self.assert_observer('core.custom', 'diacamma.invoice', 'articleShow')
        self.assert_count_equal('', 16)
        self.assert_json_equal('LABELFORM', 'reference', "ABC1")
        self.assert_count_equal('storage', 3)
        self.assert_json_equal('', 'storage/@0/area', "Lieu 1")
        self.assert_json_equal('', 'storage/@0/qty', "3.0")
        self.assert_json_equal('', 'storage/@0/amount', "15.00€")
        self.assert_json_equal('', 'storage/@0/mean', "5.00€")
        self.assert_json_equal('', 'storage/@1/area', "Lieu 2")
        self.assert_json_equal('', 'storage/@1/qty', "5.0")
        self.assert_json_equal('', 'storage/@1/amount', "20.00€")
        self.assert_json_equal('', 'storage/@1/mean', "4.00€")
        self.assert_json_equal('', 'storage/@2/area', "{[b]}Total{[/b]}")
        self.assert_json_equal('', 'storage/@2/qty', "{[b]}8.0{[/b]}")
        self.assert_json_equal('', 'storage/@2/amount', "{[b]}35.00€{[/b]}")
        self.assert_json_equal('', 'storage/@2/mean', "{[b]}4.38€{[/b]}")
        self.assert_count_equal('moving', 3)
        self.assert_json_equal('', 'moving/@0/storagesheet.date', "2014-04-01")
        self.assert_json_equal('', 'moving/@0/storagesheet.comment', "casses!")
        self.assert_json_equal('', 'moving/@0/quantity', "-7.00")
        self.assert_json_equal('', 'moving/@1/storagesheet.date', "2014-01-02")
        self.assert_json_equal('', 'moving/@1/storagesheet.comment', "B")
        self.assert_json_equal('', 'moving/@1/quantity', "5.00")
        self.assert_json_equal('', 'moving/@2/storagesheet.date', "2014-01-01")
        self.assert_json_equal('', 'moving/@2/storagesheet.comment', "A")
        self.assert_json_equal('', 'moving/@2/quantity', "10.00")

        self.factory.xfer = StorageSheetList()
        self.calljson('/diacamma.invoice/storageSheetList', {'status': -1, 'sheet_type': 1}, False)
        self.assert_observer('core.custom', 'diacamma.invoice', 'storageSheetList')
        self.assert_count_equal('storagesheet', 1)

    def test_bill(self):
        self.factory.xfer = ArticleShow()
        self.calljson('/diacamma.invoice/articleShow', {'article': '3'}, False)
        self.assert_observer('core.custom', 'diacamma.invoice', 'articleShow')
        self.assert_count_equal('', 11)
        self.assert_json_equal('LABELFORM', 'reference', "ABC3")

        self.factory.xfer = ArticleShow()
        self.calljson('/diacamma.invoice/articleShow', {'article': '1'}, False)
        self.assert_observer('core.custom', 'diacamma.invoice', 'articleShow')
        self.assert_count_equal('', 16)
        self.assert_json_equal('LABELFORM', 'reference', "ABC1")
        self.assert_count_equal('storage', 1)
        self.assert_json_equal('', 'storage/@0/area', "{[b]}Total{[/b]}")
        self.assert_json_equal('', 'storage/@0/qty', "{[b]}0.0{[/b]}")
        self.assert_json_equal('', 'storage/@0/amount', "{[b]}0.00€{[/b]}")
        self.assert_count_equal('moving', 0)

        self.factory.xfer = BillAddModify()
        self.calljson('/diacamma.invoice/billAddModify',
                      {'bill_type': 1, 'date': '2015-04-01', 'SAVE': 'YES'}, False)
        self.assert_observer('core.acknowledge', 'diacamma.invoice', 'billAddModify')
        self.factory.xfer = SupportingThirdValid()
        self.calljson('/diacamma.payoff/supportingThirdValid',
                      {'supporting': 1, 'third': 6}, False)
        self.assert_observer('core.acknowledge', 'diacamma.payoff', 'supportingThirdValid')

        self.factory.xfer = DetailAddModify()
        self.calljson('/diacamma.invoice/detailAddModify', {'bill': 1}, False)
        self.assert_observer('core.custom', 'diacamma.invoice', 'detailAddModify')
        self.assert_count_equal('', 7)
        self.assert_select_equal('article', 4)  # nb=4

        self.factory.xfer = DetailAddModify()
        self.calljson('/diacamma.invoice/detailAddModify', {'bill': 1, 'article': 1}, False)
        self.assert_observer('core.custom', 'diacamma.invoice', 'detailAddModify')
        self.assert_count_equal('', 9)
        self.assert_select_equal('storagearea', 0)  # nb=0

        self.factory.xfer = DetailAddModify()
        self.calljson('/diacamma.invoice/detailAddModify',
                      {'SAVE': 'YES', 'bill': 1, 'article': 1, 'designation': 'article A', 'price': '1.11', 'quantity': 5, 'storagearea': 1}, False)
        self.assert_observer('core.acknowledge', 'diacamma.invoice', 'detailAddModify')
        self.factory.xfer = DetailAddModify()
        self.calljson('/diacamma.invoice/detailAddModify',
                      {'SAVE': 'YES', 'bill': 1, 'article': 2, 'designation': 'article B', 'price': '2.22', 'quantity': 5, 'storagearea': 2}, False)
        self.assert_observer('core.acknowledge', 'diacamma.invoice', 'detailAddModify')
        self.factory.xfer = DetailAddModify()
        self.calljson('/diacamma.invoice/detailAddModify',
                      {'SAVE': 'YES', 'bill': 1, 'article': 3, 'designation': 'article C', 'price': '3.33', 'quantity': 5}, False)
        self.assert_observer('core.acknowledge', 'diacamma.invoice', 'detailAddModify')

        self.factory.xfer = BillShow()
        self.calljson('/diacamma.invoice/billShow', {'bill': 1}, False)
        self.assert_observer('core.custom', 'diacamma.invoice', 'billShow')
        self.assert_count_equal('detail', 3)
        self.assert_json_equal('LABELFORM', 'info',
                               "{[font color=\"red\"]}L'article ABC1 est en quantité insuffisante{[br/]}L'article ABC2 est en quantité insuffisante{[/font]}")

        self.factory.xfer = ArticleShow()
        self.calljson('/diacamma.invoice/articleShow', {'article': '1'}, False)
        self.assert_observer('core.custom', 'diacamma.invoice', 'articleShow')
        self.assert_count_equal('', 16)
        self.assert_json_equal('LABELFORM', 'reference', "ABC1")
        self.assert_count_equal('storage', 1)
        self.assert_count_equal('moving', 0)

        self.factory.xfer = BillTransition()
        self.calljson('/diacamma.invoice/billTransition',
                      {'CONFIRME': 'YES', 'bill': 1, 'withpayoff': False, 'TRANSITION': 'valid'}, False)
        self.assert_observer('core.exception', 'diacamma.invoice', 'billTransition')

        insert_storage()

        self.factory.xfer = ArticleShow()
        self.calljson('/diacamma.invoice/articleShow', {'article': '1'}, False)
        self.assert_observer('core.custom', 'diacamma.invoice', 'articleShow')
        self.assert_count_equal('', 16)
        self.assert_json_equal('LABELFORM', 'reference', "ABC1")
        self.assert_count_equal('storage', 3)
        self.assert_json_equal('', 'storage/@0/area', "Lieu 1")
        self.assert_json_equal('', 'storage/@0/qty', "10.0")
        self.assert_json_equal('', 'storage/@0/amount', "50.00€")
        self.assert_json_equal('', 'storage/@0/mean', "5.00€")
        self.assert_json_equal('', 'storage/@1/area', "Lieu 2")
        self.assert_json_equal('', 'storage/@1/qty', "5.0")
        self.assert_json_equal('', 'storage/@1/amount', "20.00€")
        self.assert_json_equal('', 'storage/@1/mean', "4.00€")
        self.assert_json_equal('', 'storage/@2/area', "{[b]}Total{[/b]}")
        self.assert_json_equal('', 'storage/@2/qty', "{[b]}15.0{[/b]}")
        self.assert_json_equal('', 'storage/@2/amount', "{[b]}70.00€{[/b]}")
        self.assert_json_equal('', 'storage/@2/mean', "{[b]}4.67€{[/b]}")
        self.assert_count_equal('moving', 2)
        self.assert_json_equal('', 'moving/@0/storagesheet.date', "2014-01-02")
        self.assert_json_equal('', 'moving/@0/storagesheet.comment', "B")
        self.assert_json_equal('', 'moving/@0/quantity', "5.00")
        self.assert_json_equal('', 'moving/@1/storagesheet.date', "2014-01-01")
        self.assert_json_equal('', 'moving/@1/storagesheet.comment', "A")
        self.assert_json_equal('', 'moving/@1/quantity', "10.00")

        self.factory.xfer = DetailAddModify()
        self.calljson('/diacamma.invoice/detailAddModify', {'bill': 1, 'article': 1}, False)
        self.assert_observer('core.custom', 'diacamma.invoice', 'detailAddModify')
        self.assert_count_equal('', 9)
        self.assert_select_equal('storagearea', {1: "Lieu 1 [10.0]", 2: "Lieu 2 [5.0]"})

        self.factory.xfer = BillShow()
        self.calljson('/diacamma.invoice/billShow', {'bill': 1}, False)
        self.assert_observer('core.custom', 'diacamma.invoice', 'billShow')
        self.assert_count_equal('detail', 3)
        self.assert_json_equal('LABELFORM', 'info', "{[font color=\"red\"]}{[/font]}")

        self.factory.xfer = BillTransition()
        self.calljson('/diacamma.invoice/billTransition',
                      {'CONFIRME': 'YES', 'bill': 1, 'withpayoff': False, 'TRANSITION': 'valid'}, False)
        self.assert_observer('core.acknowledge', 'diacamma.invoice', 'billTransition')

        self.factory.xfer = ArticleShow()
        self.calljson('/diacamma.invoice/articleShow', {'article': '1'}, False)
        self.assert_observer('core.custom', 'diacamma.invoice', 'articleShow')
        self.assert_count_equal('', 16)
        self.assert_json_equal('LABELFORM', 'reference', "ABC1")
        self.assert_count_equal('storage', 3)
        self.assert_json_equal('', 'storage/@0/area', "Lieu 1")
        self.assert_json_equal('', 'storage/@0/qty', "5.0")
        self.assert_json_equal('', 'storage/@0/amount', "25.00€")
        self.assert_json_equal('', 'storage/@1/area', "Lieu 2")
        self.assert_json_equal('', 'storage/@1/qty', "5.0")
        self.assert_json_equal('', 'storage/@1/amount', "20.00€")
        self.assert_json_equal('', 'storage/@2/area', "{[b]}Total{[/b]}")
        self.assert_json_equal('', 'storage/@2/qty', "{[b]}10.0{[/b]}")
        self.assert_json_equal('', 'storage/@2/amount', "{[b]}45.00€{[/b]}")
        self.assert_count_equal('moving', 3)
        self.assert_json_equal('', 'moving/@0/storagesheet.date', "2015-04-01")
        self.assert_json_equal('', 'moving/@0/storagesheet.comment', "facture A-1 - 1 avril 2015")
        self.assert_json_equal('', 'moving/@0/quantity', "-5.00")
        self.assert_json_equal('', 'moving/@1/storagesheet.date', "2014-01-02")
        self.assert_json_equal('', 'moving/@1/storagesheet.comment', "B")
        self.assert_json_equal('', 'moving/@1/quantity', "5.00")
        self.assert_json_equal('', 'moving/@2/storagesheet.date', "2014-01-01")
        self.assert_json_equal('', 'moving/@2/storagesheet.comment', "A")
        self.assert_json_equal('', 'moving/@2/quantity', "10.00")

        self.factory.xfer = StorageSheetList()
        self.calljson('/diacamma.invoice/storageSheetList', {'status': -1, 'sheet_type': 1}, False)
        self.assert_observer('core.custom', 'diacamma.invoice', 'storageSheetList')
        self.assert_count_equal('storagesheet', 2)

    def test_import(self):
        self.factory.xfer = ArticleList()
        self.calljson('/diacamma.invoice/articleList', {}, False)
        self.assert_observer('core.custom', 'diacamma.invoice', 'articleList')
        self.assert_count_equal('', 6)
        self.assert_grid_equal('article', {"reference": "référence", "designation": "désignation", "price_txt": "prix", "unit": "unité",
                                           "isdisabled": "désactivé ?", "sell_account": "compte de vente", "stockable": "stockable", "stockage_total": "quantités"}, 4)
        self.assert_json_equal('', 'article/@0/reference', "ABC1")
        self.assert_json_equal('', 'article/@0/stockage_total', "0.0")
        self.assert_json_equal('', 'article/@1/reference', "ABC2")
        self.assert_json_equal('', 'article/@1/stockage_total', "0.0")
        self.assert_json_equal('', 'article/@2/reference', "ABC3")
        self.assert_json_equal('', 'article/@2/stockage_total', "---")
        self.assert_json_equal('', 'article/@3/reference', "ABC4")
        self.assert_json_equal('', 'article/@3/stockage_total', "0.0")

        csv_content = """'num','prix','qty'
'ABC1','1.11','10.00'
'ABC2','2,22','5.00'
'ABC3','3.33','25,00'
'XYZ0','6.66','88.00'
'ABC4','4,44','20.00'
'ABC5','5.55','15.00'
"""
        self.factory.xfer = StorageSheetAddModify()
        self.calljson('/diacamma.invoice/storageSheetAddModify',
                      {'sheet_type': 0, 'date': '2014-04-01', 'SAVE': 'YES', 'storagearea': 1, 'comment': "arrivage massif!"}, False)
        self.assert_observer('core.acknowledge', 'diacamma.invoice', 'storageSheetAddModify')

        self.factory.xfer = StorageDetailImport()
        self.calljson('/diacamma.invoice/storageDetailImport', {'storagesheet': "1", 'step': 1, 'modelname': 'invoice.StorageDetail', 'quotechar': "'",
                                                                'delimiter': ',', 'encoding': 'utf-8', 'dateformat': '%d/%m/%Y', 'csvcontent': StringIO(csv_content)}, False)
        self.assert_observer('core.custom', 'diacamma.invoice', 'storageDetailImport')
        self.assert_count_equal('', 10)
        self.assert_select_equal('fld_article', 3)  # nb=3
        self.assert_select_equal('fld_price', 3)  # nb=3
        self.assert_select_equal('fld_quantity', 3)  # nb=3
        self.assert_count_equal('CSV', 6)
        self.assert_count_equal('#CSV/actions', 0)
        self.assertEqual(len(self.json_actions), 3)
        self.assert_action_equal(self.json_actions[0], (six.text_type('Retour'), 'images/left.png', 'diacamma.invoice', 'storageDetailImport', 0, 2, 1, {'step': '0'}))
        self.assert_action_equal(self.json_actions[1], (six.text_type('Ok'), 'images/ok.png', 'diacamma.invoice', 'storageDetailImport', 0, 2, 1, {'step': '2'}))

        self.factory.xfer = StorageDetailImport()
        self.calljson('/diacamma.invoice/storageDetailImport', {'storagesheet': "1", 'step': 2, 'modelname': 'invoice.StorageDetail', 'quotechar': "'", 'delimiter': ',',
                                                                'encoding': 'utf-8', 'dateformat': '%d/%m/%Y', 'csvcontent0': csv_content,
                                                                "fld_article": "num", "fld_price": "prix", "fld_quantity": "qty", }, False)
        self.assert_observer('core.custom', 'diacamma.invoice', 'storageDetailImport')
        self.assert_count_equal('', 5)
        self.assert_count_equal('CSV', 6)
        self.assert_count_equal('#CSV/actions', 0)
        self.assertEqual(len(self.json_actions), 3)
        self.assert_action_equal(self.json_actions[1], (six.text_type('Ok'), 'images/ok.png', 'diacamma.invoice', 'storageDetailImport', 0, 2, 1, {'step': '3'}))

        self.factory.xfer = StorageDetailImport()
        self.calljson('/diacamma.invoice/storageDetailImport', {'storagesheet': "1", 'step': 3, 'modelname': 'invoice.StorageDetail', 'quotechar': "'", 'delimiter': ',',
                                                                'encoding': 'utf-8', 'dateformat': '%d/%m/%Y', 'csvcontent0': csv_content,
                                                                "fld_article": "num", "fld_price": "prix", "fld_quantity": "qty", }, False)
        self.assert_observer('core.custom', 'diacamma.invoice', 'storageDetailImport')
        self.assert_count_equal('', 2)
        self.assert_json_equal('LABELFORM', 'result', "{[center]}{[i]}5 éléments ont été importés{[/i]}{[/center]}")
        self.assertEqual(len(self.json_actions), 1)

        self.factory.xfer = StorageSheetShow()
        self.calljson('/diacamma.invoice/storageSheetShow', {'storagesheet': "1"}, False)
        self.assert_observer('core.custom', 'diacamma.invoice', 'storageSheetShow')
        self.assert_count_equal('', 11)
        self.assert_json_equal('LABELFORM', 'status', "en création")
        self.assert_count_equal('storagedetail', 5)
        self.assert_json_equal('', 'storagedetail/@0/article', "ABC1")
        self.assert_json_equal('', 'storagedetail/@1/article', "ABC2")
        self.assert_json_equal('', 'storagedetail/@2/article', "ABC3")
        self.assert_json_equal('', 'storagedetail/@3/article', "ABC4")
        self.assert_json_equal('', 'storagedetail/@4/article', "ABC5")
        self.assert_json_equal('LABELFORM', 'info',
                               "{[font color=\"red\"]}L'article ABC3 est en non stockable{[br/]}L'article ABC5 est en non stockable{[/font]}")

        self.factory.xfer = StorageDetailDel()
        self.calljson('/diacamma.invoice/storageDetailDel', {'storagedetail': "3", 'CONFIRME': 'YES'}, False)
        self.assert_observer('core.acknowledge', 'diacamma.invoice', 'storageDetailDel')
        self.factory.xfer = StorageDetailDel()
        self.calljson('/diacamma.invoice/storageDetailDel', {'storagedetail': "5", 'CONFIRME': 'YES'}, False)
        self.assert_observer('core.acknowledge', 'diacamma.invoice', 'storageDetailDel')

        self.factory.xfer = StorageSheetShow()
        self.calljson('/diacamma.invoice/storageSheetShow', {'storagesheet': "1"}, False)
        self.assert_observer('core.custom', 'diacamma.invoice', 'storageSheetShow')
        self.assert_json_equal('LABELFORM', 'info', "{[font color=\"red\"]}{[/font]}")

        self.factory.xfer = StorageSheetTransition()
        self.calljson('/diacamma.invoice/storageSheetTransition',
                      {'CONFIRME': 'YES', 'storagesheet': 1, 'TRANSITION': 'valid'}, False)
        self.assert_observer('core.acknowledge', 'diacamma.invoice', 'storageSheetTransition')

        self.factory.xfer = ArticleList()
        self.calljson('/diacamma.invoice/articleList', {}, False)
        self.assert_observer('core.custom', 'diacamma.invoice', 'articleList')
        self.assert_count_equal('', 6)
        self.assert_count_equal('article', 4)
        self.assert_json_equal('', 'article/@0/reference', "ABC1")
        self.assert_json_equal('', 'article/@0/stockage_total', "10.0")
        self.assert_json_equal('', 'article/@1/reference', "ABC2")
        self.assert_json_equal('', 'article/@1/stockage_total', "5.0")
        self.assert_json_equal('', 'article/@2/reference', "ABC3")
        self.assert_json_equal('', 'article/@2/stockage_total', "---")
        self.assert_json_equal('', 'article/@3/reference', "ABC4")
        self.assert_json_equal('', 'article/@3/stockage_total', "20.0")
