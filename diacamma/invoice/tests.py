# -*- coding: utf-8 -*-
'''
diacamma.invoice tests package

@author: Laurent GAY
@organization: sd-libre.fr
@contact: info@sd-libre.fr
@copyright: 2015 sd-libre.fr
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
from datetime import date
from base64 import b64decode
from os.path import isfile, join

from lucterios.framework.test import LucteriosTest
from lucterios.framework.filetools import get_user_dir
from lucterios.framework.model_fields import LucteriosScheduler
from lucterios.framework.auditlog import log_create
from lucterios.CORE.models import SavedCriteria, LucteriosUser
from lucterios.CORE.parameters import Params
from lucterios.mailing.tests import configSMTP, TestReceiver, decode_b64
from lucterios.mailing.models import Message
from lucterios.contacts.models import CustomField

from diacamma.accounting.test_tools import initial_thirds_fr, default_compta_fr
from diacamma.accounting.models import CostAccounting, FiscalYear
from diacamma.accounting.views import ThirdShow
from diacamma.accounting.views_entries import EntryAccountList
from diacamma.payoff.views import PayoffAddModify, PayoffDel, SupportingThird, SupportingThirdValid, PayableEmail
from diacamma.payoff.test_tools import default_bankaccount_fr, check_pdfreport,\
    default_paymentmethod
from diacamma.invoice.models import Bill, AccountPosting, CategoryBill
from diacamma.invoice.test_tools import default_articles, InvoiceTest, default_categories, default_customize, \
    default_area, default_categorybill, clean_cache
from diacamma.invoice.views_conf import AutomaticReduceAddModify, AutomaticReduceDel
from diacamma.invoice.views import BillList, BillAddModify, BillShow, DetailAddModify, DetailDel, BillTransition, BillDel, BillToBill, \
    BillStatistic, BillStatisticPrint, BillPrint, BillMultiPay, BillSearch, \
    BillCheckAutoreduce, BillPayableEmail, BillBatch, BillToOrder, BillUndo,\
    BillToQuotation, BillCloneQuotation, BillTransitionArchive


class BillTest(InvoiceTest):

    def setUp(self):
        self.maxDiff = 4000
        initial_thirds_fr()
        LucteriosTest.setUp(self)
        default_compta_fr()
        default_bankaccount_fr()
        clean_cache()
        rmtree(get_user_dir(), True)
        LucteriosUser.objects.create(username='creator', first_name='Léonard', last_name='de Vinci', email='leonardo@davinci.org')

    def _add_create_log(self, bill_id):
        new_bill = Bill.objects.get(id=bill_id)
        log_create(None, new_bill, True)
        new_bill._last_log.username = 'creator'
        new_bill._last_log.save()

    def test_add_bill(self):
        default_articles()
        self.factory.xfer = BillList()
        self.calljson('/diacamma.invoice/billList', {}, False)
        self.assert_observer('core.custom', 'diacamma.invoice', 'billList')
        self.assert_grid_equal('bill', {"bill_type": "type de facture", "num_txt": "N°", "date": "date", "third": "tiers", "comment": "commentaire", "total": "total", "status": "statut"}, 0)  # nb=7

        self.factory.xfer = BillAddModify()
        self.calljson('/diacamma.invoice/billAddModify', {}, False)
        self.assert_observer('core.custom', 'diacamma.invoice', 'billAddModify')
        self.assert_count_equal('', 5)
        self.assert_select_equal('bill_type', 4)

        self.factory.xfer = BillAddModify()
        self.calljson('/diacamma.invoice/billAddModify', {'bill_type': 1}, False)
        self.assert_observer('core.custom', 'diacamma.invoice', 'billAddModify')
        self.assert_count_equal('', 5)
        self.assert_select_equal('bill_type', 4)

        self.factory.xfer = BillAddModify()
        self.calljson('/diacamma.invoice/billAddModify',
                      {'bill_type': 1, 'date': '2014-04-01', 'SAVE': 'YES'}, False)
        self.assert_observer('core.acknowledge', 'diacamma.invoice', 'billAddModify')
        self.assertEqual(self.response_json['action']['id'], "diacamma.invoice/billShow")
        self.assertEqual(len(self.response_json['action']['params']), 1)
        self.assertEqual(self.response_json['action']['params']['bill'], 1)
        self.assertEqual(len(self.json_context), 2)

        self.factory.xfer = BillShow()
        self.calljson('/diacamma.invoice/billShow', {'bill': 1}, False)
        self.assert_observer('core.custom', 'diacamma.invoice', 'billShow')
        self.assertEqual(len(self.json_actions), 2)
        self.assert_count_equal('', 12)
        self.assert_json_equal('LABELFORM', 'title', "facture")
        self.assert_json_equal('LABELFORM', 'num_txt', None)
        self.assert_json_equal('LABELFORM', 'status', 0)
        self.assert_json_equal('LABELFORM', 'date', "2014-04-01")
        self.assert_json_equal('LABELFORM', 'info', ["aucun tiers sélectionné", "pas de détail", "la date n'est pas incluse dans l'exercice"])
        self.assert_json_equal('LABELFORM', 'warning', [])

        self.factory.xfer = BillAddModify()
        self.calljson('/diacamma.invoice/billAddModify',
                      {'bill': 1, 'date': '2015-04-01', 'SAVE': 'YES'}, False)
        self.assert_observer('core.acknowledge', 'diacamma.invoice', 'billAddModify')

        self.factory.xfer = BillShow()
        self.calljson('/diacamma.invoice/billShow', {'bill': 1}, False)
        self.assert_observer('core.custom', 'diacamma.invoice', 'billShow')
        self.assert_json_equal('LABELFORM', 'info', ["aucun tiers sélectionné", "pas de détail"])

        self.factory.xfer = SupportingThird()
        self.calljson('/diacamma.payoff/supportingThird', {'bill': 1}, False)
        self.assert_observer('core.custom', 'diacamma.payoff', 'supportingThird')
        self.assert_count_equal('third', 7)

        self.factory.xfer = SupportingThirdValid()
        self.calljson('/diacamma.payoff/supportingThirdValid', {'supporting': 1, 'third': 6}, False)
        self.assert_observer('core.acknowledge', 'diacamma.payoff', 'supportingThirdValid')

        self.factory.xfer = BillShow()
        self.calljson('/diacamma.invoice/billShow', {'bill': 1}, False)
        self.assert_observer('core.custom', 'diacamma.invoice', 'billShow')
        self.assert_json_equal('LABELFORM', 'info', ["pas de détail"])

        self.factory.xfer = DetailAddModify()
        self.calljson('/diacamma.invoice/detailAddModify', {'bill': 1}, False)
        self.assert_observer('core.custom', 'diacamma.invoice', 'detailAddModify')
        self.assert_count_equal('', 7)
        self.assert_json_equal('FLOAT', 'quantity', 1.0)
        self.assert_json_equal('', '#quantity/min', 0.0)
        self.assert_json_equal('', '#quantity/max', 9999999.99)
        self.assert_json_equal('', '#quantity/prec', 3)

        self.factory.xfer = DetailAddModify()
        self.calljson('/diacamma.invoice/detailAddModify', {'bill': 1, 'article': 1}, False)
        self.assert_observer('core.custom', 'diacamma.invoice', 'detailAddModify')
        self.assert_count_equal('', 8)
        self.assert_json_equal('FLOAT', 'quantity', 1.0)
        self.assert_json_equal('', '#quantity/min', 0.0)
        self.assert_json_equal('', '#quantity/max', 9999999.99)
        self.assert_json_equal('', '#quantity/prec', 3)

        self.factory.xfer = DetailAddModify()
        self.calljson('/diacamma.invoice/detailAddModify', {'bill': 1, 'article': 3}, False)
        self.assert_observer('core.custom', 'diacamma.invoice', 'detailAddModify')
        self.assert_count_equal('', 8)
        self.assert_json_equal('FLOAT', 'quantity', 1.0)
        self.assert_json_equal('', '#quantity/min', 0.0)
        self.assert_json_equal('', '#quantity/max', 9999999.99)
        self.assert_json_equal('', '#quantity/prec', 0)

        self.factory.xfer = DetailAddModify()
        self.calljson('/diacamma.invoice/detailAddModify',
                      {'SAVE': 'YES', 'bill': 1, 'article': 1, 'designation': 'My article', 'price': '43.72', 'quantity': 2}, False)
        self.assert_observer('core.acknowledge', 'diacamma.invoice', 'detailAddModify')

        self.factory.xfer = BillShow()
        self.calljson('/diacamma.invoice/billShow', {'bill': 1}, False)
        self.assert_observer('core.custom', 'diacamma.invoice', 'billShow')
        self.assert_count_equal('', 13)
        self.assert_json_equal('LABELFORM', 'date', "2015-04-01")
        self.assert_json_equal('LINK', 'third', "Dalton Jack")
        self.assert_json_equal('', '#third/link', "mailto:Jack.Dalton@worldcompany.com")
        self.assert_count_equal('detail', 1)
        self.assert_json_equal('', 'detail/@0/article', 'ABC1')
        self.assert_json_equal('', 'detail/@0/designation', 'My article')
        self.assert_json_equal('', 'detail/@0/price', 43.72)
        self.assert_json_equal('', 'detail/@0/unit', '')
        self.assert_json_equal('', 'detail/@0/quantity_txt', '2,000')
        self.assert_json_equal('', 'detail/@0/reduce_txt', None)
        self.assert_json_equal('', 'detail/@0/total', 87.44)

        self.assert_json_equal('LABELFORM', 'total_excltax', 87.44)
        self.assert_json_equal('LABELFORM', 'info', [])
        self.assert_json_equal('LABELFORM', 'warning', [])
        self.assert_json_equal('', '#total_excltax/formatnum', "C2EUR")

        self.assertEqual(len(self.json_actions), 3)

        bill_item = Bill.objects.get(id=1)
        self.assertEqual(bill_item.is_revenu, True)

        self.factory.xfer = BillList()
        self.calljson('/diacamma.invoice/billList', {}, False)
        self.assert_observer('core.custom', 'diacamma.invoice', 'billList')
        self.assert_count_equal('bill', 1)

        self.factory.xfer = BillList()
        self.calljson('/diacamma.invoice/billList', {'filter': 'Dalton Jack'}, False)
        self.assert_observer('core.custom', 'diacamma.invoice', 'billList')
        self.assert_count_equal('bill', 1)

    def test_add_asset(self):
        default_articles()

        self.factory.xfer = BillAddModify()
        self.calljson('/diacamma.invoice/billAddModify',
                      {'bill_type': 2, 'date': '2014-04-01', 'SAVE': 'YES'}, False)
        self.assert_observer('core.acknowledge', 'diacamma.invoice', 'billAddModify')
        self.assertEqual(self.response_json['action']['id'], "diacamma.invoice/billShow")
        self.assertEqual(len(self.response_json['action']['params']), 1)
        self.assertEqual(self.response_json['action']['params']['bill'], 1)
        self.assertEqual(len(self.json_context), 2)

        self.factory.xfer = BillShow()
        self.calljson('/diacamma.invoice/billShow', {'bill': 1}, False)
        self.assert_observer('core.custom', 'diacamma.invoice', 'billShow')
        self.assertEqual(len(self.json_actions), 2)
        self.assert_count_equal('', 12)
        self.assert_json_equal('LABELFORM', 'title', "avoir")
        self.assert_json_equal('LABELFORM', 'num_txt', None)
        self.assert_json_equal('LABELFORM', 'status', 0)
        self.assert_json_equal('LABELFORM', 'date', "2014-04-01")
        self.assert_json_equal('LABELFORM', 'info', ["aucun tiers sélectionné", "pas de détail", "la date n'est pas incluse dans l'exercice"])
        self.assert_json_equal('LABELFORM', 'warning', [])

        self.factory.xfer = BillAddModify()
        self.calljson('/diacamma.invoice/billAddModify',
                      {'bill': 1, 'date': '2015-04-01', 'SAVE': 'YES'}, False)
        self.assert_observer('core.acknowledge', 'diacamma.invoice', 'billAddModify')

        self.factory.xfer = SupportingThirdValid()
        self.calljson('/diacamma.payoff/supportingThirdValid', {'supporting': 1, 'third': 6}, False)
        self.assert_observer('core.acknowledge', 'diacamma.payoff', 'supportingThirdValid')

        self.factory.xfer = DetailAddModify()
        self.calljson('/diacamma.invoice/detailAddModify',
                      {'SAVE': 'YES', 'bill': 1, 'article': 1, 'designation': 'My article', 'price': '43.72', 'quantity': 2}, False)
        self.assert_observer('core.acknowledge', 'diacamma.invoice', 'detailAddModify')

        self.factory.xfer = BillShow()
        self.calljson('/diacamma.invoice/billShow', {'bill': 1}, False)
        self.assert_observer('core.custom', 'diacamma.invoice', 'billShow')
        self.assert_count_equal('', 13)
        self.assert_json_equal('LABELFORM', 'info', [])
        self.assert_json_equal('LABELFORM', 'warning', [])
        self.assertEqual(len(self.json_actions), 3)

        bill_item = Bill.objects.get(id=1)
        self.assertEqual(bill_item.is_revenu, False)

    def test_add_bill_with_filter(self):
        default_categories()
        default_articles(True)
        self.factory.xfer = BillList()
        self.calljson('/diacamma.invoice/billList', {}, False)
        self.assert_observer('core.custom', 'diacamma.invoice', 'billList')
        self.assert_count_equal('bill', 0)

        self.factory.xfer = BillAddModify()
        self.calljson('/diacamma.invoice/billAddModify',
                      {'bill_type': 1, 'date': '2014-04-01', 'SAVE': 'YES'}, False)
        self.assert_observer('core.acknowledge', 'diacamma.invoice', 'billAddModify')

        self.factory.xfer = DetailAddModify()
        self.calljson('/diacamma.invoice/detailAddModify', {'bill': 1}, False)
        self.assert_observer('core.custom', 'diacamma.invoice', 'detailAddModify')
        self.assert_count_equal('', 12)
        self.assert_select_equal('article', 5)  # nb=5

        self.factory.xfer = DetailAddModify()
        self.calljson('/diacamma.invoice/detailAddModify', {'bill': 1, 'third': 2}, False)
        self.assert_observer('core.custom', 'diacamma.invoice', 'detailAddModify')
        self.assert_count_equal('', 13)
        self.assert_select_equal('article', 2)  # nb=2

        self.factory.xfer = DetailAddModify()
        self.calljson('/diacamma.invoice/detailAddModify', {'bill': 1, 'reference': '34'}, False)
        self.assert_observer('core.custom', 'diacamma.invoice', 'detailAddModify')
        self.assert_count_equal('', 13)
        self.assert_select_equal('article', 2)  # nb=2

        self.factory.xfer = DetailAddModify()
        self.calljson('/diacamma.invoice/detailAddModify', {'bill': 1, 'cat_filter': '2;3'}, False)
        self.assert_observer('core.custom', 'diacamma.invoice', 'detailAddModify')
        self.assert_count_equal('', 13)
        self.assert_select_equal('article', 1)  # nb=1

    def test_add_bill_with_manyarticles(self):
        default_categories()
        default_articles(True, False, True)
        self.factory.xfer = BillList()
        self.calljson('/diacamma.invoice/billList', {}, False)
        self.assert_observer('core.custom', 'diacamma.invoice', 'billList')
        self.assert_count_equal('bill', 0)

        self.factory.xfer = BillAddModify()
        self.calljson('/diacamma.invoice/billAddModify',
                      {'bill_type': 1, 'date': '2014-04-01', 'SAVE': 'YES'}, False)
        self.assert_observer('core.acknowledge', 'diacamma.invoice', 'billAddModify')

        self.factory.xfer = DetailAddModify()
        self.calljson('/diacamma.invoice/detailAddModify', {'bill': 1}, False)
        self.assert_observer('core.custom', 'diacamma.invoice', 'detailAddModify')
        self.assert_count_equal('', 13)
        self.assert_json_equal('LABELFORM', 'article_fake', None)
        self.assert_json_equal('LABELFORM', 'warning_filter', "Modifier le filtrage pour afficher une liste d'articles utilisables.")
        self.assert_json_equal('MEMO', 'designation', '')
        self.assert_json_equal('FLOAT', 'price', 0)
        self.assert_json_equal('FLOAT', 'quantity', 1)
        self.assert_json_equal('EDIT', 'unit', '')

        self.factory.xfer = DetailAddModify()
        self.calljson('/diacamma.invoice/detailAddModify', {'bill': 1, 'cat_filter': '2', 'CHANGE_ART': 'YES'}, False)
        self.assert_observer('core.custom', 'diacamma.invoice', 'detailAddModify')
        self.assert_count_equal('', 13)
        self.assert_select_equal('article', 52)
        self.assert_json_equal('SELECT', 'article', 2)
        self.assert_json_equal('MEMO', 'designation', 'Article 02')
        self.assert_json_equal('FLOAT', 'price', 56.78)
        self.assert_json_equal('FLOAT', 'quantity', 1)
        self.assert_json_equal('EDIT', 'unit', 'l')

        self.factory.xfer = DetailAddModify()
        self.calljson('/diacamma.invoice/detailAddModify', {'bill': 1, 'article': 3, 'cat_filter': '2', 'CHANGE_ART': 'YES'}, False)
        self.assert_observer('core.custom', 'diacamma.invoice', 'detailAddModify')
        self.assert_count_equal('', 13)
        self.assert_select_equal('article', 52)
        self.assert_json_equal('SELECT', 'article', 3)
        self.assert_json_equal('MEMO', 'designation', 'Article 03')
        self.assert_json_equal('FLOAT', 'price', 324.97)
        self.assert_json_equal('FLOAT', 'quantity', 1)
        self.assert_json_equal('EDIT', 'unit', '')

        self.factory.xfer = DetailAddModify()
        self.calljson('/diacamma.invoice/detailAddModify', {'bill': 1, 'article': 3, 'cat_filter': '2', 'ref_filter': 'CCC', 'CHANGE_ART': 'YES'}, False)
        self.assert_observer('core.custom', 'diacamma.invoice', 'detailAddModify')
        self.assert_count_equal('', 13)
        self.assert_select_equal('article', 3)
        self.assert_json_equal('SELECT', 'article', 17)
        self.assert_json_equal('MEMO', 'designation', 'Article CCC-0121')
        self.assert_json_equal('FLOAT', 'price', 110.0)
        self.assert_json_equal('FLOAT', 'quantity', 1)
        self.assert_json_equal('EDIT', 'unit', 'C')

    def test_add_bill_not_allow_empty_code(self):
        default_categories()
        default_articles(True)
        Params.setvalue('invoice-reduce-allow-article-empty', False)
        self.factory.xfer = BillList()
        self.calljson('/diacamma.invoice/billList', {}, False)
        self.assert_observer('core.custom', 'diacamma.invoice', 'billList')
        self.assert_count_equal('bill', 0)

        self.factory.xfer = BillAddModify()
        self.calljson('/diacamma.invoice/billAddModify',
                      {'bill_type': 1, 'date': '2014-04-01', 'SAVE': 'YES'}, False)
        self.assert_observer('core.acknowledge', 'diacamma.invoice', 'billAddModify')

        self.factory.xfer = DetailAddModify()
        self.calljson('/diacamma.invoice/detailAddModify', {'bill': 1}, False)
        self.assert_observer('core.custom', 'diacamma.invoice', 'detailAddModify')
        self.assert_count_equal('', 13)
        self.assert_select_equal('article', 4)  # nb=4

    def test_add_bill_bad(self):
        default_articles()
        self.factory.xfer = BillAddModify()
        self.calljson('/diacamma.invoice/billAddModify',
                      {'bill_type': 1, 'date': '2015-04-01', 'SAVE': 'YES'}, False)
        self.assert_observer('core.acknowledge', 'diacamma.invoice', 'billAddModify')
        self.factory.xfer = SupportingThirdValid()
        self.calljson('/diacamma.payoff/supportingThirdValid',
                      {'supporting': 1, 'third': 6}, False)
        self.assert_observer('core.acknowledge', 'diacamma.payoff', 'supportingThirdValid')

        self.factory.xfer = BillShow()
        self.calljson('/diacamma.invoice/billShow', {'bill': 1}, False)
        self.assert_observer('core.custom', 'diacamma.invoice', 'billShow')
        self.assert_json_equal('LABELFORM', 'info', ["pas de détail"])

        self.factory.xfer = DetailAddModify()
        self.calljson('/diacamma.invoice/detailAddModify',
                      {'SAVE': 'YES', 'bill': 1, 'article': 4, 'designation': 'My article', 'price': '43.72', 'quantity': 2}, False)
        self.assert_observer('core.acknowledge', 'diacamma.invoice', 'detailAddModify')
        self.factory.xfer = BillShow()
        self.calljson('/diacamma.invoice/billShow', {'bill': 1}, False)
        self.assert_observer('core.custom', 'diacamma.invoice', 'billShow')
        self.assert_count_equal('detail', 1)
        self.assert_json_equal('LABELFORM', 'info', ["au moins un article a un compte inconnu !"])

        self.factory.xfer = DetailDel()
        self.calljson('/diacamma.invoice/detailDel',
                      {'CONFIRME': 'YES', 'bill': 1, 'detail': 1}, False)
        self.assert_observer('core.acknowledge', 'diacamma.invoice', 'detailDel')
        self.factory.xfer = DetailAddModify()
        self.calljson('/diacamma.invoice/detailAddModify',
                      {'SAVE': 'YES', 'bill': 1, 'article': 3, 'designation': 'My article', 'price': '43.72', 'quantity': 2}, False)
        self.assert_observer('core.acknowledge', 'diacamma.invoice', 'detailAddModify')
        self.factory.xfer = BillShow()
        self.calljson('/diacamma.invoice/billShow', {'bill': 1}, False)
        self.assert_observer('core.custom', 'diacamma.invoice', 'billShow')
        self.assert_count_equal('detail', 1)
        self.assert_json_equal('LABELFORM', 'info', ["au moins un article a un compte inconnu !"])

        self.factory.xfer = DetailDel()
        self.calljson('/diacamma.invoice/detailDel',
                      {'CONFIRME': 'YES', 'bill': 1, 'detail': 2}, False)
        self.assert_observer('core.acknowledge', 'diacamma.invoice', 'detailDel')
        self.factory.xfer = DetailAddModify()
        self.calljson('/diacamma.invoice/detailAddModify',
                      {'SAVE': 'YES', 'bill': 1, 'article': 2, 'designation': 'My article', 'price': '43.72', 'quantity': 2}, False)
        self.assert_observer('core.acknowledge', 'diacamma.invoice', 'detailAddModify')
        self.factory.xfer = SupportingThirdValid()
        self.calljson('/diacamma.payoff/supportingThirdValid',
                      {'supporting': 1, 'third': 1}, False)
        self.assert_observer('core.acknowledge', 'diacamma.payoff', 'supportingThirdValid')
        self.factory.xfer = BillShow()
        self.calljson('/diacamma.invoice/billShow', {'bill': 1}, False)
        self.assert_observer('core.custom', 'diacamma.invoice', 'billShow')
        self.assert_count_equal('detail', 1)
        self.assert_json_equal('LABELFORM', 'info', ["Ce tiers n'a pas de compte correct !"])

    def check_list_del_archive(self):
        self.factory.xfer = BillList()
        self.calljson('/diacamma.invoice/billList', {'status_filter': -1}, False)
        self.assert_observer('core.custom', 'diacamma.invoice', 'billList')
        self.assert_count_equal('bill', 1)
        self.assert_count_equal('#bill/actions', 4)
        self.factory.xfer = BillList()
        self.calljson('/diacamma.invoice/billList', {'status_filter': 0}, False)
        self.assert_observer('core.custom', 'diacamma.invoice', 'billList')
        self.assert_count_equal('bill', 0)
        self.assert_count_equal('#bill/actions', 5)
        self.factory.xfer = BillList()
        self.calljson('/diacamma.invoice/billList', {'status_filter': 1}, False)
        self.assert_observer('core.custom', 'diacamma.invoice', 'billList')
        self.assert_count_equal('bill', 1)
        self.assert_count_equal('#bill/actions', 5)
        self.factory.xfer = BillList()
        self.calljson('/diacamma.invoice/billList', {'status_filter': 2}, False)
        self.assert_observer('core.custom', 'diacamma.invoice', 'billList')
        self.assert_count_equal('bill', 0)
        self.assert_count_equal('#bill/actions', 1)

        self.factory.xfer = BillDel()
        self.calljson(
            '/diacamma.invoice/billDel', {'CONFIRME': 'YES', 'bill': 1}, False)
        self.assert_observer('core.exception', 'diacamma.invoice', 'billDel')

        self.factory.xfer = BillTransition()
        self.calljson('/diacamma.invoice/billTransition',
                      {'CONFIRME': 'YES', 'bill': 1, 'TRANSITION': 'archive'}, False)
        self.assert_observer('core.acknowledge', 'diacamma.invoice', 'billTransition')

        self.factory.xfer = BillList()
        self.calljson('/diacamma.invoice/billList', {'status_filter': -1}, False)
        self.assert_observer('core.custom', 'diacamma.invoice', 'billList')
        self.assert_count_equal('bill', 0)
        self.factory.xfer = BillList()
        self.calljson('/diacamma.invoice/billList', {'status_filter': 3}, False)
        self.assert_observer('core.custom', 'diacamma.invoice', 'billList')
        self.assert_count_equal('bill', 1)
        self.assert_count_equal('#bill/actions', 3)

    def test_compta_valid_with_pay(self):
        default_articles()
        cost = CostAccounting.objects.get(name='open')
        cost.is_default = False
        cost.save()
        details = [{'article': 1, 'designation': 'article 1', 'price': '22.50', 'quantity': 3, 'reduce': '5.0'},
                   {'article': 2, 'designation': 'article 2',
                       'price': '3.25', 'quantity': 7},
                   {'article': 0, 'designation': 'article 3',
                       'price': '11.10', 'quantity': 2}]
        self._create_bill(details, 1, '2015-04-01', 6)

        self.factory.xfer = BillTransition()
        self.calljson('/diacamma.invoice/billTransition', {'bill': 1, 'TRANSITION': 'valid', "nbpayoff": 1}, False)
        self.assert_observer('core.custom', 'diacamma.invoice', 'billTransition')
        self.assert_count_equal('', 2 + 7 + 0)

        self.factory.xfer = BillTransition()
        self.calljson('/diacamma.invoice/billTransition', {'bill': 1, 'TRANSITION': 'valid', "nbpayoff": 1, 'payoff00_mode': 1}, False)
        self.assert_observer('core.custom', 'diacamma.invoice', 'billTransition')
        self.assert_count_equal('', 2 + 8 + 0)

        self.factory.xfer = BillTransition()
        self.calljson('/diacamma.invoice/billTransition', {'bill': 1, 'TRANSITION': 'valid', "nbpayoff": 1, 'payoff00_mode': 1, 'payoff00_bank_account': 2}, False)
        self.assert_observer('core.custom', 'diacamma.invoice', 'billTransition')
        self.assert_count_equal('', 2 + 9 + 0)

        configSMTP('localhost', 2025)

        self.factory.xfer = BillTransition()
        self.calljson('/diacamma.invoice/billTransition', {'bill': 1, 'TRANSITION': 'valid', "nbpayoff": 1, 'payoff00_mode': 1, 'payoff00_bank_account': 2}, False)
        self.assert_observer('core.custom', 'diacamma.invoice', 'billTransition')
        self.assert_count_equal('', 2 + 9 + 5)
        self.assert_json_equal('', 'nbpayoff', 1)
        self.assert_json_equal('', 'payoff00_amount', '107.45')
        self.assert_json_equal('', 'sendemail', False)

        self.factory.xfer = BillTransition()
        self.calljson('/diacamma.invoice/billTransition', {'bill': 1, 'TRANSITION': 'valid', 'CONFIRME': 'YES',
                                                           'nbpayoff': 2,
                                                           'payoff00_amount': '40.45', 'payoff00_date_payoff': '2015-04-07', 'payoff00_mode': 1,
                                                           'payoff00_reference': 'abc123', 'payoff00_bank_account': 2, 'payoff00_payer': "Ma'a Dalton", 'payoff00_bank_fee': '1.08',
                                                           'payoff01_amount': '67.00', 'payoff01_date_payoff': '2015-05-07', 'payoff01_mode': 1,
                                                           'payoff01_reference': 'uvw987', 'payoff01_bank_account': 2, 'payoff01_payer': "Ma'a Dalton", 'payoff01_bank_fee': '0.0',
                                                           'sendemail': True, 'subject': 'my bill', 'message': 'this is a bill.', 'model': 8}, False)
        self.assert_observer('core.acknowledge', 'diacamma.invoice', 'billTransition')
        self.assert_action_equal('POST', self.response_json['action'], ("", None, "diacamma.payoff", "payableEmail", 1, 1, 1))

        self.factory.xfer = EntryAccountList()
        self.calljson('/diacamma.accounting/entryAccountList',
                      {'year': '1', 'journal': '0', 'filter': '0'}, False)
        self.assert_observer('core.custom', 'diacamma.accounting', 'entryAccountList')
        self.assert_count_equal('entryline', 5 + 3 + 2)

        self.assert_json_equal('', 'entryline/@5/entry.num', None)
        self.assert_json_equal('', 'entryline/@5/entry.date_entry', None)
        self.assert_json_equal('', 'entryline/@5/entry.date_value', '2015-04-07')
        self.assert_json_equal('', 'entryline/@5/designation_ref', 'règlement de Facture A-1')
        self.assert_json_equal('', 'entryline/@5/entry_account', '[411 Dalton Jack]')
        self.assert_json_equal('', 'entryline/@5/credit', 40.45)
        self.assert_json_equal('', 'entryline/@5/costaccounting', None)
        self.assert_json_equal('', 'entryline/@6/entry_account', '[581] 581')
        self.assert_json_equal('', 'entryline/@6/designation_ref', 'règlement de Facture A-1{[br/]}chèque : abc123')
        self.assert_json_equal('', 'entryline/@6/debit', -39.37)
        self.assert_json_equal('', 'entryline/@6/costaccounting', None)
        self.assert_json_equal('', 'entryline/@7/entry_account', '[627] 627')
        self.assert_json_equal('', 'entryline/@7/debit', -1.08)
        self.assert_json_equal('', 'entryline/@7/costaccounting', None)
        self.assert_json_equal('', 'entryline/@8/entry.num', None)
        self.assert_json_equal('', 'entryline/@8/entry.date_entry', None)
        self.assert_json_equal('', 'entryline/@8/entry.date_value', '2015-05-07')
        self.assert_json_equal('', 'entryline/@8/designation_ref', 'règlement de Facture A-1')
        self.assert_json_equal('', 'entryline/@8/entry_account', '[411 Dalton Jack]')
        self.assert_json_equal('', 'entryline/@8/credit', 67.00)
        self.assert_json_equal('', 'entryline/@8/costaccounting', None)
        self.assert_json_equal('', 'entryline/@9/entry_account', '[581] 581')
        self.assert_json_equal('', 'entryline/@9/designation_ref', 'règlement de Facture A-1{[br/]}chèque : uvw987')
        self.assert_json_equal('', 'entryline/@9/debit', -67.00)

        server = TestReceiver()
        server.start(2025)
        try:
            self.assertEqual(0, server.count())
            self.factory.xfer = PayableEmail()
            self.calljson('/diacamma.payoff/payableEmail',
                          {'bill': 1, 'OK': 'YES', 'item_name': 'bill', 'subject': 'my bill', 'message': 'this is a bill.', 'model': 8}, False)
            self.assert_observer('core.acknowledge', 'diacamma.payoff', 'payableEmail')
            self.assertEqual(1, server.count())
            _msg_txt, _msg, msg_file = server.check_first_message('my bill', 3, {'To': 'Jack.Dalton@worldcompany.com'})
            self.save_pdf(base64_content=msg_file.get_payload())
            check_pdfreport(self, 'Bill', 1, False, msg_file.get_payload())
        finally:
            server.stop()

    def test_compta_valid_with_pay_fee_cost(self):
        default_articles()
        cost = CostAccounting.objects.get(name='open')
        cost.is_default = True
        cost.save()
        details = [{'article': 1, 'designation': 'article 1', 'price': '22.50', 'quantity': 3, 'reduce': '5.0'},
                   {'article': 2, 'designation': 'article 2',
                       'price': '3.25', 'quantity': 7},
                   {'article': 0, 'designation': 'article 3',
                       'price': '11.10', 'quantity': 2}]
        self._create_bill(details, 1, '2015-04-01', 6)

        self.factory.xfer = BillTransition()
        self.calljson('/diacamma.invoice/billTransition', {'bill': 1, 'TRANSITION': 'valid', 'CONFIRME': 'YES',
                                                           'nbpayoff': 3,
                                                           'payoff00_mode': 1, 'payoff00_amount': '107.45', 'payoff00_date_payoff': '2015-04-07',
                                                           'payoff00_reference': 'abc123', 'payoff00_bank_account': 2,
                                                           'payoff00_payer': "Ma'a Dalton", 'payoff00_bank_fee': '1.08',
                                                           'payoff01_mode': 1, 'payoff01_amount': '0.0', 'payoff01_date_payoff': '2015-04-07',
                                                           'payoff01_reference': 'abc123', 'payoff01_bank_account': 2,
                                                           'payoff01_payer': "Ma'a Dalton", 'payoff01_bank_fee': '0.0',
                                                           'payoff02_mode': 1, 'payoff02_amount': '0.0', 'payoff02_date_payoff': '2015-04-07',
                                                           'payoff02_reference': 'abc123', 'payoff02_bank_account': 2,
                                                           'payoff02_payer': "Ma'a Dalton", 'payoff02_bank_fee': '0.0',
                                                           'sendemail': False}, False)
        self.assert_observer('core.acknowledge', 'diacamma.invoice', 'billTransition')

        self.factory.xfer = EntryAccountList()
        self.calljson('/diacamma.accounting/entryAccountList',
                      {'year': '1', 'journal': '0', 'filter': '0'}, False)
        self.assert_observer('core.custom', 'diacamma.accounting', 'entryAccountList')
        self.assert_count_equal('entryline', 5 + 3)

        self.assert_json_equal('', 'entryline/@5/entry.num', None)
        self.assert_json_equal('', 'entryline/@5/entry.date_entry', None)
        self.assert_json_equal('', 'entryline/@5/entry.date_value', '2015-04-07')
        self.assert_json_equal('', 'entryline/@5/designation_ref', 'règlement de Facture A-1')
        self.assert_json_equal('', 'entryline/@5/entry_account', '[411 Dalton Jack]')
        self.assert_json_equal('', 'entryline/@5/credit', 107.45)
        self.assert_json_equal('', 'entryline/@5/costaccounting', None)
        self.assert_json_equal('', 'entryline/@6/entry_account', '[581] 581')
        self.assert_json_equal('', 'entryline/@6/debit', -106.37)
        self.assert_json_equal('', 'entryline/@6/costaccounting', None)
        self.assert_json_equal('', 'entryline/@7/entry_account', '[627] 627')
        self.assert_json_equal('', 'entryline/@7/debit', -1.08)
        self.assert_json_equal('', 'entryline/@7/costaccounting', 'open')

        self.factory.xfer = BillShow()
        self.calljson('/diacamma.invoice/billShow', {'bill': 1}, False)
        self.assert_observer('core.custom', 'diacamma.invoice', 'billShow')
        self.assert_count_equal('payoff', 1)
        self.assert_json_equal('', 'payoff/@0/date', "2015-04-07")
        self.assert_json_equal('', 'payoff/@0/mode', 1)
        self.assert_json_equal('', 'payoff/@0/amount', 107.45)
        self.assert_json_equal('', 'payoff/@0/payer', "Ma'a Dalton")
        self.assert_json_equal('', 'payoff/@0/reference', "abc123")
        self.assert_json_equal('', 'payoff/@0/bank_account_ex', 'PayPal (frais = 1,08 €)')

    def test_compta_valid_with_pay_fee_maxicost(self):
        default_articles()
        post1 = AccountPosting.objects.get(id=1)
        post1.cost_accounting = CostAccounting.objects.create(name='new', description='New cost', status=0)
        post1.save()
        post2 = AccountPosting.objects.get(id=2)
        post2.cost_accounting = CostAccounting.objects.create(name='other', description='Other cost', status=0)
        post2.save()
        cost = CostAccounting.objects.get(name='open')
        cost.is_default = False
        cost.save()
        details = [{'article': 1, 'designation': 'article 1', 'price': '22.50', 'quantity': 3, 'reduce': '5.0'},
                   {'article': 2, 'designation': 'article 2',
                       'price': '3.25', 'quantity': 7},
                   {'article': 0, 'designation': 'article 3',
                       'price': '11.10', 'quantity': 2}]
        self._create_bill(details, 1, '2015-04-01', 6)

        self.factory.xfer = BillTransition()
        self.calljson('/diacamma.invoice/billTransition', {'bill': 1, 'TRANSITION': 'valid', 'CONFIRME': 'YES',
                                                           'nbpayoff': 1, 'payoff00_mode': 1, 'payoff00_amount': '107.45', 'payoff00_date_payoff': '2015-04-07',
                                                           'payoff00_mode': 1, 'payoff00_reference': 'abc123',
                                                           'payoff00_bank_account': 2, 'payoff00_payer': "Ma'a Dalton", 'payoff00_bank_fee': '1.08',
                                                           'sendemail': False}, False)
        self.assert_observer('core.acknowledge', 'diacamma.invoice', 'billTransition')

        self.factory.xfer = EntryAccountList()
        self.calljson('/diacamma.accounting/entryAccountList',
                      {'year': '1', 'journal': '0', 'filter': '0'}, False)
        self.assert_observer('core.custom', 'diacamma.accounting', 'entryAccountList')
        self.assert_count_equal('entryline', 5 + 3)

        self.assert_json_equal('', 'entryline/@5/entry.num', None)
        self.assert_json_equal('', 'entryline/@5/entry.date_entry', None)
        self.assert_json_equal('', 'entryline/@5/entry.date_value', '2015-04-07')
        self.assert_json_equal('', 'entryline/@5/designation_ref', 'règlement de Facture A-1')
        self.assert_json_equal('', 'entryline/@5/entry_account', '[411 Dalton Jack]')
        self.assert_json_equal('', 'entryline/@5/credit', 107.45)
        self.assert_json_equal('', 'entryline/@5/costaccounting', None)
        self.assert_json_equal('', 'entryline/@6/entry_account', '[581] 581')
        self.assert_json_equal('', 'entryline/@6/debit', -106.37)
        self.assert_json_equal('', 'entryline/@6/costaccounting', None)
        self.assert_json_equal('', 'entryline/@7/entry_account', '[627] 627')
        self.assert_json_equal('', 'entryline/@7/debit', -1.08)
        self.assert_json_equal('', 'entryline/@7/costaccounting', 'new')

    def test_compta_bill(self):
        default_articles()
        CostAccounting.objects.create(name='new', description='New cost', status=0)
        post1 = AccountPosting.objects.get(id=1)
        post1.cost_accounting_id = 2
        post1.save()
        post2 = AccountPosting.objects.get(id=2)
        post2.cost_accounting_id = 3
        post2.save()
        cost = CostAccounting.objects.get(name='open')
        cost.is_default = False
        cost.save()

        details = [{'article': 1, 'designation': 'article 1', 'price': '22.50', 'quantity': 3, 'reduce': '5.0'},
                   {'article': 2, 'designation': 'article 2', 'price': '3.25', 'quantity': 7},
                   {'article': 0, 'designation': 'article 3', 'price': '11.10', 'quantity': 2}]
        self._create_bill(details, 1, '2015-04-01', 6)

        self.factory.xfer = BillShow()
        self.calljson('/diacamma.invoice/billShow', {'bill': 1}, False)
        self.assert_attrib_equal('total_excltax', 'description', "total")
        self.assert_json_equal('LABELFORM', 'total_excltax', 107.45)
        self.assert_json_equal('LABELFORM', 'info', [])
        self.assertEqual(len(self.json_actions), 3)

        self.factory.xfer = EntryAccountList()
        self.calljson('/diacamma.accounting/entryAccountList',
                      {'year': '1', 'journal': '0', 'filter': '0'}, False)
        self.assert_observer('core.custom', 'diacamma.accounting', 'entryAccountList')
        self.assert_count_equal('entryline', 0)

        self.factory.xfer = BillTransition()
        self.calljson('/diacamma.invoice/billTransition',
                      {'CONFIRME': 'YES', 'bill': 1, 'withpayoff': False, 'TRANSITION': 'valid'}, False)
        self.assert_observer('core.acknowledge', 'diacamma.invoice', 'billTransition')

        self.factory.xfer = BillShow()
        self.calljson('/diacamma.invoice/billShow', {'bill': 1}, False)
        self.assert_observer('core.custom', 'diacamma.invoice', 'billShow')
        self.assert_count_equal('', 13)
        self.assert_json_equal('LABELFORM', 'num_txt', "A-1")
        self.assert_json_equal('LABELFORM', 'status', 1)
        self.assertEqual(len(self.json_actions), 4)

        self.factory.xfer = EntryAccountList()
        self.calljson('/diacamma.accounting/entryAccountList',
                      {'year': '1', 'journal': '0', 'filter': '0'}, False)
        self.assert_observer('core.custom', 'diacamma.accounting', 'entryAccountList')
        self.assert_count_equal('entryline', 5)

        self.assert_json_equal('', 'entryline/@0/entry.num', None)
        self.assert_json_equal('', 'entryline/@0/entry.date_entry', None)
        self.assert_json_equal('', 'entryline/@0/entry.date_value', '2015-04-01')
        self.assert_json_equal('', 'entryline/@0/designation_ref', 'Facture A-1')
        self.assert_json_equal('', 'entryline/@0/entry_account', '[411 Dalton Jack]')
        self.assert_json_equal('', 'entryline/@0/debit', -107.45)
        self.assert_json_equal('', 'entryline/@0/costaccounting', None)
        self.assert_json_equal('', 'entryline/@1/entry_account', '[701] 701')
        self.assert_json_equal('', 'entryline/@1/credit', 67.50)
        self.assert_json_equal('', 'entryline/@1/costaccounting', 'open')
        self.assert_json_equal('', 'entryline/@2/entry_account', '[706] 706')
        self.assert_json_equal('', 'entryline/@2/credit', 22.20)
        self.assert_json_equal('', 'entryline/@2/costaccounting', None)
        self.assert_json_equal('', 'entryline/@3/entry_account', '[707] 707')
        self.assert_json_equal('', 'entryline/@3/credit', 22.75)
        self.assert_json_equal('', 'entryline/@3/costaccounting', 'new')
        self.assert_json_equal('', 'entryline/@4/entry_account', '[709] 709')
        self.assert_json_equal('', 'entryline/@4/debit', -5.00)
        self.assert_json_equal('', 'entryline/@4/costaccounting', 'open')

        self.factory.xfer = BillList()
        self.calljson('/diacamma.invoice/billList', {'status_filter': -1}, False)
        self.assert_observer('core.custom', 'diacamma.invoice', 'billList')
        self.assert_count_equal('bill', 1)
        self.factory.xfer = BillList()
        self.calljson('/diacamma.invoice/billList', {'status_filter': 0}, False)
        self.assert_observer('core.custom', 'diacamma.invoice', 'billList')
        self.assert_count_equal('bill', 0)
        self.factory.xfer = BillList()
        self.calljson('/diacamma.invoice/billList', {'status_filter': 1}, False)
        self.assert_observer('core.custom', 'diacamma.invoice', 'billList')
        self.assert_count_equal('bill', 1)

        self.factory.xfer = BillUndo()
        self.calljson('/diacamma.invoice/billUndo',
                      {'CONFIRME': 'YES', 'bill': 1}, False)
        self.assert_observer('core.acknowledge', 'diacamma.invoice', 'billUndo')
        self.assertEqual(self.response_json['action']['id'], "diacamma.invoice/billShow")
        self.assertEqual(len(self.response_json['action']['params']), 1)
        self.assertEqual(self.response_json['action']['params']['bill'], 2)

        self.factory.xfer = BillList()
        self.calljson('/diacamma.invoice/billList', {'status_filter': -1}, False)
        self.assert_observer('core.custom', 'diacamma.invoice', 'billList')
        self.assert_count_equal('bill', 1)
        self.factory.xfer = BillList()
        self.calljson('/diacamma.invoice/billList', {'status_filter': 0}, False)
        self.assert_observer('core.custom', 'diacamma.invoice', 'billList')
        self.assert_count_equal('bill', 1)
        self.factory.xfer = BillList()
        self.calljson('/diacamma.invoice/billList', {'status_filter': 1}, False)
        self.assert_observer('core.custom', 'diacamma.invoice', 'billList')
        self.assert_count_equal('bill', 0)
        self.factory.xfer = BillList()
        self.calljson('/diacamma.invoice/billList', {'status_filter': 2}, False)
        self.assert_observer('core.custom', 'diacamma.invoice', 'billList')
        self.assert_count_equal('bill', 0)
        self.factory.xfer = BillList()
        self.calljson('/diacamma.invoice/billList', {'status_filter': 3}, False)
        self.assert_observer('core.custom', 'diacamma.invoice', 'billList')
        self.assert_count_equal('bill', 1)

        self.factory.xfer = BillShow()
        self.calljson('/diacamma.invoice/billShow', {'bill': 2}, False)
        self.assert_observer('core.custom', 'diacamma.invoice', 'billShow')
        self.assert_count_equal('', 14)
        self.assert_json_equal('LABELFORM', 'total_excltax', 107.45)
        self.assert_json_equal('LABELFORM', 'num_txt', None)
        self.assert_json_equal('LABELFORM', 'status', 0)
        self.assert_json_equal('LABELFORM', 'title', "avoir")
        self.assert_json_equal('LABELFORM', 'date', date.today().isoformat(), True)
        self.assert_action_equal('GET', self.get_json_path('#parentbill/action'), ("origine", "diacamma.invoice/images/origin.png",
                                                                                   "diacamma.invoice", "billShow", 0, 1, 1, {'bill': 1}))
        self.factory.xfer = BillAddModify()
        self.calljson('/diacamma.invoice/billAddModify',
                      {'bill': 2, 'date': '2015-04-01', 'SAVE': 'YES'}, False)
        self.assert_observer('core.acknowledge', 'diacamma.invoice', 'billAddModify')

        self.factory.xfer = BillShow()
        self.calljson('/diacamma.invoice/billShow', {'bill': 2}, False)
        self.assert_observer('core.custom', 'diacamma.invoice', 'billShow')
        self.assert_json_equal('LABELFORM', 'date', "2015-04-01")
        self.assert_json_equal('LABELFORM', 'info', [])
        self.assert_json_equal('LABELFORM', 'warning', [])

        self.factory.xfer = BillTransition()
        self.calljson('/diacamma.invoice/billTransition',
                      {'CONFIRME': 'YES', 'bill': 2, 'withpayoff': False, 'TRANSITION': 'valid'}, False)
        self.assert_observer('core.acknowledge', 'diacamma.invoice', 'billTransition')

        self.factory.xfer = EntryAccountList()
        self.calljson('/diacamma.accounting/entryAccountList',
                      {'year': '1', 'journal': '0', 'filter': '0'}, False)
        self.assert_observer('core.custom', 'diacamma.accounting', 'entryAccountList')
        self.assert_count_equal('entryline', 10)
        self.assert_json_equal('LABELFORM', 'result', [0.00, 0.00, 0.00, 0.00, 0.00])

    def test_assert_mode(self):
        Params.setvalue('invoice-asset-mode', 1)
        default_articles()
        details = [{'article': 1, 'designation': 'article 1', 'price': '22.50', 'quantity': 3, 'reduce': '5.0'},
                   {'article': 2, 'designation': 'article 2', 'price': '3.25', 'quantity': 7},
                   {'article': 0, 'designation': 'article 3', 'price': '11.10', 'quantity': 2}]
        self._create_bill(details, 1, '2015-04-01', 6)

        self.factory.xfer = BillTransition()
        self.calljson('/diacamma.invoice/billTransition',
                      {'CONFIRME': 'YES', 'bill': 1, 'withpayoff': False, 'TRANSITION': 'valid'}, False)
        self.assert_observer('core.acknowledge', 'diacamma.invoice', 'billTransition')

        self.factory.xfer = BillShow()
        self.calljson('/diacamma.invoice/billShow', {'bill': 1}, False)
        self.assert_observer('core.custom', 'diacamma.invoice', 'billShow')
        self.assert_count_equal('', 13)
        self.assert_json_equal('LABELFORM', 'num_txt', "A-1")
        self.assert_json_equal('LABELFORM', 'status', 1)
        self.assert_json_equal('LABELFORM', 'title', "facture")

        self.factory.xfer = BillUndo()
        self.calljson('/diacamma.invoice/billUndo',
                      {'CONFIRME': 'YES', 'bill': 1}, False)
        self.assert_observer('core.acknowledge', 'diacamma.invoice', 'billUndo')
        self.assertEqual(self.response_json['action']['id'], "diacamma.invoice/billShow")
        self.assertEqual(len(self.response_json['action']['params']), 1)
        self.assertEqual(self.response_json['action']['params']['bill'], 2)

        self.factory.xfer = BillShow()
        self.calljson('/diacamma.invoice/billShow', {'bill': 2}, False)
        self.assert_observer('core.custom', 'diacamma.invoice', 'billShow')
        self.assert_json_equal('LABELFORM', 'total_excltax', 107.45)
        self.assert_json_equal('LABELFORM', 'num_txt', None)
        self.assert_json_equal('LABELFORM', 'status', 0)
        self.assert_json_equal('LABELFORM', 'title', "avoir")

        self.factory.xfer = BillShow()
        self.calljson('/diacamma.invoice/billShow', {'bill': 1}, False)
        self.assert_observer('core.custom', 'diacamma.invoice', 'billShow')
        self.assert_count_equal('', 13)
        self.assert_json_equal('LABELFORM', 'num_txt', "A-1")
        self.assert_json_equal('LABELFORM', 'status', 1)
        self.assert_json_equal('LABELFORM', 'title', "facture")

    def test_add_quotation(self):
        default_articles()
        self._create_bill([{'article': 1, 'designation': 'article 1',
                            'price': '22.50', 'quantity': 3, 'reduce': '5.0'}], 0, '2015-04-01', 6)

        self.factory.xfer = BillTransition()
        self.calljson('/diacamma.invoice/billTransition',
                      {'CONFIRME': 'YES', 'bill': 1, 'withpayoff': False, 'TRANSITION': 'valid'}, False)
        self.assert_observer('core.acknowledge', 'diacamma.invoice', 'billTransition')

        self.factory.xfer = BillShow()
        self.calljson('/diacamma.invoice/billShow', {'bill': 1}, False)
        self.assert_observer('core.custom', 'diacamma.invoice', 'billShow')
        self.assert_count_equal('', 10)
        self.assert_json_equal('LABELFORM', 'num_txt', "A-1")
        self.assert_json_equal('LABELFORM', 'status', 1)
        self.assert_json_equal('LABELFORM', 'title', "devis")
        self.assert_json_equal('LABELFORM', 'date', "2015-04-01")
        self.assert_json_equal('LABELFORM', 'total_excltax', 62.50)
        self.assertEqual(len(self.json_actions), 6)

        self.factory.xfer = EntryAccountList()
        self.calljson('/diacamma.accounting/entryAccountList',
                      {'year': '1', 'journal': '0', 'filter': '0'}, False)
        self.assert_observer('core.custom', 'diacamma.accounting', 'entryAccountList')
        self.assert_count_equal('entryline', 0)

        self.factory.xfer = BillToBill()
        self.calljson('/diacamma.invoice/billToBill',
                      {'bill': 1}, False)
        self.assert_observer('core.custom', 'diacamma.invoice', 'billToBill')
        self.assert_count_equal('', 4)
        self.assert_json_equal('DATE', 'billdate', '')
        self.assert_json_equal('MEMO', 'comment', '')

        self.factory.xfer = BillToBill()
        self.calljson('/diacamma.invoice/billToBill',
                      {'CONFIRME': 'YES', 'bill': 1, 'billdate': '2015-04-10', 'comment': 'blablabla'}, False)
        self.assert_observer('core.acknowledge', 'diacamma.invoice', 'billToBill')
        self.assertEqual(self.response_json['action']['id'], "diacamma.invoice/billShow")
        self.assertEqual(len(self.response_json['action']['params']), 1)
        self.assertEqual(self.response_json['action']['params']['bill'], 2)

        self.factory.xfer = BillList()
        self.calljson('/diacamma.invoice/billList', {'status_filter': -1}, False)
        self.assert_observer('core.custom', 'diacamma.invoice', 'billList')
        self.assert_count_equal('bill', 1)
        self.factory.xfer = BillList()
        self.calljson('/diacamma.invoice/billList', {'status_filter': 0}, False)
        self.assert_observer('core.custom', 'diacamma.invoice', 'billList')
        self.assert_count_equal('bill', 1)
        self.factory.xfer = BillList()
        self.calljson('/diacamma.invoice/billList', {'status_filter': 1}, False)
        self.assert_observer('core.custom', 'diacamma.invoice', 'billList')
        self.assert_count_equal('bill', 0)
        self.factory.xfer = BillList()
        self.calljson('/diacamma.invoice/billList', {'status_filter': 2}, False)
        self.assert_observer('core.custom', 'diacamma.invoice', 'billList')
        self.assert_count_equal('bill', 0)
        self.factory.xfer = BillList()
        self.calljson('/diacamma.invoice/billList', {'status_filter': 3}, False)
        self.assert_observer('core.custom', 'diacamma.invoice', 'billList')
        self.assert_count_equal('bill', 1)

        self.factory.xfer = BillShow()
        self.calljson('/diacamma.invoice/billShow', {'bill': 2}, False)
        self.assert_observer('core.custom', 'diacamma.invoice', 'billShow')
        self.assert_count_equal('', 14)
        self.assert_json_equal('LABELFORM', 'total_excltax', 62.50)
        self.assert_json_equal('LABELFORM', 'num_txt', None)
        self.assert_json_equal('LABELFORM', 'status', 0)
        self.assert_json_equal('LABELFORM', 'title', "facture")
        self.assert_json_equal('LABELFORM', 'date', '2015-04-10')
        self.assert_json_equal('LABELFORM', 'comment', 'blablabla')
        self.assert_action_equal('GET', self.get_json_path('#parentbill/action'), ("origine", "diacamma.invoice/images/origin.png",
                                                                                   "diacamma.invoice", "billShow", 0, 1, 1, {'bill': 1}))

    def test_cart_to_quotation(self):
        Params.setvalue('invoice-cart-active', True)
        Params.setvalue('invoice-order-mode', 1)
        default_articles()
        default_paymentmethod()
        self._create_bill([{'article': 1, 'designation': 'article 1',
                            'price': '22.50', 'quantity': 3, 'reduce': '5.0'}], 5, '2015-04-01', 6, False)
        cart_bill = Bill.objects.get(id=1)
        cart_bill.status = 1
        cart_bill.save()

        self.factory.xfer = EntryAccountList()
        self.calljson('/diacamma.accounting/entryAccountList',
                      {'year': '1', 'journal': '0', 'filter': '0'}, False)
        self.assert_observer('core.custom', 'diacamma.accounting', 'entryAccountList')
        self.assert_count_equal('entryline', 0)

        self.factory.xfer = BillList()
        self.calljson('/diacamma.invoice/billList', {'status_filter': -1, 'type_filter': 0}, False)
        self.assert_observer('core.custom', 'diacamma.invoice', 'billList')
        self.assert_select_equal('type_filter', {'-1': None, '0': "devis", '1': "facture", '2': "avoir", '3': "reçu", '4': "commande", '5': "panier"})
        self.assert_count_equal('bill', 0)

        self.factory.xfer = BillShow()
        self.calljson('/diacamma.invoice/billShow', {'bill': 1}, False)
        self.assert_observer('core.custom', 'diacamma.invoice', 'billShow')
        self.assert_json_equal('LABELFORM', 'status', 1)
        self.assert_json_equal('LABELFORM', 'title', "panier")
        self.assert_json_equal('LABELFORM', 'total_excltax', 62.50)
        self.assertEqual(len(self.json_actions), 5)

        self.factory.xfer = BillToQuotation()
        self.calljson('/diacamma.invoice/billToQuotation', {'bill': 1}, False)
        self.assert_observer('core.dialogbox', 'diacamma.invoice', 'billToQuotation')

        self.factory.xfer = BillToQuotation()
        self.calljson('/diacamma.invoice/billToQuotation', {'bill': 1, 'CONFIRME': 'YES'}, False)
        self.assert_observer('core.acknowledge', 'diacamma.invoice', 'billToQuotation')
        self.assertEqual(self.response_json['action']['id'], "diacamma.invoice/billShow")
        self.assertEqual(len(self.response_json['action']['params']), 1)
        self.assertEqual(self.response_json['action']['params']['bill'], 2)

        self.factory.xfer = BillShow()
        self.calljson('/diacamma.invoice/billShow', {'bill': 2}, False)
        self.assert_observer('core.custom', 'diacamma.invoice', 'billShow')
        self.assert_json_equal('LABELFORM', 'status', 0)
        self.assert_json_equal('LABELFORM', 'title', "devis")
        self.assert_json_equal('LABELFORM', 'total_excltax', 62.50)
        self.assertEqual(len(self.json_actions), 3)

        self.factory.xfer = EntryAccountList()
        self.calljson('/diacamma.accounting/entryAccountList',
                      {'year': '1', 'journal': '0', 'filter': '0'}, False)
        self.assert_observer('core.custom', 'diacamma.accounting', 'entryAccountList')
        self.assert_count_equal('entryline', 0)

    def test_clone_quotation(self):
        default_articles()
        self._create_bill([{'article': 1, 'designation': 'article 1',
                            'price': '22.50', 'quantity': 3, 'reduce': '5.0'}], 0, '2015-04-01', 6, True)
        self._create_bill([{'article': 2, 'designation': 'article 2',
                            'price': '11.10', 'quantity': 2}], 0, '2015-04-01', 6, True)
        self.factory.xfer = BillTransitionArchive()
        self.calljson('/diacamma.invoice/billTransitionArchive',
                      {'CONFIRME': 'YES', 'bill': 2, 'TRANSITION': 'archive'}, False)
        self.assert_observer('core.acknowledge', 'diacamma.invoice', 'billTransitionArchive')

        self.factory.xfer = EntryAccountList()
        self.calljson('/diacamma.accounting/entryAccountList',
                      {'year': '1', 'journal': '0', 'filter': '0'}, False)
        self.assert_observer('core.custom', 'diacamma.accounting', 'entryAccountList')
        self.assert_count_equal('entryline', 0)

        self.factory.xfer = BillList()
        self.calljson('/diacamma.invoice/billList', {'status_filter': -2, 'type_filter': 0}, False)
        self.assert_observer('core.custom', 'diacamma.invoice', 'billList')
        self.assert_count_equal('bill', 2)
        self.assert_json_equal('', 'bill/@0/bill_type', 0)
        self.assert_json_equal('', 'bill/@0/status', 1)
        self.assert_json_equal('', 'bill/@0/third', 'Dalton Jack')
        self.assert_json_equal('', 'bill/@0/total', 62.5)
        self.assert_json_equal('', 'bill/@1/bill_type', 0)
        self.assert_json_equal('', 'bill/@1/status', 3)
        self.assert_json_equal('', 'bill/@1/third', 'Dalton Jack')
        self.assert_json_equal('', 'bill/@1/total', 22.2)

        self.factory.xfer = BillCloneQuotation()
        self.calljson('/diacamma.invoice/billCloneQuotation', {'bill': 1}, False)
        self.assert_observer('core.dialogbox', 'diacamma.invoice', 'billCloneQuotation')

        self.factory.xfer = BillCloneQuotation()
        self.calljson('/diacamma.invoice/billCloneQuotation', {'bill': 1, "CONFIRME": "YES"}, False)
        self.assert_observer('core.acknowledge', 'diacamma.invoice', 'billCloneQuotation')

        self.factory.xfer = BillCloneQuotation()
        self.calljson('/diacamma.invoice/billCloneQuotation', {'bill': 2, "CONFIRME": "YES"}, False)
        self.assert_observer('core.acknowledge', 'diacamma.invoice', 'billCloneQuotation')

        self.factory.xfer = BillList()
        self.calljson('/diacamma.invoice/billList', {'status_filter': -2, 'type_filter': 0}, False)
        self.assert_observer('core.custom', 'diacamma.invoice', 'billList')
        self.assert_count_equal('bill', 4)
        self.assert_json_equal('', 'bill/@0/bill_type', 0)
        self.assert_json_equal('', 'bill/@0/status', 0)
        self.assert_json_equal('', 'bill/@0/third', 'Dalton Jack')
        self.assert_json_equal('', 'bill/@0/total', 62.5)
        self.assert_json_equal('', 'bill/@1/bill_type', 0)
        self.assert_json_equal('', 'bill/@1/status', 0)
        self.assert_json_equal('', 'bill/@1/third', 'Dalton Jack')
        self.assert_json_equal('', 'bill/@1/total', 22.2)
        self.assert_json_equal('', 'bill/@2/bill_type', 0)
        self.assert_json_equal('', 'bill/@2/status', 1)
        self.assert_json_equal('', 'bill/@2/third', 'Dalton Jack')
        self.assert_json_equal('', 'bill/@2/total', 62.5)
        self.assert_json_equal('', 'bill/@3/bill_type', 0)
        self.assert_json_equal('', 'bill/@3/status', 3)
        self.assert_json_equal('', 'bill/@3/third', 'Dalton Jack')
        self.assert_json_equal('', 'bill/@3/total', 22.2)

        self.factory.xfer = EntryAccountList()
        self.calljson('/diacamma.accounting/entryAccountList',
                      {'year': '1', 'journal': '0', 'filter': '0'}, False)
        self.assert_observer('core.custom', 'diacamma.accounting', 'entryAccountList')
        self.assert_count_equal('entryline', 0)

    def test_quotation_to_order(self):
        Params.setvalue('invoice-order-mode', 1)
        default_articles()
        self._create_bill([{'article': 1, 'designation': 'article 1',
                            'price': '22.50', 'quantity': 3, 'reduce': '5.0'}], 0, '2015-04-01', 6, True)

        self.factory.xfer = EntryAccountList()
        self.calljson('/diacamma.accounting/entryAccountList',
                      {'year': '1', 'journal': '0', 'filter': '0'}, False)
        self.assert_observer('core.custom', 'diacamma.accounting', 'entryAccountList')
        self.assert_count_equal('entryline', 0)

        self.factory.xfer = BillList()
        self.calljson('/diacamma.invoice/billList', {'status_filter': -1, 'type_filter': 4}, False)
        self.assert_observer('core.custom', 'diacamma.invoice', 'billList')
        self.assert_select_equal('type_filter', {'-1': None, '0': "devis", '1': "facture", '2': "avoir", '3': "reçu", '4': "commande"})
        self.assert_count_equal('bill', 0)

        self.factory.xfer = BillShow()
        self.calljson('/diacamma.invoice/billShow', {'bill': 1}, False)
        self.assert_observer('core.custom', 'diacamma.invoice', 'billShow')
        self.assert_json_equal('LABELFORM', 'status', 1)
        self.assert_json_equal('LABELFORM', 'title', "devis")
        self.assert_json_equal('LABELFORM', 'total_excltax', 62.50)
        self.assertEqual(len(self.json_actions), 7)

        self.factory.xfer = BillToOrder()
        self.calljson('/diacamma.invoice/billToOrder', {'bill': 1}, False)
        self.assert_observer('core.custom', 'diacamma.invoice', 'billToOrder')
        self.assert_count_equal('', 3 + 6 + 0)
        self.assert_json_equal('', 'withpayoff', True)
        self.assert_json_equal('', 'amount', '62.50')

        self.factory.xfer = BillToOrder()
        self.calljson('/diacamma.invoice/billToOrder', {'bill': 1, 'CONFIRME': 'YES',
                                                        'withpayoff': True, 'amount': '30.00', 'date_payoff': '2015-04-07', 'mode': 1,
                                                        'reference': 'abc123', 'bank_account': 2, 'payer': "Ma'a Dalton", 'bank_fee': '0.0',
                                                        "sendemail_quotation": False}, False)
        self.assert_observer('core.acknowledge', 'diacamma.invoice', 'billToOrder')
        self.assertEqual(self.response_json['action']['id'], "diacamma.invoice/billShow")
        self.assertEqual(len(self.response_json['action']['params']), 1)
        self.assertEqual(self.response_json['action']['params']['bill'], 2)

        self.factory.xfer = BillShow()
        self.calljson('/diacamma.invoice/billShow', {'bill': 2}, False)
        self.assert_observer('core.custom', 'diacamma.invoice', 'billShow')
        self.assert_json_equal('LABELFORM', 'status', 1)
        self.assert_json_equal('LABELFORM', 'title', "commande")
        self.assert_json_equal('LABELFORM', 'total_excltax', 62.50)
        self.assert_json_equal('LABELFORM', 'total_payed', 30.00)
        self.assert_json_equal('LABELFORM', 'total_rest_topay', 32.50)
        self.assertEqual(len(self.json_actions), 5)

        self.factory.xfer = EntryAccountList()
        self.calljson('/diacamma.accounting/entryAccountList',
                      {'year': '1', 'journal': '0', 'filter': '0'}, False)
        self.assert_observer('core.custom', 'diacamma.accounting', 'entryAccountList')
        self.assert_count_equal('entryline', 2)
        self.assert_json_equal('', 'entryline/@0/designation_ref', 'règlement de Commande A-1')
        self.assert_json_equal('', 'entryline/@0/entry_account', '[411 Dalton Jack]')
        self.assert_json_equal('', 'entryline/@0/credit', 30.0)
        self.assert_json_equal('', 'entryline/@0/link', None)
        self.assert_json_equal('', 'entryline/@1/designation_ref', 'règlement de Commande A-1{[br/]}chèque : abc123')
        self.assert_json_equal('', 'entryline/@1/entry_account', '[581] 581')
        self.assert_json_equal('', 'entryline/@1/debit', -30.0)
        self.assert_json_equal('', 'entryline/@1/link', None)

    def test_quotation_to_order_with_user(self):
        Params.setvalue('invoice-order-mode', 1)
        default_articles()
        self._create_bill([{'article': 1, 'designation': 'article 1',
                            'price': '22.50', 'quantity': 3, 'reduce': '5.0'}], 0, '2015-04-01', 6, True)
        self._add_create_log(1)

        self.factory.xfer = BillToOrder()
        self.calljson('/diacamma.invoice/billToOrder', {'bill': 1}, False)
        self.assert_observer('core.custom', 'diacamma.invoice', 'billToOrder')
        self.assert_count_equal('', 3 + 6 + 0)
        self.assert_json_equal('', 'withpayoff', True)
        self.assert_json_equal('', 'amount', '62.50')

        configSMTP('localhost', 2125)
        server = TestReceiver()
        server.start(2125)
        try:
            default_area()
            self.assertEqual(0, server.count())

            self.factory.xfer = BillToOrder()
            self.calljson('/diacamma.invoice/billToOrder', {'bill': 1}, False)
            self.assert_observer('core.custom', 'diacamma.invoice', 'billToOrder')
            self.assert_count_equal('', 3 + 6 + 5)
            self.assert_json_equal('', 'withpayoff', True)
            self.assert_json_equal('', 'amount', '62.50')
            self.assert_json_equal('', 'sendemail_quotation', True)
            self.assert_json_equal('', 'user', 'Léonard de Vinci')

            self.factory.xfer = BillToOrder()
            self.calljson('/diacamma.invoice/billToOrder', {'bill': 1, 'CONFIRME': 'YES',
                                                            'withpayoff': True, 'amount': '30.00', 'date_payoff': '2015-04-07', 'mode': 1,
                                                            'reference': 'abc123', 'bank_account': 2, 'payer': "Ma'a Dalton", 'bank_fee': '0.0',
                                                            "sendemail_quotation": True, 'subject_quotation': 'sujet quotation', 'message_quotation': 'message quotation', 'model_quotation': 8}, False)
            self.assert_observer('core.acknowledge', 'diacamma.invoice', 'billToOrder')
            msg_txt, msg, msg_file = server.check_first_message('sujet quotation', 3, {'To': 'leonardo@davinci.org'})
            self.assertEqual('text/plain', msg_txt.get_content_type())
            self.assertEqual('text/html', msg.get_content_type())
            self.assertEqual('base64', msg.get('Content-Transfer-Encoding', ''))
            self.assertEqual('<html>message quotation</html>', decode_b64(msg.get_payload()))
            self.assertTrue('commande_A-1_Dalton Jack.pdf' in msg_file.get('Content-Type', ''), msg_file.get('Content-Type', ''))
            self.save_pdf(base64_content=msg_file.get_payload())
        finally:
            server.stop()

    def test_quotation_to_order_by_link(self):
        Params.setvalue('invoice-order-mode', 2)
        default_articles()
        self._create_bill([{'article': 1, 'designation': 'article 1',
                            'price': '22.50', 'quantity': 3, 'reduce': '5.0'}], 0, '2015-04-01', 6, True)

        self.factory.xfer = BillList()
        self.calljson('/diacamma.invoice/billList', {'status_filter': -2, 'type_filter': -1}, False)
        self.assert_observer('core.custom', 'diacamma.invoice', 'billList')
        self.assert_count_equal('bill', 1)
        self.assert_json_equal('', 'bill/@0/bill_type', 0)
        self.assert_json_equal('', 'bill/@0/status', 1)
        self.assert_json_equal('', 'bill/@0/third', 'Dalton Jack')
        self.assert_json_equal('', 'bill/@0/total', 62.5)

        configSMTP('localhost', 2125)
        server = TestReceiver()
        server.start(2125)
        try:
            default_area()
            self.assertEqual(0, server.count())

            self.factory.xfer = PayableEmail()
            self.calljson('/diacamma.payoff/payableEmail',
                          {'bill': 1, 'OK': 'YES', 'item_name': 'bill', 'subject': 'my bill', 'message': 'this is a bill.', 'model': 8}, False)
            self.assert_observer('core.acknowledge', 'diacamma.payoff', 'payableEmail')

            self.assertEqual(1, server.count())
            _msg_txt, msg, _msg_file = server.check_first_message('my bill', 3, {'To': 'Jack.Dalton@worldcompany.com'})
            self.assertEqual('base64', msg.get('Content-Transfer-Encoding', ''))
            self.assertEqual("""<html>this is a bill.<hr/><center><i><u>Moyens de paiement</u></i></center><table width='90%'><tr><td><b>Validation de devis sans paiement</b></td><td><center>
En cliquant ici, vous acceptez ce devis, merci de nous envoyer votre règlement au plus tôt pour finaliser cette transaction.<br>
<a href='http://testserver/diacamma.invoice/invoiceValidQuotation?payid=1' name='validate' target='_blank'>
<button>
<img src="http://testserver/static/lucterios.CORE/images/ok.png" title="Ok" alt="Ok"> validation
</button>
</a>
</center></td></tr><tr></tr></table></html>""", decode_b64(msg.get_payload()))

            self.call_ex('/diacamma.invoice/invoiceValidQuotation', {'payid': 1}, 'get', 200)
            self.assertTrue(self.content.startswith("<!DOCTYPE html>"), self.content)
            self.assertIn('form method="post" id="validation" name="validation" action="http://testserver/diacamma.invoice/invoiceValidQuotation"', self.content)
            self.assertIn('input type="hidden" name="payid" value="1"', self.content)
            self.assertIn('input type="hidden" name="CONFIRME" value="True"', self.content)
            self.assertIn('input type="text" name="firstname" required="required"', self.content)
            self.assertIn('input type="text" name="lastname" required="required"', self.content)
            self.assertIn('img src="http://testserver/static/lucterios.CORE/images/ok.png" title="Ok" alt="Ok"', self.content)

            self.call_ex('/diacamma.invoice/invoiceValidQuotation', {'payid': 1, 'CONFIRME': 'True', 'firstname': 'Jean', 'lastname': 'Valjean'}, 'post', 200)
            self.assertTrue(self.content.startswith("<!DOCTYPE html>"), self.content)
            self.assertIn('devis validé par Jean Valjean', self.content)

            self.assertEqual(2, server.count())

            self.factory.xfer = BillList()
            self.calljson('/diacamma.invoice/billList', {'status_filter': -2, 'type_filter': -1}, False)
            self.assert_observer('core.custom', 'diacamma.invoice', 'billList')
            self.assert_count_equal('bill', 2)
            self.assert_json_equal('', 'bill/@0/bill_type', 4)
            self.assert_json_equal('', 'bill/@0/status', 1)
            self.assert_json_equal('', 'bill/@0/third', 'Dalton Jack')
            self.assert_json_equal('', 'bill/@0/total', 62.5)
            self.assert_json_equal('', 'bill/@0/num_txt', 'A-1')
            self.assert_json_equal('', 'bill/@0/comment', "{[i]}commande venant de la validation de devis A-1 par Jean Valjean le", True)
            self.assert_json_equal('', 'bill/@1/bill_type', 0)
            self.assert_json_equal('', 'bill/@1/status', 3)
            self.assert_json_equal('', 'bill/@1/third', 'Dalton Jack')
            self.assert_json_equal('', 'bill/@1/total', 62.5)
            self.assert_json_equal('', 'bill/@1/num_txt', 'A-1')
        finally:
            server.stop()

    def test_quotation_to_order_by_link_and_mailing(self):
        Params.setvalue('invoice-order-mode', 2)
        default_articles()
        self._create_bill([{'article': 1, 'designation': 'article 1',
                            'price': '22.50', 'quantity': 3, 'reduce': '5.0'}], 0, '2015-04-01', 6, True)
        self._create_bill([{'article': 1, 'designation': 'article 1',
                            'price': '15.0', 'quantity': 2, 'reduce': '0.0'}], 0, '2015-04-02', 6, True)

        self.factory.xfer = BillList()
        self.calljson('/diacamma.invoice/billList', {'status_filter': -2, 'type_filter': -1}, False)
        self.assert_observer('core.custom', 'diacamma.invoice', 'billList')
        self.assert_count_equal('bill', 2)
        self.assert_json_equal('', 'bill/@0/bill_type', 0)
        self.assert_json_equal('', 'bill/@0/status', 1)
        self.assert_json_equal('', 'bill/@0/date', "2015-04-02")
        self.assert_json_equal('', 'bill/@0/third', 'Dalton Jack')
        self.assert_json_equal('', 'bill/@0/total', 30.0)
        self.assert_json_equal('', 'bill/@1/bill_type', 0)
        self.assert_json_equal('', 'bill/@1/status', 1)
        self.assert_json_equal('', 'bill/@1/date', "2015-04-01")
        self.assert_json_equal('', 'bill/@1/third', 'Dalton Jack')
        self.assert_json_equal('', 'bill/@1/total', 62.5)

        configSMTP('localhost', 2125)
        server = TestReceiver()
        server.start(2125)
        try:
            self.factory.xfer = PayableEmail()
            self.calljson('/diacamma.payoff/payableEmail',
                          {'bill': '1;2', 'OK': 'YES', 'item_name': 'bill', 'subject': '#reference', 'message': '#name{[br/]}{[br/]}Veuillez trouver joint à ce courriel #doc.{[br/]}{[br/]}Sincères salutations', 'model': 8}, False)
            self.assert_observer('core.acknowledge', 'diacamma.payoff', 'payableEmail')

            email_msg = Message.objects.get(id=1)
            self.assertEqual(email_msg.subject, '#reference')
            self.assertEqual(email_msg.body, '#name{[br/]}{[br/]}Veuillez trouver joint à ce courriel #doc.{[br/]}{[br/]}Sincères salutations#footer')
            self.assertEqual(email_msg.status, 2)
            self.assertEqual(email_msg.recipients, "invoice.Bill id||8||1;2\n")
            self.assertEqual(email_msg.email_to_send, "invoice.Bill:1:8\ninvoice.Bill:2:8")

            self.assertEqual(1, len(LucteriosScheduler.get_list()))
            LucteriosScheduler.stop_scheduler()
            email_msg.sendemail(10, "http://testserver")
            self.assertEqual(2, server.count())
            for msg_index in range(2):
                data = {'ident': msg_index + 1}
                _msg_txt, msg, _msg_file = server.get_msg_index(msg_index, 'Devis A-%(ident)d' % data)
                message = decode_b64(msg.get_payload())
                self.assertIn('Jack Dalton<br/><br/>Veuillez trouver joint à ce courriel devis_A-%(ident)d_Dalton Jack.pdf.<br/><br/>Sincères salutations' % data, message)
                self.assertIn("<center><i><u>Moyens de paiement</u></i></center>", message)
                self.assertIn("<a href='http://testserver/diacamma.invoice/invoiceValidQuotation?payid=%(ident)d' name='validate' target='_blank'>" % data, message)
        finally:
            server.stop()

    def test_valid_bill_with_user(self):
        Params.setvalue('invoice-order-mode', 1)
        Params.setvalue('invoice-default-nbpayoff', 2)
        Params.setvalue('invoice-default-send-pdf', True)
        default_articles()
        quotation_id = self._create_bill([{'article': 1, 'designation': 'article 1',
                                           'price': '22.50', 'quantity': 3, 'reduce': '5.0'}], 0, '2015-04-01', 6, True)
        self._add_create_log(quotation_id)
        order_id = self._create_bill([{'article': 1, 'designation': 'article 1',
                                       'price': '22.50', 'quantity': 3, 'reduce': '5.0'}], 4, '2015-04-01', 6, True)
        order = Bill.objects.get(id=order_id)
        order.parentbill_id = quotation_id
        order.save()
        bill_id = self._create_bill([{'article': 1, 'designation': 'article 1',
                                      'price': '22.50', 'quantity': 3, 'reduce': '5.0'}], 1, '2015-04-01', 6, False)
        bill = Bill.objects.get(id=bill_id)
        bill.parentbill_id = order_id
        bill.save()
        self.factory.xfer = BillAddModify()
        self.calljson('/diacamma.invoice/billAddModify',
                      {'bill': bill_id, 'date': '2015-04-02', 'SAVE': 'YES'}, False)
        self.assert_observer('core.acknowledge', 'diacamma.invoice', 'billAddModify')

        self.factory.xfer = BillTransition()
        self.calljson('/diacamma.invoice/billTransition', {'bill': bill_id, 'TRANSITION': 'valid', 'nbpayoff': 0}, False)
        self.assert_observer('core.custom', 'diacamma.invoice', 'billTransition')
        self.assert_count_equal('', 3 + 0 + 0 + 0)
        self.assert_json_equal('', 'nbpayoff', 0)

        self.factory.xfer = BillTransition()
        self.calljson('/diacamma.invoice/billTransition', {'bill': bill_id, 'TRANSITION': 'valid', 'nbpayoff': 1}, False)
        self.assert_observer('core.custom', 'diacamma.invoice', 'billTransition')
        self.assert_count_equal('', 3 + 6 + 0 + 0)
        self.assert_json_equal('', 'nbpayoff', 1)
        self.assert_json_equal('', 'payoff00_amount', '62.50')

        self.factory.xfer = BillTransition()
        self.calljson('/diacamma.invoice/billTransition', {'bill': bill_id, 'TRANSITION': 'valid', 'nbpayoff': 3}, False)
        self.assert_observer('core.custom', 'diacamma.invoice', 'billTransition')
        self.assert_count_equal('', 3 + 6 * 3 + 0 + 0)
        self.assert_json_equal('', 'nbpayoff', 3)
        self.assert_json_equal('', 'payoff00_amount', '62.50')
        self.assert_json_equal('', 'payoff01_amount', '0.00')
        self.assert_json_equal('', 'payoff02_amount', '0.00')

        configSMTP('localhost', 2125)
        server = TestReceiver()
        server.start(2125)
        try:
            self.factory.xfer = BillTransition()
            self.calljson('/diacamma.invoice/billTransition', {'bill': bill_id, 'TRANSITION': 'valid'}, False)
            self.assert_observer('core.custom', 'diacamma.invoice', 'billTransition')
            self.assert_count_equal('', 3 + 6 * 2 + 5 + 0)
            self.assert_json_equal('', 'nbpayoff', 2)
            self.assert_json_equal('', 'sendemail', True)

            default_area()
            self.assertEqual(0, server.count())

            self.factory.xfer = BillTransition()
            self.calljson('/diacamma.invoice/billTransition', {'bill': bill_id, 'TRANSITION': 'valid'}, False)
            self.assert_observer('core.custom', 'diacamma.invoice', 'billTransition')
            self.assert_count_equal('', 3 + 6 * 2 + 5 + 5)
            self.assert_json_equal('', 'nbpayoff', 2)
            self.assert_json_equal('', 'sendemail', True)
            self.assert_json_equal('', 'sendemail_quotation', True)

            self.factory.xfer = BillTransition()
            self.calljson('/diacamma.invoice/billTransition', {'bill': bill_id, 'TRANSITION': 'valid', 'CONFIRME': 'YES',
                                                               'nbpayoff': 0, "sendemail": False,
                                                               "sendemail_quotation": True, 'subject_quotation': 'sujet facture', 'message_quotation': 'message facture', 'model_quotation': 8}, False)
            self.assert_observer('core.acknowledge', 'diacamma.invoice', 'billTransition')
            msg_txt, msg, msg_file = server.check_first_message('sujet facture', 3, {'To': 'leonardo@davinci.org'})
            self.assertEqual('text/plain', msg_txt.get_content_type())
            self.assertEqual('text/html', msg.get_content_type())
            self.assertEqual('base64', msg.get('Content-Transfer-Encoding', ''))
            self.assertEqual('<html>message facture</html>', decode_b64(msg.get_payload()))
            self.assertTrue('facture_A-1_Dalton Jack.pdf' in msg_file.get('Content-Type', ''), msg_file.get('Content-Type', ''))
            self.save_pdf(base64_content=msg_file.get_payload())
        finally:
            server.stop()

    def test_order_to_bill(self):
        Params.setvalue('invoice-order-mode', 1)
        default_articles()
        self._create_bill([{'article': 1, 'designation': 'article 1',
                            'price': '22.50', 'quantity': 3, 'reduce': '0.0'}], 4, '2015-04-01', 6, True)
        self.factory.xfer = PayoffAddModify()
        self.calljson('/diacamma.payoff/payoffAddModify', {'SAVE': 'YES', 'supporting': 1, 'amount': '67.50', 'payer': "Ma'a Dalton", 'date': '2015-04-07', 'mode': 0, 'reference': 'abc', 'bank_account': 0}, False)
        self.assert_observer('core.acknowledge', 'diacamma.payoff', 'payoffAddModify')

        self.factory.xfer = EntryAccountList()
        self.calljson('/diacamma.accounting/entryAccountList',
                      {'year': '1', 'journal': '0', 'filter': '0'}, False)
        self.assert_observer('core.custom', 'diacamma.accounting', 'entryAccountList')
        self.assert_count_equal('entryline', 2)

        self.factory.xfer = BillShow()
        self.calljson('/diacamma.invoice/billShow', {'bill': 1}, False)
        self.assert_observer('core.custom', 'diacamma.invoice', 'billShow')
        self.assert_json_equal('LABELFORM', 'status', 1)
        self.assert_json_equal('LABELFORM', 'title', "commande")
        self.assert_json_equal('LABELFORM', 'total_excltax', 67.50)
        self.assert_json_equal('LABELFORM', 'total_payed', 67.50)
        self.assert_json_equal('LABELFORM', 'total_rest_topay', 0.0)

        self.factory.xfer = BillToBill()
        self.calljson('/diacamma.invoice/billToBill',
                      {'CONFIRME': 'YES', 'bill': 1}, False)
        self.assert_observer('core.acknowledge', 'diacamma.invoice', 'billToBill')
        self.assertEqual(self.response_json['action']['id'], "diacamma.invoice/billShow")
        self.assertEqual(len(self.response_json['action']['params']), 1)
        self.assertEqual(self.response_json['action']['params']['bill'], 2)

        self.factory.xfer = BillAddModify()
        self.calljson('/diacamma.invoice/billAddModify',
                      {'bill': 2, 'date': '2015-04-02', 'SAVE': 'YES'}, False)
        self.assert_observer('core.acknowledge', 'diacamma.invoice', 'billAddModify')

        self.factory.xfer = BillShow()
        self.calljson('/diacamma.invoice/billShow', {'bill': 2}, False)
        self.assert_observer('core.custom', 'diacamma.invoice', 'billShow')
        self.assert_json_equal('LABELFORM', 'title', "facture")
        self.assert_json_equal('LABELFORM', 'info', [])

        self.factory.xfer = BillTransition()
        self.calljson('/diacamma.invoice/billTransition',
                      {'CONFIRME': 'YES', 'bill': 2, 'TRANSITION': 'valid'}, False)
        self.assert_observer('core.acknowledge', 'diacamma.invoice', 'billTransition')

        self.factory.xfer = EntryAccountList()
        self.calljson('/diacamma.accounting/entryAccountList',
                      {'year': '1', 'journal': '0', 'filter': '0'}, False)
        self.assert_observer('core.custom', 'diacamma.accounting', 'entryAccountList')
        self.assert_count_equal('entryline', 4)
        self.assert_json_equal('', 'entryline/@0/designation_ref', 'Facture A-1')
        self.assert_json_equal('', 'entryline/@0/entry_account', '[411 Dalton Jack]')
        self.assert_json_equal('', 'entryline/@0/debit', -67.50)
        self.assert_json_equal('', 'entryline/@0/link', 'A')
        self.assert_json_equal('', 'entryline/@1/designation_ref', 'Facture A-1')
        self.assert_json_equal('', 'entryline/@1/entry_account', '[701] 701')
        self.assert_json_equal('', 'entryline/@1/credit', 67.50)
        self.assert_json_equal('', 'entryline/@1/link', None)
        self.assert_json_equal('', 'entryline/@2/designation_ref', 'règlement de Commande A-1')
        self.assert_json_equal('', 'entryline/@2/entry_account', '[411 Dalton Jack]')
        self.assert_json_equal('', 'entryline/@2/credit', 67.50)
        self.assert_json_equal('', 'entryline/@2/link', 'A')
        self.assert_json_equal('', 'entryline/@3/designation_ref', 'règlement de Commande A-1{[br/]}espèces : abc')
        self.assert_json_equal('', 'entryline/@3/entry_account', '[531] 531')
        self.assert_json_equal('', 'entryline/@3/debit', -67.50)
        self.assert_json_equal('', 'entryline/@3/link', None)

    def test_compta_asset(self):
        default_articles()
        cost = CostAccounting.objects.get(name='open')
        cost.is_default = True
        cost.save()
        self._create_bill([{'article': 0, 'designation': 'article A', 'price': '22.20', 'quantity': 3},
                           {'article': 0, 'designation': 'article B', 'price': '11.10', 'quantity': 2}], 2, '2015-04-01', 6)

        self.factory.xfer = EntryAccountList()
        self.calljson('/diacamma.accounting/entryAccountList',
                      {'year': '1', 'journal': '0', 'filter': '0'}, False)
        self.assert_observer('core.custom', 'diacamma.accounting', 'entryAccountList')
        self.assert_count_equal('entryline', 0)

        self.factory.xfer = BillTransition()
        self.calljson('/diacamma.invoice/billTransition',
                      {'CONFIRME': 'YES', 'bill': 1, 'withpayoff': False, 'TRANSITION': 'valid'}, False)
        self.assert_observer('core.acknowledge', 'diacamma.invoice', 'billTransition')

        self.factory.xfer = BillShow()
        self.calljson('/diacamma.invoice/billShow', {'bill': 1}, False)
        self.assert_observer('core.custom', 'diacamma.invoice', 'billShow')
        self.assert_count_equal('', 13)
        self.assert_json_equal('LABELFORM', 'title', "avoir")
        self.assert_json_equal('LABELFORM', 'total_excltax', 88.80)
        self.assert_json_equal('LABELFORM', 'num_txt', "A-1")
        self.assert_json_equal('LABELFORM', 'status', 1)
        self.assertEqual(len(self.json_actions), 4)

        self.factory.xfer = EntryAccountList()
        self.calljson('/diacamma.accounting/entryAccountList',
                      {'year': '1', 'journal': '0', 'filter': '0'}, False)
        self.assert_observer('core.custom', 'diacamma.accounting', 'entryAccountList')
        self.assert_count_equal('entryline', 2)

        self.assert_json_equal('', 'entryline/@0/entry.num', None)
        self.assert_json_equal('', 'entryline/@0/entry.date_entry', None)
        self.assert_json_equal('', 'entryline/@0/entry.date_value', '2015-04-01')
        self.assert_json_equal('', 'entryline/@0/link', None)
        self.assert_json_equal('', 'entryline/@0/entry_account', '[411 Dalton Jack]')
        self.assert_json_equal('', 'entryline/@0/credit', 88.80)
        self.assert_json_equal('', 'entryline/@1/entry_account', '[706] 706')
        self.assert_json_equal('', 'entryline/@1/debit', -88.80)
        self.assert_json_equal('', 'entryline/@1/costaccounting', 'open')

        self.check_list_del_archive()

    def test_compta_receive(self):
        default_articles()
        self._create_bill([{'article': 2, 'designation': 'article', 'price': '25.00', 'quantity': 1}],
                          3, '2015-04-01', 6)

        self.factory.xfer = EntryAccountList()
        self.calljson('/diacamma.accounting/entryAccountList',
                      {'year': '1', 'journal': '0', 'filter': '0'}, False)
        self.assert_observer('core.custom', 'diacamma.accounting', 'entryAccountList')
        self.assert_count_equal('entryline', 0)

        self.factory.xfer = BillTransition()
        self.calljson('/diacamma.invoice/billTransition',
                      {'CONFIRME': 'YES', 'bill': 1, 'withpayoff': False, 'TRANSITION': 'valid'}, False)
        self.assert_observer('core.acknowledge', 'diacamma.invoice', 'billTransition')

        self.factory.xfer = BillShow()
        self.calljson('/diacamma.invoice/billShow', {'bill': 1}, False)
        self.assert_observer('core.custom', 'diacamma.invoice', 'billShow')
        self.assert_count_equal('', 13)
        self.assert_json_equal('LABELFORM', 'total_excltax', 25.00)
        self.assert_json_equal('LABELFORM', 'num_txt', "A-1")
        self.assert_json_equal('LABELFORM', 'status', 1)
        self.assert_json_equal('LABELFORM', 'title', "reçu")
        self.assert_json_equal('LABELFORM', 'date', "2015-04-01")
        self.assertEqual(len(self.json_actions), 4)

        self.factory.xfer = EntryAccountList()
        self.calljson('/diacamma.accounting/entryAccountList',
                      {'year': '1', 'journal': '0', 'filter': '0'}, False)
        self.assert_observer('core.custom', 'diacamma.accounting', 'entryAccountList')
        self.assert_count_equal('entryline', 2)

        self.assert_json_equal('', 'entryline/@0/entry.num', None)
        self.assert_json_equal('', 'entryline/@0/entry.date_entry', None)
        self.assert_json_equal('', 'entryline/@0/entry.date_value', '2015-04-01')
        self.assert_json_equal('', 'entryline/@0/link', None)
        self.assert_json_equal('', 'entryline/@0/costaccounting', None)
        self.assert_json_equal('', 'entryline/@0/entry_account', "[411 Dalton Jack]")
        self.check_list_del_archive()

    def test_bill_price_with_vat(self):
        default_articles()
        Params.setvalue('invoice-vat-mode', '2')
        details = [{'article': 1, 'designation': 'article 1', 'price': '22.50', 'quantity': 3, 'reduce': '5.0'},  # code 701
                   {'article': 2, 'designation': 'article 2',  # +5% vat => 1.08 - code 707
                       'price': '3.25', 'quantity': 7},
                   {'article': 0, 'designation': 'article 3',
                       'price': '11.10', 'quantity': 2},  # code 709
                   {'article': 5, 'designation': 'article 4', 'price': '6.33', 'quantity': 3.25}]  # +20% vat => 3.43  - code 701
        self._create_bill(details, 1, '2015-04-01', 6)

        self.factory.xfer = BillShow()
        self.calljson('/diacamma.invoice/billShow', {'bill': 1}, False)

        self.assert_grid_equal('detail', {"article": "article", "designation": "désignation", "price": "prix TTC", "unit": "unité",
                                          "quantity_txt": "quantité", "storagearea": "lieu de stockage", "reduce_txt": "réduction", "total": "total TTC"}, 4)  # nb=8
        self.assert_attrib_equal('total_excltax', 'description', "total HT")
        self.assert_json_equal('LABELFORM', 'info', [])
        self.assert_attrib_equal('total_incltax', 'description', "total TTC")
        self.assert_json_equal('LABELFORM', 'total_incltax', 128.02)
        self.assert_json_equal('LABELFORM', 'vta_sum', 4.51)
        self.assert_json_equal('LABELFORM', 'total_excltax', 123.51)
        self.assert_json_equal('', '#total_incltax/formatnum', "C2EUR")
        self.assert_json_equal('', '#vta_sum/formatnum', "C2EUR")
        self.assert_json_equal('', '#total_excltax/formatnum', "C2EUR")

        self.assertEqual(len(self.json_actions), 3)

        self.factory.xfer = BillTransition()
        self.calljson('/diacamma.invoice/billTransition',
                      {'CONFIRME': 'YES', 'bill': 1, 'withpayoff': False, 'TRANSITION': 'valid'}, False)
        self.assert_observer('core.acknowledge', 'diacamma.invoice', 'billTransition')

        self.factory.xfer = EntryAccountList()
        self.calljson('/diacamma.accounting/entryAccountList',
                      {'year': '1', 'journal': '0', 'filter': '0'}, False)
        self.assert_observer('core.custom', 'diacamma.accounting', 'entryAccountList')
        self.assert_count_equal('entryline', 6)
        self.assert_json_equal('', 'entryline/@0/entry_account', "[411 Dalton Jack]")
        self.assert_json_equal('', 'entryline/@1/entry_account', "[4455] 4455")
        self.assert_json_equal('', 'entryline/@1/credit', 4.51)
        self.assert_json_equal('LABELFORM', 'result', [123.51, 0.00, 123.51, 0.00, 0.00])

        self.factory.xfer = BillList()
        self.calljson('/diacamma.invoice/billList', {}, False)
        self.assert_observer('core.custom', 'diacamma.invoice', 'billList')
        self.assert_grid_equal('bill', {"bill_type": "type de facture", "num_txt": "N°", "date": "date", "third": "tiers", "comment": "commentaire", "total": "total TTC", "status": "statut"}, 1)  # nb=7

    def test_bill_price_without_vat(self):
        default_articles()
        Params.setvalue('invoice-vat-mode', '1')
        details = [{'article': 1, 'designation': 'article 1', 'price': '22.50', 'quantity': 3, 'reduce': '5.0'},
                   {'article': 2, 'designation': 'article 2',  # +5% vat => 1.14
                       'price': '3.25', 'quantity': 7},
                   {'article': 0, 'designation': 'article 3',
                       'price': '11.10', 'quantity': 2},
                   {'article': 5, 'designation': 'article 4', 'price': '6.33', 'quantity': 3.25}]  # +20% vat => 4.11
        self._create_bill(details, 1, '2015-04-01', 6)

        self.factory.xfer = BillShow()
        self.calljson('/diacamma.invoice/billShow', {'bill': 1}, False)

        self.assert_grid_equal('detail', {"article": "article", "designation": "désignation", "price": "prix HT", "unit": "unité",
                                          "quantity_txt": "quantité", "storagearea": "lieu de stockage", "reduce_txt": "réduction", "total": "total HT"}, 4)  # nb=8
        self.assert_json_equal('', '#detail/headers/@2/@0', "price")
        self.assert_json_equal('', '#detail/headers/@2/@2', "C2EUR")
        self.assert_json_equal('', '#detail/headers/@7/@0', "total")
        self.assert_json_equal('', '#detail/headers/@7/@2', "C2EUR")

        self.assert_attrib_equal('total_excltax', 'description', "total HT")
        self.assert_json_equal('LABELFORM', 'info', [])
        self.assert_attrib_equal('total_incltax', 'description', "total TTC")
        self.assert_json_equal('LABELFORM', 'total_incltax', 133.27)
        self.assert_json_equal('LABELFORM', 'vta_sum', 5.25)
        self.assert_json_equal('LABELFORM', 'total_excltax', 128.02)

        self.assertEqual(len(self.json_actions), 3)

        self.factory.xfer = BillTransition()
        self.calljson('/diacamma.invoice/billTransition',
                      {'CONFIRME': 'YES', 'bill': 1, 'withpayoff': False, 'TRANSITION': 'valid'}, False)
        self.assert_observer('core.acknowledge', 'diacamma.invoice', 'billTransition')

        self.factory.xfer = EntryAccountList()
        self.calljson('/diacamma.accounting/entryAccountList',
                      {'year': '1', 'journal': '0', 'filter': '0'}, False)
        self.assert_observer('core.custom', 'diacamma.accounting', 'entryAccountList')
        self.assert_count_equal('entryline', 6)
        self.assert_json_equal('', 'entryline/@0/entry_account', "[411 Dalton Jack]")
        self.assert_json_equal('', 'entryline/@0/debit', -133.27)
        self.assert_json_equal('', 'entryline/@1/entry_account', "[4455] 4455")
        self.assert_json_equal('', 'entryline/@1/credit', 5.25)
        self.assert_json_equal('', 'entryline/@2/entry_account', "[701] 701")
        self.assert_json_equal('', 'entryline/@2/credit', 88.07)
        self.assert_json_equal('', 'entryline/@3/entry_account', "[706] 706")
        self.assert_json_equal('', 'entryline/@3/credit', 22.20)
        self.assert_json_equal('', 'entryline/@4/entry_account', "[707] 707")
        self.assert_json_equal('', 'entryline/@4/credit', 22.75)
        self.assert_json_equal('', 'entryline/@5/entry_account', "[709] 709")
        self.assert_json_equal('', 'entryline/@5/debit', -5.00)
        self.assert_json_equal('LABELFORM', 'result', [128.02, 0.00, 128.02, 0.00, 0.00])

        self.factory.xfer = BillList()
        self.calljson('/diacamma.invoice/billList', {}, False)
        self.assert_observer('core.custom', 'diacamma.invoice', 'billList')
        self.assert_grid_equal('bill', {"bill_type": "type de facture", "num_txt": "N°", "date": "date", "third": "tiers", "comment": "commentaire", "total": "total HT", "status": "statut"}, 1)  # nb=7

    def test_list_sorted(self):
        default_articles()
        details = [{'article': 0, 'designation': 'article 0', 'price': '20.00', 'quantity': 15}]
        self._create_bill(details, 0, '2015-04-01', 6, True)  # 59.50
        details = [{'article': 1, 'designation': 'article 1', 'price': '22.00', 'quantity': 3, 'reduce': '5.0'},
                   {'article': 2, 'designation': 'article 2', 'price': '3.25', 'quantity': 7}]
        self._create_bill(details, 1, '2015-04-01', 6, True)  # 83.75
        details = [{'article': 0, 'designation': 'article 0', 'price': '50.00', 'quantity': 2},
                   {'article': 5, 'designation': 'article 5', 'price': '6.33', 'quantity': 6.75}]
        self._create_bill(details, 3, '2015-04-01', 4, True)  # 142.73
        details = [{'article': 1, 'designation': 'article 1', 'price': '23.00', 'quantity': 3},
                   {'article': 5, 'designation': 'article 5', 'price': '6.33', 'quantity': 3.50}]
        self._create_bill(details, 1, '2015-04-01', 5, True)  # 91.16
        details = [{'article': 2, 'designation': 'article 2', 'price': '3.30', 'quantity': 5},
                   {'article': 5, 'designation': 'article 5', 'price': '6.35', 'quantity': 4.25, 'reduce': '2.0'}]
        self._create_bill(details, 1, '2015-04-01', 6, True)  # 41.49
        details = [{'article': 5, 'designation': 'article 5', 'price': '6.33', 'quantity': 1.25}]
        self._create_bill(details, 2, '2015-04-01', 4, True)  # 7.91

        self.factory.xfer = BillList()
        self.calljson('/diacamma.invoice/billList', {}, False)
        self.assert_observer('core.custom', 'diacamma.invoice', 'billList')
        self.assert_count_equal('bill', 6)
        self.assert_json_equal('', 'bill/@0/third', 'Dalton Jack')
        self.assert_json_equal('', 'bill/@1/third', 'Dalton Jack')
        self.assert_json_equal('', 'bill/@2/third', 'Minimum')
        self.assert_json_equal('', 'bill/@3/third', 'Dalton William')
        self.assert_json_equal('', 'bill/@4/third', 'Dalton Jack')
        self.assert_json_equal('', 'bill/@5/third', 'Minimum')

        self.factory.xfer = BillList()
        self.calljson('/diacamma.invoice/billList', {'GRID_ORDER%bill': 'third'}, False)
        self.assert_observer('core.custom', 'diacamma.invoice', 'billList')
        self.assert_json_equal('', 'bill/@0/third', 'Dalton Jack')
        self.assert_json_equal('', 'bill/@1/third', 'Dalton Jack')
        self.assert_json_equal('', 'bill/@2/third', 'Dalton Jack')
        self.assert_json_equal('', 'bill/@3/third', 'Dalton William')
        self.assert_json_equal('', 'bill/@4/third', 'Minimum')
        self.assert_json_equal('', 'bill/@5/third', 'Minimum')

        self.factory.xfer = BillList()
        self.calljson('/diacamma.invoice/billList', {'GRID_ORDER%bill': 'third', 'GRID_ORDER%bill_third': '+'}, False)
        self.assert_observer('core.custom', 'diacamma.invoice', 'billList')
        self.assert_json_equal('', 'bill/@5/third', 'Dalton Jack')
        self.assert_json_equal('', 'bill/@4/third', 'Dalton Jack')
        self.assert_json_equal('', 'bill/@3/third', 'Dalton Jack')
        self.assert_json_equal('', 'bill/@2/third', 'Dalton William')
        self.assert_json_equal('', 'bill/@1/third', 'Minimum')
        self.assert_json_equal('', 'bill/@0/third', 'Minimum')

    def test_statistic(self):
        default_articles()
        details = [{'article': 0, 'designation': 'article 0', 'price': '20.00', 'quantity': 15, 'reduce': '15.0'}]
        self._create_bill(details, 0, '2015-01-01', 6, True)  # 59.50
        details = [{'article': 1, 'designation': 'article 1', 'price': '22.00', 'quantity': 3, 'reduce': '5.0'},
                   {'article': 2, 'designation': 'article 2', 'price': '3.25', 'quantity': 7}]
        self._create_bill(details, 1, '2015-02-01', 6, True)  # 83.75
        details = [{'article': 0, 'designation': 'article 0', 'price': '50.00', 'quantity': 2},
                   {'article': 5, 'designation': 'article 5', 'price': '6.33', 'quantity': 6.75}]
        self._create_bill(details, 3, '2015-03-01', 4, True)  # 142.73
        details = [{'article': 1, 'designation': 'article 1', 'price': '23.00', 'quantity': 3},
                   {'article': 5, 'designation': 'article 5', 'price': '6.33', 'quantity': 3.50}]
        self._create_bill(details, 1, '2015-04-01', 5, True)  # 91.16
        details = [{'article': 2, 'designation': 'article 2', 'price': '3.30', 'quantity': 5},
                   {'article': 5, 'designation': 'article 5', 'price': '6.35', 'quantity': 4.25, 'reduce': '2.0'}]
        self._create_bill(details, 1, '2015-05-01', 6, True)  # 41.49
        details = [{'article': 5, 'designation': 'article 5', 'price': '6.33', 'quantity': 1.25}]
        self._create_bill(details, 2, '2015-06-01', 4, True)  # 7.91

        self.factory.xfer = BillStatistic()
        self.calljson('/diacamma.invoice/billStatistic', {}, False)
        self.assert_observer('core.custom', 'diacamma.invoice', 'billStatistic')
        self.assert_count_equal('', 16)

        self.assert_count_equal('articles', 5)
        self.assert_json_equal('', 'articles/@0/article', "ABC1")
        self.assert_json_equal('', 'articles/@0/amount', 130.00)
        self.assert_json_equal('', 'articles/@0/number', 6.00)
        self.assert_json_equal('', 'articles/@1/article', "---")
        self.assert_json_equal('', 'articles/@1/amount', 100.00)
        self.assert_json_equal('', 'articles/@1/number', 2.00)
        self.assert_json_equal('', 'articles/@1/mean', 50.00)
        self.assert_json_equal('', 'articles/@1/ratio', 28.47)

        self.assert_json_equal('', 'articles/@2/article', "ABC5")
        self.assert_json_equal('', 'articles/@2/amount', 81.97)
        self.assert_json_equal('', 'articles/@2/number', 13.25)
        self.assert_json_equal('', 'articles/@3/article', "ABC2")
        self.assert_json_equal('', 'articles/@3/amount', 39.25)
        self.assert_json_equal('', 'articles/@3/number', 12.00)
        self.assert_json_equal('', 'articles/@4/article', '{[b]}total{[/b]}')
        self.assert_json_equal('', 'articles/@4/amount', {'format': '{[b]}{0}{[/b]}', 'value': 351.22})
        self.assert_json_equal('', 'articles/@4/number', {'format': '{[b]}{0}{[/b]}', 'value': None})

        self.assert_count_equal('customers', 4)
        self.assert_json_equal('', 'customers/@0/customer', "Minimum")
        self.assert_json_equal('', 'customers/@0/amount', 134.82)
        self.assert_json_equal('', 'customers/@1/customer', "Dalton Jack")
        self.assert_json_equal('', 'customers/@1/amount', 125.24)
        self.assert_json_equal('', 'customers/@1/ratio', 35.66)
        self.assert_json_equal('', 'customers/@2/customer', "Dalton William")
        self.assert_json_equal('', 'customers/@2/amount', 91.16)
        self.assert_json_equal('', 'customers/@3/customer', '{[b]}total{[/b]}')
        self.assert_json_equal('', 'customers/@3/amount', {'format': '{[b]}{0}{[/b]}', 'value': 351.22})

        self.assert_count_equal('months', 13)
        self.assert_json_equal('', 'months/@0/amount', 0.00)
        self.assert_json_equal('', 'months/@1/amount', 83.75)
        self.assert_json_equal('', 'months/@2/amount', 142.73)
        self.assert_json_equal('', 'months/@3/amount', 91.16)
        self.assert_json_equal('', 'months/@4/amount', 41.49)
        self.assert_json_equal('', 'months/@5/amount', -7.91)
        self.assert_json_equal('', 'months/@6/amount', 0.00)
        self.assert_json_equal('', 'months/@7/amount', 0.00)
        self.assert_json_equal('', 'months/@8/amount', 0.00)
        self.assert_json_equal('', 'months/@9/amount', 0.00)
        self.assert_json_equal('', 'months/@10/amount', 0.00)
        self.assert_json_equal('', 'months/@11/amount', 0.00)
        self.assert_json_equal('', 'months/@12/amount', {'format': "{[b]}{0}{[/b]}", 'value': 351.22})

        self.assert_count_equal('payoffs_True', 1)
        self.assert_count_equal('payoffs_False', 1)

        self.assert_count_equal('articles_quote', 2)
        self.assert_json_equal('', 'articles_quote/@0/article', "---")
        self.assert_json_equal('', 'articles_quote/@0/amount', 285.00)
        self.assert_json_equal('', 'articles_quote/@0/number', 15.00)
        self.assert_json_equal('', 'articles_quote/@0/mean', 19.00)
        self.assert_json_equal('', 'articles_quote/@0/ratio', 100.0)

        self.factory.xfer = BillStatisticPrint()
        self.calljson('/diacamma.invoice/billStatisticPrint', {'PRINT_MODE': '4'}, False)
        self.assert_observer('core.print', 'diacamma.invoice', 'billStatisticPrint')
        csv_value = b64decode(str(self.response_json['print']['content'])).decode("utf-8")
        content_csv = csv_value.split('\n')
        self.assertEqual(len(content_csv), 50, str(content_csv))
        self.assertEqual(content_csv[1].strip(), '"Impression des statistiques"')
        self.assertEqual(content_csv[13].strip(), '"total";"351,22 €";"100,00 %";', str(content_csv))
        self.assertEqual(content_csv[20].strip(), '"total";"351,22 €";"---";"---";"100,00 %";', str(content_csv))

        self.factory.xfer = BillPrint()
        self.calljson('/diacamma.invoice/billPrint', {'bill': '1;2;3;4;5'}, False)
        self.assert_observer('core.custom', 'diacamma.invoice', 'billPrint')
        self.assert_count_equal('', 3)
        self.assert_json_equal('LABELFORM', 'print_sep', '{[u]}Attention:{[/u]} Des éléments ont des raports sauvegardés mais devront être regénérés.')

        self.factory.xfer = BillPrint()
        self.calljson('/diacamma.invoice/billPrint', {'bill': '1;2;3;4;5', 'PRINT_MODE': 3, 'MODEL': 8}, False)
        self.assert_observer('core.print', 'diacamma.invoice', 'billPrint')
        self.save_pdf()

        self.factory.xfer = BillPrint()
        self.calljson('/diacamma.invoice/billPrint', {'bill': '2;3;4;5'}, False)
        self.assert_observer('core.custom', 'diacamma.invoice', 'billPrint')
        self.assert_count_equal('', 3)
        self.assert_json_equal('SELECT', 'PRINT_PERSITENT_MODE', 0)
        self.assert_select_equal('PRINT_PERSITENT_MODE', {0: 'Obtenir le rapport sauvegardé', 1: 'Générer un rapport duplicata', 2: 'Recréer un rapport officiel'})

        download_file = join(get_user_dir(), "pdfreports.zip")
        self.assertFalse(isfile(download_file))
        self.factory.xfer = BillPrint()
        self.calljson('/diacamma.invoice/billPrint', {'bill': '2;3;4;5', 'PRINT_PERSITENT_MODE': 0}, False)
        self.assert_observer('core.custom', 'diacamma.invoice', 'billPrint')
        self.assert_json_equal('DOWNLOAD', 'filename', 'pdfreports.zip')
        self.assert_json_equal('', '#filename/filename', "CORE/download?filename=pdfreports.zip&sign=", True)
        self.assertTrue(isfile(download_file))

    def test_statistic_without_reduce(self):
        default_articles()
        details = [{'article': 0, 'designation': 'article 0', 'price': '20.00', 'quantity': 15, 'reduce': '15.0'}]
        self._create_bill(details, 0, '2015-01-01', 6, True)  # 59.50
        details = [{'article': 1, 'designation': 'article 1', 'price': '22.00', 'quantity': 3, 'reduce': '5.0'},
                   {'article': 2, 'designation': 'article 2', 'price': '3.25', 'quantity': 7}]
        self._create_bill(details, 1, '2015-02-01', 6, True)  # 83.75
        details = [{'article': 0, 'designation': 'article 0', 'price': '50.00', 'quantity': 2},
                   {'article': 5, 'designation': 'article 5', 'price': '6.33', 'quantity': 6.75}]
        self._create_bill(details, 3, '2015-03-01', 4, True)  # 142.73
        details = [{'article': 1, 'designation': 'article 1', 'price': '23.00', 'quantity': 3},
                   {'article': 5, 'designation': 'article 5', 'price': '6.33', 'quantity': 3.50}]
        self._create_bill(details, 1, '2015-04-01', 5, True)  # 91.16
        details = [{'article': 2, 'designation': 'article 2', 'price': '3.30', 'quantity': 5},
                   {'article': 5, 'designation': 'article 5', 'price': '6.35', 'quantity': 4.25, 'reduce': '2.0'}]
        self._create_bill(details, 1, '2015-05-01', 6, True)  # 41.49
        details = [{'article': 5, 'designation': 'article 5', 'price': '6.33', 'quantity': 1.25}]
        self._create_bill(details, 2, '2015-06-01', 4, True)  # 7.91

        self.factory.xfer = BillStatistic()
        self.calljson('/diacamma.invoice/billStatistic', {'without_reduct': True}, False)
        self.assert_observer('core.custom', 'diacamma.invoice', 'billStatistic')
        self.assert_count_equal('', 16)

        self.assert_count_equal('articles', 5)
        self.assert_json_equal('', 'articles/@0/article', "ABC1")
        self.assert_json_equal('', 'articles/@0/amount', 135.00)
        self.assert_json_equal('', 'articles/@0/number', 6.00)

        self.assert_json_equal('', 'articles/@1/article', "---")
        self.assert_json_equal('', 'articles/@1/amount', 100.00)
        self.assert_json_equal('', 'articles/@1/number', 2.00)
        self.assert_json_equal('', 'articles/@1/mean', 50.00)
        self.assert_json_equal('', 'articles/@1/ratio', 27.92)

        self.assert_json_equal('', 'articles/@2/article', "ABC5")
        self.assert_json_equal('', 'articles/@2/amount', 83.97)
        self.assert_json_equal('', 'articles/@2/number', 13.25)

        self.assert_json_equal('', 'articles/@3/article', "ABC2")
        self.assert_json_equal('', 'articles/@3/amount', 39.25)
        self.assert_json_equal('', 'articles/@3/number', 12.00)

        self.assert_json_equal('', 'articles/@4/article', '{[b]}total{[/b]}')
        self.assert_json_equal('', 'articles/@4/amount', {'format': '{[b]}{0}{[/b]}', 'value': 358.22})
        self.assert_json_equal('', 'articles/@4/number', {'format': '{[b]}{0}{[/b]}', 'value': None})

        self.assert_count_equal('customers', 4)
        self.assert_json_equal('', 'customers/@0/customer', "Minimum")
        self.assert_json_equal('', 'customers/@0/amount', 134.82)

        self.assert_json_equal('', 'customers/@1/customer', "Dalton Jack")
        self.assert_json_equal('', 'customers/@1/amount', 132.24)
        self.assert_json_equal('', 'customers/@1/ratio', 36.92)

        self.assert_json_equal('', 'customers/@2/customer', "Dalton William")
        self.assert_json_equal('', 'customers/@2/amount', 91.16)

        self.assert_json_equal('', 'customers/@3/customer', '{[b]}total{[/b]}')
        self.assert_json_equal('', 'customers/@3/amount', {'format': '{[b]}{0}{[/b]}', 'value': 358.22})

        self.assert_count_equal('months', 13)
        self.assert_json_equal('', 'months/@0/amount', 0.00)
        self.assert_json_equal('', 'months/@1/amount', 88.75)
        self.assert_json_equal('', 'months/@2/amount', 142.73)
        self.assert_json_equal('', 'months/@3/amount', 91.16)
        self.assert_json_equal('', 'months/@4/amount', 43.49)
        self.assert_json_equal('', 'months/@5/amount', -7.91)
        self.assert_json_equal('', 'months/@6/amount', 0.00)
        self.assert_json_equal('', 'months/@7/amount', 0.00)
        self.assert_json_equal('', 'months/@8/amount', 0.00)
        self.assert_json_equal('', 'months/@9/amount', 0.00)
        self.assert_json_equal('', 'months/@10/amount', 0.0)
        self.assert_json_equal('', 'months/@11/amount', 0.0)
        self.assert_json_equal('', 'months/@12/amount', {'format': "{[b]}{0}{[/b]}", 'value': 358.22})

        self.assert_count_equal('payoffs_True', 1)
        self.assert_count_equal('payoffs_False', 1)

        self.assert_count_equal('articles_quote', 2)
        self.assert_json_equal('', 'articles_quote/@0/article', "---")
        self.assert_json_equal('', 'articles_quote/@0/amount', 300.00)
        self.assert_json_equal('', 'articles_quote/@0/number', 15.00)
        self.assert_json_equal('', 'articles_quote/@0/mean', 20.00)
        self.assert_json_equal('', 'articles_quote/@0/ratio', 100.0)

    def test_payoff_bill(self):
        default_articles()
        details = [{'article': 0, 'designation': 'article 0', 'price': '100.00', 'quantity': 1}]
        bill_id = self._create_bill(details, 1, '2015-04-01', 6, True)  # 59.50
        bill_item = Bill.objects.get(id=bill_id)
        self.assertEqual(bill_item.is_revenu, True)

        self.factory.xfer = EntryAccountList()
        self.calljson('/diacamma.accounting/entryAccountList', {'year': '1', 'journal': '0', 'filter': '0'}, False)
        self.assert_observer('core.custom', 'diacamma.accounting', 'entryAccountList')
        self.assert_count_equal('entryline', 2)
        self.assert_json_equal('LABELFORM', 'result', [100.00, 0.00, 100.00, 0.00, 0.00])

        self.factory.xfer = BillShow()
        self.calljson('/diacamma.invoice/billShow', {'bill': bill_id}, False)
        self.assertEqual(self.json_context['supporting'], bill_id)
        self.assert_observer('core.custom', 'diacamma.invoice', 'billShow')
        self.assert_json_equal('LABELFORM', 'total_excltax', 100.00)
        self.assert_json_equal('LABELFORM', 'total_payed', 0.0)
        self.assert_json_equal('LABELFORM', 'total_rest_topay', 100.0)
        self.assert_count_equal('payoff', 0)
        self.assert_count_equal('#payoff/actions', 3)

        self.factory.xfer = PayoffAddModify()
        self.calljson('/diacamma.payoff/payoffAddModify', {'supporting': bill_id}, False)
        self.assert_observer('core.custom', 'diacamma.payoff', 'payoffAddModify')
        self.assert_count_equal('', 7)
        self.assert_json_equal('FLOAT', 'amount', "100.00")
        self.assert_attrib_equal('amount', 'max', "10000.0")
        self.assert_json_equal('EDIT', 'payer', "Dalton Jack")

        self.factory.xfer = PayoffAddModify()
        self.calljson('/diacamma.payoff/payoffAddModify', {'supporting': bill_id, 'amount': '60.0', 'payer': "Ma'a Dalton", 'date': '2015-04-03'}, False)
        self.assert_observer('core.custom', 'diacamma.payoff', 'payoffAddModify')
        self.assert_json_equal('FLOAT', 'amount', "60.00")
        self.assert_json_equal('DATE', 'date', "2015-04-03")
        self.assert_json_equal('EDIT', 'payer', "Ma'a Dalton")

        self.factory.xfer = PayoffAddModify()
        self.calljson('/diacamma.payoff/payoffAddModify', {'SAVE': 'YES', 'supporting': bill_id, 'amount': '60.0', 'payer': "Ma'a Dalton", 'date': '2015-04-03', 'mode': 0, 'reference': 'abc', 'bank_account': 0}, False)
        self.assert_observer('core.acknowledge', 'diacamma.payoff', 'payoffAddModify')

        self.factory.xfer = BillShow()
        self.calljson('/diacamma.invoice/billShow', {'bill': bill_id}, False)
        self.assertEqual(self.json_context['supporting'], bill_id)
        self.assert_observer('core.custom', 'diacamma.invoice', 'billShow')
        self.assert_json_equal('LABELFORM', 'total_excltax', 100.00)
        self.assert_json_equal('LABELFORM', 'total_payed', 60.0)
        self.assert_json_equal('LABELFORM', 'total_rest_topay', 40.0)
        self.assert_count_equal('payoff', 1)
        self.assert_count_equal('#payoff/actions', 3)
        self.assert_json_equal('', 'payoff/@0/date', "2015-04-03")
        self.assert_json_equal('', 'payoff/@0/mode', 0)
        self.assert_json_equal('', 'payoff/@0/amount', 60.0)
        self.assert_json_equal('', 'payoff/@0/payer', "Ma'a Dalton")
        self.assert_json_equal('', 'payoff/@0/reference', "abc")
        self.assert_json_equal('', 'payoff/@0/bank_account_ex', None)

        self.factory.xfer = EntryAccountList()
        self.calljson('/diacamma.accounting/entryAccountList',
                      {'year': '1', 'journal': '0', 'filter': '0'}, False)
        self.assert_observer('core.custom', 'diacamma.accounting', 'entryAccountList')
        self.assert_count_equal('entryline', 4)
        self.assert_json_equal('', 'entryline/@3/entry_account', "[531] 531")
        self.assert_json_equal('LABELFORM', 'result', [100.00, 0.00, 100.00, 60.00, 0.00])

        self.factory.xfer = PayoffAddModify()
        self.calljson('/diacamma.payoff/payoffAddModify', {'supporting': bill_id}, False)
        self.assert_observer('core.custom', 'diacamma.payoff', 'payoffAddModify')
        self.assert_json_equal('FLOAT', 'amount', "40.00")
        self.assert_attrib_equal('amount', 'max', "4000.0")

        self.factory.xfer = PayoffAddModify()
        self.calljson('/diacamma.payoff/payoffAddModify', {'SAVE': 'YES', 'supporting': bill_id, 'amount': '40.0', 'payer': "Dalton Jack", 'date': '2015-04-04', 'mode': 2, 'reference': 'efg', 'bank_account': 2}, False)
        self.assert_observer('core.acknowledge', 'diacamma.payoff', 'payoffAddModify')

        self.factory.xfer = BillShow()
        self.calljson('/diacamma.invoice/billShow', {'bill': bill_id}, False)
        self.assertEqual(self.json_context['supporting'], bill_id)
        self.assert_observer('core.custom', 'diacamma.invoice', 'billShow')
        self.assert_json_equal('LABELFORM', 'total_excltax', 100.00)
        self.assert_json_equal('LABELFORM', 'total_payed', 100.00)
        self.assert_json_equal('LABELFORM', 'total_rest_topay', 0.00)
        self.assert_count_equal('payoff', 2)
        self.assert_count_equal('#payoff/actions', 2)

        self.factory.xfer = EntryAccountList()
        self.calljson('/diacamma.accounting/entryAccountList', {'year': '1', 'journal': '0', 'filter': '0'}, False)
        self.assert_observer('core.custom', 'diacamma.accounting', 'entryAccountList')
        self.assert_count_equal('entryline', 6)
        self.assert_json_equal('', 'entryline/@5/entry_account', "[581] 581")
        self.assert_json_equal('LABELFORM', 'result', [100.00, 0.00, 100.00, 100.00, 0.00])

    def test_payoff_bill_too_much(self):
        default_articles()
        details = [{'article': 0, 'designation': 'article 0', 'price': '100.00', 'quantity': 1}]
        bill_id = self._create_bill(details, 1, '2015-04-01', 6, True)  # 59.50
        bill_item = Bill.objects.get(id=bill_id)
        self.assertEqual(bill_item.is_revenu, True)

        self.factory.xfer = PayoffAddModify()
        self.calljson('/diacamma.payoff/payoffAddModify', {'supporting': bill_id}, False)
        self.assert_observer('core.custom', 'diacamma.payoff', 'payoffAddModify')
        self.assert_count_equal('', 7)
        self.assert_json_equal('FLOAT', 'amount', "100.00")
        self.assert_attrib_equal('amount', 'min', "0.01")
        self.assert_attrib_equal('amount', 'max', "10000.0")
        self.assert_json_equal('EDIT', 'payer', "Dalton Jack")

        self.factory.xfer = PayoffAddModify()
        self.calljson('/diacamma.payoff/payoffAddModify', {'SAVE': 'YES', 'supporting': bill_id, 'amount': '120.0', 'payer': "Ma'a Dalton", 'date': '2015-04-03', 'mode': 2, 'reference': 'abc', 'bank_account': 2}, False)
        self.assert_observer('core.acknowledge', 'diacamma.payoff', 'payoffAddModify')

        self.factory.xfer = BillShow()
        self.calljson('/diacamma.invoice/billShow', {'bill': bill_id}, False)
        self.assertEqual(self.json_context['supporting'], bill_id)
        self.assert_observer('core.custom', 'diacamma.invoice', 'billShow')
        self.assert_json_equal('LABELFORM', 'total_excltax', 100.00)
        self.assert_json_equal('LABELFORM', 'total_payed', 120.00)
        self.assert_json_equal('LABELFORM', 'total_rest_topay', -20.0)
        self.assert_count_equal('payoff', 1)
        self.assert_count_equal('#payoff/actions', 3)

        self.factory.xfer = PayoffAddModify()
        self.calljson('/diacamma.payoff/payoffAddModify', {'supporting': bill_id}, False)
        self.assert_observer('core.custom', 'diacamma.payoff', 'payoffAddModify')
        self.assert_count_equal('', 7)
        self.assert_json_equal('FLOAT', 'amount', "-20.00")
        self.assert_attrib_equal('amount', 'min', "-30.0")
        self.assert_attrib_equal('amount', 'max', "-0.01")

        self.factory.xfer = PayoffAddModify()
        self.calljson('/diacamma.payoff/payoffAddModify', {'SAVE': 'YES', 'supporting': bill_id, 'amount': '-20.0', 'payer': "Ma'a Dalton", 'date': '2015-04-03', 'mode': 0, 'reference': 'abc', 'bank_account': 0}, False)
        self.assert_observer('core.acknowledge', 'diacamma.payoff', 'payoffAddModify')

        self.factory.xfer = BillShow()
        self.calljson('/diacamma.invoice/billShow', {'bill': bill_id}, False)
        self.assertEqual(self.json_context['supporting'], bill_id)
        self.assert_observer('core.custom', 'diacamma.invoice', 'billShow')
        self.assert_json_equal('LABELFORM', 'total_excltax', 100.00)
        self.assert_json_equal('LABELFORM', 'total_payed', 100.00)
        self.assert_json_equal('LABELFORM', 'total_rest_topay', 0.00)
        self.assert_count_equal('payoff', 2)
        self.assert_count_equal('#payoff/actions', 2)

        self.factory.xfer = EntryAccountList()
        self.calljson('/diacamma.accounting/entryAccountList', {'year': '1', 'journal': '0', 'filter': '0'}, False)
        self.assert_observer('core.custom', 'diacamma.accounting', 'entryAccountList')
        self.assert_count_equal('entryline', 6)
        self.assert_json_equal('', 'entryline/@3/entry_account', "[581] 581")
        self.assert_json_equal('', 'entryline/@3/debit', -120.00)
        self.assert_json_equal('', 'entryline/@5/entry_account', "[531] 531")
        self.assert_json_equal('', 'entryline/@5/credit', 20.00)
        self.assert_json_equal('LABELFORM', 'result', [100.00, 0.00, 100.00, 100.00, 0.00])

    def test_payoff_asset(self):
        default_articles()
        details = [{'article': 0, 'designation': 'article 0', 'price': '50.00', 'quantity': 1}]
        bill_id = self._create_bill(details, 2, '2015-04-01', 6, True)  # 59.50
        bill_item = Bill.objects.get(id=bill_id)
        self.assertEqual(bill_item.is_revenu, False)

        self.factory.xfer = EntryAccountList()
        self.calljson('/diacamma.accounting/entryAccountList', {'year': '1', 'journal': '0', 'filter': '0'}, False)
        self.assert_observer('core.custom', 'diacamma.accounting', 'entryAccountList')
        self.assert_count_equal('entryline', 2)
        self.assert_json_equal('LABELFORM', 'result', [-50.00, 0.00, -50.00, 0.00, 0.00])

        self.factory.xfer = PayoffAddModify()
        self.calljson('/diacamma.payoff/payoffAddModify', {'supporting': bill_id, 'mode': 3}, False)
        self.assert_observer('core.custom', 'diacamma.payoff', 'payoffAddModify')
        self.assert_count_equal('', 7)
        self.assert_select_equal('bank_account', 2)  # nb=2

        self.factory.xfer = PayoffAddModify()
        self.calljson('/diacamma.payoff/payoffAddModify', {'SAVE': 'YES', 'supporting': bill_id, 'amount': '50.0', 'date': '2015-04-04', 'mode': 3, 'reference': 'ijk', 'bank_account': 1}, False)
        self.assert_observer('core.acknowledge', 'diacamma.payoff', 'payoffAddModify')

        self.factory.xfer = BillShow()
        self.calljson('/diacamma.invoice/billShow', {'bill': bill_id}, False)
        self.assertEqual(self.json_context['supporting'], bill_id)
        self.assert_observer('core.custom', 'diacamma.invoice', 'billShow')
        self.assert_json_equal('LABELFORM', 'total_excltax', 50.00)
        self.assert_json_equal('LABELFORM', 'total_payed', 50.00)
        self.assert_json_equal('LABELFORM', 'total_rest_topay', 0.00)
        self.assert_count_equal('payoff', 1)
        self.assert_count_equal('#payoff/actions', 2)
        self.assert_json_equal('', 'payoff/@0/date', "2015-04-04")
        self.assert_json_equal('', 'payoff/@0/mode', 3)
        self.assert_json_equal('', 'payoff/@0/amount', 50.0)
        self.assert_json_equal('', 'payoff/@0/reference', "ijk")
        self.assert_json_equal('', 'payoff/@0/bank_account_ex', "My bank")

        self.factory.xfer = EntryAccountList()
        self.calljson('/diacamma.accounting/entryAccountList', {'year': '1', 'journal': '0', 'filter': '0'}, False)
        self.assert_observer('core.custom', 'diacamma.accounting', 'entryAccountList')
        self.assert_count_equal('entryline', 4)
        self.assert_json_equal('', 'entryline/@2/entry_account', "[411 Dalton Jack]")
        self.assert_json_equal('', 'entryline/@3/entry_account', "[512] 512")
        self.assert_json_equal('LABELFORM', 'result', [-50.00, 0.00, -50.00, -50.00, 0.00])

        self.factory.xfer = PayoffDel()
        self.calljson('/diacamma.payoff/payoffDel', {'CONFIRME': 'YES', 'payoff': 1}, False)
        self.assert_observer('core.acknowledge', 'diacamma.payoff', 'payoffDel')

        self.factory.xfer = EntryAccountList()
        self.calljson('/diacamma.accounting/entryAccountList', {'year': '1', 'journal': '0', 'filter': '0'}, False)
        self.assert_observer('core.custom', 'diacamma.accounting', 'entryAccountList')
        self.assert_count_equal('entryline', 2)
        self.assert_json_equal('LABELFORM', 'result', [-50.00, 0.00, -50.00, 0.00, 0.00])

        self.factory.xfer = BillPrint()
        self.calljson('/diacamma.invoice/billPrint', {'bill': '1', 'PRINT_MODE': 3, 'MODEL': 9}, False)
        self.assert_observer('core.print', 'diacamma.invoice', 'billPrint')
        self.save_pdf()
        check_pdfreport(self, 'Bill', 1, False)

        self.factory.xfer = BillPrint()
        self.calljson('/diacamma.invoice/billPrint', {'bill': '1', 'PRINT_PERSITENT_MODE': 0, 'PRINT_MODE': 3, 'MODEL': 9}, False)
        self.assert_observer('core.print', 'diacamma.invoice', 'billPrint')
        check_pdfreport(self, 'Bill', 1, True)

    def test_payoff_multi(self):
        default_articles()
        details = [{'article': 0, 'designation': 'article 0', 'price': '100.00', 'quantity': 1}]
        bill_id1 = self._create_bill(details, 1, '2015-04-01', 6, True)
        details = [{'article': 0, 'designation': 'article 0', 'price': '50.00', 'quantity': 1}]
        bill_id2 = self._create_bill(details, 1, '2015-04-01', 4, True)

        self.factory.xfer = EntryAccountList()
        self.calljson('/diacamma.accounting/entryAccountList', {'year': '1', 'journal': '0', 'filter': '0'}, False)
        self.assert_observer('core.custom', 'diacamma.accounting', 'entryAccountList')
        self.assert_count_equal('entryline', 4)
        self.assert_json_equal('', 'entryline/@0/entry_account', '[411 Dalton Jack]')
        self.assert_json_equal('', 'entryline/@0/link', None)
        self.assert_json_equal('', 'entryline/@1/entry_account', '[706] 706')
        self.assert_json_equal('', 'entryline/@1/link', None)
        self.assert_json_equal('', 'entryline/@2/entry_account', '[411 Minimum]')
        self.assert_json_equal('', 'entryline/@2/link', None)
        self.assert_json_equal('', 'entryline/@3/entry_account', '[706] 706')
        self.assert_json_equal('', 'entryline/@3/link', None)
        self.assert_json_equal('LABELFORM', 'result',
                               [150.00, 0.00, 150.00, 0.00, 0.00])

        self.factory.xfer = BillMultiPay()
        self.calljson('/diacamma.invoice/billMultiPay', {'bill': '%s;%s' % (bill_id1, bill_id2)}, False)
        self.assert_observer('core.acknowledge', 'diacamma.invoice', 'billMultiPay')
        self.assertEqual(self.response_json['action']['id'], "diacamma.payoff/payoffAddModify")
        self.assertEqual(len(self.response_json['action']['params']), 1)
        self.assertEqual(self.response_json['action']['params']['supportings'], '%s;%s' % (bill_id1, bill_id2))

        self.factory.xfer = PayoffAddModify()
        self.calljson('/diacamma.payoff/payoffAddModify', {'supportings': '%s;%s' % (bill_id1, bill_id2)}, False)
        self.assert_observer('core.custom', 'diacamma.payoff', 'payoffAddModify')
        self.assert_json_equal('FLOAT', 'amount', "150.00")
        self.assert_attrib_equal('amount', 'max', "15000.0")
        self.assert_json_equal('EDIT', 'payer', "Dalton Jack")
        self.assert_select_equal('repartition', 2)  # nb=2
        self.assert_json_equal('SELECT', 'repartition', "0")

        self.factory.xfer = PayoffAddModify()
        self.calljson('/diacamma.payoff/payoffAddModify', {'SAVE': 'YES', 'supportings': '%s;%s' % (bill_id1, bill_id2),
                                                           'amount': '100.0', 'date': '2015-04-04', 'mode': 0, 'reference': '', 'bank_account': 0, 'payer': "Ma'a Dalton"}, False)
        self.assert_observer('core.acknowledge', 'diacamma.payoff', 'payoffAddModify')

        self.factory.xfer = BillShow()
        self.calljson('/diacamma.invoice/billShow', {'bill': bill_id1}, False)
        self.assert_observer('core.custom', 'diacamma.invoice', 'billShow')
        self.assert_json_equal('LABELFORM', 'total_excltax', 100.00)
        self.assert_json_equal('LABELFORM', 'total_payed', 66.67)
        self.assert_json_equal('LABELFORM', 'total_rest_topay', 33.33)

        self.factory.xfer = BillShow()
        self.calljson('/diacamma.invoice/billShow', {'bill': bill_id2}, False)
        self.assert_observer('core.custom', 'diacamma.invoice', 'billShow')
        self.assert_json_equal('LABELFORM', 'total_excltax', 50.00)
        self.assert_json_equal('LABELFORM', 'total_payed', 33.33)
        self.assert_json_equal('LABELFORM', 'total_rest_topay', 16.67)

        self.factory.xfer = EntryAccountList()
        self.calljson('/diacamma.accounting/entryAccountList', {'year': '1', 'journal': '0', 'filter': '0'}, False)
        self.assert_observer('core.custom', 'diacamma.accounting', 'entryAccountList')
        self.assert_count_equal('entryline', 7)
        self.assert_json_equal('', 'entryline/@0/designation_ref', 'Facture A-1')
        self.assert_json_equal('', 'entryline/@0/entry_account', '[411 Dalton Jack]')
        self.assert_json_equal('', 'entryline/@0/link', None)
        self.assert_json_equal('', 'entryline/@1/entry_account', '[706] 706')
        self.assert_json_equal('', 'entryline/@1/link', None)
        self.assert_json_equal('', 'entryline/@2/designation_ref', 'Facture A-2')
        self.assert_json_equal('', 'entryline/@2/entry_account', '[411 Minimum]')
        self.assert_json_equal('', 'entryline/@2/link', None)
        self.assert_json_equal('', 'entryline/@3/entry_account', '[706] 706')
        self.assert_json_equal('', 'entryline/@3/link', None)

        self.assert_json_equal('', 'entryline/@4/designation_ref', 'règlement de Facture A-1,Facture A-2')
        self.assert_json_equal('', 'entryline/@4/entry_account', '[411 Minimum]')
        self.assert_json_equal('', 'entryline/@4/link', None)
        self.assert_json_equal('', 'entryline/@5/entry_account', '[411 Dalton Jack]')
        self.assert_json_equal('', 'entryline/@5/link', None)
        self.assert_json_equal('', 'entryline/@6/entry_account', '[531] 531')
        self.assert_json_equal('', 'entryline/@6/link', None)
        self.assert_json_equal('LABELFORM', 'result',
                               [150.00, 0.00, 150.00, 100.00, 0.00])

        self.factory.xfer = PayoffAddModify()
        self.calljson('/diacamma.payoff/payoffAddModify', {'SAVE': 'YES', 'supportings': '%s;%s' % (bill_id1, bill_id2),
                                                           'amount': '50.0', 'date': '2015-04-05', 'mode': 0, 'reference': '', 'bank_account': 0, 'payer': "Ma'a Dalton"}, False)
        self.assert_observer('core.acknowledge', 'diacamma.payoff', 'payoffAddModify')

        self.factory.xfer = EntryAccountList()
        self.calljson('/diacamma.accounting/entryAccountList', {'year': '1', 'journal': '0', 'filter': '0'}, False)
        self.assert_observer('core.custom', 'diacamma.accounting', 'entryAccountList')
        self.assert_count_equal('entryline', 10)
        self.assert_json_equal('', 'entryline/@0/entry_account', '[411 Dalton Jack]')
        self.assert_json_equal('', 'entryline/@0/link', 'A')
        self.assert_json_equal('', 'entryline/@1/entry_account', '[706] 706')
        self.assert_json_equal('', 'entryline/@1/link', None)
        self.assert_json_equal('', 'entryline/@2/entry_account', '[411 Minimum]')
        self.assert_json_equal('', 'entryline/@2/link', 'D')
        self.assert_json_equal('', 'entryline/@3/entry_account', '[706] 706')
        self.assert_json_equal('', 'entryline/@3/link', None)
        self.assert_json_equal('', 'entryline/@4/entry_account', '[411 Minimum]')
        self.assert_json_equal('', 'entryline/@4/link', 'D')
        self.assert_json_equal('', 'entryline/@5/entry_account', '[411 Dalton Jack]')
        self.assert_json_equal('', 'entryline/@5/link', 'A')
        self.assert_json_equal('', 'entryline/@6/entry_account', '[531] 531')
        self.assert_json_equal('', 'entryline/@6/link', None)
        self.assert_json_equal('', 'entryline/@7/entry_account', '[411 Minimum]')
        self.assert_json_equal('', 'entryline/@7/link', 'D')
        self.assert_json_equal('', 'entryline/@8/entry_account', '[411 Dalton Jack]')
        self.assert_json_equal('', 'entryline/@8/link', 'A')
        self.assert_json_equal('', 'entryline/@9/entry_account', '[531] 531')
        self.assert_json_equal('', 'entryline/@9/link', None)
        self.assert_json_equal('LABELFORM', 'result',
                               [150.00, 0.00, 150.00, 150.00, 0.00])

    def test_payoff_multi_edit(self):
        default_articles()
        details = [{'article': 0, 'designation': 'article 0', 'price': '100.00', 'quantity': 1}]
        bill_id1 = self._create_bill(details, 1, '2015-04-01', 6, True)
        details = [{'article': 0, 'designation': 'article 0', 'price': '50.00', 'quantity': 1}]
        bill_id2 = self._create_bill(details, 1, '2015-04-01', 4, True)

        self.factory.xfer = PayoffAddModify()
        self.calljson('/diacamma.payoff/payoffAddModify', {'SAVE': 'YES', 'supportings': '%s;%s' % (bill_id1, bill_id2),
                                                           'amount': '100.0', 'date': '2015-04-04', 'mode': 2, 'reference': '', 'bank_account': 2,
                                                           'repartition': 0, 'payer': "Ma'a Dalton"}, False)
        self.assert_observer('core.acknowledge', 'diacamma.payoff', 'payoffAddModify')

        self.factory.xfer = PayoffAddModify()
        self.calljson('/diacamma.payoff/payoffAddModify', {'payoff': 1}, False)
        self.assert_observer('core.custom', 'diacamma.payoff', 'payoffAddModify')
        self.assert_json_equal('FLOAT', 'amount', "100.00")
        self.assert_json_equal('EDIT', 'payer', "Ma'a Dalton")
        self.assert_json_equal('SELECT', 'mode', "2")
        self.assert_json_equal('SELECT', 'bank_account', "2")
        self.assert_json_equal('SELECT', 'repartition', "0")
        self.assert_json_equal('LABELFORM', 'supportings', "facture A-1 - 1 avril 2015{[br/]}facture A-2 - 1 avril 2015")

        self.factory.xfer = PayoffAddModify()
        self.calljson('/diacamma.payoff/payoffAddModify', {'payoff': 2}, False)
        self.assert_observer('core.custom', 'diacamma.payoff', 'payoffAddModify')
        self.assert_json_equal('FLOAT', 'amount', "100.00")
        self.assert_json_equal('EDIT', 'payer', "Ma'a Dalton")
        self.assert_json_equal('SELECT', 'mode', "2")
        self.assert_json_equal('SELECT', 'bank_account', "2")
        self.assert_json_equal('SELECT', 'repartition', "0")
        self.assert_json_equal('LABELFORM', 'supportings', "facture A-1 - 1 avril 2015{[br/]}facture A-2 - 1 avril 2015")
        self.assertEqual(self.json_context['supportings'], '%s;%s' % (bill_id1, bill_id2))
        self.assertEqual(self.json_context['amount'], '100.000')

        self.factory.xfer = PayoffAddModify()
        self.calljson('/diacamma.payoff/payoffAddModify', {'SAVE': 'YES', 'payoff': 1, 'supportings': '%s;%s' % (bill_id1, bill_id2),
                                                           'amount': '120.0', 'date': '2015-04-04', 'mode': 0, 'reference': '', 'bank_account': 0,
                                                           'repartition': 0, 'payer': "Ma'a Dalton"}, False)
        self.assert_observer('core.acknowledge', 'diacamma.payoff', 'payoffAddModify')

        self.factory.xfer = BillShow()
        self.calljson('/diacamma.invoice/billShow', {'bill': bill_id1}, False)
        self.assert_observer('core.custom', 'diacamma.invoice', 'billShow')
        self.assert_json_equal('LABELFORM', 'total_excltax', 100.00)
        self.assert_json_equal('LABELFORM', 'total_payed', 80.00)
        self.assert_json_equal('LABELFORM', 'total_rest_topay', 20.00)

        self.factory.xfer = EntryAccountList()
        self.calljson('/diacamma.accounting/entryAccountList',
                      {'year': '1', 'journal': '0', 'filter': '0'}, False)
        self.assert_observer('core.custom', 'diacamma.accounting', 'entryAccountList')
        self.assert_count_equal('entryline', 7)
        self.assert_json_equal('', 'entryline/@4/entry_account', '[411 Minimum]')
        self.assert_json_equal('', 'entryline/@4/credit', 40.00)
        self.assert_json_equal('', 'entryline/@5/entry_account', '[411 Dalton Jack]')
        self.assert_json_equal('', 'entryline/@5/credit', 80.00)
        self.assert_json_equal('', 'entryline/@6/entry_account', '[531] 531')
        self.assert_json_equal('', 'entryline/@6/debit', -120.00)
        self.assert_json_equal('LABELFORM', 'result',
                               [150.00, 0.00, 150.00, 120.00, 0.00])

    def test_payoff_multi_samethird(self):
        default_articles()
        details = [{'article': 0, 'designation': 'article 0', 'price': '100.00', 'quantity': 1}]
        bill_id1 = self._create_bill(details, 1, '2015-04-01', 6, True)
        details = [{'article': 0, 'designation': 'article 0', 'price': '50.00', 'quantity': 1}]
        bill_id2 = self._create_bill(details, 1, '2015-04-01', 6, True)

        self.factory.xfer = EntryAccountList()
        self.calljson('/diacamma.accounting/entryAccountList',
                      {'year': '1', 'journal': '0', 'filter': '0'}, False)
        self.assert_observer('core.custom', 'diacamma.accounting', 'entryAccountList')
        self.assert_count_equal('entryline', 4)
        self.assert_json_equal('', 'entryline/@0/link', None)
        self.assert_json_equal('', 'entryline/@1/link', None)
        self.assert_json_equal('', 'entryline/@2/link', None)
        self.assert_json_equal('', 'entryline/@3/link', None)
        self.assert_json_equal('LABELFORM', 'result', [150.00, 0.00, 150.00, 0.00, 0.00])

        self.factory.xfer = BillMultiPay()
        self.calljson('/diacamma.invoice/billMultiPay', {'bill': '%s;%s' % (bill_id1, bill_id2)}, False)
        self.assert_observer('core.acknowledge', 'diacamma.invoice', 'billMultiPay')
        self.assertEqual(self.response_json['action']['id'], "diacamma.payoff/payoffAddModify")
        self.assertEqual(len(self.response_json['action']['params']), 1)
        self.assertEqual(self.response_json['action']['params']['supportings'], '%s;%s' % (bill_id1, bill_id2))

        self.factory.xfer = PayoffAddModify()
        self.calljson('/diacamma.payoff/payoffAddModify', {'supportings': '%s;%s' % (bill_id1, bill_id2)}, False)
        self.assert_observer('core.custom', 'diacamma.payoff', 'payoffAddModify')
        self.assert_json_equal('FLOAT', 'amount', "150.00")
        self.assert_attrib_equal('amount', 'max', "15000.0")
        self.assert_json_equal('EDIT', 'payer', "Dalton Jack")
        self.assert_select_equal('repartition', 2)  # nb=2
        self.assert_json_equal('SELECT', 'repartition', "0")

        self.factory.xfer = PayoffAddModify()
        self.calljson('/diacamma.payoff/payoffAddModify', {'SAVE': 'YES', 'supportings': '%s;%s' % (bill_id1, bill_id2), 'amount': '150.0',
                                                           'date': '2015-04-04', 'mode': 0, 'reference': '', 'bank_account': 0, 'payer': "Ma'a Dalton", "repartition": 0}, False)
        self.assert_observer('core.acknowledge', 'diacamma.payoff', 'payoffAddModify')

        self.factory.xfer = BillShow()
        self.calljson('/diacamma.invoice/billShow', {'bill': bill_id1}, False)
        self.assert_observer('core.custom', 'diacamma.invoice', 'billShow')
        self.assert_json_equal('LABELFORM', 'total_excltax', 100.00)
        self.assert_json_equal('LABELFORM', 'total_payed', 100.00)
        self.assert_json_equal('LABELFORM', 'total_rest_topay', 0.00)

        self.factory.xfer = BillShow()
        self.calljson('/diacamma.invoice/billShow', {'bill': bill_id2}, False)
        self.assert_observer('core.custom', 'diacamma.invoice', 'billShow')
        self.assert_json_equal('LABELFORM', 'total_excltax', 50.00)
        self.assert_json_equal('LABELFORM', 'total_payed', 50.00)
        self.assert_json_equal('LABELFORM', 'total_rest_topay', 0.00)

        self.factory.xfer = EntryAccountList()
        self.calljson('/diacamma.accounting/entryAccountList',
                      {'year': '1', 'journal': '0', 'filter': '0'}, False)
        self.assert_observer('core.custom', 'diacamma.accounting', 'entryAccountList')
        self.assert_count_equal('entryline', 7)
        self.assert_json_equal('', 'entryline/@0/entry_account', '[411 Dalton Jack]')
        self.assert_json_equal('', 'entryline/@0/link', 'A')
        self.assert_json_equal('', 'entryline/@1/entry_account', '[706] 706')
        self.assert_json_equal('', 'entryline/@1/link', None)
        self.assert_json_equal('', 'entryline/@2/entry_account', '[411 Dalton Jack]')
        self.assert_json_equal('', 'entryline/@2/link', 'A')
        self.assert_json_equal('', 'entryline/@3/entry_account', '[706] 706')
        self.assert_json_equal('', 'entryline/@3/link', None)
        self.assert_json_equal('', 'entryline/@4/entry_account', '[411 Dalton Jack]')
        self.assert_json_equal('', 'entryline/@4/link', 'A')
        self.assert_json_equal('', 'entryline/@5/entry_account', '[411 Dalton Jack]')
        self.assert_json_equal('', 'entryline/@5/link', 'A')
        self.assert_json_equal('', 'entryline/@6/entry_account', '[531] 531')
        self.assert_json_equal('', 'entryline/@6/link', None)
        self.assert_json_equal('LABELFORM', 'result', [150.00, 0.00, 150.00, 150.00, 0.00])

    def test_payoff_multi_bydate(self):
        default_articles()
        details = [{'article': 0, 'designation': 'article 0', 'price': '100.00', 'quantity': 1}]
        bill_id1 = self._create_bill(details, 1, '2015-04-01', 6, True)
        details = [{'article': 0, 'designation': 'article 0', 'price': '50.00', 'quantity': 1}]
        bill_id2 = self._create_bill(details, 1, '2015-04-03', 6, True)

        self.factory.xfer = EntryAccountList()
        self.calljson('/diacamma.accounting/entryAccountList',
                      {'year': '1', 'journal': '0', 'filter': '0'}, False)
        self.assert_observer('core.custom', 'diacamma.accounting', 'entryAccountList')
        self.assert_count_equal('entryline', 4)
        self.assert_json_equal('', 'entryline/@3/link', None)
        self.assert_json_equal('', 'entryline/@2/link', None)
        self.assert_json_equal('', 'entryline/@1/link', None)
        self.assert_json_equal('', 'entryline/@0/link', None)
        self.assert_json_equal('LABELFORM', 'result',
                               [150.00, 0.00, 150.00, 0.00, 0.00])

        self.factory.xfer = BillMultiPay()
        self.calljson('/diacamma.invoice/billMultiPay',
                      {'bill': '%s;%s' % (bill_id1, bill_id2)}, False)
        self.assert_observer('core.acknowledge', 'diacamma.invoice', 'billMultiPay')
        self.assertEqual(self.response_json['action']['id'], "diacamma.payoff/payoffAddModify")
        self.assertEqual(len(self.response_json['action']['params']), 1)
        self.assertEqual(self.response_json['action']['params']['supportings'], '%s;%s' % (bill_id1, bill_id2))

        self.factory.xfer = PayoffAddModify()
        self.calljson('/diacamma.payoff/payoffAddModify', {'supportings': '%s;%s' % (bill_id1, bill_id2)}, False)
        self.assert_observer('core.custom', 'diacamma.payoff', 'payoffAddModify')
        self.assert_json_equal('FLOAT', 'amount', "150.00")
        self.assert_attrib_equal('amount', 'max', "15000.0")
        self.assert_json_equal('EDIT', 'payer', "Dalton Jack")
        self.assert_select_equal('repartition', 2)  # nb=2
        self.assert_json_equal('SELECT', 'repartition', "0")

        self.factory.xfer = PayoffAddModify()
        self.calljson('/diacamma.payoff/payoffAddModify', {'SAVE': 'YES', 'supportings': '%s;%s' % (bill_id1, bill_id2), 'amount': '120.0',
                                                           'date': '2015-04-07', 'mode': 0, 'reference': '', 'bank_account': 0, 'payer': "Ma'a Dalton", "repartition": 1}, False)
        self.assert_observer('core.acknowledge', 'diacamma.payoff', 'payoffAddModify')

        self.factory.xfer = BillShow()
        self.calljson('/diacamma.invoice/billShow', {'bill': bill_id1}, False)
        self.assert_observer('core.custom', 'diacamma.invoice', 'billShow')
        self.assert_json_equal('LABELFORM', 'total_excltax', 100.00)
        self.assert_json_equal('LABELFORM', 'total_payed', 100.00)
        self.assert_json_equal('LABELFORM', 'total_rest_topay', 0.00)

        self.factory.xfer = BillShow()
        self.calljson('/diacamma.invoice/billShow', {'bill': bill_id2}, False)
        self.assert_observer('core.custom', 'diacamma.invoice', 'billShow')
        self.assert_json_equal('LABELFORM', 'total_excltax', 50.00)
        self.assert_json_equal('LABELFORM', 'total_payed', 20.00)
        self.assert_json_equal('LABELFORM', 'total_rest_topay', 30.00)

        self.factory.xfer = EntryAccountList()
        self.calljson('/diacamma.accounting/entryAccountList',
                      {'year': '1', 'journal': '0', 'filter': '0'}, False)
        self.assert_observer('core.custom', 'diacamma.accounting', 'entryAccountList')
        self.assert_count_equal('entryline', 7)
        self.assert_json_equal('', 'entryline/@6/link', None)
        self.assert_json_equal('', 'entryline/@5/link', None)
        self.assert_json_equal('', 'entryline/@4/link', None)
        self.assert_json_equal('', 'entryline/@3/link', None)
        self.assert_json_equal('', 'entryline/@2/link', None)
        self.assert_json_equal('', 'entryline/@1/link', None)
        self.assert_json_equal('', 'entryline/@0/link', None)
        self.assert_json_equal('LABELFORM', 'result', [150.00, 0.00, 150.00, 120.00, 0.00])

    def test_payoff_internal(self):
        default_articles()
        details = [{'article': 0, 'designation': 'article 0', 'price': '100.00', 'quantity': 1}]
        bill_id = self._create_bill(details, 1, '2015-04-01', 6, True)  # 59.50
        bill_item = Bill.objects.get(id=bill_id)
        self.assertEqual(bill_item.is_revenu, True)

        self.factory.xfer = EntryAccountList()
        self.calljson('/diacamma.accounting/entryAccountList', {'year': '1', 'journal': '0', 'filter': '0'}, False)
        self.assert_observer('core.custom', 'diacamma.accounting', 'entryAccountList')
        self.assert_count_equal('entryline', 2)
        self.assert_json_equal('LABELFORM', 'result', [100.00, 0.00, 100.00, 0.00, 0.00])

        self.factory.xfer = BillShow()
        self.calljson('/diacamma.invoice/billShow', {'bill': bill_id}, False)
        self.assertEqual(self.json_context['supporting'], bill_id)
        self.assert_observer('core.custom', 'diacamma.invoice', 'billShow')
        self.assert_json_equal('LABELFORM', 'total_rest_topay', 100.0)
        self.assert_count_equal('payoff', 0)
        self.assert_count_equal('#payoff/actions', 3)

        self.factory.xfer = PayoffAddModify()
        self.calljson('/diacamma.payoff/payoffAddModify', {'supporting': bill_id}, False)
        self.assert_observer('core.custom', 'diacamma.payoff', 'payoffAddModify')
        self.assert_count_equal('', 7)
        self.assert_select_equal('mode', {0: 'espèces', 1: 'chèque', 2: 'virement', 3: 'carte de crédit', 4: 'autre', 5: 'prélèvement'})

        details = [{'article': 0, 'designation': 'article 0', 'price': '50.00', 'quantity': 1}]
        asset_id = self._create_bill(details, 2, '2015-04-05', 6, True)  # 59.50
        asset_item = Bill.objects.get(id=asset_id)
        self.assertEqual(asset_item.is_revenu, False)

        self.factory.xfer = EntryAccountList()
        self.calljson('/diacamma.accounting/entryAccountList', {'year': '1', 'journal': '0', 'filter': '0'}, False)
        self.assert_observer('core.custom', 'diacamma.accounting', 'entryAccountList')
        self.assert_count_equal('entryline', 4)
        self.assert_json_equal('', 'entryline/@0/designation_ref', 'Facture A-1')
        self.assert_json_equal('', 'entryline/@0/entry_account', '[411 Dalton Jack]')
        self.assert_json_equal('', 'entryline/@0/debit', -100.00)
        self.assert_json_equal('', 'entryline/@0/link', None)
        self.assert_json_equal('', 'entryline/@1/designation_ref', 'Facture A-1')
        self.assert_json_equal('', 'entryline/@1/entry_account', '[706] 706')
        self.assert_json_equal('', 'entryline/@1/credit', 100.00)
        self.assert_json_equal('', 'entryline/@1/link', None)
        self.assert_json_equal('', 'entryline/@2/designation_ref', 'Avoir A-1')
        self.assert_json_equal('', 'entryline/@2/entry_account', '[411 Dalton Jack]')
        self.assert_json_equal('', 'entryline/@2/credit', 50.00)
        self.assert_json_equal('', 'entryline/@2/link', None)
        self.assert_json_equal('', 'entryline/@3/designation_ref', 'Avoir A-1')
        self.assert_json_equal('', 'entryline/@3/entry_account', '[706] 706')
        self.assert_json_equal('', 'entryline/@3/debit', -50.00)
        self.assert_json_equal('', 'entryline/@3/link', None)
        self.assert_json_equal('LABELFORM', 'result', [50.00, 0.00, 50.00, 0.00, 0.00])

        self.factory.xfer = BillShow()
        self.calljson('/diacamma.invoice/billShow', {'bill': asset_id}, False)
        self.assertEqual(self.json_context['supporting'], asset_id)
        self.assert_observer('core.custom', 'diacamma.invoice', 'billShow')
        self.assert_json_equal('LABELFORM', 'total_rest_topay', 50.0)
        self.assert_count_equal('payoff', 0)
        self.assert_count_equal('#payoff/actions', 3)

        self.factory.xfer = PayoffAddModify()
        self.calljson('/diacamma.payoff/payoffAddModify', {'supporting': asset_id}, False)
        self.assert_observer('core.custom', 'diacamma.payoff', 'payoffAddModify')
        self.assert_count_equal('', 6)
        self.assert_select_equal('mode', {0: 'espèces', 1: 'chèque', 2: 'virement', 3: 'carte de crédit', 4: 'autre', 5: 'prélèvement', 6: 'interne'})

        self.factory.xfer = PayoffAddModify()
        self.calljson('/diacamma.payoff/payoffAddModify', {'supporting': asset_id, 'mode': 6}, False)
        self.assert_observer('core.custom', 'diacamma.payoff', 'payoffAddModify')
        self.assert_count_equal('', 6)
        self.assert_select_equal('linked_supporting', {bill_id: str(bill_item)})
        self.assert_json_equal('LABELFORM', 'amount', 50.0)

        self.factory.xfer = PayoffAddModify()
        self.calljson('/diacamma.payoff/payoffAddModify', {'SAVE': 'YES', 'supporting': asset_id, 'amount': '50.0',
                                                           'date': '2015-04-07', 'mode': 6, 'linked_supporting': bill_id}, False)
        self.assert_observer('core.acknowledge', 'diacamma.payoff', 'payoffAddModify')

        self.factory.xfer = BillShow()
        self.calljson('/diacamma.invoice/billShow', {'bill': asset_id}, False)
        self.assertEqual(self.json_context['supporting'], asset_id)
        self.assert_observer('core.custom', 'diacamma.invoice', 'billShow')
        self.assert_json_equal('LABELFORM', 'total_rest_topay', 0.0)
        self.assert_count_equal('payoff', 1)
        self.assert_count_equal('#payoff/actions', 2)
        self.assert_json_equal('', 'payoff/@0/date', "2015-04-07")
        self.assert_json_equal('', 'payoff/@0/mode', 6)
        self.assert_json_equal('', 'payoff/@0/amount', 50.0)
        self.assert_json_equal('', 'payoff/@0/reference', "facture A-1 - 1 avril 2015")
        self.assert_json_equal('', 'payoff/@0/bank_account_ex', None)

        self.factory.xfer = BillShow()
        self.calljson('/diacamma.invoice/billShow', {'bill': bill_id}, False)
        self.assertEqual(self.json_context['supporting'], bill_id)
        self.assert_observer('core.custom', 'diacamma.invoice', 'billShow')
        self.assert_json_equal('LABELFORM', 'total_rest_topay', 50.0)
        self.assert_count_equal('payoff', 1)
        self.assert_count_equal('#payoff/actions', 3)
        self.assert_json_equal('', 'payoff/@0/date', "2015-04-07")
        self.assert_json_equal('', 'payoff/@0/mode', 6)
        self.assert_json_equal('', 'payoff/@0/amount', 50.0)
        self.assert_json_equal('', 'payoff/@0/reference', "avoir A-1 - 5 avril 2015")
        self.assert_json_equal('', 'payoff/@0/bank_account_ex', None)

        self.factory.xfer = EntryAccountList()
        self.calljson('/diacamma.accounting/entryAccountList', {'year': '1', 'journal': '0', 'filter': '0'}, False)
        self.assert_observer('core.custom', 'diacamma.accounting', 'entryAccountList')
        self.assert_count_equal('entryline', 4)
        self.assert_json_equal('', 'entryline/@0/designation_ref', 'Facture A-1')
        self.assert_json_equal('', 'entryline/@0/entry_account', '[411 Dalton Jack]')
        self.assert_json_equal('', 'entryline/@0/debit', -100.00)
        self.assert_json_equal('', 'entryline/@0/link', None)
        self.assert_json_equal('', 'entryline/@1/designation_ref', 'Facture A-1')
        self.assert_json_equal('', 'entryline/@1/entry_account', '[706] 706')
        self.assert_json_equal('', 'entryline/@1/credit', 100.00)
        self.assert_json_equal('', 'entryline/@1/link', None)
        self.assert_json_equal('', 'entryline/@2/designation_ref', 'Avoir A-1')
        self.assert_json_equal('', 'entryline/@2/entry_account', '[411 Dalton Jack]')
        self.assert_json_equal('', 'entryline/@2/credit', 50.00)
        self.assert_json_equal('', 'entryline/@2/link', None)
        self.assert_json_equal('', 'entryline/@3/designation_ref', 'Avoir A-1')
        self.assert_json_equal('', 'entryline/@3/entry_account', '[706] 706')
        self.assert_json_equal('', 'entryline/@3/debit', -50.00)
        self.assert_json_equal('', 'entryline/@3/link', None)
        self.assert_json_equal('LABELFORM', 'result', [50.00, 0.00, 50.00, 0.00, 0.00])

    def test_payoff_internal_equals(self):
        default_articles()
        details = [{'article': 0, 'designation': 'article 0', 'price': '100.00', 'quantity': 1}]
        bill_id = self._create_bill(details, 1, '2015-04-01', 6, True)  # 59.50
        bill_item = Bill.objects.get(id=bill_id)
        self.assertEqual(bill_item.is_revenu, True)

        details = [{'article': 0, 'designation': 'article 0', 'price': '100.00', 'quantity': 1}]
        asset_id = self._create_bill(details, 2, '2015-04-05', 6, True)  # 59.50
        asset_item = Bill.objects.get(id=asset_id)
        self.assertEqual(asset_item.is_revenu, False)

        self.factory.xfer = EntryAccountList()
        self.calljson('/diacamma.accounting/entryAccountList', {'year': '1', 'journal': '0', 'filter': '0'}, False)
        self.assert_observer('core.custom', 'diacamma.accounting', 'entryAccountList')
        self.assert_count_equal('entryline', 4)
        self.assert_json_equal('', 'entryline/@0/designation_ref', 'Facture A-1')
        self.assert_json_equal('', 'entryline/@0/entry_account', '[411 Dalton Jack]')
        self.assert_json_equal('', 'entryline/@0/debit', -100.00)
        self.assert_json_equal('', 'entryline/@0/link', None)
        self.assert_json_equal('', 'entryline/@1/designation_ref', 'Facture A-1')
        self.assert_json_equal('', 'entryline/@1/entry_account', '[706] 706')
        self.assert_json_equal('', 'entryline/@1/credit', 100.00)
        self.assert_json_equal('', 'entryline/@1/link', None)
        self.assert_json_equal('', 'entryline/@2/designation_ref', 'Avoir A-1')
        self.assert_json_equal('', 'entryline/@2/entry_account', '[411 Dalton Jack]')
        self.assert_json_equal('', 'entryline/@2/credit', 100.00)
        self.assert_json_equal('', 'entryline/@2/link', None)
        self.assert_json_equal('', 'entryline/@3/designation_ref', 'Avoir A-1')
        self.assert_json_equal('', 'entryline/@3/entry_account', '[706] 706')
        self.assert_json_equal('', 'entryline/@3/debit', -100.00)
        self.assert_json_equal('', 'entryline/@3/link', None)
        self.assert_json_equal('LABELFORM', 'result', [0.00, 0.00, 0.00, 0.00, 0.00])

        self.factory.xfer = PayoffAddModify()
        self.calljson('/diacamma.payoff/payoffAddModify', {'supporting': bill_id, 'mode': 6}, False)
        self.assert_observer('core.custom', 'diacamma.payoff', 'payoffAddModify')
        self.assert_count_equal('', 6)
        self.assert_select_equal('linked_supporting', {asset_id: str(asset_item)})
        self.assert_json_equal('LABELFORM', 'amount', 100.0)

        self.factory.xfer = PayoffAddModify()
        self.calljson('/diacamma.payoff/payoffAddModify', {'SAVE': 'YES', 'supporting': bill_id, 'amount': '100.0',
                                                           'date': '2015-04-07', 'mode': 6, 'linked_supporting': asset_id}, False)
        self.assert_observer('core.acknowledge', 'diacamma.payoff', 'payoffAddModify')

        self.factory.xfer = EntryAccountList()
        self.calljson('/diacamma.accounting/entryAccountList', {'year': '1', 'journal': '0', 'filter': '0'}, False)
        self.assert_observer('core.custom', 'diacamma.accounting', 'entryAccountList')
        self.assert_count_equal('entryline', 4)
        self.assert_json_equal('', 'entryline/@0/designation_ref', 'Facture A-1')
        self.assert_json_equal('', 'entryline/@0/entry_account', '[411 Dalton Jack]')
        self.assert_json_equal('', 'entryline/@0/debit', -100.00)
        self.assert_json_equal('', 'entryline/@0/link', 'A')
        self.assert_json_equal('', 'entryline/@1/designation_ref', 'Facture A-1')
        self.assert_json_equal('', 'entryline/@1/entry_account', '[706] 706')
        self.assert_json_equal('', 'entryline/@1/credit', 100.00)
        self.assert_json_equal('', 'entryline/@1/link', None)
        self.assert_json_equal('', 'entryline/@2/designation_ref', 'Avoir A-1')
        self.assert_json_equal('', 'entryline/@2/entry_account', '[411 Dalton Jack]')
        self.assert_json_equal('', 'entryline/@2/credit', 100.00)
        self.assert_json_equal('', 'entryline/@2/link', 'A')
        self.assert_json_equal('', 'entryline/@3/designation_ref', 'Avoir A-1')
        self.assert_json_equal('', 'entryline/@3/entry_account', '[706] 706')
        self.assert_json_equal('', 'entryline/@3/debit', -100.00)
        self.assert_json_equal('', 'entryline/@3/link', None)
        self.assert_json_equal('LABELFORM', 'result', [0.00, 0.00, 0.00, 0.00, 0.00])

        self.factory.xfer = PayoffDel()
        self.calljson('/diacamma.payoff/payoffDel', {'CONFIRME': 'YES', 'payoff': 1}, False)
        self.assert_observer('core.acknowledge', 'diacamma.payoff', 'payoffDel')

        self.factory.xfer = BillShow()
        self.calljson('/diacamma.invoice/billShow', {'bill': bill_id}, False)
        self.assertEqual(self.json_context['supporting'], bill_id)
        self.assert_observer('core.custom', 'diacamma.invoice', 'billShow')
        self.assert_json_equal('LABELFORM', 'total_rest_topay', 100.0)
        self.assert_count_equal('payoff', 0)

        self.factory.xfer = BillShow()
        self.calljson('/diacamma.invoice/billShow', {'bill': asset_id}, False)
        self.assertEqual(self.json_context['supporting'], asset_id)
        self.assert_observer('core.custom', 'diacamma.invoice', 'billShow')
        self.assert_json_equal('LABELFORM', 'total_rest_topay', 100.0)
        self.assert_count_equal('payoff', 0)

        self.factory.xfer = EntryAccountList()
        self.calljson('/diacamma.accounting/entryAccountList', {'year': '1', 'journal': '0', 'filter': '0'}, False)
        self.assert_observer('core.custom', 'diacamma.accounting', 'entryAccountList')
        self.assert_count_equal('entryline', 4)
        self.assert_json_equal('', 'entryline/@0/designation_ref', 'Facture A-1')
        self.assert_json_equal('', 'entryline/@0/entry_account', '[411 Dalton Jack]')
        self.assert_json_equal('', 'entryline/@0/debit', -100.00)
        self.assert_json_equal('', 'entryline/@0/link', None)
        self.assert_json_equal('', 'entryline/@1/designation_ref', 'Facture A-1')
        self.assert_json_equal('', 'entryline/@1/entry_account', '[706] 706')
        self.assert_json_equal('', 'entryline/@1/credit', 100.00)
        self.assert_json_equal('', 'entryline/@1/link', None)
        self.assert_json_equal('', 'entryline/@2/designation_ref', 'Avoir A-1')
        self.assert_json_equal('', 'entryline/@2/entry_account', '[411 Dalton Jack]')
        self.assert_json_equal('', 'entryline/@2/credit', 100.00)
        self.assert_json_equal('', 'entryline/@2/link', None)
        self.assert_json_equal('', 'entryline/@3/designation_ref', 'Avoir A-1')
        self.assert_json_equal('', 'entryline/@3/entry_account', '[706] 706')
        self.assert_json_equal('', 'entryline/@3/debit', -100.00)
        self.assert_json_equal('', 'entryline/@3/link', None)
        self.assert_json_equal('LABELFORM', 'result', [0.00, 0.00, 0.00, 0.00, 0.00])

    def test_send_bill(self):
        default_articles()
        configSMTP('localhost', 2125)
        server = TestReceiver()
        server.start(2125)
        try:
            self.assertEqual(0, server.count())
            details = [{'article': 0, 'designation': 'article 0', 'price': '100.00', 'quantity': 1}]
            bill_id = self._create_bill(details, 1, '2015-04-01', 6, True)  # 59.50
            self.factory.xfer = PayableEmail()
            self.calljson('/diacamma.payoff/payableEmail',
                          {'item_name': 'bill', 'bill': bill_id}, False)
            self.assert_observer('core.custom', 'diacamma.payoff', 'payableEmail')
            self.assert_count_equal('', 5)
            self.assert_json_equal('EDIT', 'subject', 'Facture A-1')
            self.assert_json_equal('MEMO', 'message', 'Jack Dalton{[br/]}{[br/]}Veuillez trouver joint à ce courriel facture A-1 - 1 avril 2015.{[br/]}{[br/]}Sincères salutations')

            self.factory.xfer = PayableEmail()
            self.calljson('/diacamma.payoff/payableEmail',
                          {'bill': bill_id, 'OK': 'YES', 'item_name': 'bill', 'subject': 'my bill', 'message': 'this is a bill.', 'model': 8}, False)
            self.assert_observer('core.acknowledge', 'diacamma.payoff', 'payableEmail')
            self.assertEqual(1, server.count())
            self.assertEqual('mr-sylvestre@worldcompany.com', server.get(0)[1])
            self.assertEqual(['Jack.Dalton@worldcompany.com', 'mr-sylvestre@worldcompany.com'], server.get(0)[2])
            msg_txt, msg, msg_file = server.check_first_message('my bill', 3, {'To': 'Jack.Dalton@worldcompany.com'})
            self.assertEqual('text/plain', msg_txt.get_content_type())
            self.assertEqual('text/html', msg.get_content_type())
            self.assertEqual('base64', msg.get('Content-Transfer-Encoding', ''))
            self.assertEqual('<html>this is a bill.</html>', decode_b64(msg.get_payload()))
            self.assertTrue('facture_A-1_Dalton Jack.pdf' in msg_file.get('Content-Type', ''), msg_file.get('Content-Type', ''))
            self.save_pdf(base64_content=msg_file.get_payload())
            check_pdfreport(self, 'Bill', bill_id, False, msg_file.get_payload())
        finally:
            server.stop()

    def test_send_bill_saved(self):
        default_articles()
        configSMTP('localhost', 2225)
        server = TestReceiver()
        server.start(2225)
        try:
            self.assertEqual(0, server.count())
            details = [{'article': 0, 'designation': 'article 0', 'price': '100.00', 'quantity': 1}]
            bill_id = self._create_bill(details, 1, '2015-04-01', 6, True)  # 59.50
            self.factory.xfer = PayableEmail()
            self.calljson('/diacamma.payoff/payableEmail',
                          {'item_name': 'bill', 'bill': bill_id}, False)
            self.assert_observer('core.custom', 'diacamma.payoff', 'payableEmail')
            self.assert_count_equal('', 5)

            self.factory.xfer = PayableEmail()
            self.calljson('/diacamma.payoff/payableEmail',
                          {'bill': bill_id, 'OK': 'YES', 'PRINT_PERSITENT_MODE': 0, 'item_name': 'bill', 'subject': 'my bill', 'message': 'this is a bill.', 'model': 8, }, False)
            self.assert_observer('core.acknowledge', 'diacamma.payoff', 'payableEmail')
            self.assertEqual(1, server.count())
            _msg_txt, _msg, msg_file = server.check_first_message('my bill', 3, {'To': 'Jack.Dalton@worldcompany.com'})
            check_pdfreport(self, 'Bill', bill_id, True, msg_file.get_payload())
        finally:
            server.stop()

    def test_send_multi_bill(self):
        default_articles()
        default_paymentmethod()
        configSMTP('localhost', 2325)
        server = TestReceiver()
        server.start(2325)
        try:
            self._create_bill([{'article': 5, 'designation': 'article 5', 'price': '100', 'quantity': 1}], 1, '2015-04-01', 6, True)
            self._create_bill([{'article': 5, 'designation': 'article 5', 'price': '100', 'quantity': 1}], 3, '2015-04-02', 4, True)
            self._create_bill([{'article': 5, 'designation': 'article 5', 'price': '100', 'quantity': 1}], 2, '2015-04-03', 6, True)
            self._create_bill([{'article': 5, 'designation': 'article 5', 'price': '100', 'quantity': 1}], 1, '2015-04-04', 5, True)

            self.factory.xfer = BillList()
            self.calljson('/diacamma.invoice/billList', {'status_filter': -2}, False)
            self.assert_observer('core.custom', 'diacamma.invoice', 'billList')
            self.assert_count_equal('bill', 4)
            self.assert_count_equal('#bill/actions', 4)

            self.factory.xfer = BillList()
            self.calljson('/diacamma.invoice/billList', {'status_filter': 0}, False)
            self.assert_observer('core.custom', 'diacamma.invoice', 'billList')
            self.assert_count_equal('bill', 0)
            self.assert_count_equal('#bill/actions', 5)

            self.factory.xfer = BillList()
            self.calljson('/diacamma.invoice/billList', {'status_filter': 1}, False)
            self.assert_observer('core.custom', 'diacamma.invoice', 'billList')
            self.assert_count_equal('bill', 4)
            self.assert_json_equal('', 'bill/@0/total', 100.00)
            self.assert_json_equal('', 'bill/@0/total_rest_topay', 100.00)
            self.assert_json_equal('', 'bill/@1/total', 100.00)
            self.assert_json_equal('', 'bill/@1/total_rest_topay', 100.00)
            self.assert_json_equal('', 'bill/@2/total', 100.00)
            self.assert_json_equal('', 'bill/@2/total_rest_topay', 100.00)
            self.assert_json_equal('', 'bill/@3/total', 100.00)
            self.assert_json_equal('', 'bill/@3/total_rest_topay', 100.00)
            self.assert_count_equal('#bill/actions', 6)
            self.assert_action_equal('POST', self.get_json_path('#bill/actions/@5'), ("Envoyer", "lucterios.mailing/images/email.png", "diacamma.invoice", "billPayableEmail", 0, 1, 2))

            self.factory.xfer = BillPayableEmail()
            self.calljson('/diacamma.invoice/billPayableEmail', {'status_filter': 1, 'bill': '1;2;3;4'}, False)
            self.assert_observer('core.acknowledge', 'diacamma.invoice', 'billPayableEmail')
            self.assertEqual(self.response_json['action']['id'], "diacamma.payoff/payableEmail")
            self.assertEqual(len(self.response_json['action']['params']), 2)
            self.assertEqual(self.response_json['action']['params']['item_name'], 'bill')
            self.assertEqual(self.response_json['action']['params']['modelname'], 'invoice.Bill')

            self.factory.xfer = PayableEmail()
            self.calljson('/diacamma.payoff/payableEmail',
                          {'item_name': 'bill', 'bill': "1;2;3;4", 'modelname': 'invoice.Bill'}, False)
            self.assert_observer('core.custom', 'diacamma.payoff', 'payableEmail')
            self.assert_count_equal('', 6)
            self.assert_json_equal('LABELFORM', "nb_item", '4')
            self.assert_json_equal('EDIT', 'subject', '#reference')
            self.assert_json_equal('MEMO', 'message', '#name{[br/]}{[br/]}Veuillez trouver joint à ce courriel #doc.{[br/]}{[br/]}Sincères salutations')

            self.factory.xfer = PayableEmail()
            self.calljson('/diacamma.payoff/payableEmail',
                          {'bill': "1;2;3;4", 'OK': 'YES', 'item_name': 'bill', 'subject': '#reference',
                           'message': '#name{[br/]}{[br/]}Veuillez trouver joint à ce courriel #doc.{[br/]}{[br/]}Sincères salutations', 'model': 8}, False)
            self.assert_observer('core.acknowledge', 'diacamma.payoff', 'payableEmail')

            email_msg = Message.objects.get(id=1)
            self.assertEqual(email_msg.subject, '#reference')
            self.assertEqual(email_msg.body, '#name{[br/]}{[br/]}Veuillez trouver joint à ce courriel #doc.{[br/]}{[br/]}Sincères salutations#footer')
            self.assertEqual(email_msg.status, 2)
            self.assertEqual(email_msg.recipients, "invoice.Bill id||8||1;2;3;4\n")
            self.assertEqual(email_msg.email_to_send, "invoice.Bill:1:8\ninvoice.Bill:2:8\ninvoice.Bill:3:8\ninvoice.Bill:4:8")

            self.assertEqual(1, len(LucteriosScheduler.get_list()))
            LucteriosScheduler.stop_scheduler()
            email_msg.sendemail(10, "http://testserver")
            self.assertEqual(4, server.count())
            for msg_index in range(4):
                _msg_txt, msg, msg_file = server.get_msg_index(msg_index)
                message = decode_b64(msg.get_payload())
                if msg_index == 2:
                    self.assertNotIn("<center><i><u>Moyens de paiement</u></i></center>", message)
                else:
                    self.assertIn("<center><i><u>Moyens de paiement</u></i></center>", message)
                    self.assertIn("<tr><td><b>virement</b></td><td><center><table width='100%'><tr>    <td><u><i>IBAN</i></u></td>    <td>123456789</td></tr><tr>    <td><u><i>BIC</i></u></td>    <td>AABBCCDD</td></tr>", message)
                    self.assertIn("<tr><td><b>chèque</b></td><td><center><table width='100%%'>    <tr>        <td><u><i>à l'ordre de</i></u></td>        <td>Truc</td>    </tr>    <tr>        <td><u><i>adresse</i></u></td>        <td>1 rue de la Paix<newline>99000 LA-BAS</td>    </tr>", message)
                self.save_pdf(base64_content=msg_file.get_payload(), ident=msg_index + 1)
                check_pdfreport(self, 'Bill', msg_index + 1, False, msg_file.get_payload())
        finally:
            server.stop()

    def test_send_multi_bill_saved(self):
        default_articles()
        configSMTP('localhost', 2425)
        server = TestReceiver()
        server.start(2425)
        try:
            self._create_bill([{'article': 5, 'designation': 'article 5', 'price': '100', 'quantity': 1}], 1, '2015-04-01', 6, True)
            self._create_bill([{'article': 5, 'designation': 'article 5', 'price': '100', 'quantity': 1}], 3, '2015-04-02', 4, True)
            self._create_bill([{'article': 5, 'designation': 'article 5', 'price': '100', 'quantity': 1}], 2, '2015-04-03', 6, True)
            self._create_bill([{'article': 5, 'designation': 'article 5', 'price': '100', 'quantity': 1}], 1, '2015-04-04', 5, True)

            self.factory.xfer = PayableEmail()
            self.calljson('/diacamma.payoff/payableEmail',
                          {'bill': "1;2;3;4", 'OK': 'YES', 'item_name': 'bill', 'PRINT_PERSITENT_MODE': 0, 'subject': '#reference',
                           'message': '#name{[br/]}{[br/]}Veuillez trouver joint à ce courriel #doc.{[br/]}{[br/]}Sincères salutations', 'model': 8}, False)
            self.assert_observer('core.acknowledge', 'diacamma.payoff', 'payableEmail')

            email_msg = Message.objects.get(id=1)
            self.assertEqual(email_msg.subject, '#reference')
            self.assertEqual(email_msg.body, '#name{[br/]}{[br/]}Veuillez trouver joint à ce courriel #doc.{[br/]}{[br/]}Sincères salutations#footer')
            self.assertEqual(email_msg.status, 2)
            self.assertEqual(email_msg.recipients, "invoice.Bill id||8||1;2;3;4\n")
            self.assertEqual(email_msg.email_to_send, "invoice.Bill:1:0\ninvoice.Bill:2:0\ninvoice.Bill:3:0\ninvoice.Bill:4:0")

            self.assertEqual(1, len(LucteriosScheduler.get_list()))
            LucteriosScheduler.stop_scheduler()
            email_msg.sendemail(10, "http://testserver")
            self.assertEqual(4, server.count())
            for msg_index in range(4):
                _msg, _msg_txt, msg_file = server.get_msg_index(msg_index)
                self.save_pdf(base64_content=msg_file.get_payload(), ident=msg_index + 1)
                # print('Content-Type:', msg_file.get('Content-Type', ''))
                check_pdfreport(self, 'Bill', msg_index + 1, True, msg_file.get_payload())
        finally:
            server.stop()

    def test_search(self):
        CustomField.objects.create(modelname='accounting.Third', name='categorie', kind=4, args="{'list':['---','petit','moyen','gros']}")
        CustomField.objects.create(modelname='accounting.Third', name='value', kind=1, args="{'min':0,'max':100}")
        default_customize()
        initial_thirds_fr()
        default_categories()
        default_articles()
        details = [{'article': 0, 'designation': 'article 0', 'price': '20.00', 'quantity': 15}]
        self._create_bill(details, 0, '2015-04-01', 6, True)  # 59.50
        details = [{'article': 1, 'designation': 'article 1', 'price': '22.00', 'quantity': 3, 'reduce': '5.0'},
                   {'article': 2, 'designation': 'article 2', 'price': '3.25', 'quantity': 7}]
        self._create_bill(details, 1, '2015-04-01', 6, True)  # 83.75
        details = [{'article': 0, 'designation': 'article 0', 'price': '50.00', 'quantity': 2},
                   {'article': 5, 'designation': 'article 5', 'price': '6.33', 'quantity': 6.75}]
        self._create_bill(details, 3, '2015-04-01', 4, True)  # 142.73
        details = [{'article': 1, 'designation': 'article 1', 'price': '23.00', 'quantity': 3},
                   {'article': 5, 'designation': 'article 5', 'price': '6.33', 'quantity': 3.50}]
        self._create_bill(details, 1, '2015-04-01', 5, True)  # 91.16
        details = [{'article': 2, 'designation': 'article 2', 'price': '3.30', 'quantity': 5},
                   {'article': 5, 'designation': 'article 5', 'price': '6.35', 'quantity': 4.25, 'reduce': '2.0'}]
        self._create_bill(details, 1, '2015-04-01', 6, True)  # 41.49
        details = [{'article': 5, 'designation': 'article 5', 'price': '6.33', 'quantity': 1.25}]
        self._create_bill(details, 2, '2015-04-01', 4, True)  # 7.91

        self.factory.xfer = BillSearch()
        self.calljson('/diacamma.invoice/billSearch', {}, False)
        self.assert_observer('core.custom', 'diacamma.invoice', 'billSearch')
        self.assert_count_equal('bill', 6)

        search_field_list = Bill.get_search_fields()
        # bill + contact +  custom contact + custom third + third + detail + article + art custom + category + provider + storage detail + payoff
        self.assertEqual(6 + 3 + 8 + 1 + 2 + 2 + 4 + 9 + 2 + 3 + 2 + 1 + 6,
                         len(search_field_list), search_field_list)

    def test_autoreduce1(self):
        initial_thirds_fr()
        default_categories()
        default_articles()

        self.factory.xfer = AutomaticReduceAddModify()
        self.calljson('/diacamma.invoice/automaticReduceAddModify', {'name': "reduct #1a", 'category': 2, 'mode': 0, 'amount': '20.0', 'occurency': '3', 'filtercriteria': '0', 'SAVE': 'YES'}, False)
        self.assert_observer('core.acknowledge', 'diacamma.invoice', 'automaticReduceAddModify')

        self.factory.xfer = AutomaticReduceAddModify()
        self.calljson('/diacamma.invoice/automaticReduceAddModify', {'name': "reduct #1b", 'category': 2, 'mode': 0, 'amount': '30.0', 'occurency': '4', 'filtercriteria': '0', 'SAVE': 'YES'}, False)
        self.assert_observer('core.acknowledge', 'diacamma.invoice', 'automaticReduceAddModify')

        self.factory.xfer = BillList()
        self.calljson('/diacamma.invoice/billList', {'status_filter': 1}, False)
        self.assert_observer('core.custom', 'diacamma.invoice', 'billList')
        self.assert_count_equal('bill', 0)

        self._create_bill([{'article': 5, 'designation': 'article 5', 'price': '100', 'quantity': 1}], 1, '2015-04-01', 6, True)  # 100
        self._create_bill([{'article': 5, 'designation': 'article 5', 'price': '100', 'quantity': 1}], 3, '2015-04-02', 6, True)  # 100
        self._create_bill([{'article': 5, 'designation': 'article 5', 'price': '100', 'quantity': 1}], 1, '2015-04-03', 6, True)  # 80
        self._create_bill([{'article': 5, 'designation': 'article 5', 'price': '100', 'quantity': 1}], 0, '2015-04-04', 6, True)  # 70
        self._create_bill([{'article': 5, 'designation': 'article 5', 'price': '100', 'quantity': 1}], 1, '2015-04-05', 6, False)  # 70
        self._create_bill([{'article': 5, 'designation': 'article 5', 'price': '100', 'quantity': 1}], 1, '2015-04-06', 5, True)  # 100
        self._create_bill([{'article': 1, 'designation': 'article 1', 'price': '100', 'quantity': 1}], 1, '2015-04-07', 6, True)  # 100
        self._create_bill([{'article': 5, 'designation': 'article 5', 'price': '15', 'quantity': 1}], 1, '2015-04-08', 6, True)  # 0

        self.factory.xfer = BillList()
        self.calljson('/diacamma.invoice/billList', {'status_filter': -2, 'GRID_ORDER%bill': 'id'}, False)
        self.assert_observer('core.custom', 'diacamma.invoice', 'billList')
        self.assert_count_equal('bill', 8)
        self.assert_json_equal('', 'bill/@0/third', 'Dalton Jack')
        self.assert_json_equal('', 'bill/@0/total', 100.00)
        self.assert_json_equal('', 'bill/@0/date', '2015-04-01')
        self.assert_json_equal('', 'bill/@1/third', 'Dalton Jack')
        self.assert_json_equal('', 'bill/@1/total', 100.00)
        self.assert_json_equal('', 'bill/@1/date', '2015-04-02')
        self.assert_json_equal('', 'bill/@2/third', 'Dalton Jack')
        self.assert_json_equal('', 'bill/@2/total', 80.00)
        self.assert_json_equal('', 'bill/@2/date', '2015-04-03')
        self.assert_json_equal('', 'bill/@3/third', 'Dalton Jack')
        self.assert_json_equal('', 'bill/@3/total', 70.00)
        self.assert_json_equal('', 'bill/@3/date', '2015-04-04')
        self.assert_json_equal('', 'bill/@4/third', 'Dalton Jack')
        self.assert_json_equal('', 'bill/@4/total', 70.00)
        self.assert_json_equal('', 'bill/@4/date', '2015-04-05')
        self.assert_json_equal('', 'bill/@5/third', 'Dalton William')
        self.assert_json_equal('', 'bill/@5/total', 100.00)
        self.assert_json_equal('', 'bill/@5/date', '2015-04-06')
        self.assert_json_equal('', 'bill/@6/third', 'Dalton Jack')
        self.assert_json_equal('', 'bill/@6/total', 100.00)
        self.assert_json_equal('', 'bill/@6/date', '2015-04-07')
        self.assert_json_equal('', 'bill/@7/third', 'Dalton Jack')
        self.assert_json_equal('', 'bill/@7/total', 0.00)
        self.assert_json_equal('', 'bill/@7/date', '2015-04-08')

        self.factory.xfer = BillShow()
        self.calljson('/diacamma.invoice/billShow', {'bill': 4}, False)
        self.assert_observer('core.custom', 'diacamma.invoice', 'billShow')
        self.assert_json_equal('LINK', 'third', "Dalton Jack")
        self.assert_count_equal('detail', 1)
        self.assert_json_equal('', 'detail/@0/article', 'ABC5')
        self.assert_json_equal('', 'detail/@0/designation', 'article 5')
        self.assert_json_equal('', 'detail/@0/price', 100.00)
        self.assert_json_equal('', 'detail/@0/unit', '')
        self.assert_json_equal('', 'detail/@0/quantity_txt', '1,00')
        self.assert_json_equal('', 'detail/@0/reduce_txt', '30,00 €(30.00%)')
        self.assert_json_equal('', 'detail/@0/total', 70.00)

    def test_autoreduce2(self):
        initial_thirds_fr()
        default_categories()
        default_articles()
        SavedCriteria.objects.create(name='my filter', modelname='accounting.Third', criteria="contact.city||1||LE PRECHEUR")

        self.factory.xfer = AutomaticReduceAddModify()
        self.calljson('/diacamma.invoice/automaticReduceAddModify', {'name': "reduct #2", 'category': 2, 'mode': 1, 'amount': '10.0', 'occurency': '0', 'filtercriteria': '1', 'SAVE': 'YES'}, False)
        self.assert_observer('core.acknowledge', 'diacamma.invoice', 'automaticReduceAddModify')

        self.factory.xfer = BillList()
        self.calljson('/diacamma.invoice/billList', {'status_filter': 1}, False)
        self.assert_observer('core.custom', 'diacamma.invoice', 'billList')
        self.assert_count_equal('bill', 0)

        self._create_bill([{'article': 5, 'designation': 'article 5', 'price': '200', 'quantity': 1}], 1, '2015-04-01', 6, True)  # 180
        self._create_bill([{'article': 5, 'designation': 'article 5', 'price': '50', 'quantity': 1}], 0, '2015-04-02', 5, True)  # 45
        self._create_bill([{'article': 5, 'designation': 'article 5', 'price': '100', 'quantity': 1}], 1, '2015-04-03', 4, True)  # 100
        self._create_bill([{'article': 1, 'designation': 'article 1', 'price': '100', 'quantity': 1}], 1, '2015-04-04', 6, True)  # 100
        self._create_bill([{'article': 5, 'designation': 'article 5', 'price': '75', 'quantity': 2}], 3, '2015-04-05', 0, False)  # 150
        self._create_bill([{'article': 0, 'designation': 'article 0', 'price': '45', 'quantity': 3}], 1, '2015-04-05', 6, False)  # 135

        self.factory.xfer = BillList()
        self.calljson('/diacamma.invoice/billList', {'status_filter': -2, 'GRID_ORDER%bill': 'id'}, False)
        self.assert_observer('core.custom', 'diacamma.invoice', 'billList')
        self.assert_count_equal('bill', 6)
        self.assert_json_equal('', 'bill/@0/third', 'Dalton Jack')
        self.assert_json_equal('', 'bill/@0/total', 180.00)
        self.assert_json_equal('', 'bill/@1/third', 'Dalton William')
        self.assert_json_equal('', 'bill/@1/total', 45.00)
        self.assert_json_equal('', 'bill/@2/third', 'Minimum')
        self.assert_json_equal('', 'bill/@2/total', 100.00)
        self.assert_json_equal('', 'bill/@3/third', 'Dalton Jack')
        self.assert_json_equal('', 'bill/@3/total', 100.00)
        self.assert_json_equal('', 'bill/@4/third', None)
        self.assert_json_equal('', 'bill/@4/total', 150.00)
        self.assert_json_equal('', 'bill/@5/third', 'Dalton Jack')
        self.assert_json_equal('', 'bill/@5/total', 135.00)

        self.factory.xfer = BillShow()
        self.calljson('/diacamma.invoice/billShow', {'bill': 2}, False)
        self.assert_observer('core.custom', 'diacamma.invoice', 'billShow')
        self.assert_json_equal('LINK', 'third', "Dalton William")
        self.assert_count_equal('detail', 1)
        self.assert_json_equal('', 'detail/@0/article', 'ABC5')
        self.assert_json_equal('', 'detail/@0/designation', 'article 5')
        self.assert_json_equal('', 'detail/@0/price', 50.00)
        self.assert_json_equal('', 'detail/@0/unit', '')
        self.assert_json_equal('', 'detail/@0/quantity_txt', '1,00')
        self.assert_json_equal('', 'detail/@0/reduce_txt', '5,00 €(10.00%)')
        self.assert_json_equal('', 'detail/@0/total', 45.00)

        self.factory.xfer = SupportingThirdValid()
        self.calljson('/diacamma.payoff/supportingThirdValid', {'supporting': 5, 'third': 6}, False)
        self.assert_observer('core.acknowledge', 'diacamma.payoff', 'supportingThirdValid')

        self.factory.xfer = BillList()
        self.calljson('/diacamma.invoice/billList', {'status_filter': -2, 'GRID_ORDER%bill': 'id'}, False)
        self.assert_observer('core.custom', 'diacamma.invoice', 'billList')
        self.assert_count_equal('bill', 6)
        self.assert_json_equal('', 'bill/@4/third', 'Dalton Jack')
        self.assert_json_equal('', 'bill/@4/total', 135.00)

    def test_autoreduce3(self):
        Params.setvalue('invoice-reduce-with-ratio', 'False')

        initial_thirds_fr()
        default_categories()
        default_articles()

        self.factory.xfer = AutomaticReduceAddModify()
        self.calljson('/diacamma.invoice/automaticReduceAddModify', {'name': "reduct #3", 'category': 2, 'mode': 2, 'amount': '25.0', 'occurency': '10', 'filtercriteria': '0', 'SAVE': 'YES'}, False)
        self.assert_observer('core.acknowledge', 'diacamma.invoice', 'automaticReduceAddModify')

        self.factory.xfer = BillList()
        self.calljson('/diacamma.invoice/billList', {'status_filter': 1}, False)
        self.assert_observer('core.custom', 'diacamma.invoice', 'billList')
        self.assert_count_equal('bill', 0)

        self._create_bill([{'article': 5, 'designation': 'article 5', 'price': '15', 'quantity': 5}], 1, '2015-04-01', 6, True)  # 75
        self._create_bill([{'article': 5, 'designation': 'article 5', 'price': '15', 'quantity': 7}], 1, '2015-04-02', 6, True)  # 60
        self._create_bill([{'article': 5, 'designation': 'article 5', 'price': '15', 'quantity': 2}], 1, '2015-04-03', 6, True)  # 22.5
        self._create_bill([{'article': 1, 'designation': 'article 1', 'price': '15', 'quantity': 20}], 1, '2015-04-04', 6, True)  # 300

        self.factory.xfer = BillList()
        self.calljson('/diacamma.invoice/billList', {'status_filter': -2, 'GRID_ORDER%bill': 'id'}, False)
        self.assert_observer('core.custom', 'diacamma.invoice', 'billList')
        self.assert_count_equal('bill', 4)
        self.assert_json_equal('', 'bill/@0/third', 'Dalton Jack')
        self.assert_json_equal('', 'bill/@0/total', 75.00)
        self.assert_json_equal('', 'bill/@0/date', '2015-04-01')
        self.assert_json_equal('', 'bill/@1/third', 'Dalton Jack')
        self.assert_json_equal('', 'bill/@1/total', 60.00)
        self.assert_json_equal('', 'bill/@1/date', '2015-04-02')
        self.assert_json_equal('', 'bill/@2/third', 'Dalton Jack')
        self.assert_json_equal('', 'bill/@2/total', 22.50)
        self.assert_json_equal('', 'bill/@2/date', '2015-04-03')
        self.assert_json_equal('', 'bill/@3/third', 'Dalton Jack')
        self.assert_json_equal('', 'bill/@3/total', 300.00)
        self.assert_json_equal('', 'bill/@3/date', '2015-04-04')

        self.factory.xfer = BillShow()
        self.calljson('/diacamma.invoice/billShow', {'bill': 2}, False)
        self.assert_observer('core.custom', 'diacamma.invoice', 'billShow')
        self.assert_json_equal('LINK', 'third', "Dalton Jack")
        self.assert_count_equal('detail', 1)
        self.assert_json_equal('', 'detail/@0/article', 'ABC5')
        self.assert_json_equal('', 'detail/@0/designation', 'article 5')
        self.assert_json_equal('', 'detail/@0/price', 15.00)
        self.assert_json_equal('', 'detail/@0/unit', '')
        self.assert_json_equal('', 'detail/@0/quantity_txt', '7,00')
        self.assert_json_equal('', 'detail/@0/reduce_txt', '45,00 €')
        self.assert_json_equal('', 'detail/@0/total', 60.00)

        new_year = FiscalYear.objects.create(begin='2016-01-01', end='2016-12-31', status=0, last_fiscalyear_id=1)
        new_year.set_has_actif()
        self.assertEqual(FiscalYear.get_current().id, 2)

        self._create_bill([{'article': 5, 'designation': 'article 5', 'price': '15', 'quantity': 3}], 1, '2016-04-01', 6, False)  # 45
        self.factory.xfer = BillList()
        self.calljson('/diacamma.invoice/billList', {'status_filter': -2, 'GRID_ORDER%bill': 'id'}, False)
        self.assert_observer('core.custom', 'diacamma.invoice', 'billList')
        self.assert_count_equal('bill', 5)
        self.assert_json_equal('', 'bill/@4/third', 'Dalton Jack')
        self.assert_json_equal('', 'bill/@4/total', 45.00)
        self.assert_json_equal('', 'bill/@4/date', '2016-04-01')

    def test_autoreduce_checked(self):
        Params.setvalue('invoice-reduce-with-ratio', 'False')

        initial_thirds_fr()
        default_categories()
        default_articles()

        self.factory.xfer = ThirdShow()
        self.calljson('/diacamma.accounting/thirdShow', {"third": 6, 'status_filter': -2, 'GRID_ORDER%bill': 'id'}, False)
        self.assert_observer('core.custom', 'diacamma.accounting', 'thirdShow')
        self.assert_count_equal('bill', 0)
        self.assertFalse('btn_autoreduce' in self.json_data.keys(), self.json_data.keys())
        self.assertFalse('sum_summary' in self.json_data.keys(), self.json_data.keys())

        self._create_bill([{'article': 5, 'designation': 'article 5', 'price': '15', 'quantity': 5}], 0, '2015-04-01', 6, False)
        self._create_bill([{'article': 5, 'designation': 'article 5', 'price': '15', 'quantity': 7}], 0, '2015-04-02', 6, False)
        self._create_bill([{'article': 5, 'designation': 'article 5', 'price': '15', 'quantity': 2}], 1, '2015-04-03', 6, False)
        self._create_bill([{'article': 1, 'designation': 'article 1', 'price': '15', 'quantity': 20}], 1, '2015-04-04', 6, False)

        self.factory.xfer = ThirdShow()
        self.calljson('/diacamma.accounting/thirdShow', {"third": 6, 'status_filter': -2, 'GRID_ORDER%bill': 'id'}, False)
        self.assert_observer('core.custom', 'diacamma.accounting', 'thirdShow')
        self.assert_count_equal('bill', 4)
        self.assertFalse('btn_autoreduce' in self.json_data.keys(), self.json_data.keys())
        self.assert_json_equal('', 'sum_summary', [510.0, 0.0, 510.0])

        self.factory.xfer = AutomaticReduceAddModify()
        self.calljson('/diacamma.invoice/automaticReduceAddModify', {'name': "reduct #3", 'category': 2, 'mode': 2, 'amount': '25.0', 'occurency': '10', 'filtercriteria': '0', 'SAVE': 'YES'}, False)
        self.assert_observer('core.acknowledge', 'diacamma.invoice', 'automaticReduceAddModify')

        self.factory.xfer = ThirdShow()
        self.calljson('/diacamma.accounting/thirdShow', {"third": 6, 'status_filter': -2, 'GRID_ORDER%bill': 'id'}, False)
        self.assert_observer('core.custom', 'diacamma.accounting', 'thirdShow')
        self.assert_count_equal('bill', 4)
        self.assert_json_equal('', 'bill/@0/third', 'Dalton Jack')
        self.assert_json_equal('', 'bill/@0/total', 75.00)
        self.assert_json_equal('', 'bill/@0/date', '2015-04-01')
        self.assert_json_equal('', 'bill/@1/third', 'Dalton Jack')
        self.assert_json_equal('', 'bill/@1/total', 105.00)
        self.assert_json_equal('', 'bill/@1/date', '2015-04-02')
        self.assert_json_equal('', 'bill/@2/third', 'Dalton Jack')
        self.assert_json_equal('', 'bill/@2/total', 30.00)
        self.assert_json_equal('', 'bill/@2/date', '2015-04-03')
        self.assert_json_equal('', 'bill/@3/third', 'Dalton Jack')
        self.assert_json_equal('', 'bill/@3/total', 300.00)
        self.assert_json_equal('', 'bill/@3/date', '2015-04-04')
        self.assertTrue('btn_autoreduce' in self.json_data.keys(), self.json_data.keys())
        self.assert_json_equal('', 'sum_summary', [510.0, 0.0, 510.0])

        self.factory.xfer = BillCheckAutoreduce()
        self.calljson('/diacamma.invoice/billCheckAutoreduce', {'third': 6, 'CONFIRME': 'YES'}, False)
        self.assert_observer('core.acknowledge', 'diacamma.invoice', 'billCheckAutoreduce')

        self.factory.xfer = ThirdShow()
        self.calljson('/diacamma.accounting/thirdShow', {"third": 6, 'status_filter': -2, 'GRID_ORDER%bill': 'id'}, False)
        self.assert_observer('core.custom', 'diacamma.accounting', 'thirdShow')
        self.assert_count_equal('bill', 4)
        self.assert_json_equal('', 'bill/@0/third', 'Dalton Jack')
        self.assert_json_equal('', 'bill/@0/total', 75.00)
        self.assert_json_equal('', 'bill/@0/date', '2015-04-01')
        self.assert_json_equal('', 'bill/@1/third', 'Dalton Jack')
        self.assert_json_equal('', 'bill/@1/total', 52.50)
        self.assert_json_equal('', 'bill/@1/date', '2015-04-02')
        self.assert_json_equal('', 'bill/@2/third', 'Dalton Jack')
        self.assert_json_equal('', 'bill/@2/total', 30.00)
        self.assert_json_equal('', 'bill/@2/date', '2015-04-03')
        self.assert_json_equal('', 'bill/@3/third', 'Dalton Jack')
        self.assert_json_equal('', 'bill/@3/total', 300.00)
        self.assert_json_equal('', 'bill/@3/date', '2015-04-04')
        self.assert_json_equal('', 'sum_summary', [510.0, 52.5, 457.5])

        self.factory.xfer = AutomaticReduceDel()
        self.calljson('/diacamma.invoice/automaticReduceDel', {'automaticreduce': '1', 'CONFIRME': 'YES'}, False)
        self.assert_observer('core.acknowledge', 'diacamma.invoice', 'automaticReduceDel')

        self.factory.xfer = AutomaticReduceAddModify()
        self.calljson('/diacamma.invoice/automaticReduceAddModify', {'name': "reduct #2", 'category': 2, 'mode': 1, 'amount': '10.0', 'occurency': '0', 'filtercriteria': '0', 'SAVE': 'YES'}, False)
        self.assert_observer('core.acknowledge', 'diacamma.invoice', 'automaticReduceAddModify')

        self.factory.xfer = BillCheckAutoreduce()
        self.calljson('/diacamma.invoice/billCheckAutoreduce', {'third': 6, 'CONFIRME': 'YES'}, False)
        self.assert_observer('core.acknowledge', 'diacamma.invoice', 'billCheckAutoreduce')

        self.factory.xfer = ThirdShow()
        self.calljson('/diacamma.accounting/thirdShow', {"third": 6, 'status_filter': -2, 'GRID_ORDER%bill': 'id'}, False)
        self.assert_observer('core.custom', 'diacamma.accounting', 'thirdShow')
        self.assert_count_equal('bill', 4)
        self.assert_json_equal('', 'bill/@0/third', 'Dalton Jack')
        self.assert_json_equal('', 'bill/@0/total', 67.50)
        self.assert_json_equal('', 'bill/@0/date', '2015-04-01')
        self.assert_json_equal('', 'bill/@0/status', 0)
        self.assert_json_equal('', 'bill/@1/third', 'Dalton Jack')
        self.assert_json_equal('', 'bill/@1/total', 94.50)
        self.assert_json_equal('', 'bill/@1/date', '2015-04-02')
        self.assert_json_equal('', 'bill/@1/status', 0)
        self.assert_json_equal('', 'bill/@2/third', 'Dalton Jack')
        self.assert_json_equal('', 'bill/@2/total', 27.00)
        self.assert_json_equal('', 'bill/@2/date', '2015-04-03')
        self.assert_json_equal('', 'bill/@2/status', 0)
        self.assert_json_equal('', 'bill/@3/third', 'Dalton Jack')
        self.assert_json_equal('', 'bill/@3/total', 300.00)
        self.assert_json_equal('', 'bill/@3/date', '2015-04-04')
        self.assert_json_equal('', 'bill/@3/status', 0)
        self.assertTrue('btn_autoreduce' in self.json_data.keys(), self.json_data.keys())
        self.assert_json_equal('', 'sum_summary', [510.0, 21.0, 489.0])

    def test_autoreduce_valid_quotation(self):
        Params.setvalue('invoice-reduce-with-ratio', 'False')

        initial_thirds_fr()
        default_categories()
        default_articles()

        self.factory.xfer = ThirdShow()
        self.calljson('/diacamma.accounting/thirdShow', {"third": 6, 'status_filter': -2, 'GRID_ORDER%bill': 'id'}, False)
        self.assert_observer('core.custom', 'diacamma.accounting', 'thirdShow')
        self.assert_count_equal('bill', 0)
        self.assertFalse('btn_autoreduce' in self.json_data.keys(), self.json_data.keys())
        self.assertFalse('sum_summary' in self.json_data.keys(), self.json_data.keys())

        self.factory.xfer = AutomaticReduceAddModify()
        self.calljson('/diacamma.invoice/automaticReduceAddModify', {'name': "reduct #3", 'category': 2, 'mode': 2, 'amount': '25.0', 'occurency': '10', 'filtercriteria': '0', 'SAVE': 'YES'}, False)
        self.assert_observer('core.acknowledge', 'diacamma.invoice', 'automaticReduceAddModify')

        self._create_bill([{'article': 5, 'designation': 'article 5', 'price': '15', 'quantity': 5}], 0, '2015-04-01', 6, True)
        self._create_bill([{'article': 5, 'designation': 'article 5', 'price': '15', 'quantity': 7}], 0, '2015-04-02', 6, True)
        self._create_bill([{'article': 5, 'designation': 'article 5', 'price': '15', 'quantity': 2}], 1, '2015-04-03', 6, True)
        self._create_bill([{'article': 1, 'designation': 'article 1', 'price': '15', 'quantity': 20}], 1, '2015-04-04', 6, True)

        self.factory.xfer = ThirdShow()
        self.calljson('/diacamma.accounting/thirdShow', {"third": 6, 'status_filter': -2, 'GRID_ORDER%bill': 'id'}, False)
        self.assert_observer('core.custom', 'diacamma.accounting', 'thirdShow')
        self.assert_count_equal('bill', 4)
        self.assert_json_equal('', 'bill/@0/third', 'Dalton Jack')
        self.assert_json_equal('', 'bill/@0/total', 75.00)
        self.assert_json_equal('', 'bill/@0/status', 1)
        self.assert_json_equal('', 'bill/@0/date', '2015-04-01')
        self.assert_json_equal('', 'bill/@1/third', 'Dalton Jack')
        self.assert_json_equal('', 'bill/@1/total', 60.00)
        self.assert_json_equal('', 'bill/@1/status', 1)
        self.assert_json_equal('', 'bill/@1/date', '2015-04-02')
        self.assert_json_equal('', 'bill/@2/third', 'Dalton Jack')
        self.assert_json_equal('', 'bill/@2/total', 22.50)
        self.assert_json_equal('', 'bill/@2/date', '2015-04-03')
        self.assert_json_equal('', 'bill/@2/status', 1)
        self.assert_json_equal('', 'bill/@3/third', 'Dalton Jack')
        self.assert_json_equal('', 'bill/@3/total', 300.00)
        self.assert_json_equal('', 'bill/@3/date', '2015-04-04')
        self.assert_json_equal('', 'bill/@3/status', 1)
        self.assert_json_equal('', '#sum_summary/formatnum', 'C2EUR')
        self.assert_json_equal('', '#sum_summary/formatstr', "{[b]}Total brut{[/b]} : {0} - {[b]}total des réductions{[/b]} : {1} = {[b]}total à règler{[/b]} : {2}")
        self.assert_json_equal('', 'sum_summary', [510.0, 52.5, 457.5])

        self.factory.xfer = BillToBill()
        self.calljson('/diacamma.invoice/billToBill', {'CONFIRME': 'YES', 'bill': 1}, False)
        self.assert_observer('core.acknowledge', 'diacamma.invoice', 'billToBill')

        self.factory.xfer = ThirdShow()
        self.calljson('/diacamma.accounting/thirdShow', {"third": 6, 'status_filter': -2, 'GRID_ORDER%bill': 'id'}, False)
        self.assert_observer('core.custom', 'diacamma.accounting', 'thirdShow')
        self.assert_count_equal('bill', 5)
        self.assert_json_equal('', 'bill/@0/third', 'Dalton Jack')
        self.assert_json_equal('', 'bill/@0/total', 75.00)
        self.assert_json_equal('', 'bill/@0/status', 3)
        self.assert_json_equal('', 'bill/@0/date', '2015-04-01')
        self.assert_json_equal('', 'bill/@1/third', 'Dalton Jack')
        self.assert_json_equal('', 'bill/@1/total', 60.00)
        self.assert_json_equal('', 'bill/@1/status', 1)
        self.assert_json_equal('', 'bill/@1/date', '2015-04-02')
        self.assert_json_equal('', 'bill/@2/third', 'Dalton Jack')
        self.assert_json_equal('', 'bill/@2/total', 22.50)
        self.assert_json_equal('', 'bill/@2/date', '2015-04-03')
        self.assert_json_equal('', 'bill/@2/status', 1)
        self.assert_json_equal('', 'bill/@3/third', 'Dalton Jack')
        self.assert_json_equal('', 'bill/@3/total', 300.00)
        self.assert_json_equal('', 'bill/@3/date', '2015-04-04')
        self.assert_json_equal('', 'bill/@3/status', 1)
        self.assert_json_equal('', 'bill/@4/third', 'Dalton Jack')
        self.assert_json_equal('', 'bill/@4/total', 75.00)
        self.assert_json_equal('', 'bill/@4/status', 0)
        self.assert_json_equal('', 'sum_summary', [510.0, 52.5, 457.5])

        self.factory.xfer = BillCheckAutoreduce()
        self.calljson('/diacamma.invoice/billCheckAutoreduce', {'third': 6, 'CONFIRME': 'YES'}, False)
        self.assert_observer('core.acknowledge', 'diacamma.invoice', 'billCheckAutoreduce')

        self.factory.xfer = ThirdShow()
        self.calljson('/diacamma.accounting/thirdShow', {"third": 6, 'status_filter': -2, 'GRID_ORDER%bill': 'id'}, False)
        self.assert_observer('core.custom', 'diacamma.accounting', 'thirdShow')
        self.assert_count_equal('bill', 5)
        self.assert_json_equal('', 'bill/@0/third', 'Dalton Jack')
        self.assert_json_equal('', 'bill/@0/total', 75.00)
        self.assert_json_equal('', 'bill/@0/status', 3)
        self.assert_json_equal('', 'bill/@0/date', '2015-04-01')
        self.assert_json_equal('', 'bill/@1/third', 'Dalton Jack')
        self.assert_json_equal('', 'bill/@1/total', 60.00)
        self.assert_json_equal('', 'bill/@1/status', 1)
        self.assert_json_equal('', 'bill/@1/date', '2015-04-02')
        self.assert_json_equal('', 'bill/@2/third', 'Dalton Jack')
        self.assert_json_equal('', 'bill/@2/total', 22.50)
        self.assert_json_equal('', 'bill/@2/date', '2015-04-03')
        self.assert_json_equal('', 'bill/@2/status', 1)
        self.assert_json_equal('', 'bill/@3/third', 'Dalton Jack')
        self.assert_json_equal('', 'bill/@3/total', 300.00)
        self.assert_json_equal('', 'bill/@3/date', '2015-04-04')
        self.assert_json_equal('', 'bill/@3/status', 1)
        self.assert_json_equal('', 'bill/@4/third', 'Dalton Jack')
        self.assert_json_equal('', 'bill/@4/total', 75.00)
        self.assert_json_equal('', 'bill/@4/status', 0)
        self.assert_json_equal('', 'sum_summary', [510.0, 52.5, 457.5])

    def test_autoreduce_with_asset1(self):
        initial_thirds_fr()
        default_categories()
        default_articles()

        self.factory.xfer = AutomaticReduceAddModify()
        self.calljson('/diacamma.invoice/automaticReduceAddModify', {'name': "reduct #1", 'category': 2, 'mode': 0, 'amount': '15.0', 'occurency': '4', 'filtercriteria': '0', 'SAVE': 'YES'}, False)
        self.assert_observer('core.acknowledge', 'diacamma.invoice', 'automaticReduceAddModify')

        self.factory.xfer = BillList()
        self.calljson('/diacamma.invoice/billList', {'status_filter': 1}, False)
        self.assert_observer('core.custom', 'diacamma.invoice', 'billList')
        self.assert_count_equal('bill', 0)

        self._create_bill([{'article': 5, 'designation': 'article 5', 'price': '100', 'quantity': 5}], 1, '2015-04-01', 6, True)  # +470€
        self._create_bill([{'article': 5, 'designation': 'article 5', 'price': '100', 'quantity': 3}], 2, '2015-04-02', 6, True)  # -270€
        self._create_bill([{'article': 5, 'designation': 'article 5', 'price': '100', 'quantity': 2}], 1, '2015-04-03', 6, True)  # +185€

        self.factory.xfer = ThirdShow()
        self.calljson('/diacamma.accounting/thirdShow', {'third': 6, 'status_filter': -2, 'GRID_ORDER%bill': 'id'}, False)
        self.assert_observer('core.custom', 'diacamma.accounting', 'thirdShow')
        self.assert_count_equal('bill', 3)
        self.assert_json_equal('', 'bill/@0/bill_type', 1)
        self.assert_json_equal('', 'bill/@0/third', 'Dalton Jack')
        self.assert_json_equal('', 'bill/@0/total', 470.00)
        self.assert_json_equal('', 'bill/@0/date', '2015-04-01')
        self.assert_json_equal('', 'bill/@1/bill_type', 2)
        self.assert_json_equal('', 'bill/@1/third', 'Dalton Jack')
        self.assert_json_equal('', 'bill/@1/total', 270.00)
        self.assert_json_equal('', 'bill/@1/date', '2015-04-02')
        self.assert_json_equal('', 'bill/@2/bill_type', 1)
        self.assert_json_equal('', 'bill/@2/third', 'Dalton Jack')
        self.assert_json_equal('', 'bill/@2/total', 185.00)
        self.assert_json_equal('', 'bill/@2/date', '2015-04-03')
        self.assert_json_equal('LABELFORM', 'sum_summary', [400.0, 15.0, 385.0])

    def test_autoreduce_with_asset2(self):
        initial_thirds_fr()
        default_categories()
        default_articles()

        self.factory.xfer = AutomaticReduceAddModify()
        self.calljson('/diacamma.invoice/automaticReduceAddModify', {'name': "reduct #2", 'category': 2, 'mode': 1, 'amount': '20.0', 'occurency': '4', 'filtercriteria': '0', 'SAVE': 'YES'}, False)
        self.assert_observer('core.acknowledge', 'diacamma.invoice', 'automaticReduceAddModify')

        self.factory.xfer = BillList()
        self.calljson('/diacamma.invoice/billList', {'status_filter': 1}, False)
        self.assert_observer('core.custom', 'diacamma.invoice', 'billList')
        self.assert_count_equal('bill', 0)

        self._create_bill([{'article': 5, 'designation': 'article 5', 'price': '100', 'quantity': 5}], 1, '2015-04-01', 6, True)  # +460€
        self._create_bill([{'article': 5, 'designation': 'article 5', 'price': '100', 'quantity': 3}], 2, '2015-04-02', 6, True)  # -260€
        self._create_bill([{'article': 5, 'designation': 'article 5', 'price': '100', 'quantity': 2}], 1, '2015-04-03', 6, True)  # +180€

        self.factory.xfer = ThirdShow()
        self.calljson('/diacamma.accounting/thirdShow', {'third': 6, 'status_filter': -2, 'GRID_ORDER%bill': 'id'}, False)
        self.assert_observer('core.custom', 'diacamma.accounting', 'thirdShow')
        self.assert_count_equal('bill', 3)
        self.assert_json_equal('', 'bill/@0/bill_type', 1)
        self.assert_json_equal('', 'bill/@0/third', 'Dalton Jack')
        self.assert_json_equal('', 'bill/@0/total', 460.00)
        self.assert_json_equal('', 'bill/@0/date', '2015-04-01')
        self.assert_json_equal('', 'bill/@1/bill_type', 2)
        self.assert_json_equal('', 'bill/@1/third', 'Dalton Jack')
        self.assert_json_equal('', 'bill/@1/total', 260.00)
        self.assert_json_equal('', 'bill/@1/date', '2015-04-02')
        self.assert_json_equal('', 'bill/@2/bill_type', 1)
        self.assert_json_equal('', 'bill/@2/third', 'Dalton Jack')
        self.assert_json_equal('', 'bill/@2/total', 180.00)
        self.assert_json_equal('', 'bill/@2/date', '2015-04-03')
        self.assert_json_equal('LABELFORM', 'sum_summary', [400.0, 20.0, 380.0])

    def test_autoreduce_with_asset3(self):
        initial_thirds_fr()
        default_categories()
        default_articles()

        self.factory.xfer = AutomaticReduceAddModify()
        self.calljson('/diacamma.invoice/automaticReduceAddModify', {'name': "reduct #3", 'category': 2, 'mode': 2, 'amount': '10.0', 'occurency': '4', 'filtercriteria': '0', 'SAVE': 'YES'}, False)
        self.assert_observer('core.acknowledge', 'diacamma.invoice', 'automaticReduceAddModify')

        self.factory.xfer = BillList()
        self.calljson('/diacamma.invoice/billList', {'status_filter': 1}, False)
        self.assert_observer('core.custom', 'diacamma.invoice', 'billList')
        self.assert_count_equal('bill', 0)

        self._create_bill([{'article': 5, 'designation': 'article 5', 'price': '100', 'quantity': 5}], 1, '2015-04-01', 6, True)  # +450€
        self._create_bill([{'article': 5, 'designation': 'article 5', 'price': '100', 'quantity': 3}], 2, '2015-04-02', 6, True)  # -250€
        self._create_bill([{'article': 5, 'designation': 'article 5', 'price': '100', 'quantity': 4}], 1, '2015-04-03', 6, True)  # +340€
        self._create_bill([{'article': 5, 'designation': 'article 5', 'price': '100', 'quantity': 1}], 2, '2015-04-02', 6, True)  # -90€

        self.factory.xfer = ThirdShow()
        self.calljson('/diacamma.accounting/thirdShow', {'third': 6, 'status_filter': -2, 'GRID_ORDER%bill': 'id'}, False)
        self.assert_observer('core.custom', 'diacamma.accounting', 'thirdShow')
        self.assert_count_equal('bill', 4)
        self.assert_json_equal('', 'bill/@0/bill_type', 1)
        self.assert_json_equal('', 'bill/@0/third', 'Dalton Jack')
        self.assert_json_equal('', 'bill/@0/total', 450.00)
        self.assert_json_equal('', 'bill/@0/date', '2015-04-01')
        self.assert_json_equal('', 'bill/@1/bill_type', 2)
        self.assert_json_equal('', 'bill/@1/third', 'Dalton Jack')
        self.assert_json_equal('', 'bill/@1/total', 250.00)
        self.assert_json_equal('', 'bill/@1/date', '2015-04-02')
        self.assert_json_equal('', 'bill/@2/bill_type', 1)
        self.assert_json_equal('', 'bill/@2/third', 'Dalton Jack')
        self.assert_json_equal('', 'bill/@2/total', 340.00)
        self.assert_json_equal('', 'bill/@2/date', '2015-04-03')
        self.assert_json_equal('', 'bill/@3/bill_type', 2)
        self.assert_json_equal('', 'bill/@3/third', 'Dalton Jack')
        self.assert_json_equal('', 'bill/@3/total', 90.00)
        self.assert_json_equal('', 'bill/@3/date', '2015-04-02')
        self.assert_json_equal('LABELFORM', 'sum_summary', [500.0, 50.0, 450.0])

    def test_autoreduce_with_asset_mutliple(self):
        initial_thirds_fr()
        default_categories()
        default_articles()

        self.factory.xfer = AutomaticReduceAddModify()
        self.calljson('/diacamma.invoice/automaticReduceAddModify', {'name': "reduct #A", 'category': 2, 'mode': 2, 'amount': '10.0', 'occurency': '3', 'filtercriteria': '0', 'SAVE': 'YES'}, False)
        self.assert_observer('core.acknowledge', 'diacamma.invoice', 'automaticReduceAddModify')
        self.factory.xfer = AutomaticReduceAddModify()
        self.calljson('/diacamma.invoice/automaticReduceAddModify', {'name': "reduct #B", 'category': 2, 'mode': 2, 'amount': '15.0', 'occurency': '4', 'filtercriteria': '0', 'SAVE': 'YES'}, False)
        self.assert_observer('core.acknowledge', 'diacamma.invoice', 'automaticReduceAddModify')
        self.factory.xfer = AutomaticReduceAddModify()
        self.calljson('/diacamma.invoice/automaticReduceAddModify', {'name': "reduct #C", 'category': 2, 'mode': 2, 'amount': '25.0', 'occurency': '5', 'filtercriteria': '0', 'SAVE': 'YES'}, False)
        self.assert_observer('core.acknowledge', 'diacamma.invoice', 'automaticReduceAddModify')

        details = [
            {'article': 5, 'designation': 'article 5', 'price': '185', 'quantity': 1},
            {'article': 5, 'designation': 'article 5', 'price': '200', 'quantity': 1},
            {'article': 5, 'designation': 'article 5', 'price': '200', 'quantity': 1},
            {'article': 5, 'designation': 'article 5', 'price': '200', 'quantity': 1},
            {'article': 5, 'designation': 'article 5', 'price': '215', 'quantity': 1},
            {'article': 5, 'designation': 'article 5', 'price': '185', 'quantity': 1},
            {'article': 5, 'designation': 'article 5', 'price': '185', 'quantity': 1},
            {'article': 5, 'designation': 'article 5', 'price': '185', 'quantity': 1},
            {'article': 5, 'designation': 'article 5', 'price': '200', 'quantity': 1},
            {'article': 5, 'designation': 'article 5', 'price': '200', 'quantity': 1},
            {'article': 5, 'designation': 'article 5', 'price': '200', 'quantity': 1},
        ]
        self._create_bill(details, 1, '2015-04-01', 6, True)

        self.factory.xfer = ThirdShow()
        self.calljson('/diacamma.accounting/thirdShow', {'third': 6, 'status_filter': -2, 'GRID_ORDER%bill': 'id'}, False)
        self.assert_observer('core.custom', 'diacamma.accounting', 'thirdShow')
        self.assert_count_equal('bill', 1)
        self.assert_json_equal('', 'bill/@0/bill_type', 1)
        self.assert_json_equal('', 'bill/@0/third', 'Dalton Jack')
        self.assert_json_equal('', 'bill/@0/total', 1616.25)
        self.assert_json_equal('', 'bill/@0/date', '2015-04-01')
        self.assert_json_equal('LABELFORM', 'sum_summary', [2155, 538.75, 1616.25])

        self._create_bill([{'article': 5, 'designation': 'article 5', 'price': '200', 'quantity': 1}], 2, '2015-04-02', 6, True)

        self.factory.xfer = ThirdShow()
        self.calljson('/diacamma.accounting/thirdShow', {'third': 6, 'status_filter': -2, 'GRID_ORDER%bill': 'id'}, False)
        self.assert_observer('core.custom', 'diacamma.accounting', 'thirdShow')
        self.assert_count_equal('bill', 2)
        self.assert_json_equal('', 'bill/@0/bill_type', 1)
        self.assert_json_equal('', 'bill/@0/third', 'Dalton Jack')
        self.assert_json_equal('', 'bill/@0/total', 1616.25)
        self.assert_json_equal('', 'bill/@0/date', '2015-04-01')
        self.assert_json_equal('', 'bill/@1/bill_type', 2)
        self.assert_json_equal('', 'bill/@1/third', 'Dalton Jack')
        self.assert_json_equal('', 'bill/@1/total', 150.00)
        self.assert_json_equal('', 'bill/@1/date', '2015-04-02')
        self.assert_json_equal('LABELFORM', 'sum_summary', [1955, 488.75, 1466.25])

    def test_valid_multiple(self):
        default_articles()
        details = [{'article': 0, 'designation': 'article 0', 'price': '20.00', 'quantity': 15}]
        self._create_bill(details, 0, '2015-04-01', 6, False)  # 59.50
        details = [{'article': 1, 'designation': 'article 1', 'price': '22.00', 'quantity': 3, 'reduce': '5.0'},
                   {'article': 2, 'designation': 'article 2', 'price': '3.25', 'quantity': 7}]
        self._create_bill(details, 1, '2015-04-01', 6, False)  # 83.75
        details = [{'article': 0, 'designation': 'article 0', 'price': '50.00', 'quantity': 2},
                   {'article': 5, 'designation': 'article 5', 'price': '6.33', 'quantity': 6.75}]
        self._create_bill(details, 3, '2015-04-01', 4, False)  # 142.73
        details = [{'article': 1, 'designation': 'article 1', 'price': '23.00', 'quantity': 3},
                   {'article': 5, 'designation': 'article 5', 'price': '6.33', 'quantity': 3.50}]
        self._create_bill(details, 1, '2015-04-01', 5, False)  # 91.16
        details = [{'article': 2, 'designation': 'article 2', 'price': '3.30', 'quantity': 5},
                   {'article': 5, 'designation': 'article 5', 'price': '6.35', 'quantity': 4.25, 'reduce': '2.0'}]
        self._create_bill(details, 1, '2015-04-01', 6, False)  # 41.49
        details = [{'article': 5, 'designation': 'article 5', 'price': '6.33', 'quantity': 1.25}]
        self._create_bill(details, 2, '2015-04-01', 4, False)  # 7.91

        self.factory.xfer = BillList()
        self.calljson('/diacamma.invoice/billList', {'status_filter': 0}, False)
        self.assert_observer('core.custom', 'diacamma.invoice', 'billList')
        self.assert_count_equal('bill', 6)

        self.factory.xfer = BillList()
        self.calljson('/diacamma.invoice/billList', {'status_filter': 1}, False)
        self.assert_observer('core.custom', 'diacamma.invoice', 'billList')
        self.assert_count_equal('bill', 0)

        self.factory.xfer = BillTransition()
        self.calljson('/diacamma.invoice/billTransition',
                      {'bill': '1;2;4;6', 'TRANSITION': 'valid'}, False)
        self.assert_observer('core.dialogbox', 'diacamma.invoice', 'billTransition')

        self.factory.xfer = BillTransition()
        self.calljson('/diacamma.invoice/billTransition',
                      {'CONFIRME': 'YES', 'bill': '1;2;4;6', 'TRANSITION': 'valid'}, False)
        self.assert_observer('core.acknowledge', 'diacamma.invoice', 'billTransition')

        self.factory.xfer = BillList()
        self.calljson('/diacamma.invoice/billList', {'status_filter': 0}, False)
        self.assert_observer('core.custom', 'diacamma.invoice', 'billList')
        self.assert_count_equal('bill', 2)

        self.factory.xfer = BillList()
        self.calljson('/diacamma.invoice/billList', {'status_filter': 1}, False)
        self.assert_observer('core.custom', 'diacamma.invoice', 'billList')
        self.assert_count_equal('bill', 4)

    def test_archive_multiple(self):
        default_articles()
        details = [{'article': 0, 'designation': 'article 0', 'price': '20.00', 'quantity': 15}]
        self._create_bill(details, 0, '2015-04-01', 6, True)  # 59.50
        details = [{'article': 1, 'designation': 'article 1', 'price': '22.00', 'quantity': 3, 'reduce': '5.0'},
                   {'article': 2, 'designation': 'article 2', 'price': '3.25', 'quantity': 7}]
        self._create_bill(details, 1, '2015-04-01', 6, True)  # 83.75
        details = [{'article': 0, 'designation': 'article 0', 'price': '50.00', 'quantity': 2},
                   {'article': 5, 'designation': 'article 5', 'price': '6.33', 'quantity': 6.75}]
        self._create_bill(details, 3, '2015-04-01', 4, True)  # 142.73
        details = [{'article': 1, 'designation': 'article 1', 'price': '23.00', 'quantity': 3},
                   {'article': 5, 'designation': 'article 5', 'price': '6.33', 'quantity': 3.50}]
        self._create_bill(details, 1, '2015-04-01', 5, True)  # 91.16
        details = [{'article': 2, 'designation': 'article 2', 'price': '3.30', 'quantity': 5},
                   {'article': 5, 'designation': 'article 5', 'price': '6.35', 'quantity': 4.25, 'reduce': '2.0'}]
        self._create_bill(details, 1, '2015-04-01', 6, True)  # 41.49
        details = [{'article': 5, 'designation': 'article 5', 'price': '6.33', 'quantity': 1.25}]
        self._create_bill(details, 2, '2015-04-01', 4, True)  # 7.91

        self.factory.xfer = BillList()
        self.calljson('/diacamma.invoice/billList', {'status_filter': 0}, False)
        self.assert_observer('core.custom', 'diacamma.invoice', 'billList')
        self.assert_count_equal('bill', 0)

        self.factory.xfer = BillList()
        self.calljson('/diacamma.invoice/billList', {'status_filter': 1}, False)
        self.assert_observer('core.custom', 'diacamma.invoice', 'billList')
        self.assert_count_equal('bill', 6)

        self.factory.xfer = BillList()
        self.calljson('/diacamma.invoice/billList', {'status_filter': 3}, False)
        self.assert_observer('core.custom', 'diacamma.invoice', 'billList')
        self.assert_count_equal('bill', 0)

        self.factory.xfer = BillTransition()
        self.calljson('/diacamma.invoice/billTransition',
                      {'bill': '2;3;5;6', 'TRANSITION': 'archive'}, False)
        self.assert_observer('core.dialogbox', 'diacamma.invoice', 'billTransition')

        self.factory.xfer = BillTransition()
        self.calljson('/diacamma.invoice/billTransition',
                      {'CONFIRME': 'YES', 'bill': '2;3;5;6', 'TRANSITION': 'archive'}, False)
        self.assert_observer('core.acknowledge', 'diacamma.invoice', 'billTransition')

        self.factory.xfer = BillList()
        self.calljson('/diacamma.invoice/billList', {'status_filter': 0}, False)
        self.assert_observer('core.custom', 'diacamma.invoice', 'billList')
        self.assert_count_equal('bill', 0)

        self.factory.xfer = BillList()
        self.calljson('/diacamma.invoice/billList', {'status_filter': 1}, False)
        self.assert_observer('core.custom', 'diacamma.invoice', 'billList')
        self.assert_count_equal('bill', 2)

        self.factory.xfer = BillList()
        self.calljson('/diacamma.invoice/billList', {'status_filter': 3}, False)
        self.assert_observer('core.custom', 'diacamma.invoice', 'billList')
        self.assert_count_equal('bill', 4)

    def test_batch(self):
        default_articles()
        SavedCriteria.objects.create(name='my filter', modelname='accounting.Third', criteria="contact.city||1||LE PRECHEUR")
        SavedCriteria.objects.create(name='other filter', modelname='accounting.Third', criteria='')

        self.factory.xfer = BillList()
        self.calljson('/diacamma.invoice/billList', {'status_filter': -2}, False)
        self.assert_observer('core.custom', 'diacamma.invoice', 'billList')
        self.assert_count_equal('bill', 0)

        self.factory.xfer = BillBatch()
        self.calljson('/diacamma.invoice/billBatch', {}, False)
        self.assert_observer('core.custom', 'diacamma.invoice', 'billBatch')
        self.assert_count_equal('', 14)
        self.assert_select_equal('thirds', {1: 'my filter', 2: 'other filter'})
        self.assert_select_equal('article', 5)

        self.factory.xfer = BillBatch()
        self.calljson('/diacamma.invoice/billBatch', {"SAVE": "YES", 'thirds': 1, "bill_type": 2, "date": "2015-06-20", "comment": "remboursement",
                                                      "article": 3, "designation": "Article 03", "price": 12.34, "quantity": 5.6, "unit": "", "reduce": 9.9}, False)
        self.assert_observer('core.dialogbox', 'diacamma.invoice', 'billBatch')
        self.assert_json_equal('', 'text', 'Voulez-vous créer le justificatif "avoir" de 59,20 € pour 5 clients ?')

        self.factory.xfer = BillBatch()
        self.calljson('/diacamma.invoice/billBatch', {"SAVE": "YES", 'CONFIRME': 'YES', 'thirds': 1, "bill_type": 2, "date": "2015-06-20", "comment": "remboursement",
                                                      "article": 3, "designation": "Article 03", "price": 12.34, "quantity": 5.6, "unit": "", "reduce": 9.9}, False)
        self.assert_observer('core.acknowledge', 'diacamma.invoice', 'billBatch')

        self.factory.xfer = BillList()
        self.calljson('/diacamma.invoice/billList', {'status_filter': -2}, False)
        self.assert_observer('core.custom', 'diacamma.invoice', 'billList')
        self.assert_count_equal('bill', 5)

    def test_with_categorybill(self):
        Params.setvalue('invoice-cart-active', True)
        default_paymentmethod()
        default_articles()
        default_categorybill()

        self.factory.xfer = BillAddModify()
        self.calljson('/diacamma.invoice/billAddModify', {}, False)
        self.assert_observer('core.custom', 'diacamma.invoice', 'billAddModify')
        self.assert_count_equal('', 6)
        self.assert_select_equal('categoryBill', {0: None, 1: '1st type', 2: '2nd type'})
        self.assert_json_equal('SELECT', 'categoryBill', 0)
        self.assert_select_equal('bill_type', {0: 'devis', 1: 'facture', 2: 'avoir', 3: 'reçu'})

        cat2 = CategoryBill.objects.get(id=2)
        cat2.change_has_default()

        self.factory.xfer = BillAddModify()
        self.calljson('/diacamma.invoice/billAddModify', {}, False)
        self.assert_observer('core.custom', 'diacamma.invoice', 'billAddModify')
        self.assert_count_equal('', 6)
        self.assert_json_equal('SELECT', 'categoryBill', 2)
        self.assert_select_equal('bill_type', {0: 'Type Q', 1: 'Type B', 2: 'Type A'})

        self.factory.xfer = BillAddModify()
        self.calljson('/diacamma.invoice/billAddModify', {'categoryBill': 2, 'bill_type': 0, 'date': '2015-06-20', 'SAVE': 'YES'}, False)
        self.assert_observer('core.acknowledge', 'diacamma.invoice', 'billAddModify')

        self.factory.xfer = SupportingThirdValid()
        self.calljson('/diacamma.payoff/supportingThirdValid', {'supporting': 1, 'third': 6}, False)
        self.assert_observer('core.acknowledge', 'diacamma.payoff', 'supportingThirdValid')

        self.factory.xfer = DetailAddModify()
        self.calljson('/diacamma.invoice/detailAddModify',
                      {'SAVE': 'YES', 'bill': 1, 'article': 1, 'designation': 'My article', 'price': '50.00', 'quantity': 2}, False)
        self.assert_observer('core.acknowledge', 'diacamma.invoice', 'detailAddModify')

        self.factory.xfer = BillTransition()
        self.calljson('/diacamma.invoice/billTransition',
                      {'CONFIRME': 'YES', 'bill': 1, 'TRANSITION': 'valid'}, False)
        self.assert_observer('core.acknowledge', 'diacamma.invoice', 'billTransition')

        self.factory.xfer = BillList()
        self.calljson('/diacamma.invoice/billList', {'status_filter': -2}, False)
        self.assert_observer('core.custom', 'diacamma.invoice', 'billList')
        self.assert_select_equal('type_filter', {'-1': None,
                                                 '0': "devis", '4': "commande", '1': "facture", '2': "avoir", '3': "reçu",
                                                 '2|5': "[2nd type]Type C", '2|0': "[2nd type]Type Q", '2|1': "[2nd type]Type B", '2|2': "[2nd type]Type A",
                                                 '1|0': "[1st type]QQQ", '1|1': "[1st type]BBB", '1|2': "[1st type]AAA",
                                                 })
        self.assert_grid_equal('bill', {"bill_type": "type de facture", 'billtype': 'titre du type', "num_txt": "N°", "date": "date", "third": "tiers", "comment": "commentaire", "total": "total", "status": "statut"}, 1)
        self.assert_json_equal('', 'bill/@0/bill_type', 0)
        self.assert_json_equal('', 'bill/@0/billtype', 'Type Q')
        self.assert_json_equal('', 'bill/@0/third', "Dalton Jack")
        self.assert_json_equal('', 'bill/@0/date', '2015-06-20')
        self.assert_json_equal('', 'bill/@0/total', 100.00)
        self.assert_json_equal('', 'bill/@0/status', 1)

        self.factory.xfer = BillPrint()
        self.calljson('/diacamma.invoice/billPrint', {'bill': 1}, False)
        self.assert_observer('core.custom', 'diacamma.invoice', 'billPrint')
        self.assert_json_equal('SELECT', 'MODEL', 9)

        self.factory.xfer = BillShow()
        self.calljson('/diacamma.invoice/billShow', {'bill': 1}, False)
        self.assert_observer('core.custom', 'diacamma.invoice', 'billShow')
        self.assert_count_equal('', 12)
        self.assert_json_equal('LABELFORM', 'title', "Type Q")
        self.assert_json_equal('LABELFORM', 'num_txt', "A-1")
        self.assert_json_equal('LABELFORM', 'status', 1)
        self.assert_json_equal('LABELFORM', 'date', "2015-06-20")
        self.assert_json_equal('LABELFORM', 'categoryBill', '2nd type')
        self.assert_json_equal('LABELFORM', 'bill_type', 0)
        self.assert_count_equal('detail', 1)

        self.factory.xfer = BillToBill()
        self.calljson('/diacamma.invoice/billToBill',
                      {'CONFIRME': 'YES', 'bill': 1}, False)
        self.assert_observer('core.acknowledge', 'diacamma.invoice', 'billToBill')

        self.factory.xfer = BillAddModify()
        self.calljson('/diacamma.invoice/billAddModify', {'bill': 2, 'date': '2015-06-24', 'SAVE': 'YES'}, False)
        self.assert_observer('core.acknowledge', 'diacamma.invoice', 'billAddModify')

        self.factory.xfer = BillAddModify()
        self.calljson('/diacamma.invoice/billAddModify', {'categoryBill': 1, 'bill_type': 1, 'date': '2015-06-18', 'SAVE': 'YES'}, False)
        self.assert_observer('core.acknowledge', 'diacamma.invoice', 'billAddModify')

        self.factory.xfer = BillList()
        self.calljson('/diacamma.invoice/billList', {'status_filter': -2}, False)
        self.assert_observer('core.custom', 'diacamma.invoice', 'billList')
        self.assert_count_equal('bill', 3)
        self.assert_json_equal('', 'bill/@0/bill_type', 1)
        self.assert_json_equal('', 'bill/@0/billtype', 'Type B')
        self.assert_json_equal('', 'bill/@0/third', "Dalton Jack")
        self.assert_json_equal('', 'bill/@0/date', '2015-06-24')
        self.assert_json_equal('', 'bill/@0/total', 100.00)
        self.assert_json_equal('', 'bill/@0/status', 0)
        self.assert_json_equal('', 'bill/@1/bill_type', 0)
        self.assert_json_equal('', 'bill/@1/billtype', 'Type Q')
        self.assert_json_equal('', 'bill/@1/third', "Dalton Jack")
        self.assert_json_equal('', 'bill/@1/date', '2015-06-20')
        self.assert_json_equal('', 'bill/@1/total', 100.00)
        self.assert_json_equal('', 'bill/@1/status', 3)
        self.assert_json_equal('', 'bill/@2/bill_type', 1)
        self.assert_json_equal('', 'bill/@2/billtype', 'BBB')
        self.assert_json_equal('', 'bill/@2/third', None)
        self.assert_json_equal('', 'bill/@2/date', '2015-06-18')
        self.assert_json_equal('', 'bill/@2/total', 0.00)
        self.assert_json_equal('', 'bill/@2/status', 0)

        self.factory.xfer = BillList()
        self.calljson('/diacamma.invoice/billList', {'status_filter': -2, 'type_filter': '2|1'}, False)
        self.assert_observer('core.custom', 'diacamma.invoice', 'billList')
        self.assert_count_equal('bill', 1)
        self.assert_json_equal('', 'bill/@0/bill_type', 1)
        self.assert_json_equal('', 'bill/@0/billtype', 'Type B')
        self.assert_json_equal('', 'bill/@0/third', "Dalton Jack")
        self.assert_json_equal('', 'bill/@0/date', '2015-06-24')
        self.assert_json_equal('', 'bill/@0/total', 100.00)
        self.assert_json_equal('', 'bill/@0/status', 0)

        self.factory.xfer = BillPrint()
        self.calljson('/diacamma.invoice/billPrint', {'bill': 2}, False)
        self.assert_observer('core.custom', 'diacamma.invoice', 'billPrint')
        self.assert_json_equal('SELECT', 'MODEL', 8)

        self.factory.xfer = BillShow()
        self.calljson('/diacamma.invoice/billShow', {'bill': 2}, False)
        self.assert_observer('core.custom', 'diacamma.invoice', 'billShow')
        self.assert_count_equal('', 16)
        self.assert_json_equal('LABELFORM', 'title', "Type B")
        self.assert_json_equal('LABELFORM', 'num_txt', None)
        self.assert_json_equal('LABELFORM', 'status', 0)
        self.assert_json_equal('LABELFORM', 'date', "2015-06-24")
        self.assert_json_equal('LABELFORM', 'categoryBill', '2nd type')
        self.assert_json_equal('LABELFORM', 'bill_type', 1)
        self.assert_count_equal('detail', 1)

        configSMTP('localhost', 2125)
        server = TestReceiver()
        server.start(2125)
        try:
            self.assertEqual(0, server.count())
            self.factory.xfer = PayableEmail()
            self.calljson('/diacamma.payoff/payableEmail',
                          {'item_name': 'bill', 'bill': 1}, False)
            self.assert_observer('core.custom', 'diacamma.payoff', 'payableEmail')
            self.assert_count_equal('', 4)
            self.assert_json_equal('SELECT', 'model', 9)
            self.assert_json_equal('EDIT', 'subject', 'Warning: Type q A-1')
            self.assert_json_equal('MEMO', 'message', 'Hello{[br/]}name=Jack Dalton{[br/]}doc=Type Q A-1 - 20 juin 2015{[br/]}{[br/]}Kiss')

            self.factory.xfer = PayableEmail()
            self.calljson('/diacamma.payoff/payableEmail',
                          {'bill': 1, 'OK': 'YES', 'item_name': 'bill', 'subject': 'Warning: Type q A-1', 'message': 'this is a bill.', 'model': 9}, False)
            self.assert_observer('core.acknowledge', 'diacamma.payoff', 'payableEmail')
            self.assertEqual(1, server.count())
            self.assertEqual('mr-sylvestre@worldcompany.com', server.get(0)[1])
            self.assertEqual(['Jack.Dalton@worldcompany.com', 'mr-sylvestre@worldcompany.com'], server.get(0)[2])
            msg_txt, msg, msg_file = server.check_first_message('Warning: Type q A-1', 3, {'To': 'Jack.Dalton@worldcompany.com'})
            self.assertEqual('text/plain', msg_txt.get_content_type())
            self.assertEqual('text/html', msg.get_content_type())
            self.assertEqual('base64', msg.get('Content-Transfer-Encoding', ''))
            self.assertEqual('<html>this is a bill.</html>', decode_b64(msg.get_payload()))
            self.assertTrue('Type Q_A-1_Dalton Jack.pdf' in msg_file.get('Content-Type', ''), msg_file.get('Content-Type', ''))
            self.save_pdf(base64_content=msg_file.get_payload(), ident=1)
        finally:
            server.stop()

        server = TestReceiver()
        server.start(2125)
        try:
            self.assertEqual(0, server.count())
            self.factory.xfer = BillTransition()
            self.calljson('/diacamma.invoice/billTransition', {'bill': 2, 'TRANSITION': 'valid', 'nbpayoff': 0}, False)
            self.assert_observer('core.custom', 'diacamma.invoice', 'billTransition')
            self.assert_count_equal('', 3 + 0 + 5 + 0)
            self.assert_json_equal('', 'nbpayoff', 0)
            self.assert_json_equal('', 'sendemail', False)
            self.assert_json_equal('', 'subject', 'Warning: #reference')
            self.assert_json_equal('', 'message', 'Hello{[br/]}name=Jack Dalton{[br/]}doc=#doc{[br/]}{[br/]}Kiss')
            self.assert_json_equal('', 'model', 8)

            self.factory.xfer = BillTransition()
            self.calljson('/diacamma.invoice/billTransition', {'bill': 2, 'TRANSITION': 'valid', 'nbpayoff': 0, 'sendemail': True, 'CONFIRME': 'YES',
                                                               'subject': 'Warning: #reference',
                                                               'message': 'Hello{[br/]}name=Jack Dalton{[br/]}doc=#doc{[br/]}{[br/]}Kiss',
                                                               'model': 9
                                                               }, False)
            self.assert_observer('core.acknowledge', 'diacamma.invoice', 'billTransition')
            self.assertEqual(self.response_json['action']['id'], "diacamma.payoff/payableEmail")
            self.assertEqual(self.response_json['action']['params'], {"item_name": 'bill',
                                                                      "modelname": 'invoice.Bill',
                                                                      'subject': 'Warning: Type b A-1',
                                                                      'message': 'Hello{[br/]}name=Jack Dalton{[br/]}doc=Type B A-1 - 24 juin 2015{[br/]}{[br/]}Kiss',
                                                                      "OK": "YES"})

            self.factory.xfer = PayableEmail()
            self.calljson('/diacamma.payoff/payableEmail',
                          {'bill': 2, 'OK': 'YES', 'item_name': 'bill', "modelname": 'invoice.Bill',
                           'subject': 'Warning: Type b A-1', 'message': 'Hello{[br/]}name=Jack Dalton{[br/]}doc=Type B A-1 - 24 juin 2015{[br/]}{[br/]}Kiss',
                           'model': 9}, False)
            self.assertEqual(1, server.count())
            self.assertEqual('mr-sylvestre@worldcompany.com', server.get(0)[1])
            self.assertEqual(['Jack.Dalton@worldcompany.com', 'mr-sylvestre@worldcompany.com'], server.get(0)[2])
            msg_txt, msg, msg_file = server.check_first_message('Warning: Type b A-1', 3, {'To': 'Jack.Dalton@worldcompany.com'})
            self.assertEqual('text/plain', msg_txt.get_content_type())
            self.assertEqual('text/html', msg.get_content_type())
            self.assertEqual('base64', msg.get('Content-Transfer-Encoding', ''))
            self.assertEqual("<html>Hello<br/>name=Jack Dalton<br/>doc=Type B A-1 - 24 juin 2015<br/><br/>Kiss<hr/><center><i><u>Moyens de paiement</u></i></center><table width='90%'><tr><td><b>virement</b></td><td><center><table width='100%'><tr>    <td><u><i>IBAN</i></u></td>    <td>123456789</td></tr><tr>    <td><u><i>BIC</i></u></td>    <td>AABBCCDD</td></tr></table></center></td></tr><tr></tr><tr><td><b>chèque</b></td><td><center><table width='100%%'>    <tr>        <td><u><i>à l'ordre de</i></u></td>        <td>Truc</td>    </tr>    <tr>        <td><u><i>adresse</i></u></td>        <td>1 rue de la Paix<newline>99000 LA-BAS</td>    </tr></table></center></td></tr><tr></tr><tr><td><b>PayPal</b></td><td><center><a href='https://www.paypal.com/cgi-bin/webscr?business=monney%40truc.org&currency_code=EUR&lc=fr&return=http%3A%2F%2Ftestserver&cancel_return=http%3A%2F%2Ftestserver&notify_url=http%3A%2F%2Ftestserver%2Fdiacamma.payoff%2FvalidationPaymentPaypal&item_name=Type+B+A-1+-+24+juin+2015&custom=2&tax=0.0&amount=100.0&cmd=_xclick&no_note=1&no_shipping=1' name='paypal' target='_blank'><img src='http://testserver/static/diacamma.payoff/images/pp_cc_mark_74x46.jpg' title='PayPal' alt='PayPal' /></a></center></td></tr><tr></tr><tr><td><b>MoneticoPaiement</b></td><td><center><a href='http://testserver/diacamma.payoff/checkPaymentMoneticoPaiement?payid=2&url=http%3A//testserver' name='moneticopaiement' target='_blank'><img src='http://testserver/static/diacamma.payoff/images/monetico_logo.png' title='MoneticoPaiement' alt='MoneticoPaiement' /></a></center></td></tr><tr></tr><tr><td><b>Hello-Asso</b></td><td><center><a href='http://testserver/diacamma.payoff/checkPaymentHelloAsso?payid=2&url=http%3A//testserver' name='hello-asso' target='_blank'><img src='http://testserver/static/diacamma.payoff/images/helloasso-logo.png' title='Hello-Asso' alt='Hello-Asso' /></a></center></td></tr><tr></tr></table></html>", decode_b64(msg.get_payload()))

            self.assertTrue('Type B_A-1_Dalton Jack.pdf' in msg_file.get('Content-Type', ''), msg_file.get('Content-Type', ''))
            self.save_pdf(base64_content=msg_file.get_payload(), ident=2)
            check_pdfreport(self, 'Bill', 2, False, msg_file.get_payload())
        finally:
            server.stop()

    def test_with_categorybill_check_numbering(self):
        Params.setvalue('invoice-order-mode', 1)
        default_paymentmethod()
        default_articles()
        default_categorybill()

        cat2 = CategoryBill.objects.get(id=2)
        cat2.special_numbering = True
        cat2.prefix_numbering = 'T'
        cat2.workflow_order = 1
        cat2.save()

        self.factory.xfer = BillAddModify()
        self.calljson('/diacamma.invoice/billAddModify', {'categoryBill': 0, 'bill_type': 0, 'date': '2015-06-20', 'third': 6, 'SAVE': 'YES'}, False)
        self.assert_observer('core.acknowledge', 'diacamma.invoice', 'billAddModify')
        self.factory.xfer = BillAddModify()
        self.calljson('/diacamma.invoice/billAddModify', {'categoryBill': 0, 'bill_type': 0, 'date': '2015-06-21', 'third': 6, 'SAVE': 'YES'}, False)
        self.assert_observer('core.acknowledge', 'diacamma.invoice', 'billAddModify')
        self.factory.xfer = BillAddModify()
        self.calljson('/diacamma.invoice/billAddModify', {'categoryBill': 0, 'bill_type': 0, 'date': '2015-06-22', 'third': 6, 'SAVE': 'YES'}, False)
        self.assert_observer('core.acknowledge', 'diacamma.invoice', 'billAddModify')
        self.factory.xfer = BillAddModify()
        self.calljson('/diacamma.invoice/billAddModify', {'categoryBill': 2, 'bill_type': 0, 'date': '2015-07-20', 'third': 6, 'SAVE': 'YES'}, False)
        self.assert_observer('core.acknowledge', 'diacamma.invoice', 'billAddModify')
        self.factory.xfer = BillAddModify()
        self.calljson('/diacamma.invoice/billAddModify', {'categoryBill': 2, 'bill_type': 0, 'date': '2015-07-21', 'third': 6, 'SAVE': 'YES'}, False)
        self.assert_observer('core.acknowledge', 'diacamma.invoice', 'billAddModify')
        self.factory.xfer = BillAddModify()
        self.calljson('/diacamma.invoice/billAddModify', {'categoryBill': 2, 'bill_type': 0, 'date': '2015-07-22', 'third': 6, 'SAVE': 'YES'}, False)
        self.assert_observer('core.acknowledge', 'diacamma.invoice', 'billAddModify')

        for bill_id in range(1, 7):
            self.factory.xfer = DetailAddModify()
            self.calljson('/diacamma.invoice/detailAddModify',
                          {'SAVE': 'YES', 'bill': bill_id, 'article': 1, 'designation': 'My article', 'price': '50.00', 'quantity': 2}, False)
            self.assert_observer('core.acknowledge', 'diacamma.invoice', 'detailAddModify')

        for bill_id in range(1, 7):
            self.factory.xfer = BillTransition()
            self.calljson('/diacamma.invoice/billTransition', {'CONFIRME': 'YES', 'bill': bill_id, 'TRANSITION': 'valid'}, False)
            self.assert_observer('core.acknowledge', 'diacamma.invoice', 'billTransition')

        self.factory.xfer = BillList()
        self.calljson('/diacamma.invoice/billList', {'status_filter': -2}, False)
        self.assert_observer('core.custom', 'diacamma.invoice', 'billList')
        self.assert_count_equal('bill', 6)
        self.assert_json_equal('', 'bill/@0/bill_type', 0)
        self.assert_json_equal('', 'bill/@0/billtype', 'Type Q')
        self.assert_json_equal('', 'bill/@0/num_txt', 'A-T-3')
        self.assert_json_equal('', 'bill/@0/date', '2015-07-22')
        self.assert_json_equal('', 'bill/@0/status', 1)
        self.assert_json_equal('', 'bill/@1/bill_type', 0)
        self.assert_json_equal('', 'bill/@1/billtype', 'Type Q')
        self.assert_json_equal('', 'bill/@1/num_txt', 'A-T-2')
        self.assert_json_equal('', 'bill/@1/date', '2015-07-21')
        self.assert_json_equal('', 'bill/@1/status', 1)
        self.assert_json_equal('', 'bill/@2/bill_type', 0)
        self.assert_json_equal('', 'bill/@2/billtype', 'Type Q')
        self.assert_json_equal('', 'bill/@2/num_txt', 'A-T-1')
        self.assert_json_equal('', 'bill/@2/date', '2015-07-20')
        self.assert_json_equal('', 'bill/@2/status', 1)
        self.assert_json_equal('', 'bill/@3/bill_type', 0)
        self.assert_json_equal('', 'bill/@3/billtype', 'devis')
        self.assert_json_equal('', 'bill/@3/num_txt', 'A-3')
        self.assert_json_equal('', 'bill/@3/date', '2015-06-22')
        self.assert_json_equal('', 'bill/@3/status', 1)
        self.assert_json_equal('', 'bill/@4/bill_type', 0)
        self.assert_json_equal('', 'bill/@4/billtype', 'devis')
        self.assert_json_equal('', 'bill/@4/num_txt', 'A-2')
        self.assert_json_equal('', 'bill/@4/date', '2015-06-21')
        self.assert_json_equal('', 'bill/@4/status', 1)
        self.assert_json_equal('', 'bill/@5/bill_type', 0)
        self.assert_json_equal('', 'bill/@5/billtype', 'devis')
        self.assert_json_equal('', 'bill/@5/num_txt', 'A-1')
        self.assert_json_equal('', 'bill/@5/date', '2015-06-20')
        self.assert_json_equal('', 'bill/@5/status', 1)

        self.factory.xfer = BillShow()
        self.calljson('/diacamma.invoice/billShow', {'bill': 1}, False)
        self.assert_observer('core.custom', 'diacamma.invoice', 'billShow')
        self.assertEqual(len(self.json_actions), 8)
        self.assertEqual(self.json_actions[0]['id'], 'diacamma.payoff/payableShow')
        self.assertEqual(self.json_actions[1]['id'], 'diacamma.invoice/billTransition')
        self.assertEqual(self.json_actions[2]['id'], 'diacamma.invoice/billTransitionArchive')
        self.assertEqual(self.json_actions[3]['id'], 'diacamma.invoice/billPrint')
        self.assertEqual(self.json_actions[4]['id'], 'diacamma.invoice/billToBill')
        self.assertEqual(self.json_actions[5]['id'], 'diacamma.invoice/billToOrder')
        self.assertEqual(self.json_actions[6]['id'], 'diacamma.invoice/billCloneQuotation')
        self.assertEqual(self.json_actions[7]['id'], '')

        self.factory.xfer = BillShow()
        self.calljson('/diacamma.invoice/billShow', {'bill': 4}, False)
        self.assert_observer('core.custom', 'diacamma.invoice', 'billShow')
        self.assertEqual(len(self.json_actions), 7)
        self.assertEqual(self.json_actions[0]['id'], 'diacamma.payoff/payableShow')
        self.assertEqual(self.json_actions[1]['id'], 'diacamma.invoice/billTransition')
        self.assertEqual(self.json_actions[2]['id'], 'diacamma.invoice/billTransitionArchive')
        self.assertEqual(self.json_actions[3]['id'], 'diacamma.invoice/billPrint')
        self.assertEqual(self.json_actions[4]['id'], 'diacamma.invoice/billToOrder')
        self.assertEqual(self.json_actions[5]['id'], 'diacamma.invoice/billCloneQuotation')
        self.assertEqual(self.json_actions[6]['id'], '')

    def test_with_categorybill_withmultiemail(self):
        Params.setvalue('invoice-cart-active', True)
        default_paymentmethod()
        default_articles()
        default_categorybill(with_extra=True)

        details = [{'article': 0, 'designation': 'article 0', 'price': '20.00', 'quantity': 15}]
        bill_id = self._create_bill(details, 0, '2015-04-01', 6, True, 3)  # 59.50
        self.factory.xfer = PayableEmail()
        self.calljson('/diacamma.payoff/payableEmail',
                      {'item_name': 'bill', 'bill': bill_id, 'modelname': 'invoice.Bill'}, False)
        self.assert_observer('core.custom', 'diacamma.payoff', 'payableEmail')
        self.assert_json_equal('EDIT', 'subject', 'Q')
        self.assert_json_equal('MEMO', 'message', 'QQ qq')

        details = [{'article': 0, 'designation': 'article 0', 'price': '20.00', 'quantity': 15}]
        bill_id = self._create_bill(details, 4, '2015-04-01', 6, True, 3)  # 59.50
        self.factory.xfer = PayableEmail()
        self.calljson('/diacamma.payoff/payableEmail',
                      {'item_name': 'bill', 'bill': bill_id, 'modelname': 'invoice.Bill'}, False)
        self.assert_observer('core.custom', 'diacamma.payoff', 'payableEmail')
        self.assert_json_equal('EDIT', 'subject', 'O')
        self.assert_json_equal('MEMO', 'message', 'OO oo')
