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
from datetime import date, timedelta

from lucterios.framework.xfergraphic import XferContainerAcknowledge
from lucterios.framework.test import LucteriosTest
from lucterios.framework.filetools import get_user_dir
from lucterios.CORE.views import StatusMenu

from diacamma.accounting.views import ThirdList, ThirdAdd, ThirdSave, ThirdShow, \
    AccountThirdAddModify, AccountThirdDel
from diacamma.accounting.views_admin import Configuration, JournalAddModify, \
    JournalDel, FiscalYearAddModify, FiscalYearActive, FiscalYearDel
from diacamma.accounting.test_tools import initial_contacts, fill_entries, initial_thirds, \
    create_third, fill_accounts, fill_thirds, default_compta, \
    set_accounting_system
from diacamma.accounting.models import FiscalYear, clear_system_account, \
    current_system_account
from diacamma.accounting.system import get_accounting_system

class ThirdTest(LucteriosTest):
    # pylint: disable=too-many-public-methods,too-many-statements

    def setUp(self):
        self.xfer_class = XferContainerAcknowledge
        LucteriosTest.setUp(self)
        initial_contacts()
        rmtree(get_user_dir(), True)
        clear_system_account()

    def test_add_abstract(self):
        self.factory.xfer = ThirdList()
        self.call('/diacamma.accounting/thirdListing', {}, False)
        self.assert_observer('Core.Custom', 'diacamma.accounting', 'thirdListing')
        self.assert_count_equal('COMPONENTS/GRID[@name="third"]/RECORD', 0)

        self.factory.xfer = ThirdAdd()
        self.call('/diacamma.accounting/thirdAdd', {}, False)
        self.assert_observer('Core.Custom', 'diacamma.accounting', 'thirdAdd')
        self.assert_comp_equal('COMPONENTS/SELECT[@name="modelname"]', 'contacts.AbstractContact', (2, 0, 3, 1))
        self.assert_count_equal('COMPONENTS/SELECT[@name="modelname"]/CASE', 3)
        self.assert_count_equal('COMPONENTS/GRID[@name="abstractcontact"]/HEADER', 4)
        self.assert_count_equal('COMPONENTS/GRID[@name="abstractcontact"]/RECORD', 8)

        self.factory.xfer = ThirdSave()
        self.call('/diacamma.accounting/thirdSave', {'pkname':'abstractcontact', 'abstractcontact':5}, False)
        self.assert_observer('Core.Acknowledge', 'diacamma.accounting', 'thirdSave')
        self.assert_attrib_equal('ACTION', 'action', 'thirdShow')
        self.assert_xml_equal('ACTION/PARAM[@name="third"]', '1')

        self.factory.xfer = ThirdList()
        self.call('/diacamma.accounting/thirdListing', {}, False)
        self.assert_observer('Core.Custom', 'diacamma.accounting', 'thirdListing')
        self.assert_count_equal('COMPONENTS/GRID[@name="third"]/RECORD', 1)
        self.assert_xml_equal('COMPONENTS/GRID[@name="third"]/RECORD[1]/VALUE[@name="contact"]', 'Dalton Joe')

    def test_add_legalentity(self):
        self.factory.xfer = ThirdList()
        self.call('/diacamma.accounting/thirdListing', {}, False)
        self.assert_observer('Core.Custom', 'diacamma.accounting', 'thirdListing')
        self.assert_count_equal('COMPONENTS/GRID[@name="third"]/RECORD', 0)

        self.factory.xfer = ThirdAdd()
        self.call('/diacamma.accounting/thirdAdd', {'modelname':'contacts.LegalEntity'}, False)
        self.assert_observer('Core.Custom', 'diacamma.accounting', 'thirdAdd')
        self.assert_comp_equal('COMPONENTS/SELECT[@name="modelname"]', 'contacts.LegalEntity', (2, 0, 3, 1))
        self.assert_count_equal('COMPONENTS/GRID[@name="legalentity"]/HEADER', 4)
        self.assert_count_equal('COMPONENTS/GRID[@name="legalentity"]/RECORD', 3)

        self.factory.xfer = ThirdSave()
        self.call('/diacamma.accounting/thirdSave', {'pkname':'legalentity', 'legalentity':7}, False)
        self.assert_observer('Core.Acknowledge', 'diacamma.accounting', 'thirdSave')
        self.assert_attrib_equal('ACTION', 'action', 'thirdShow')
        self.assert_xml_equal('ACTION/PARAM[@name="third"]', '1')

        self.factory.xfer = ThirdList()
        self.call('/diacamma.accounting/thirdListing', {}, False)
        self.assert_observer('Core.Custom', 'diacamma.accounting', 'thirdListing')
        self.assert_count_equal('COMPONENTS/GRID[@name="third"]/RECORD', 1)
        self.assert_xml_equal('COMPONENTS/GRID[@name="third"]/RECORD[1]/VALUE[@name="contact"]', 'Minimum')

        self.factory.xfer = ThirdShow()
        self.call('/diacamma.accounting/thirdShow', {"third":1}, False)
        self.assert_observer('Core.Custom', 'diacamma.accounting', 'thirdShow')
        self.assert_xml_equal('COMPONENTS/LABELFORM[@name="contact"]', 'Minimum')
        self.assert_attrib_equal('COMPONENTS/BUTTON[@name="show"]/ACTIONS/ACTION', 'extension', 'lucterios.contacts')
        self.assert_attrib_equal('COMPONENTS/BUTTON[@name="show"]/ACTIONS/ACTION', 'action', 'legalEntityShow')
        self.assert_xml_equal('COMPONENTS/BUTTON[@name="show"]/ACTIONS/ACTION/PARAM[@name="legalentity"]', '7')

    def test_add_individual(self):
        self.factory.xfer = ThirdList()
        self.call('/diacamma.accounting/thirdListing', {}, False)
        self.assert_observer('Core.Custom', 'diacamma.accounting', 'thirdListing')
        self.assert_count_equal('COMPONENTS/GRID[@name="third"]/RECORD', 0)

        self.factory.xfer = ThirdAdd()
        self.call('/diacamma.accounting/thirdAdd', {'modelname':'contacts.Individual'}, False)
        self.assert_observer('Core.Custom', 'diacamma.accounting', 'thirdAdd')
        self.assert_comp_equal('COMPONENTS/SELECT[@name="modelname"]', 'contacts.Individual', (2, 0, 3, 1))
        self.assert_count_equal('COMPONENTS/GRID[@name="individual"]/HEADER', 5)
        self.assert_count_equal('COMPONENTS/GRID[@name="individual"]/RECORD', 5)

        self.factory.xfer = ThirdSave()
        self.call('/diacamma.accounting/thirdSave', {'pkname':'individual', 'individual':3}, False)
        self.assert_observer('Core.Acknowledge', 'diacamma.accounting', 'thirdSave')
        self.assert_attrib_equal('ACTION', 'action', 'thirdShow')
        self.assert_xml_equal('ACTION/PARAM[@name="third"]', '1')

        self.factory.xfer = ThirdList()
        self.call('/diacamma.accounting/thirdListing', {}, False)
        self.assert_observer('Core.Custom', 'diacamma.accounting', 'thirdListing')
        self.assert_count_equal('COMPONENTS/GRID[@name="third"]/RECORD', 1)
        self.assert_xml_equal('COMPONENTS/GRID[@name="third"]/RECORD[1]/VALUE[@name="contact"]', 'Dalton William')

        self.factory.xfer = ThirdShow()
        self.call('/diacamma.accounting/thirdShow', {"third":1}, False)
        self.assert_observer('Core.Custom', 'diacamma.accounting', 'thirdShow')
        self.assert_xml_equal('COMPONENTS/LABELFORM[@name="contact"]', 'Dalton William')
        self.assert_attrib_equal('COMPONENTS/BUTTON[@name="show"]/ACTIONS/ACTION', 'extension', 'lucterios.contacts')
        self.assert_attrib_equal('COMPONENTS/BUTTON[@name="show"]/ACTIONS/ACTION', 'action', 'individualShow')
        self.assert_xml_equal('COMPONENTS/BUTTON[@name="show"]/ACTIONS/ACTION/PARAM[@name="individual"]', '3')

    def test_check_double(self):
        self.factory.xfer = ThirdList()
        self.call('/diacamma.accounting/thirdListing', {}, False)
        self.assert_observer('Core.Custom', 'diacamma.accounting', 'thirdListing')
        self.assert_count_equal('COMPONENTS/GRID[@name="third"]/RECORD', 0)

        self.factory.xfer = ThirdSave()
        self.call('/diacamma.accounting/thirdSave', {'pkname':'abstractcontact', 'abstractcontact':5}, False)
        self.assert_observer('Core.Acknowledge', 'diacamma.accounting', 'thirdSave')
        self.assert_attrib_equal('ACTION', 'action', 'thirdShow')
        self.assert_xml_equal('ACTION/PARAM[@name="third"]', '1')

        self.factory.xfer = ThirdSave()
        self.call('/diacamma.accounting/thirdSave', {'pkname':'abstractcontact', 'abstractcontact':5}, False)
        self.assert_observer('Core.Acknowledge', 'diacamma.accounting', 'thirdSave')
        self.assert_attrib_equal('ACTION', 'action', 'thirdShow')
        self.assert_xml_equal('ACTION/PARAM[@name="third"]', '1')

        self.factory.xfer = ThirdSave()
        self.call('/diacamma.accounting/thirdSave', {'pkname':'abstractcontact', 'abstractcontact':5}, False)
        self.assert_observer('Core.Acknowledge', 'diacamma.accounting', 'thirdSave')
        self.assert_attrib_equal('ACTION', 'action', 'thirdShow')
        self.assert_xml_equal('ACTION/PARAM[@name="third"]', '1')

        self.factory.xfer = ThirdList()
        self.call('/diacamma.accounting/thirdListing', {}, False)
        self.assert_observer('Core.Custom', 'diacamma.accounting', 'thirdListing')
        self.assert_count_equal('COMPONENTS/GRID[@name="third"]/RECORD', 1)

    def test_show(self):
        create_third([3])
        self.factory.xfer = ThirdShow()
        self.call('/diacamma.accounting/thirdShow', {"third":1}, False)
        self.assert_observer('Core.Custom', 'diacamma.accounting', 'thirdShow')
        self.assert_count_equal('COMPONENTS/TAB', 1)
        self.assert_count_equal('COMPONENTS/*', 16 + 7)
        self.assert_xml_equal('COMPONENTS/LABELFORM[@name="contact"]', 'Dalton William')
        self.assert_xml_equal('COMPONENTS/LABELFORM[@name="status"]', 'Actif')
        self.assert_count_equal('COMPONENTS/GRID[@name="accountthird"]/HEADER', 2)
        self.assert_xml_equal('COMPONENTS/GRID[@name="accountthird"]/HEADER[@name="code"]', "code")
        self.assert_xml_equal('COMPONENTS/GRID[@name="accountthird"]/HEADER[@name="total_txt"]', "total")
        self.assert_count_equal('COMPONENTS/GRID[@name="accountthird"]/RECORD', 0)
        self.assert_xml_equal('COMPONENTS/LABELFORM[@name="total"]', '0.00€')

        self.factory.xfer = AccountThirdAddModify()
        self.call('/diacamma.accounting/accountThirdAddModify', {"third":1}, False)
        self.assert_observer('Core.Custom', 'diacamma.accounting', 'accountThirdAddModify')
        self.assert_count_equal('COMPONENTS/*', 3)
        self.assert_xml_equal('COMPONENTS/EDIT[@name="code"]', None)

        self.factory.xfer = AccountThirdAddModify()
        self.call('/diacamma.accounting/accountThirdAddModify', {'SAVE':'YES', "third":1, 'code':'411000'}, False)
        self.assert_observer('Core.Acknowledge', 'diacamma.accounting', 'accountThirdAddModify')

        self.factory.xfer = ThirdShow()
        self.call('/diacamma.accounting/thirdShow', {"third":1}, False)
        self.assert_observer('Core.Custom', 'diacamma.accounting', 'thirdShow')
        self.assert_count_equal('COMPONENTS/GRID[@name="accountthird"]/HEADER', 2)
        self.assert_count_equal('COMPONENTS/GRID[@name="accountthird"]/RECORD', 1)
        self.assert_xml_equal('COMPONENTS/GRID[@name="accountthird"]/RECORD[1]/VALUE[@name="code"]', '411000')
        self.assert_xml_equal('COMPONENTS/GRID[@name="accountthird"]/RECORD[1]/VALUE[@name="total_txt"]', '{[font color="green"]}Crédit: 0.00€{[/font]}')
        self.assert_xml_equal('COMPONENTS/LABELFORM[@name="total"]', '0.00€')

        self.factory.xfer = AccountThirdDel()
        self.call('/diacamma.accounting/accountThirdDel', {'CONFIRME':'YES', "accountthird":1}, False)
        self.assert_observer('Core.Acknowledge', 'diacamma.accounting', 'accountThirdDel')

        self.factory.xfer = ThirdShow()
        self.call('/diacamma.accounting/thirdShow', {"third":1}, False)
        self.assert_observer('Core.Custom', 'diacamma.accounting', 'thirdShow')
        self.assert_count_equal('COMPONENTS/GRID[@name="accountthird"]/HEADER', 2)
        self.assert_count_equal('COMPONENTS/GRID[@name="accountthird"]/RECORD', 0)

    def test_show_withdata(self):
        fill_thirds()
        default_compta()
        fill_entries(1)
        self.factory.xfer = ThirdShow()
        self.call('/diacamma.accounting/thirdShow', {"third":4}, False)
        self.assert_observer('Core.Custom', 'diacamma.accounting', 'thirdShow')
        self.assert_count_equal('COMPONENTS/TAB', 2)
        self.assert_count_equal('COMPONENTS/*', 16 + 7 + 4)
        self.assert_xml_equal('COMPONENTS/LABELFORM[@name="contact"]', 'Minimum')
        self.assert_xml_equal('COMPONENTS/LABELFORM[@name="status"]', 'Actif')
        self.assert_count_equal('COMPONENTS/GRID[@name="accountthird"]/HEADER', 2)
        self.assert_xml_equal('COMPONENTS/GRID[@name="accountthird"]/HEADER[@name="code"]', "code")
        self.assert_xml_equal('COMPONENTS/GRID[@name="accountthird"]/HEADER[@name="total_txt"]', "total")

        self.assert_count_equal('COMPONENTS/GRID[@name="accountthird"]/RECORD', 2)
        self.assert_attrib_equal('COMPONENTS/GRID[@name="accountthird"]/RECORD[1]', 'id', '5')

        self.assert_xml_equal('COMPONENTS/GRID[@name="accountthird"]/RECORD[1]/VALUE[@name="code"]', '411000')
        self.assert_xml_equal('COMPONENTS/GRID[@name="accountthird"]/RECORD[1]/VALUE[@name="total_txt"]', '{[font color="blue"]}Débit: 34.01€{[/font]}')
        self.assert_attrib_equal('COMPONENTS/GRID[@name="accountthird"]/RECORD[2]', 'id', '6')

        self.assert_xml_equal('COMPONENTS/GRID[@name="accountthird"]/RECORD[2]/VALUE[@name="code"]', '401000')
        self.assert_xml_equal('COMPONENTS/GRID[@name="accountthird"]/RECORD[2]/VALUE[@name="total_txt"]', '{[font color="green"]}Crédit: 0.00€{[/font]}')
        self.assert_xml_equal('COMPONENTS/LABELFORM[@name="total"]', '34.01€')

        self.assert_xml_equal('COMPONENTS/SELECT[@name="lines_filter"]', '0')
        self.assert_count_equal('COMPONENTS/SELECT[@name="lines_filter"]/CASE', 3)
        self.assert_count_equal('COMPONENTS/GRID[@name="entrylineaccount"]/HEADER', 8)
        self.assert_count_equal('COMPONENTS/GRID[@name="entrylineaccount"]/RECORD', 3)
        self.assert_xml_equal('COMPONENTS/GRID[@name="entrylineaccount"]/RECORD[1]/VALUE[@name="entry.num"]', '2')
        self.assert_xml_equal('COMPONENTS/GRID[@name="entrylineaccount"]/RECORD[1]/VALUE[@name="credit"]', '63.94€')
        self.assert_xml_equal('COMPONENTS/GRID[@name="entrylineaccount"]/RECORD[1]/VALUE[@name="entry.link"]', 'A')
        self.assert_xml_equal('COMPONENTS/GRID[@name="entrylineaccount"]/RECORD[2]/VALUE[@name="entry.num"]', '3')
        self.assert_xml_equal('COMPONENTS/GRID[@name="entrylineaccount"]/RECORD[2]/VALUE[@name="debit"]', '63.94€')
        self.assert_xml_equal('COMPONENTS/GRID[@name="entrylineaccount"]/RECORD[2]/VALUE[@name="entry.link"]', 'A')
        self.assert_xml_equal('COMPONENTS/GRID[@name="entrylineaccount"]/RECORD[3]/VALUE[@name="entry.num"]', '---')
        self.assert_xml_equal('COMPONENTS/GRID[@name="entrylineaccount"]/RECORD[3]/VALUE[@name="debit"]', '34.01€')
        self.assert_xml_equal('COMPONENTS/GRID[@name="entrylineaccount"]/RECORD[3]/VALUE[@name="entry.link"]', '---')

        self.factory.xfer = AccountThirdDel()
        self.call('/diacamma.accounting/accountThirdDel', {"accountthird":6}, False)
        self.assert_observer('CORE.Exception', 'diacamma.accounting', 'accountThirdDel')
        self.assert_xml_equal('EXCEPTION/MESSAGE', "Ce compte comporte des écritures!")

    def test_show_withdata_linesfilter(self):
        fill_thirds()
        default_compta()
        fill_entries(1)

        self.factory.xfer = ThirdShow()
        self.call('/diacamma.accounting/thirdShow', {"third":4, 'lines_filter':0}, False)
        self.assert_observer('Core.Custom', 'diacamma.accounting', 'thirdShow')
        self.assert_count_equal('COMPONENTS/TAB', 2)
        self.assert_count_equal('COMPONENTS/*', 16 + 7 + 4)
        self.assert_xml_equal('COMPONENTS/SELECT[@name="lines_filter"]', '0')
        self.assert_count_equal('COMPONENTS/SELECT[@name="lines_filter"]/CASE', 3)
        self.assert_count_equal('COMPONENTS/GRID[@name="entrylineaccount"]/HEADER', 8)
        self.assert_count_equal('COMPONENTS/GRID[@name="entrylineaccount"]/RECORD', 3)

        self.factory.xfer = ThirdShow()
        self.call('/diacamma.accounting/thirdShow', {"third":4, 'lines_filter':1}, False)
        self.assert_observer('Core.Custom', 'diacamma.accounting', 'thirdShow')
        self.assert_count_equal('COMPONENTS/TAB', 2)
        self.assert_count_equal('COMPONENTS/*', 16 + 7 + 4)
        self.assert_xml_equal('COMPONENTS/SELECT[@name="lines_filter"]', '1')
        self.assert_count_equal('COMPONENTS/SELECT[@name="lines_filter"]/CASE', 3)
        self.assert_count_equal('COMPONENTS/GRID[@name="entrylineaccount"]/HEADER', 8)
        self.assert_count_equal('COMPONENTS/GRID[@name="entrylineaccount"]/RECORD', 1)

        default_compta()

        self.factory.xfer = ThirdShow()
        self.call('/diacamma.accounting/thirdShow', {"third":4, 'lines_filter':0}, False)
        self.assert_observer('Core.Custom', 'diacamma.accounting', 'thirdShow')
        self.assert_count_equal('COMPONENTS/TAB', 2)
        self.assert_count_equal('COMPONENTS/*', 16 + 7 + 4)
        self.assert_xml_equal('COMPONENTS/SELECT[@name="lines_filter"]', '0')
        self.assert_count_equal('COMPONENTS/SELECT[@name="lines_filter"]/CASE', 3)
        self.assert_count_equal('COMPONENTS/GRID[@name="entrylineaccount"]/HEADER', 8)
        self.assert_count_equal('COMPONENTS/GRID[@name="entrylineaccount"]/RECORD', 0)

        self.factory.xfer = ThirdShow()
        self.call('/diacamma.accounting/thirdShow', {"third":4, 'lines_filter':2}, False)
        self.assert_observer('Core.Custom', 'diacamma.accounting', 'thirdShow')
        self.assert_count_equal('COMPONENTS/TAB', 2)
        self.assert_count_equal('COMPONENTS/*', 16 + 7 + 4)
        self.assert_xml_equal('COMPONENTS/SELECT[@name="lines_filter"]', '2')
        self.assert_count_equal('COMPONENTS/SELECT[@name="lines_filter"]/CASE', 3)
        self.assert_count_equal('COMPONENTS/GRID[@name="entrylineaccount"]/HEADER', 8)
        self.assert_count_equal('COMPONENTS/GRID[@name="entrylineaccount"]/RECORD', 3)

    def test_list(self):
        fill_thirds()

        self.factory.xfer = ThirdList()
        self.call('/diacamma.accounting/thirdListing', {}, False)
        self.assert_observer('Core.Custom', 'diacamma.accounting', 'thirdListing')
        self.assert_count_equal('COMPONENTS/*', 8)
        self.assert_count_equal('COMPONENTS/GRID[@name="third"]/HEADER', 2)
        self.assert_xml_equal('COMPONENTS/GRID[@name="third"]/HEADER[@name="contact"]', "contact")
        self.assert_xml_equal('COMPONENTS/GRID[@name="third"]/HEADER[@name="accountthird_set"]', "compte")
        self.assert_count_equal('COMPONENTS/GRID[@name="third"]/RECORD', 7)
        self.assert_xml_equal('COMPONENTS/GRID[@name="third"]/RECORD[1]/VALUE[@name="contact"]', 'Dalton Avrel')
        self.assert_xml_equal('COMPONENTS/GRID[@name="third"]/RECORD[1]/VALUE[@name="accountthird_set"]', '401000')
        self.assert_xml_equal('COMPONENTS/GRID[@name="third"]/RECORD[2]/VALUE[@name="contact"]', 'Dalton Jack')
        self.assert_xml_equal('COMPONENTS/GRID[@name="third"]/RECORD[2]/VALUE[@name="accountthird_set"]', '411000')
        self.assert_xml_equal('COMPONENTS/GRID[@name="third"]/RECORD[3]/VALUE[@name="contact"]', 'Dalton Joe')
        self.assert_xml_equal('COMPONENTS/GRID[@name="third"]/RECORD[3]/VALUE[@name="accountthird_set"]', '411000')
        self.assert_xml_equal('COMPONENTS/GRID[@name="third"]/RECORD[4]/VALUE[@name="contact"]', 'Dalton William')
        self.assert_xml_equal('COMPONENTS/GRID[@name="third"]/RECORD[4]/VALUE[@name="accountthird_set"]', '411000')
        self.assert_xml_equal('COMPONENTS/GRID[@name="third"]/RECORD[5]/VALUE[@name="contact"]', 'Luke Lucky')
        self.assert_xml_equal('COMPONENTS/GRID[@name="third"]/RECORD[5]/VALUE[@name="accountthird_set"]', '411000{[br/]}401000')
        self.assert_xml_equal('COMPONENTS/GRID[@name="third"]/RECORD[6]/VALUE[@name="contact"]', 'Maximum')
        self.assert_xml_equal('COMPONENTS/GRID[@name="third"]/RECORD[6]/VALUE[@name="accountthird_set"]', '401000')
        self.assert_xml_equal('COMPONENTS/GRID[@name="third"]/RECORD[7]/VALUE[@name="contact"]', 'Minimum')
        self.assert_xml_equal('COMPONENTS/GRID[@name="third"]/RECORD[7]/VALUE[@name="accountthird_set"]', '411000{[br/]}401000')

    def test_list_withfilter(self):
        fill_thirds()
        self.factory.xfer = ThirdList()
        self.call('/diacamma.accounting/thirdListing', {'filter':'joe'}, False)
        self.assert_observer('Core.Custom', 'diacamma.accounting', 'thirdListing')
        self.assert_count_equal('COMPONENTS/*', 8)
        self.assert_count_equal('COMPONENTS/GRID[@name="third"]/HEADER', 2)
        self.assert_xml_equal('COMPONENTS/GRID[@name="third"]/HEADER[@name="contact"]', "contact")
        self.assert_xml_equal('COMPONENTS/GRID[@name="third"]/HEADER[@name="accountthird_set"]', "compte")
        self.assert_count_equal('COMPONENTS/GRID[@name="third"]/RECORD', 1)
        self.assert_xml_equal('COMPONENTS/GRID[@name="third"]/RECORD[1]/VALUE[@name="contact"]', 'Dalton Joe')
        self.assert_xml_equal('COMPONENTS/GRID[@name="third"]/RECORD[1]/VALUE[@name="accountthird_set"]', '411000')

    def test_list_display(self):
        fill_thirds()
        default_compta()
        fill_entries(1)
        self.factory.xfer = ThirdList()
        self.call('/diacamma.accounting/thirdListing', {'show_filter':'1'}, False)
        self.assert_observer('Core.Custom', 'diacamma.accounting', 'thirdListing')
        self.assert_count_equal('COMPONENTS/*', 8)
        self.assert_count_equal('COMPONENTS/GRID[@name="third"]/HEADER', 3)
        self.assert_xml_equal('COMPONENTS/GRID[@name="third"]/HEADER[@name="contact"]', "contact")
        self.assert_xml_equal('COMPONENTS/GRID[@name="third"]/HEADER[@name="accountthird_set"]', "compte")
        self.assert_xml_equal('COMPONENTS/GRID[@name="third"]/HEADER[@name="total"]', "total")
        self.assert_count_equal('COMPONENTS/GRID[@name="third"]/RECORD', 7)
        self.assert_xml_equal('COMPONENTS/GRID[@name="third"]/RECORD[2]/VALUE[@name="contact"]', 'Dalton Jack')
        self.assert_xml_equal('COMPONENTS/GRID[@name="third"]/RECORD[2]/VALUE[@name="accountthird_set"]', '411000')
        self.assert_xml_equal('COMPONENTS/GRID[@name="third"]/RECORD[2]/VALUE[@name="total"]', '0.00€')
        self.assert_xml_equal('COMPONENTS/GRID[@name="third"]/RECORD[4]/VALUE[@name="contact"]', 'Dalton William')
        self.assert_xml_equal('COMPONENTS/GRID[@name="third"]/RECORD[4]/VALUE[@name="accountthird_set"]', '411000')
        self.assert_xml_equal('COMPONENTS/GRID[@name="third"]/RECORD[4]/VALUE[@name="total"]', '125.97€')
        self.assert_xml_equal('COMPONENTS/GRID[@name="third"]/RECORD[7]/VALUE[@name="contact"]', 'Minimum')
        self.assert_xml_equal('COMPONENTS/GRID[@name="third"]/RECORD[7]/VALUE[@name="accountthird_set"]', '411000{[br/]}401000')
        self.assert_xml_equal('COMPONENTS/GRID[@name="third"]/RECORD[7]/VALUE[@name="total"]', '34.01€')

        self.factory.xfer = ThirdList()
        self.call('/diacamma.accounting/thirdListing', {'show_filter':'2'}, False)
        self.assert_observer('Core.Custom', 'diacamma.accounting', 'thirdListing')
        self.assert_count_equal('COMPONENTS/*', 8)
        self.assert_count_equal('COMPONENTS/GRID[@name="third"]/HEADER', 3)
        self.assert_xml_equal('COMPONENTS/GRID[@name="third"]/HEADER[@name="contact"]', "contact")
        self.assert_xml_equal('COMPONENTS/GRID[@name="third"]/HEADER[@name="accountthird_set"]', "compte")
        self.assert_xml_equal('COMPONENTS/GRID[@name="third"]/HEADER[@name="total"]', "total")
        self.assert_count_equal('COMPONENTS/GRID[@name="third"]/RECORD', 3)
        self.assert_xml_equal('COMPONENTS/GRID[@name="third"]/RECORD[1]/VALUE[@name="contact"]', 'Dalton William')
        self.assert_xml_equal('COMPONENTS/GRID[@name="third"]/RECORD[1]/VALUE[@name="accountthird_set"]', '411000')
        self.assert_xml_equal('COMPONENTS/GRID[@name="third"]/RECORD[1]/VALUE[@name="total"]', '125.97€')
        self.assert_xml_equal('COMPONENTS/GRID[@name="third"]/RECORD[2]/VALUE[@name="contact"]', 'Maximum')
        self.assert_xml_equal('COMPONENTS/GRID[@name="third"]/RECORD[2]/VALUE[@name="accountthird_set"]', '401000')
        self.assert_xml_equal('COMPONENTS/GRID[@name="third"]/RECORD[2]/VALUE[@name="total"]', '78.24€')
        self.assert_xml_equal('COMPONENTS/GRID[@name="third"]/RECORD[3]/VALUE[@name="contact"]', 'Minimum')
        self.assert_xml_equal('COMPONENTS/GRID[@name="third"]/RECORD[3]/VALUE[@name="accountthird_set"]', '411000{[br/]}401000')
        self.assert_xml_equal('COMPONENTS/GRID[@name="third"]/RECORD[3]/VALUE[@name="total"]', '34.01€')

class AdminTest(LucteriosTest):
    # pylint: disable=too-many-public-methods,too-many-statements

    def setUp(self):
        self.xfer_class = XferContainerAcknowledge
        LucteriosTest.setUp(self)
        rmtree(get_user_dir(), True)

    def test_summary(self):
        self.factory.xfer = StatusMenu()
        self.call('/CORE/statusMenu', {}, False)
        self.assert_observer('Core.Custom', 'CORE', 'statusMenu')
        self.assert_xml_equal("COMPONENTS/LABELFORM[@name='accountingtitle']", "{[center]}{[b]}{[u]}Financier{[/u]}{[/b]}{[/center]}")
        self.assert_xml_equal("COMPONENTS/LABELFORM[@name='accounting_error']", "{[center]}Pas d'exercice défini!{[/center]}")
        self.assert_action_equal("COMPONENTS/BUTTON[@name='accounting_conf']/ACTIONS/ACTION", ("conf.", None, 'diacamma.accounting', 'configuration', 0, 1, 1))

    def test_default_configuration(self):
        self.factory.xfer = Configuration()
        self.call('/diacamma.accounting/configuration', {}, False)
        self.assert_observer('Core.Custom', 'diacamma.accounting', 'configuration')
        self.assert_count_equal('COMPONENTS/TAB', 3)
        self.assert_count_equal('COMPONENTS/*', 2 + 3 + 4 + 1 + 7)

        self.assert_count_equal('COMPONENTS/GRID[@name="fiscalyear"]/HEADER', 4)
        self.assert_xml_equal('COMPONENTS/GRID[@name="fiscalyear"]/HEADER[@name="begin"]', "début")
        self.assert_xml_equal('COMPONENTS/GRID[@name="fiscalyear"]/HEADER[@name="end"]', "fin")
        self.assert_xml_equal('COMPONENTS/GRID[@name="fiscalyear"]/HEADER[@name="status"]', "status")
        self.assert_xml_equal('COMPONENTS/GRID[@name="fiscalyear"]/HEADER[@name="is_actif"]', "actif")
        self.assert_count_equal('COMPONENTS/GRID[@name="fiscalyear"]/RECORD', 0)
        self.assert_xml_equal('COMPONENTS/LABELFORM[@name="nb"]', 'Nombre total de exercices: 0')

        self.assert_count_equal('COMPONENTS/GRID[@name="journal"]/HEADER', 1)
        self.assert_xml_equal('COMPONENTS/GRID[@name="journal"]/HEADER[@name="name"]', "nom")
        self.assert_count_equal('COMPONENTS/GRID[@name="journal"]/RECORD', 5)
        self.assert_xml_equal('COMPONENTS/GRID[@name="journal"]/RECORD[@id="1"]/VALUE[@name="name"]', 'Report à nouveau')
        self.assert_xml_equal('COMPONENTS/GRID[@name="journal"]/RECORD[@id="2"]/VALUE[@name="name"]', 'Achat')
        self.assert_xml_equal('COMPONENTS/GRID[@name="journal"]/RECORD[@id="3"]/VALUE[@name="name"]', 'Vente')
        self.assert_xml_equal('COMPONENTS/GRID[@name="journal"]/RECORD[@id="4"]/VALUE[@name="name"]', 'Règlement')
        self.assert_xml_equal('COMPONENTS/GRID[@name="journal"]/RECORD[@id="5"]/VALUE[@name="name"]', 'Autre')

        self.assert_xml_equal('COMPONENTS/LABELFORM[@name="accounting-devise"]', '€')
        self.assert_xml_equal('COMPONENTS/LABELFORM[@name="accounting-devise-iso"]', 'EUR')
        self.assert_xml_equal('COMPONENTS/LABELFORM[@name="accounting-devise-prec"]', '2')

    def test_configuration_journal(self):
        self.factory.xfer = JournalAddModify()
        self.call('/diacamma.accounting/journalAddModify', {'journal':'2'}, False)
        self.assert_observer('Core.Custom', 'diacamma.accounting', 'journalAddModify')
        self.assert_count_equal('COMPONENTS/*', 3)
        self.assert_xml_equal('COMPONENTS/EDIT[@name="name"]', 'Achat')

        self.factory.xfer = JournalAddModify()
        self.call('/diacamma.accounting/journalAddModify', {'SAVE':'YES', 'journal':'2', 'name':'Dépense'}, False)
        self.assert_observer('Core.Acknowledge', 'diacamma.accounting', 'journalAddModify')

        self.factory.xfer = Configuration()
        self.call('/diacamma.accounting/configuration', {}, False)
        self.assert_count_equal('COMPONENTS/GRID[@name="journal"]/RECORD', 5)
        self.assert_xml_equal('COMPONENTS/GRID[@name="journal"]/RECORD[@id="2"]/VALUE[@name="name"]', 'Dépense')

        self.factory.xfer = JournalAddModify()
        self.call('/diacamma.accounting/journalAddModify', {'SAVE':'YES', 'name':'Caisse'}, False)
        self.assert_observer('Core.Acknowledge', 'diacamma.accounting', 'journalAddModify')

        self.factory.xfer = Configuration()
        self.call('/diacamma.accounting/configuration', {}, False)
        self.assert_count_equal('COMPONENTS/GRID[@name="journal"]/RECORD', 6)
        self.assert_xml_equal('COMPONENTS/GRID[@name="journal"]/RECORD[@id="6"]/VALUE[@name="name"]', 'Caisse')

        self.factory.xfer = JournalDel()
        self.call('/diacamma.accounting/journalAddModify', {'journal':'2'}, False)
        self.assert_observer('CORE.Exception', 'diacamma.accounting', 'journalAddModify')
        self.assert_xml_equal('EXCEPTION/MESSAGE', 'journal réservé!')

        self.factory.xfer = JournalDel()
        self.call('/diacamma.accounting/journalAddModify', {'CONFIRME':'YES', 'journal':'6'}, False)
        self.assert_observer('Core.Acknowledge', 'diacamma.accounting', 'journalAddModify')

        self.factory.xfer = Configuration()
        self.call('/diacamma.accounting/configuration', {}, False)
        self.assert_count_equal('COMPONENTS/GRID[@name="journal"]/RECORD', 5)

    def test_configuration_fiscalyear(self):
        to_day = date.today()
        to_day_plus_1 = date(to_day.year + 1, to_day.month, to_day.day) - timedelta(days=1)

        self.factory.xfer = FiscalYearAddModify()
        self.call('/diacamma.accounting/fiscalYearAddModify', {}, False)
        self.assert_observer('CORE.Exception', 'diacamma.accounting', 'fiscalYearAddModify')
        self.assert_xml_equal('EXCEPTION/MESSAGE', "Système comptable non défini!")

        set_accounting_system()

        self.factory.xfer = FiscalYearAddModify()
        self.call('/diacamma.accounting/fiscalYearAddModify', {}, False)
        self.assert_observer('Core.Custom', 'diacamma.accounting', 'fiscalYearAddModify')
        self.assert_count_equal('COMPONENTS/*', 7)
        self.assert_xml_equal('COMPONENTS/LABELFORM[@name="status"]', 'en création')
        self.assert_xml_equal('COMPONENTS/DATE[@name="begin"]', to_day.isoformat())
        self.assert_xml_equal('COMPONENTS/DATE[@name="end"]', to_day_plus_1.isoformat())

        self.factory.xfer = FiscalYearAddModify()
        self.call('/diacamma.accounting/fiscalYearAddModify', {'SAVE':'YES', 'begin':'2015-07-01', 'end':'2016-06-30'}, False)
        self.assert_observer('Core.Acknowledge', 'diacamma.accounting', 'fiscalYearAddModify')

        self.factory.xfer = Configuration()
        self.call('/diacamma.accounting/configuration', {}, False)
        self.assert_observer('Core.Custom', 'diacamma.accounting', 'configuration')
        self.assert_count_equal('COMPONENTS/GRID[@name="fiscalyear"]/HEADER', 4)
        self.assert_count_equal('COMPONENTS/GRID[@name="fiscalyear"]/RECORD', 1)
        self.assert_xml_equal('COMPONENTS/GRID[@name="fiscalyear"]/RECORD[1]/VALUE[@name="begin"]', '1 juillet 2015')
        self.assert_xml_equal('COMPONENTS/GRID[@name="fiscalyear"]/RECORD[1]/VALUE[@name="end"]', '30 juin 2016')
        self.assert_xml_equal('COMPONENTS/GRID[@name="fiscalyear"]/RECORD[1]/VALUE[@name="status"]', "en création")
        self.assert_xml_equal('COMPONENTS/GRID[@name="fiscalyear"]/RECORD[1]/VALUE[@name="is_actif"]', "1")
        self.assert_xml_equal('COMPONENTS/LABELFORM[@name="nb"]', 'Nombre total de exercices: 1')

        self.factory.xfer = FiscalYearAddModify()
        self.call('/diacamma.accounting/fiscalYearAddModify', {}, False)
        self.assert_observer('Core.Custom', 'diacamma.accounting', 'fiscalYearAddModify')
        self.assert_count_equal('COMPONENTS/*', 7)
        self.assert_xml_equal("CONTEXT/PARAM[@name='begin']", "2016-07-01")
        self.assert_xml_equal('COMPONENTS/LABELFORM[@name="status"]', 'en création')
        self.assert_xml_equal('COMPONENTS/LABELFORM[@name="begin"]', '1 juillet 2016')
        self.assert_xml_equal('COMPONENTS/DATE[@name="end"]', '2017-06-30')

        self.factory.xfer = FiscalYearAddModify()
        self.call('/diacamma.accounting/fiscalYearAddModify', {'SAVE':'YES', 'begin':'2016-07-01', 'end':'2017-06-30'}, False)
        self.assert_observer('Core.Acknowledge', 'diacamma.accounting', 'fiscalYearAddModify')

        self.factory.xfer = Configuration()
        self.call('/diacamma.accounting/configuration', {}, False)
        self.assert_observer('Core.Custom', 'diacamma.accounting', 'configuration')
        self.assert_count_equal('COMPONENTS/GRID[@name="fiscalyear"]/HEADER', 4)
        self.assert_count_equal('COMPONENTS/GRID[@name="fiscalyear"]/RECORD', 2)
        self.assert_xml_equal('COMPONENTS/GRID[@name="fiscalyear"]/RECORD[2]/VALUE[@name="begin"]', '1 juillet 2016')
        self.assert_xml_equal('COMPONENTS/GRID[@name="fiscalyear"]/RECORD[2]/VALUE[@name="end"]', '30 juin 2017')
        self.assert_xml_equal('COMPONENTS/GRID[@name="fiscalyear"]/RECORD[2]/VALUE[@name="status"]', "en création")
        self.assert_xml_equal('COMPONENTS/GRID[@name="fiscalyear"]/RECORD[2]/VALUE[@name="is_actif"]', "0")
        self.assert_xml_equal('COMPONENTS/LABELFORM[@name="nb"]', 'Nombre total de exercices: 2')

        self.factory.xfer = FiscalYearActive()
        self.call('/diacamma.accounting/fiscalYearActive', {'fiscalyear':'2'}, False)
        self.assert_observer('Core.Acknowledge', 'diacamma.accounting', 'fiscalYearActive')

        self.factory.xfer = Configuration()
        self.call('/diacamma.accounting/configuration', {}, False)
        self.assert_observer('Core.Custom', 'diacamma.accounting', 'configuration')
        self.assert_count_equal('COMPONENTS/GRID[@name="fiscalyear"]/RECORD', 2)
        self.assert_xml_equal('COMPONENTS/GRID[@name="fiscalyear"]/RECORD[1]/VALUE[@name="is_actif"]', "0")
        self.assert_xml_equal('COMPONENTS/GRID[@name="fiscalyear"]/RECORD[2]/VALUE[@name="is_actif"]', "1")

        self.factory.xfer = FiscalYearAddModify()
        self.call('/diacamma.accounting/fiscalYearAddModify', {'fiscalyear':'1'}, False)
        self.assert_observer('CORE.Exception', 'diacamma.accounting', 'fiscalYearAddModify')
        self.assert_xml_equal('EXCEPTION/MESSAGE', "Cet exercice n'est pas le dernier!")

        self.factory.xfer = FiscalYearAddModify()
        self.call('/diacamma.accounting/fiscalYearAddModify', {'fiscalyear':'2'}, False)
        self.assert_observer('Core.Custom', 'diacamma.accounting', 'fiscalYearAddModify')
        self.assert_count_equal('COMPONENTS/*', 7)
        self.assert_xml_equal('COMPONENTS/LABELFORM[@name="status"]', 'en création')
        self.assert_xml_equal('COMPONENTS/LABELFORM[@name="begin"]', '1 juillet 2016')
        self.assert_xml_equal('COMPONENTS/DATE[@name="end"]', '2017-06-30')

    def test_confi_delete(self):
        year1 = FiscalYear.objects.create(begin='2014-07-01', end='2015-06-30', status=2, is_actif=False, last_fiscalyear=None)  # pylint: disable=no-member
        year2 = FiscalYear.objects.create(begin='2015-07-01', end='2016-06-30', status=1, is_actif=False, last_fiscalyear=year1)  # pylint: disable=no-member
        FiscalYear.objects.create(begin='2016-07-01', end='2017-06-30', status=0, is_actif=True, last_fiscalyear=year2)  # pylint: disable=no-member
        set_accounting_system()
        initial_thirds()
        fill_accounts()
        fill_entries(3)

        self.factory.xfer = Configuration()
        self.call('/diacamma.accounting/configuration', {}, False)
        self.assert_observer('Core.Custom', 'diacamma.accounting', 'configuration')
        self.assert_count_equal('COMPONENTS/GRID[@name="fiscalyear"]/RECORD', 3)

        self.factory.xfer = FiscalYearDel()
        self.call('/diacamma.accounting/fiscalYearDel', {'fiscalyear':'1'}, False)
        self.assert_observer('CORE.Exception', 'diacamma.accounting', 'fiscalYearDel')
        self.assert_xml_equal('EXCEPTION/MESSAGE', "Cet exercice n'est pas le dernier!")

        self.factory.xfer = FiscalYearDel()
        self.call('/diacamma.accounting/fiscalYearDel', {'fiscalyear':'2'}, False)
        self.assert_observer('CORE.Exception', 'diacamma.accounting', 'fiscalYearDel')
        self.assert_xml_equal('EXCEPTION/MESSAGE', "Cet exercice n'est pas le dernier!")

        self.factory.xfer = FiscalYearDel()
        self.call('/diacamma.accounting/fiscalYearDel', {'CONFIRME':'YES', 'fiscalyear':'3'}, False)
        self.assert_observer('Core.Acknowledge', 'diacamma.accounting', 'fiscalYearDel')

        self.factory.xfer = Configuration()
        self.call('/diacamma.accounting/configuration', {}, False)
        self.assert_observer('Core.Custom', 'diacamma.accounting', 'configuration')
        self.assert_count_equal('COMPONENTS/GRID[@name="fiscalyear"]/RECORD', 2)

        self.factory.xfer = FiscalYearDel()
        self.call('/diacamma.accounting/fiscalYearDel', {'CONFIRME':'YES', 'fiscalyear':'2'}, False)
        self.assert_observer('Core.Acknowledge', 'diacamma.accounting', 'fiscalYearDel')

        self.factory.xfer = FiscalYearDel()
        self.call('/diacamma.accounting/fiscalYearDel', {'fiscalyear':'1'}, False)
        self.assert_observer('CORE.Exception', 'diacamma.accounting', 'fiscalYearDel')
        self.assert_xml_equal('EXCEPTION/MESSAGE', "Cet exercice est terminé!")

    def test_system_accounting(self):
        self.assertEqual(get_accounting_system('').__class__.__name__, "DefaultSystemAccounting")
        self.assertEqual(get_accounting_system('accountingsystem.foo.DummySystemAcounting').__class__.__name__, "DefaultSystemAccounting")
        self.assertEqual(get_accounting_system('diacamma.accounting.system.french.DummySystemAcounting').__class__.__name__, "DefaultSystemAccounting")
        self.assertEqual(get_accounting_system('diacamma.accounting.system.french.FrenchSystemAcounting').__class__.__name__, "FrenchSystemAcounting")

        self.assertEqual(current_system_account().__class__.__name__, "DefaultSystemAccounting")
        set_accounting_system()
        self.assertEqual(current_system_account().__class__.__name__, "FrenchSystemAcounting")
