# -*- coding: utf-8 -*-
'''
Describe test for Django
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
from importlib import import_module
from base64 import b64decode


from lucterios.framework.test import LucteriosTest
from lucterios.framework.filetools import get_user_dir
from lucterios.CORE.parameters import Params
from lucterios.documents.views import DocumentSearch

from diacamma.accounting.test_tools import initial_thirds_fr, default_compta_fr, fill_entries_fr, set_accounting_system, add_entry,\
    create_account, check_pdfreport
from diacamma.accounting.views_accounts import ChartsAccountList, ChartsAccountDel, ChartsAccountShow, ChartsAccountAddModify, ChartsAccountListing, ChartsAccountImportFiscalYear
from diacamma.accounting.views_accounts import FiscalYearBegin, FiscalYearClose, FiscalYearReportLastYear
from diacamma.accounting.views_entries import EntryAccountEdit, EntryAccountList
from diacamma.accounting.models import FiscalYear
from diacamma.accounting.views import ThirdList
from diacamma.accounting.views_budget import BudgetList, BudgetAddModify, BudgetDel
from diacamma.payoff.test_tools import PaymentTest
from diacamma.accounting.views_reports import FiscalYearIncomeStatement,\
    FiscalYearBalanceSheet


class ChartsAccountTest(LucteriosTest):

    def setUp(self):
        LucteriosTest.setUp(self)
        set_accounting_system()
        initial_thirds_fr()
        default_compta_fr()
        fill_entries_fr(1)
        rmtree(get_user_dir(), True)

    def test_all(self):
        self.factory.xfer = ChartsAccountList()
        self.calljson('/diacamma.accounting/chartsAccountList', {'year': '1', 'type_of_account': '-1'}, False)
        self.assert_observer('core.custom', 'diacamma.accounting', 'chartsAccountList')
        self.assert_count_equal('', 8)
        self.assert_grid_equal('chartsaccount', {"code": "code", "name": "nom", "last_year_total": "total de l'exercice précédent", "current_total": "total de l'exercice", "current_validated": "total validé"}, 17)  # nb=5
        self.assert_json_equal('LABELFORM', 'result', [230.62, 348.60, -117.98, 1050.66, 1244.74])
        self.assert_select_equal('type_of_account', {0: 'Actif', 1: 'Passif', 2: 'Capitaux', 3: 'Produit', 4: 'Charge', 5: 'Autres comptes', -1: '---'})

    def test_asset(self):
        self.factory.xfer = ChartsAccountList()
        self.calljson('/diacamma.accounting/chartsAccountList', {'year': '1', 'type_of_account': '0'}, False)
        self.assert_observer('core.custom', 'diacamma.accounting', 'chartsAccountList')
        self.assert_count_equal('', 8)
        self.assert_count_equal('chartsaccount', 3)
        self.assert_json_equal('', '#chartsaccount/headers/@2/@0', 'last_year_total')
        self.assert_json_equal('', '#chartsaccount/headers/@2/@2', "C2EUR")
        self.assert_json_equal('', '#chartsaccount/headers/@2/@4', '{[p align=\'right\']}{[font color="green"]}Crédit: %s{[/font]}{[/p]};{[p align=\'right\']}{[font color="blue"]}Débit: %s{[/font]}{[/p]};{[p align=\'right\']}%s{[/p]}')
        self.assert_json_equal('', '#chartsaccount/headers/@3/@0', 'current_total')
        self.assert_json_equal('', '#chartsaccount/headers/@3/@2', "C2EUR")
        self.assert_json_equal('', '#chartsaccount/headers/@3/@4', '{[p align=\'right\']}{[font color="green"]}Crédit: %s{[/font]}{[/p]};{[p align=\'right\']}{[font color="blue"]}Débit: %s{[/font]}{[/p]};{[p align=\'right\']}%s{[/p]}')
        self.assert_json_equal('', '#chartsaccount/headers/@4/@0', 'current_validated')
        self.assert_json_equal('', '#chartsaccount/headers/@4/@2', "C2EUR")
        self.assert_json_equal('', '#chartsaccount/headers/@4/@4', '{[p align=\'right\']}{[font color="green"]}Crédit: %s{[/font]}{[/p]};{[p align=\'right\']}{[font color="blue"]}Débit: %s{[/font]}{[/p]};{[p align=\'right\']}%s{[/p]}')

        self.assert_json_equal('', 'chartsaccount/@0/code', '411')
        self.assert_json_equal('', 'chartsaccount/@0/name', '411')
        self.assert_json_equal('', 'chartsaccount/@0/last_year_total', 0.00)
        self.assert_json_equal('', 'chartsaccount/@0/current_total', -159.98)
        self.assert_json_equal('', 'chartsaccount/@0/current_validated', -125.97)
        self.assert_json_equal('', 'chartsaccount/@1/code', '512')
        self.assert_json_equal('', 'chartsaccount/@1/name', '512')
        self.assert_json_equal('', 'chartsaccount/@1/last_year_total', -1135.93)
        self.assert_json_equal('', 'chartsaccount/@1/current_total', -1130.29)
        self.assert_json_equal('', 'chartsaccount/@1/current_validated', -1130.29)
        self.assert_json_equal('', 'chartsaccount/@2/code', '531')
        self.assert_json_equal('', 'chartsaccount/@2/name', '531')
        self.assert_json_equal('', 'chartsaccount/@2/last_year_total', -114.45)
        self.assert_json_equal('', 'chartsaccount/@2/current_total', 79.63)
        self.assert_json_equal('', 'chartsaccount/@2/current_validated', -114.45)

    def test_liability(self):
        self.factory.xfer = ChartsAccountList()
        self.calljson('/diacamma.accounting/chartsAccountList', {'year': '1', 'type_of_account': '1'}, False)
        self.assert_observer('core.custom', 'diacamma.accounting', 'chartsAccountList')
        self.assert_count_equal('', 8)
        self.assert_count_equal('chartsaccount', 1)
        self.assert_json_equal('', 'chartsaccount/@0/code', '401')
        self.assert_json_equal('', 'chartsaccount/@0/name', '401')
        self.assert_json_equal('', 'chartsaccount/@0/last_year_total', 0.00)
        self.assert_json_equal('', 'chartsaccount/@0/current_total', 78.24)
        self.assert_json_equal('', 'chartsaccount/@0/current_validated', 0.00)

    def test_equity(self):
        self.factory.xfer = ChartsAccountList()
        self.calljson('/diacamma.accounting/chartsAccountList', {'year': '1', 'type_of_account': '2'}, False)
        self.assert_observer('core.custom', 'diacamma.accounting', 'chartsAccountList')
        self.assert_count_equal('', 8)
        self.assert_count_equal('chartsaccount', 5)
        self.assert_json_equal('', 'chartsaccount/@0/code', '106')
        self.assert_json_equal('', 'chartsaccount/@0/name', '106')
        self.assert_json_equal('', 'chartsaccount/@0/last_year_total', 1250.38)
        self.assert_json_equal('', 'chartsaccount/@0/current_total', 1250.38)
        self.assert_json_equal('', 'chartsaccount/@0/current_validated', 1250.38)

    def test_revenue(self):
        self.factory.xfer = ChartsAccountList()
        self.calljson('/diacamma.accounting/chartsAccountList', {'year': '1', 'type_of_account': '3'}, False)
        self.assert_observer('core.custom', 'diacamma.accounting', 'chartsAccountList')
        self.assert_count_equal('', 8)
        self.assert_count_equal('chartsaccount', 3)
        self.assert_json_equal('', 'chartsaccount/@2/code', '707')
        self.assert_json_equal('', 'chartsaccount/@2/name', '707')
        self.assert_json_equal('', 'chartsaccount/@2/last_year_total', 0.00)
        self.assert_json_equal('', 'chartsaccount/@2/current_total', 230.62)
        self.assert_json_equal('', 'chartsaccount/@2/current_validated', 196.61)

    def test_expense(self):
        self.factory.xfer = ChartsAccountList()
        self.calljson('/diacamma.accounting/chartsAccountList', {'year': '1', 'type_of_account': '4'}, False)
        self.assert_observer('core.custom', 'diacamma.accounting', 'chartsAccountList')
        self.assert_count_equal('', 8)
        self.assert_count_equal('chartsaccount', 5)
        self.assert_json_equal('', 'chartsaccount/@0/code', '601')
        self.assert_json_equal('', 'chartsaccount/@0/name', '601')
        self.assert_json_equal('', 'chartsaccount/@0/last_year_total', 0.00)
        self.assert_json_equal('', 'chartsaccount/@0/current_total', -78.24)
        self.assert_json_equal('', 'chartsaccount/@0/current_validated', 0.00)
        self.assert_json_equal('', 'chartsaccount/@1/code', '602')
        self.assert_json_equal('', 'chartsaccount/@1/name', '602')
        self.assert_json_equal('', 'chartsaccount/@1/last_year_total', 0.00)
        self.assert_json_equal('', 'chartsaccount/@1/current_total', -63.94)
        self.assert_json_equal('', 'chartsaccount/@1/current_validated', -63.94)

    def test_contraaccounts(self):
        self.factory.xfer = ChartsAccountList()
        self.calljson('/diacamma.accounting/chartsAccountList', {'year': '1', 'type_of_account': '5'}, False)
        self.assert_observer('core.custom', 'diacamma.accounting', 'chartsAccountList')
        self.assert_count_equal('', 8)
        self.assert_count_equal('chartsaccount', 0)

    def test_show(self):
        self.factory.xfer = ChartsAccountShow()
        self.calljson('/diacamma.accounting/chartsAccountShow', {'year': '1', 'type_of_account': '-1', 'chartsaccount': '10'}, False)
        self.assert_observer('core.custom', 'diacamma.accounting', 'chartsAccountShow')
        self.assert_count_equal('', 5)
        self.assert_json_equal('LABELFORM', 'code', '707')
        self.assert_json_equal('LABELFORM', 'name', '707')
        self.assert_json_equal('LABELFORM', 'type_of_account', 3)
        self.assert_json_equal('', '#type_of_account/formatnum', {'0': 'Actif', '1': 'Passif', '2': 'Capitaux', '3': 'Produit', '4': 'Charge', '5': 'Autres comptes'})

        self.assert_grid_equal('entryaccount', {"num": "N°", "date_entry": "date d'écriture", "date_value": "date de pièce", "description": "description"}, 3)  # nb=5
        self.assert_json_equal('', 'entryaccount/@0/num', '4')
        self.assert_json_equal('', 'entryaccount/@0/date_value', '2015-02-21')
        description = self.json_data['entryaccount'][0]['description']
        self.assertTrue('vente 1' in description, description)
        self.assertTrue('70,64 €' in description, description)

        self.assert_json_equal('', 'entryaccount/@1/num', '6')
        self.assert_json_equal('', 'entryaccount/@1/date_value', '2015-02-21')
        description = self.json_data['entryaccount'][1]['description']
        self.assertTrue('vente 2' in description, description)
        self.assertTrue('125,97 €' in description, description)

        self.assert_json_equal('', 'entryaccount/@2/num', None)
        self.assert_json_equal('', 'entryaccount/@2/date_value', '2015-02-24')
        description = self.json_data['entryaccount'][2]['description']
        self.assertTrue('vente 3' in description, description)
        self.assertTrue('34,01 €' in description, description)

    def test_delete(self):
        self.factory.xfer = ChartsAccountDel()
        self.calljson('/diacamma.accounting/chartsAccountDel',
                      {'CONFIRME': 'YES', 'year': '1', 'type_of_account': '5', 'chartsaccount': '10'}, False)
        self.assert_observer('core.exception', 'diacamma.accounting', 'chartsAccountDel')
        self.assert_json_equal('', 'message', "Impossible de supprimer cet enregistrement: il est associé avec d'autres sous-enregistrements")
        self.factory.xfer = ChartsAccountDel()
        self.calljson('/diacamma.accounting/chartsAccountDel',
                      {'CONFIRME': 'YES', 'year': '1', 'type_of_account': '5', 'chartsaccount': '9'}, False)
        self.assert_observer('core.acknowledge', 'diacamma.accounting', 'chartsAccountDel')

    def test_add(self):
        self.factory.xfer = ChartsAccountAddModify()
        self.calljson('/diacamma.accounting/chartsAccountAddModify',
                      {'year': '1', 'type_of_account': '-1'}, False)
        self.assert_observer('core.custom', 'diacamma.accounting', 'chartsAccountAddModify')
        self.assert_count_equal('', 5)
        self.assert_json_equal('EDIT', 'code', '')
        self.assert_json_equal('EDIT', 'name', '')
        self.assert_json_equal('LABELFORM', 'type_of_account', None)
        self.assert_json_equal('LABELFORM', 'error_code', "")
        self.assert_json_equal('', '#error_code/formatstr', '{[center]}{[font color="red"]}%s{[/font]}{[/center]}')

        self.factory.xfer = ChartsAccountAddModify()
        self.calljson('/diacamma.accounting/chartsAccountAddModify',
                      {'year': '1', 'type_of_account': '-1', 'code': '2301'}, False)
        self.assert_observer('core.custom', 'diacamma.accounting', 'chartsAccountAddModify')
        self.assert_count_equal('', 5)
        self.assert_json_equal('EDIT', 'code', '2301')
        self.assert_json_equal('EDIT', 'name', 'Immobilisations en cours')
        self.assert_json_equal('LABELFORM', 'type_of_account', 0)
        self.assert_json_equal('LABELFORM', 'error_code', "")

        self.factory.xfer = ChartsAccountAddModify()
        self.calljson('/diacamma.accounting/chartsAccountAddModify',
                      {'year': '1', 'type_of_account': '-1', 'code': '3015'}, False)
        self.assert_observer('core.custom', 'diacamma.accounting', 'chartsAccountAddModify')
        self.assert_count_equal('', 5)
        self.assert_json_equal('EDIT', 'code', '3015!')
        self.assert_json_equal('EDIT', 'name', '')
        self.assert_json_equal('LABELFORM', 'type_of_account', None)
        self.assert_json_equal('LABELFORM', 'error_code', "Code invalide !")

        self.factory.xfer = ChartsAccountAddModify()
        self.calljson('/diacamma.accounting/chartsAccountAddModify',
                      {'year': '1', 'type_of_account': '-1', 'code': 'abcd'}, False)
        self.assert_observer('core.custom', 'diacamma.accounting', 'chartsAccountAddModify')
        self.assert_count_equal('', 5)
        self.assert_json_equal('EDIT', 'code', 'abcd!')
        self.assert_json_equal('EDIT', 'name', '')
        self.assert_json_equal('LABELFORM', 'type_of_account', None)
        self.assert_json_equal('LABELFORM', 'error_code', "Code invalide !")

    def test_modify(self):
        self.factory.xfer = ChartsAccountAddModify()
        self.calljson('/diacamma.accounting/chartsAccountAddModify',
                      {'year': '1', 'type_of_account': '-1', 'chartsaccount': '9'}, False)
        self.assert_observer('core.custom', 'diacamma.accounting', 'chartsAccountAddModify')
        self.assert_count_equal('', 5)
        self.assert_json_equal('EDIT', 'code', '706')
        self.assert_json_equal('EDIT', 'name', '706')
        self.assert_json_equal('LABELFORM', 'type_of_account', 3)
        self.assert_json_equal('LABELFORM', 'error_code', "")

        self.factory.xfer = ChartsAccountAddModify()
        self.calljson('/diacamma.accounting/chartsAccountAddModify',
                      {'year': '1', 'type_of_account': '-1', 'chartsaccount': '9', 'code': '7061'}, False)
        self.assert_observer('core.custom', 'diacamma.accounting', 'chartsAccountAddModify')
        self.assert_count_equal('', 5)
        self.assert_json_equal('EDIT', 'code', '7061')
        self.assert_json_equal('EDIT', 'name', '706')
        self.assert_json_equal('LABELFORM', 'type_of_account', 3)
        self.assert_json_equal('LABELFORM', 'error_code', "")

        self.factory.xfer = ChartsAccountAddModify()
        self.calljson('/diacamma.accounting/chartsAccountAddModify',
                      {'year': '1', 'type_of_account': '-1', 'chartsaccount': '9', 'code': '3015'}, False)
        self.assert_observer('core.custom', 'diacamma.accounting', 'chartsAccountAddModify')
        self.assert_count_equal('', 5)
        self.assert_json_equal('EDIT', 'code', '3015!')
        self.assert_json_equal('EDIT', 'name', '706')
        self.assert_json_equal('LABELFORM', 'type_of_account', 3)
        self.assert_json_equal('LABELFORM', 'error_code', "Code invalide !")

        self.factory.xfer = ChartsAccountAddModify()
        self.calljson('/diacamma.accounting/chartsAccountAddModify',
                      {'year': '1', 'type_of_account': '-1', 'chartsaccount': '9', 'code': 'abcd'}, False)
        self.assert_observer('core.custom', 'diacamma.accounting', 'chartsAccountAddModify')
        self.assert_count_equal('', 5)
        self.assert_json_equal('EDIT', 'code', 'abcd!')
        self.assert_json_equal('EDIT', 'name', '706')
        self.assert_json_equal('LABELFORM', 'type_of_account', 3)
        self.assert_json_equal('LABELFORM', 'error_code', "Code invalide !")

        self.factory.xfer = ChartsAccountAddModify()
        self.calljson('/diacamma.accounting/chartsAccountAddModify',
                      {'year': '1', 'type_of_account': '-1', 'chartsaccount': '9', 'code': '6125'}, False)
        self.assert_observer('core.custom', 'diacamma.accounting', 'chartsAccountAddModify')
        self.assert_count_equal('', 5)
        self.assert_json_equal('EDIT', 'code', '6125!')
        self.assert_json_equal('EDIT', 'name', '706')
        self.assert_json_equal('LABELFORM', 'type_of_account', 3)
        self.assert_json_equal('LABELFORM', 'error_code', "Changement non permis !")

    def test_modify_with_validated_line(self):
        entry = add_entry(1, 3, '2015-04-15', 'Subvention 2', '-1|9|0|100.000000|0|0|None|\n-2|2|0|100.000000|0|0|None|', False)
        self.factory.xfer = ChartsAccountAddModify()
        self.calljson('/diacamma.accounting/chartsAccountAddModify',
                      {'year': '1', 'type_of_account': '-1', 'chartsaccount': '9'}, False)
        self.assert_observer('core.custom', 'diacamma.accounting', 'chartsAccountAddModify')
        self.assert_count_equal('', 5)
        self.assert_json_equal('EDIT', 'code', '706')
        self.assert_json_equal('EDIT', 'name', '706')
        self.assert_json_equal('LABELFORM', 'type_of_account', 3)
        self.assert_json_equal('LABELFORM', 'error_code', "")

        entry.closed()
        self.factory.xfer = ChartsAccountAddModify()
        self.calljson('/diacamma.accounting/chartsAccountAddModify',
                      {'year': '1', 'type_of_account': '-1', 'chartsaccount': '9'}, False)
        self.assert_observer('core.custom', 'diacamma.accounting', 'chartsAccountAddModify')
        self.assert_count_equal('', 5)
        self.assert_json_equal('LABELFORM', 'code', '706')
        self.assert_json_equal('EDIT', 'name', '706')
        self.assert_json_equal('LABELFORM', 'type_of_account', 3)
        self.assert_json_equal('LABELFORM', 'error_code', "")

        self.factory.xfer = ChartsAccountAddModify()
        self.calljson('/diacamma.accounting/chartsAccountAddModify',
                      {'year': '1', 'type_of_account': '-1', 'chartsaccount': '9', 'code': '7061'}, False)
        self.assert_observer('core.custom', 'diacamma.accounting', 'chartsAccountAddModify')
        self.assert_count_equal('', 5)
        self.assert_json_equal('LABELFORM', 'code', '706')
        self.assert_json_equal('EDIT', 'name', '706')
        self.assert_json_equal('LABELFORM', 'type_of_account', 3)
        self.assert_json_equal('LABELFORM', 'error_code', "")

        self.factory.xfer = ChartsAccountAddModify()
        self.calljson('/diacamma.accounting/chartsAccountAddModify',
                      {'SAVE': 'YES', 'year': '1', 'type_of_account': '-1', 'chartsaccount': '9', 'code': '7061', 'name': "new code name"}, False)
        self.assert_observer('core.acknowledge', 'diacamma.accounting', 'chartsAccountAddModify')

        self.factory.xfer = ChartsAccountAddModify()
        self.calljson('/diacamma.accounting/chartsAccountAddModify',
                      {'year': '1', 'type_of_account': '-1', 'chartsaccount': '9'}, False)
        self.assert_observer('core.custom', 'diacamma.accounting', 'chartsAccountAddModify')
        self.assert_count_equal('', 5)
        self.assert_json_equal('LABELFORM', 'code', '706')
        self.assert_json_equal('EDIT', 'name', 'new code name')
        self.assert_json_equal('LABELFORM', 'type_of_account', 3)
        self.assert_json_equal('LABELFORM', 'error_code', "")

    def test_listing(self):
        self.factory.xfer = ChartsAccountListing()
        self.calljson('/diacamma.accounting/chartsAccountListing',
                      {'year': '1', 'type_of_account': '-1', 'PRINT_MODE': '4', 'MODEL': 6}, False)
        self.assert_observer('core.print', 'diacamma.accounting', 'chartsAccountListing')
        csv_value = b64decode(
            str(self.response_json['print']['content'])).decode("utf-8")
        content_csv = csv_value.split('\n')
        self.assertEqual(len(content_csv), 30, str(content_csv))
        self.assertEqual(content_csv[1].strip()[:27], '"Liste des comptes du plan ')
        self.assertEqual(content_csv[6].strip(), '"code";"nom";"total de l\'exercice précédent";"total de l\'exercice";"total validé";')
        self.assertEqual(content_csv[7].strip(), '"106";"106";"Crédit: 1 250,38 €";"Crédit: 1 250,38 €";"Crédit: 1 250,38 €";')
        self.assertEqual(content_csv[14].strip(), '"512";"512";"Débit: 1 135,93 €";"Débit: 1 130,29 €";"Débit: 1 130,29 €";')
        self.assertEqual(content_csv[15].strip(), '"531";"531";"Débit: 114,45 €";"Crédit: 79,63 €";"Débit: 114,45 €";')

        self.factory.xfer = ChartsAccountListing()
        self.calljson('/diacamma.accounting/chartsAccountListing',
                      {'year': '1', 'type_of_account': '4', 'PRINT_MODE': '4', 'MODEL': 6}, False)
        self.assert_observer('core.print', 'diacamma.accounting', 'chartsAccountListing')
        csv_value = b64decode(
            str(self.response_json['print']['content'])).decode("utf-8")
        content_csv = csv_value.split('\n')
        self.assertEqual(len(content_csv), 18, str(content_csv))

    def test_budget(self):
        self.factory.xfer = BudgetList()
        self.calljson('/diacamma.accounting/budgetList', {'year': '1'}, False)
        self.assert_observer('core.custom', 'diacamma.accounting', 'budgetList')
        self.assert_count_equal('', 6)
        self.assertEqual(len(self.json_actions), 4)
        self.assert_count_equal('budget_revenue', 2)
        self.assert_json_equal('', '#budget_revenue/headers/@0/@0', 'budget')
        self.assert_json_equal('', '#budget_revenue/headers/@0/@2', None)
        self.assert_json_equal('', '#budget_revenue/headers/@0/@4', "%s")
        self.assert_json_equal('', '#budget_revenue/headers/@1/@0', 'montant')
        self.assert_json_equal('', '#budget_revenue/headers/@1/@2', "C2EUR")
        self.assert_json_equal('', '#budget_revenue/headers/@1/@4', '{[p align=\'right\']}{[font color="green"]}Crédit: %s{[/font]}{[/p]};{[p align=\'right\']}{[font color="blue"]}Débit: %s{[/font]}{[/p]};{[p align=\'right\']}%s{[/p]}')

        self.assert_json_equal('', '#budget_expense/headers/@0/@0', 'budget')
        self.assert_json_equal('', '#budget_expense/headers/@0/@2', None)
        self.assert_json_equal('', '#budget_expense/headers/@0/@4', "%s")
        self.assert_json_equal('', '#budget_expense/headers/@1/@0', 'montant')
        self.assert_json_equal('', '#budget_expense/headers/@1/@2', "C2EUR")
        self.assert_json_equal('', '#budget_expense/headers/@1/@4', '{[p align=\'right\']}{[font color="green"]}Crédit: %s{[/font]}{[/p]};{[p align=\'right\']}{[font color="blue"]}Débit: %s{[/font]}{[/p]};{[p align=\'right\']}%s{[/p]}')

        self.assert_count_equal('#budget_revenue/actions', 2)
        self.assert_json_equal('', 'budget_revenue/@0/budget', '[701] 701')
        self.assert_json_equal('', 'budget_revenue/@0/montant', 67.89)
        self.assert_json_equal('', 'budget_revenue/@1/budget', '[707] 707')
        self.assert_json_equal('', 'budget_revenue/@1/montant', 123.45)
        self.assert_count_equal('budget_expense', 3)
        self.assert_json_equal('', 'budget_expense/@0/budget', '[601] 601')
        self.assert_json_equal('', 'budget_expense/@0/montant', -8.19)
        self.assert_json_equal('', 'budget_expense/@1/budget', '[602] 602')
        self.assert_json_equal('', 'budget_expense/@1/montant', -7.35)
        self.assert_json_equal('', 'budget_expense/@2/budget', '[604] 604')
        self.assert_json_equal('', 'budget_expense/@2/montant', -6.24)
        self.assert_count_equal('#budget_expense/actions', 2)
        self.assert_json_equal('LABELFORM', 'result', 169.56)

        self.factory.xfer = BudgetAddModify()
        self.calljson('/diacamma.accounting/budgetAddModify', {'year': '1', 'budget_expense': 'C602'}, False)
        self.assert_observer('core.custom', 'diacamma.accounting', 'budgetAddModify')
        self.assert_count_equal('', 4)
        self.assertEqual(len(self.json_actions), 2)
        self.assert_json_equal('', 'code', '602')
        self.assert_json_equal('', 'debit_val', '7.35')
        self.assert_json_equal('', 'credit_val', '0.00')

        self.factory.xfer = BudgetAddModify()
        self.calljson('/diacamma.accounting/budgetAddModify', {'year': '1', 'budget_expense': 'C602', 'code': '602', 'debit_val': '19.64', 'credit_val': '0.00', 'SAVE': 'YES'}, False)
        self.assert_observer('core.acknowledge', 'diacamma.accounting', 'budgetAddModify')

        self.factory.xfer = BudgetList()
        self.calljson('/diacamma.accounting/budgetList', {'year': '1'}, False)
        self.assert_observer('core.custom', 'diacamma.accounting', 'budgetList')
        self.assert_count_equal('budget_revenue', 2)
        self.assert_count_equal('budget_expense', 3)
        self.assert_json_equal('', 'budget_expense/@1/budget', '[602] 602')
        self.assert_json_equal('', 'budget_expense/@1/montant', -19.64)
        self.assert_json_equal('LABELFORM', 'result', 157.27)

        self.factory.xfer = BudgetAddModify()
        self.calljson('/diacamma.accounting/budgetAddModify', {'year': '1', 'code': '607', 'debit_val': '92.73', 'credit_val': '0.00', 'SAVE': 'YES'}, False)
        self.assert_observer('core.acknowledge', 'diacamma.accounting', 'budgetAddModify')

        self.factory.xfer = BudgetList()
        self.calljson('/diacamma.accounting/budgetList', {'year': '1'}, False)
        self.assert_observer('core.custom', 'diacamma.accounting', 'budgetList')
        self.assert_count_equal('budget_revenue', 2)
        self.assert_count_equal('budget_expense', 4)
        self.assert_json_equal('', 'budget_expense/@3/budget', '[607] 607')
        self.assert_json_equal('', 'budget_expense/@3/montant', -92.73)
        self.assert_json_equal('LABELFORM', 'result', 64.54)

        self.factory.xfer = BudgetDel()
        self.calljson('/diacamma.accounting/budgetDel', {'year': '1', 'budget_expense': 'C604', 'CONFIRME': 'YES'}, False)
        self.assert_observer('core.acknowledge', 'diacamma.accounting', 'budgetDel')

        self.factory.xfer = BudgetList()
        self.calljson('/diacamma.accounting/budgetList', {'year': '1'}, False)
        self.assert_observer('core.custom', 'diacamma.accounting', 'budgetList')
        self.assert_count_equal('budget_revenue', 2)
        self.assert_count_equal('budget_expense', 3)
        self.assert_json_equal('LABELFORM', 'result', 70.78)

        self.factory.xfer = BudgetList()
        self.calljson('/diacamma.accounting/budgetList', {'year': '1', 'readonly': True}, False)
        self.assert_observer('core.custom', 'diacamma.accounting', 'budgetList')
        self.assert_count_equal('', 6)
        self.assertEqual(len(self.json_actions), 2)
        self.assert_count_equal('budget_revenue', 2)
        self.assert_count_equal('#budget_revenue/actions', 0)
        self.assert_count_equal('budget_expense', 3)
        self.assert_count_equal('#budget_expense/actions', 0)
        self.assert_json_equal('LABELFORM', 'result', 70.78)


class FiscalYearWorkflowTest(PaymentTest):

    def setUp(self):
        # BudgetList.url_text
        LucteriosTest.setUp(self)
        set_accounting_system()
        initial_thirds_fr()
        default_compta_fr()
        fill_entries_fr(1)
        rmtree(get_user_dir(), True)

    def _add_subvention(self):
        create_account(['441'], 1)  # subvention (état) N°18
        create_account(['740'], 3)  # subvention (revenu) N°19
        add_entry(1, 3, '2015-03-10', 'Subvention 1', '-1|19|0|35.500000|0|0|None|\n-2|18|0|-35.500000|0|0|None|', True)  # 23 24
        add_entry(1, 3, '2015-04-15', 'Subvention 2', '-1|19|0|99.950000|0|0|None|\n-2|18|0|-99.950000|0|0|None|', True)  # 25 26

    def test_begin_simple(self):
        self.assertEqual(FiscalYear.objects.get(id=1).status, 0)

        self.factory.xfer = ChartsAccountList()
        self.calljson('/diacamma.accounting/chartsAccountList',
                      {'year': '1', 'type_of_account': '-1'}, False)
        self.assert_observer('core.custom', 'diacamma.accounting', 'chartsAccountList')
        self.assert_count_equal('', 8)
        self.assertEqual(len(self.json_actions), 4)
        self.assert_action_equal('POST', self.json_actions[0], ('Commencer', 'images/ok.png', 'diacamma.accounting', 'fiscalYearBegin', 0, 1, 1))

        self.factory.xfer = FiscalYearBegin()
        self.calljson('/diacamma.accounting/fiscalYearBegin',
                      {'year': '1', 'type_of_account': '-1'}, False)
        self.assert_observer('core.dialogbox', 'diacamma.accounting', 'fiscalYearBegin')
        self.assert_json_equal('', 'text', "Voulez-vous commencer 'Exercice du 1 janvier 2015 au 31 décembre 2015", True)

        self.factory.xfer = FiscalYearBegin()
        self.calljson('/diacamma.accounting/fiscalYearBegin',
                      {'CONFIRME': 'YES', 'year': '1', 'type_of_account': '-1'}, False)
        self.assert_observer('core.acknowledge', 'diacamma.accounting', 'fiscalYearBegin')

        self.assertEqual(FiscalYear.objects.get(id=1).status, 1)

        self.factory.xfer = ChartsAccountList()
        self.calljson('/diacamma.accounting/chartsAccountList',
                      {'year': '1', 'type_of_account': '-1'}, False)
        self.assert_observer('core.custom', 'diacamma.accounting', 'chartsAccountList')
        self.assertEqual(len(self.json_actions), 4)
        self.assert_action_equal('POST', self.json_actions[0], ('Clôture', 'images/ok.png', 'diacamma.accounting', 'fiscalYearClose', 0, 1, 1))

    def test_begin_lastyearnovalid(self):
        self.assertEqual(FiscalYear.objects.get(id=1).status, 0)
        new_entry = add_entry(1, 1, '2015-04-11', 'Report à nouveau aussi', '-1|1|0|37.61|0|0|None|\n-2|2|0|-37.61|0|0|None|', False)

        self.factory.xfer = FiscalYearBegin()
        self.calljson('/diacamma.accounting/fiscalYearBegin',
                      {'year': '1', 'type_of_account': '-1'}, False)
        self.assert_observer('core.exception', 'diacamma.accounting', 'fiscalYearBegin')
        self.assert_json_equal('', 'message', "Des écritures au journal Report à nouveau ne sont pas validées !")

        new_entry.closed()

        self.factory.xfer = FiscalYearBegin()
        self.calljson('/diacamma.accounting/fiscalYearBegin',
                      {'CONFIRME': 'YES', 'year': '1', 'type_of_account': '-1'}, False)
        self.assert_observer('core.acknowledge', 'diacamma.accounting', 'fiscalYearBegin')
        self.assertEqual(FiscalYear.objects.get(id=1).status, 1)

    def test_begin_withbenef(self):
        self.assertEqual(FiscalYear.objects.get(id=1).status, 0)
        add_entry(1, 1, '2015-04-11', 'Report à nouveau bénèf', '-1|16|0|123.45|0|0|None|\n-2|2|0|123.45|0|0|None|', True)

        self.factory.xfer = ChartsAccountList()
        self.calljson('/diacamma.accounting/chartsAccountList',
                      {'year': '1', 'type_of_account': '2'}, False)
        self.assert_observer('core.custom', 'diacamma.accounting', 'chartsAccountList')
        self.assert_count_equal('chartsaccount', 5)
        self.assert_json_equal('', 'chartsaccount/@0/code', '106')
        self.assert_json_equal('', 'chartsaccount/@0/last_year_total', 1250.38)
        self.assert_json_equal('', 'chartsaccount/@3/code', '120')
        self.assert_json_equal('', 'chartsaccount/@3/last_year_total', 123.45)

        self.factory.xfer = FiscalYearBegin()
        self.calljson('/diacamma.accounting/fiscalYearBegin',
                      {'year': '1', 'type_of_account': '-1'}, False)
        self.assert_observer('core.custom', 'diacamma.accounting', 'fiscalYearBegin')
        self.assert_count_equal('', 4)
        self.assert_json_equal('LABELFORM', 'info', "{[i]}Vous avez un bénéfice de 123,45 €.{[br/]}", True)
        self.assert_json_equal('SELECT', 'profit_account', '5')
        self.assert_select_equal('profit_account', 3)  # nb=3
        self.assertEqual(len(self.json_actions), 2)

        self.factory.xfer = FiscalYearBegin()
        self.calljson('/diacamma.accounting/fiscalYearBegin',
                      {'profit_account': '5', 'year': '1', 'type_of_account': '-1'}, False)
        self.assert_observer('core.acknowledge', 'diacamma.accounting', 'fiscalYearBegin')

        self.assertEqual(FiscalYear.objects.get(id=1).status, 1)

        self.factory.xfer = ChartsAccountList()
        self.calljson('/diacamma.accounting/chartsAccountList',
                      {'year': '1', 'type_of_account': '2'}, False)
        self.assert_observer('core.custom', 'diacamma.accounting', 'chartsAccountList')
        self.assert_count_equal('chartsaccount', 5)
        self.assert_json_equal('', 'chartsaccount/@0/code', '106')
        self.assert_json_equal('', 'chartsaccount/@0/last_year_total', 1250.38)
        self.assert_json_equal('', 'chartsaccount/@0/current_total', 1373.83)
        self.assert_json_equal('', 'chartsaccount/@3/code', '120')
        self.assert_json_equal('', 'chartsaccount/@3/last_year_total', 123.45)
        self.assert_json_equal('', 'chartsaccount/@3/current_total', 0.00)

    def test_begin_dont_add_report(self):
        self.factory.xfer = FiscalYearBegin()
        self.calljson('/diacamma.accounting/fiscalYearBegin',
                      {'CONFIRME': 'YES', 'year': '1', 'type_of_account': '-1'}, False)
        self.assert_observer('core.acknowledge', 'diacamma.accounting', 'fiscalYearBegin')
        self.assertEqual(FiscalYear.objects.get(id=1).status, 1)

        self.factory.xfer = EntryAccountEdit()
        self.calljson('/diacamma.accounting/entryAccountEdit', {'year': '1', 'journal': '1'}, False)
        self.assert_observer('core.custom', 'diacamma.accounting', 'entryAccountEdit')
        self.assert_count_equal('', 4)
        self.assert_select_equal('journal', 4)  # nb=4
        self.assert_json_equal('SELECT', 'journal', '2')
        self.assertEqual(len(self.json_actions), 2)

    def test_import_charsaccount(self):
        import_module("diacamma.asso.views")
        FiscalYear.objects.create(begin='2016-01-01', end='2016-12-31', status=0,
                                  last_fiscalyear=FiscalYear.objects.get(id=1))
        self.assertEqual(FiscalYear.objects.get(id=1).status, 0)
        self.assertEqual(FiscalYear.objects.get(id=2).status, 0)

        self.factory.xfer = ChartsAccountImportFiscalYear()
        self.calljson('/diacamma.accounting/chartsAccountImportFiscalYear',
                      {'CONFIRME': 'YES', 'year': '1', 'type_of_account': '-1'}, False)
        self.assert_observer('core.exception', 'diacamma.accounting', 'chartsAccountImportFiscalYear')
        self.assert_json_equal('', 'message', "Cet exercice n'a pas d'exercice précédent !")

        self.factory.xfer = ChartsAccountList()
        self.calljson('/diacamma.accounting/chartsAccountList', {'year': '1', 'type_of_account': '-1'}, False)
        self.assert_observer('core.custom', 'diacamma.accounting', 'chartsAccountList')
        self.assert_count_equal('chartsaccount', 17)
        self.assert_count_equal('#chartsaccount/actions', 5)

        self.factory.xfer = ChartsAccountList()
        self.calljson('/diacamma.accounting/chartsAccountList', {'year': '2', 'type_of_account': '-1'}, False)
        self.assert_observer('core.custom', 'diacamma.accounting', 'chartsAccountList')
        self.assert_count_equal('chartsaccount', 0)
        self.assert_count_equal('#chartsaccount/actions', 6)
        self.assert_action_equal('POST', '#chartsaccount/actions/@3',
                                 ('Import', 'images/right.png', 'diacamma.accounting', 'chartsAccountImportFiscalYear', 0, 1, 1))

        self.factory.xfer = ChartsAccountImportFiscalYear()
        self.calljson('/diacamma.accounting/chartsAccountImportFiscalYear',
                      {'CONFIRME': 'YES', 'year': '2', 'type_of_account': '-1'}, False)
        self.assert_observer('core.acknowledge', 'diacamma.accounting', 'chartsAccountImportFiscalYear')

        self.factory.xfer = ChartsAccountList()
        self.calljson('/diacamma.accounting/chartsAccountList',
                      {'year': '2', 'type_of_account': '-1'}, False)
        self.assert_observer('core.custom', 'diacamma.accounting', 'chartsAccountList')
        self.assert_count_equal('chartsaccount', 17)

        self.factory.xfer = ChartsAccountImportFiscalYear()
        self.calljson('/diacamma.accounting/chartsAccountImportFiscalYear',
                      {'CONFIRME': 'YES', 'year': '2', 'type_of_account': '-1'}, False)
        self.assert_observer('core.acknowledge', 'diacamma.accounting', 'chartsAccountImportFiscalYear')

        self.factory.xfer = ChartsAccountList()
        self.calljson('/diacamma.accounting/chartsAccountList',
                      {'year': '2', 'type_of_account': '-1'}, False)
        self.assert_observer('core.custom', 'diacamma.accounting', 'chartsAccountList')
        self.assert_count_equal('chartsaccount', 17)

    def test_close(self):
        self._add_subvention()
        Params.setvalue('accounting-needcost', '1')
        self.factory.xfer = DocumentSearch()
        self.calljson('/lucterios.documents/documentSearch', {}, False)
        self.assert_observer('core.custom', 'lucterios.documents', 'documentSearch')
        self.assert_count_equal('document', 0)

        self.assertEqual(FiscalYear.objects.get(id=1).status, 0)
        self.factory.xfer = FiscalYearClose()
        self.calljson('/diacamma.accounting/fiscalYearClose', {'year': '1', 'type_of_account': '-1'}, False)
        self.assert_observer('core.exception', 'diacamma.accounting', 'fiscalYearClose')
        self.assert_json_equal('', 'message', "Cet exercice n'est pas 'en cours' !")

        self.factory.xfer = FiscalYearBegin()
        self.calljson('/diacamma.accounting/fiscalYearBegin', {'CONFIRME': 'YES', 'year': '1', 'type_of_account': '-1'}, False)
        self.assert_observer('core.acknowledge', 'diacamma.accounting', 'fiscalYearBegin')
        self.assertEqual(FiscalYear.objects.get(id=1).status, 1)

        self.factory.xfer = ThirdList()
        self.calljson('/diacamma.accounting/thirdList', {'show_filter': '1'}, False)
        self.assert_observer('core.custom', 'diacamma.accounting', 'thirdList')
        self.assert_json_equal('', '#third/headers/@2/@0', 'total')
        self.assert_json_equal('', '#third/headers/@2/@1', 'total')
        self.assert_json_equal('', '#third/headers/@2/@2', "C2EUR")
        self.assert_json_equal('', '#third/headers/@2/@4', "{[p align='right']}%s{[/p]}")

        self.assert_json_equal('', 'third/@1/contact', 'Dalton Jack')
        self.assert_json_equal('', 'third/@1/total', 0.0)
        self.assert_json_equal('', 'third/@3/contact', 'Dalton William')
        self.assert_json_equal('', 'third/@3/total', -125.97)
        self.assert_json_equal('', 'third/@6/contact', 'Minimum')
        self.assert_json_equal('', 'third/@6/total', -34.01)
        self.check_account(1, '411', 159.98)
        self.check_account(1, '401', 78.24)
        self.check_account(1, '441', -135.45)

        self.factory.xfer = FiscalYearClose()
        self.calljson('/diacamma.accounting/fiscalYearClose', {'year': '1', 'type_of_account': '-1'}, False)
        self.assert_observer('core.exception', 'diacamma.accounting', 'fiscalYearClose')
        self.assert_json_equal('', 'message', "Cet exercice a des écritures non-validées et pas d'exercice suivant !")

        FiscalYear.objects.create(begin='2016-01-01', end='2016-12-31', status=0, last_fiscalyear=FiscalYear.objects.get(id=1))

        self.factory.xfer = FiscalYearClose()
        self.calljson('/diacamma.accounting/fiscalYearClose', {'year': '1', 'type_of_account': '-1'}, False)
        self.assert_observer('core.custom', 'diacamma.accounting', 'fiscalYearClose')
        text_value = self.json_data['info']

        self.assertTrue('Voulez-vous clôturer cet exercice ?' in text_value, text_value)
        self.assertTrue('les 4 écritures non validées' in text_value, text_value)

        self.factory.xfer = EntryAccountList()
        self.calljson('/diacamma.accounting/entryAccountList', {'year': '1', 'journal': '0', 'filter': '0'}, False)
        self.assert_observer('core.custom', 'diacamma.accounting', 'entryAccountList')
        self.assert_count_equal('entryline', 25)
        self.assert_json_equal('LABELFORM', 'result', [366.07, 348.60, 17.47, 1050.66, 1244.74])

        self.factory.xfer = EntryAccountList()
        self.calljson('/diacamma.accounting/entryAccountList', {'year': '2', 'journal': '0', 'filter': '0'}, False)
        self.assert_observer('core.custom', 'diacamma.accounting', 'entryAccountList')
        self.assert_count_equal('entryline', 0)
        self.assert_json_equal('LABELFORM', 'result', [0.00, 0.00, 0.00, 0.00, 0.00])

        self.factory.xfer = FiscalYearClose()
        self.calljson('/diacamma.accounting/fiscalYearClose', {'CONFIRME': 'YES', 'year': '1', 'type_of_account': '-1'}, False)
        self.assert_observer('core.acknowledge', 'diacamma.accounting', 'fiscalYearClose')

        self.assertEqual(FiscalYear.objects.get(id=1).status, 2)

        self.factory.xfer = EntryAccountList()
        self.calljson('/diacamma.accounting/entryAccountList', {'year': '1', 'journal': '0', 'filter': '0'}, False)
        self.assert_observer('core.custom', 'diacamma.accounting', 'entryAccountList')
        self.assert_count_equal('entryline', 25)
        self.assert_json_equal('LABELFORM', 'result', [332.06, 76.28, 255.78, 1244.74, 1244.74])

        self.factory.xfer = EntryAccountList()
        self.calljson('/diacamma.accounting/entryAccountList', {'year': '1', 'journal': '5', 'filter': '2'}, False)
        self.assert_observer('core.custom', 'diacamma.accounting', 'entryAccountList')
        self.assert_count_equal('entryline', 9)
        self.assert_json_equal('', 'entryline/@2/designation_ref', "Cloture d'exercice - Résultat")
        self.assert_json_equal('', 'entryline/@2/entry_account', "[120] 120")
        self.assert_json_equal('', 'entryline/@2/credit', 255.78)
        self.assert_json_equal('', 'entryline/@2/link', None)
        self.assert_json_equal('', 'entryline/@3/designation_ref', "Cloture d'exercice - Résultat")
        self.assert_json_equal('', 'entryline/@3/entry_account', "[602] 602")
        self.assert_json_equal('', 'entryline/@3/credit', 63.94)
        self.assert_json_equal('', 'entryline/@4/designation_ref', "Cloture d'exercice - Résultat")
        self.assert_json_equal('', 'entryline/@4/entry_account', "[627] 627")
        self.assert_json_equal('', 'entryline/@4/credit', 12.34)
        self.assert_json_equal('', 'entryline/@5/designation_ref', "Cloture d'exercice - Résultat")
        self.assert_json_equal('', 'entryline/@5/entry_account', "[707] 707")
        self.assert_json_equal('', 'entryline/@5/debit', -196.61)
        self.assert_json_equal('', 'entryline/@6/designation_ref', "Cloture d'exercice - Résultat")
        self.assert_json_equal('', 'entryline/@6/entry_account', "[740] 740")
        self.assert_json_equal('', 'entryline/@6/debit', -135.45)

        self.assert_json_equal('', 'entryline/@7/designation_ref', "Cloture d'exercice - Tiers")
        self.assert_json_equal('', 'entryline/@7/entry_account', "[411] 411")
        self.assert_json_equal('', 'entryline/@7/debit', -125.97)
        self.assert_json_equal('', 'entryline/@7/link', None)
        self.assert_json_equal('', 'entryline/@8/designation_ref', "Cloture d'exercice - Tiers{[br/]}vente 2")
        self.assert_json_equal('', 'entryline/@8/entry_account', "[411 Dalton William]")
        self.assert_json_equal('', 'entryline/@8/credit', 125.97)
        self.assert_json_equal('', 'entryline/@8/link', "E")

        self.factory.xfer = EntryAccountList()
        self.calljson('/diacamma.accounting/entryAccountList', {'year': '2', 'journal': '0', 'filter': '0'}, False)
        self.assert_observer('core.custom', 'diacamma.accounting', 'entryAccountList')
        self.assert_count_equal('entryline', 8)
        self.assert_json_equal('LABELFORM', 'result', [34.01, 272.32, -238.31, -194.08, 0.00])

        self.factory.xfer = ChartsAccountList()
        self.calljson('/diacamma.accounting/chartsAccountList', {'year': '1', 'type_of_account': '-1'}, False)
        self.assert_observer('core.custom', 'diacamma.accounting', 'chartsAccountList')
        self.assert_count_equal('', 8)
        self.assert_count_equal('chartsaccount', 19)
        self.assert_json_equal('', 'chartsaccount/@3/code', '120')
        self.assert_json_equal('', 'chartsaccount/@3/current_total', 255.78)
        self.assert_json_equal('', 'chartsaccount/@5/code', '401')
        self.assert_json_equal('', 'chartsaccount/@5/current_total', 0.00)
        self.assert_json_equal('', 'chartsaccount/@6/code', '411')
        self.assert_json_equal('', 'chartsaccount/@6/current_total', -125.97)
        self.assert_json_equal('', 'chartsaccount/@7/code', '441')
        self.assert_json_equal('', 'chartsaccount/@7/current_total', -135.45)

        check_pdfreport(self, '1', 'Bilan.pdf', "FiscalYearBalanceSheet", "diacamma.accounting.views_reports")
        check_pdfreport(self, '1', 'Compte de resultat.pdf', "FiscalYearIncomeStatement", "diacamma.accounting.views_reports")

        self.factory.xfer = DocumentSearch()
        self.calljson('/lucterios.documents/documentSearch', {}, False)
        self.assert_observer('core.custom', 'lucterios.documents', 'documentSearch')
        self.assert_count_equal('document', 4)

        self.factory.xfer = FiscalYearIncomeStatement()
        self.calljson('/diacamma.accounting/fiscalYearIncomeStatement', {'year': '1'}, False)
        self.assert_observer('core.custom', 'diacamma.accounting', 'fiscalYearIncomeStatement')
        self.assert_count_equal('', 4)
        self.assert_count_equal('report_1', 8)
        self.assert_json_equal('', 'report_1/@0/left', "[601] 601")
        self.assert_json_equal('', 'report_1/@0/left_n', "")
        self.assert_json_equal('', 'report_1/@0/left_b', 8.19)
        self.assert_json_equal('', 'report_1/@0/right', "[701] 701")
        self.assert_json_equal('', 'report_1/@0/right_n', "")
        self.assert_json_equal('', 'report_1/@0/right_b', 67.89)
        self.assert_json_equal('', 'report_1/@1/left', "[602] 602")
        self.assert_json_equal('', 'report_1/@1/left_n', 63.94)
        self.assert_json_equal('', 'report_1/@1/left_b', 7.359)
        self.assert_json_equal('', 'report_1/@1/right', "[707] 707")
        self.assert_json_equal('', 'report_1/@1/right_n', 196.61)
        self.assert_json_equal('', 'report_1/@1/right_b', 123.45)
        self.assert_json_equal('', 'report_1/@2/left', "[604] 604")
        self.assert_json_equal('', 'report_1/@2/left_n', "")
        self.assert_json_equal('', 'report_1/@2/left_b', 6.24)
        self.assert_json_equal('', 'report_1/@2/right', "[740] 740")
        self.assert_json_equal('', 'report_1/@2/right_n', 135.45)
        self.assert_json_equal('', 'report_1/@2/right_b', "")
        self.assert_json_equal('', 'report_1/@3/left', "[627] 627")
        self.assert_json_equal('', 'report_1/@3/left_n', 12.34)
        self.assert_json_equal('', 'report_1/@3/left_b', "")
        self.assert_json_equal('', 'report_1/@3/right', "")
        self.assert_json_equal('', 'report_1/@3/right_n', "")
        self.assert_json_equal('', 'report_1/@3/right_b', "")

        self.assert_json_equal('', 'report_1/@5/left', "&#160;&#160;&#160;&#160;&#160;&#160;&#160;&#160;&#160;&#160;{[u]}{[b]}total{[/b]}{[/u]}")
        self.assert_json_equal('', 'report_1/@5/left_n', {"value": 76.28, "format": "{[u]}{[b]}{0}{[/b]}{[/u]}"})
        self.assert_json_equal('', 'report_1/@5/left_b', {"value": 21.78, "format": "{[u]}{[b]}{0}{[/b]}{[/u]}"})
        self.assert_json_equal('', 'report_1/@5/right', "&#160;&#160;&#160;&#160;&#160;&#160;&#160;&#160;&#160;&#160;{[u]}{[b]}total{[/b]}{[/u]}")
        self.assert_json_equal('', 'report_1/@5/right_n', {"value": 332.06, "format": "{[u]}{[b]}{0}{[/b]}{[/u]}"})
        self.assert_json_equal('', 'report_1/@5/right_b', {"value": 191.34, "format": "{[u]}{[b]}{0}{[/b]}{[/u]}"})
        self.assert_json_equal('', 'report_1/@6/left', "&#160;&#160;&#160;&#160;&#160;{[i]}résultat (excédent){[/i]}")
        self.assert_json_equal('', 'report_1/@6/left_n', 255.78)
        self.assert_json_equal('', 'report_1/@6/left_b', 169.56)
        self.assert_json_equal('', 'report_1/@6/right', "")
        self.assert_json_equal('', 'report_1/@6/right_n', "")
        self.assert_json_equal('', 'report_1/@6/right_b', "")

        self.factory.xfer = FiscalYearBalanceSheet()
        self.calljson('/diacamma.accounting/fiscalYearBalanceSheet', {'year': '1'}, False)
        self.assert_observer('core.custom', 'diacamma.accounting', 'fiscalYearBalanceSheet')
        self.assert_count_equal('report_1', 11)
        self.assert_json_equal('', 'report_1/@1/left', "[411] 411")
        self.assert_json_equal('', 'report_1/@1/left_n', 125.97)
        self.assert_json_equal('', 'report_1/@1/right', "[106] 106")
        self.assert_json_equal('', 'report_1/@1/right_n', 1250.38)
        self.assert_json_equal('', 'report_1/@2/left', "[441] 441")
        self.assert_json_equal('', 'report_1/@2/left_n', 135.45)
        self.assert_json_equal('', 'report_1/@2/right', "[120] 120")
        self.assert_json_equal('', 'report_1/@2/right_n', 255.78)
        self.assert_json_equal('', 'report_1/@3/left', {"format": "{[i]}{0}{[/i]}", "value": "&#160;&#160;&#160;&#160;&#160;&#160;&#160;&#160;&#160;&#160;Sous-total"})
        self.assert_json_equal('', 'report_1/@3/left_n', {"format": "{[i]}{0}{[/i]}", "value": 261.41999999999996})
        self.assert_json_equal('', 'report_1/@3/right', {"format": "{[i]}{0}{[/i]}", "value": "&#160;&#160;&#160;&#160;&#160;&#160;&#160;&#160;&#160;&#160;Sous-total"})
        self.assert_json_equal('', 'report_1/@3/right_n', {"format": "{[i]}{0}{[/i]}", "value": 1506.16})

        self.assert_json_equal('', 'report_1/@6/left', "[512] 512")
        self.assert_json_equal('', 'report_1/@6/left_n', 1130.2900000000002)
        self.assert_json_equal('', 'report_1/@6/right', "")
        self.assert_json_equal('', 'report_1/@6/right_n', "")
        self.assert_json_equal('', 'report_1/@7/left', "[531] 531")
        self.assert_json_equal('', 'report_1/@7/left_n', 114.45)
        self.assert_json_equal('', 'report_1/@7/right', "")
        self.assert_json_equal('', 'report_1/@7/right_n', "")
        self.assert_json_equal('', 'report_1/@8/left', {"format": "{[i]}{0}{[/i]}", "value": "&#160;&#160;&#160;&#160;&#160;&#160;&#160;&#160;&#160;&#160;Sous-total"})
        self.assert_json_equal('', 'report_1/@8/left_n', {"format": "{[i]}{0}{[/i]}", "value": 1244.7400000000002})
        self.assert_json_equal('', 'report_1/@8/right', "")
        self.assert_json_equal('', 'report_1/@8/right_n', "")

        self.assert_json_equal('', 'report_1/@10/left', {"format": "{[u]}{[b]}{0}{[/b]}{[/u]}", "value": "Total"})
        self.assert_json_equal('', 'report_1/@10/left_n', {"value": 1506.1600000000003, "format": "{[u]}{[b]}{0}{[/b]}{[/u]}"})
        self.assert_json_equal('', 'report_1/@10/right', {"format": "{[u]}{[b]}{0}{[/b]}{[/u]}", "value": "Total"})
        self.assert_json_equal('', 'report_1/@10/right_n', {"value": 1506.16, "format": "{[u]}{[b]}{0}{[/b]}{[/u]}"})

    def test_import_lastyear(self):
        self._add_subvention()

        FiscalYear.objects.create(begin='2016-01-01', end='2016-12-31', status=0, last_fiscalyear=FiscalYear.objects.get(id=1))
        self.factory.xfer = FiscalYearBegin()
        self.calljson('/diacamma.accounting/fiscalYearBegin', {'CONFIRME': 'YES', 'year': '1', 'type_of_account': '-1'}, False)
        self.assert_observer('core.acknowledge', 'diacamma.accounting', 'fiscalYearBegin')
        self.assertEqual(FiscalYear.objects.get(id=1).status, 1)
        self.factory.xfer = FiscalYearClose()
        self.calljson('/diacamma.accounting/fiscalYearClose', {'CONFIRME': 'YES', 'year': '1', 'type_of_account': '-1'}, False)
        self.assert_observer('core.acknowledge', 'diacamma.accounting', 'fiscalYearClose')

        self.assertEqual(FiscalYear.objects.get(id=1).status, 2)
        self.assertEqual(FiscalYear.objects.get(id=2).status, 0)

        self.factory.xfer = FiscalYearReportLastYear()
        self.calljson('/diacamma.accounting/fiscalYearReportLastYear', {'CONFIRME': 'YES', 'year': '2', 'type_of_account': '-1'}, False)
        self.assert_observer('core.acknowledge', 'diacamma.accounting', 'fiscalYearReportLastYear')
        self.assertEqual(FiscalYear.objects.get(id=2).status, 0)

        self.factory.xfer = EntryAccountList()
        self.calljson('/diacamma.accounting/entryAccountList', {'year': '2', 'journal': '0', 'filter': '0'}, False)
        self.assert_observer('core.custom', 'diacamma.accounting', 'entryAccountList')
        self.assert_count_equal('entryline', 16)
        self.assert_json_equal('LABELFORM', 'result', [34.01, 272.32, -238.31, 1050.66, 1244.74])

        self.factory.xfer = EntryAccountList()
        self.calljson('/diacamma.accounting/entryAccountList', {'year': '2', 'journal': '1', 'filter': '0'}, False)
        self.assert_observer('core.custom', 'diacamma.accounting', 'entryAccountList')
        self.assert_count_equal('entryline', 8)

        self.assert_json_equal('', 'entryline/@0/designation_ref', "Report à nouveau - Bilan")
        self.assert_json_equal('', 'entryline/@0/entry_account', "[106] 106")
        self.assert_json_equal('', 'entryline/@0/link', None)
        self.assert_json_equal('', 'entryline/@1/designation_ref', "Report à nouveau - Bilan")
        self.assert_json_equal('', 'entryline/@1/entry_account', "[120] 120")
        self.assert_json_equal('', 'entryline/@1/link', None)
        self.assert_json_equal('', 'entryline/@2/designation_ref', "Report à nouveau - Bilan")
        self.assert_json_equal('', 'entryline/@2/entry_account', "[411] 411")
        self.assert_json_equal('', 'entryline/@2/link', None)
        self.assert_json_equal('', 'entryline/@3/designation_ref', "Report à nouveau - Bilan")
        self.assert_json_equal('', 'entryline/@3/entry_account', "[441] 441")
        self.assert_json_equal('', 'entryline/@3/link', None)

        self.assert_json_equal('', 'entryline/@4/designation_ref', "Report à nouveau - Bilan")
        self.assert_json_equal('', 'entryline/@4/entry_account', "[512] 512")
        self.assert_json_equal('', 'entryline/@4/link', None)
        self.assert_json_equal('', 'entryline/@5/designation_ref', "Report à nouveau - Bilan")
        self.assert_json_equal('', 'entryline/@5/entry_account', "[531] 531")
        self.assert_json_equal('', 'entryline/@5/link', None)

        self.assert_json_equal('', 'entryline/@6/designation_ref', "Report à nouveau - Dette tiers")
        self.assert_json_equal('', 'entryline/@6/entry_account', "[411] 411")
        self.assert_json_equal('', 'entryline/@6/credit', 125.97)
        self.assert_json_equal('', 'entryline/@6/link', None)
        self.assert_json_equal('', 'entryline/@7/designation_ref', "Report à nouveau - Dette tiers{[br/]}vente 2")
        self.assert_json_equal('', 'entryline/@7/entry_account', "[411 Dalton William]")
        self.assert_json_equal('', 'entryline/@7/debit', -125.97)
        self.assert_json_equal('', 'entryline/@7/link', None)

        self.factory.xfer = ChartsAccountList()
        self.calljson('/diacamma.accounting/chartsAccountList', {'year': '2', 'type_of_account': '-1'}, False)
        self.assert_observer('core.custom', 'diacamma.accounting', 'chartsAccountList')
        self.assert_count_equal('', 8)
        self.assertEqual(len(self.json_actions), 4)
        self.assert_count_equal('chartsaccount', 10)
        self.assert_json_equal('', 'chartsaccount/@1/code', '120')
        self.assert_json_equal('', 'chartsaccount/@1/current_total', 255.78)
        self.assert_json_equal('', 'chartsaccount/@3/code', '411')
        self.assert_json_equal('', 'chartsaccount/@3/current_total', -159.98)
        self.assert_json_equal('', 'chartsaccount/@4/code', '441')
        self.assert_json_equal('', 'chartsaccount/@4/current_total', -135.45)

        self.factory.xfer = ChartsAccountList()
        self.calljson('/diacamma.accounting/chartsAccountList', {'year': '1', 'type_of_account': '-1'}, False)
        self.assert_observer('core.custom', 'diacamma.accounting', 'chartsAccountList')
        self.assertEqual(len(self.json_actions), 3)
