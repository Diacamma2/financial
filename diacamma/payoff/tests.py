# -*- coding: utf-8 -*-
'''
diacamma.payoff tests package

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

from lucterios.framework.test import LucteriosTest
from lucterios.framework.filetools import get_user_dir

from lucterios.contacts.tests_contacts import change_ourdetail

from diacamma.payoff.views_conf import PayoffConf, BankAccountAddModify,\
    BankAccountDelete, PaymentMethodAddModify
from diacamma.accounting.test_tools import default_compta_fr


class PayoffTest(LucteriosTest):

    def setUp(self):
        LucteriosTest.setUp(self)
        rmtree(get_user_dir(), True)
        change_ourdetail()
        default_compta_fr()

    def test_bank(self):
        self.factory.xfer = PayoffConf()
        self.calljson('/diacamma.payoff/payoffConf', {}, False)
        self.assert_observer('core.custom', 'diacamma.payoff', 'payoffConf')
        self.assertTrue('__tab_3' in self.json_data.keys(), self.json_data.keys())
        self.assert_count_equal('', 2 + 3 + 2 + 5)

        self.assert_grid_equal('bankaccount', {'order_key': 'ordre', 'designation': "désignation", 'reference': "référence", 'account_code': "compte bancaire", 'temporary_account_code': "compte d'attente", 'fee_account_code': 'imputation des frais'}, 0)

        self.factory.xfer = BankAccountAddModify()
        self.calljson('/diacamma.payoff/bankAccountAddModify', {}, False)
        self.assert_observer('core.custom', 'diacamma.payoff', 'bankAccountAddModify')
        self.assert_count_equal('', 9)

        self.factory.xfer = BankAccountAddModify()
        self.calljson('/diacamma.payoff/bankAccountAddModify',
                      {'designation': 'My bank', 'reference': '0123 456789 654 12', 'account_code': '512', 'bank_journal': 4, 'temporary_account_code': '', 'temporary_journal': 4,
                       'fee_account_code': '', 'is_disabled': 0, 'SAVE': 'YES'}, False)
        self.assert_observer('core.acknowledge', 'diacamma.payoff', 'bankAccountAddModify')

        self.factory.xfer = PayoffConf()
        self.calljson('/diacamma.payoff/payoffConf', {'show_only_enabled_bank': True}, False)
        self.assert_count_equal('bankaccount', 1)
        self.assert_json_equal('', 'bankaccount/@0/id', '1')
        self.assert_json_equal('', 'bankaccount/@0/designation', 'My bank')
        self.assert_json_equal('', 'bankaccount/@0/reference', '0123 456789 654 12')
        self.assert_json_equal('', 'bankaccount/@0/account_code', '512')
        self.assert_json_equal('', 'bankaccount/@0/temporary_account_code', '')
        self.assert_json_equal('', 'bankaccount/@0/fee_account_code', '')

        self.factory.xfer = BankAccountAddModify()
        self.calljson('/diacamma.payoff/bankAccountAddModify',
                      {'bankaccount': 1, 'designation': 'My bank', 'reference': '0123 456789 654 12', 'account_code': '512', 'bank_journal': 4, 'temporary_account_code': '', 'temporary_journal': 4,
                       'fee_account_code': '', 'is_disabled': 1, 'SAVE': 'YES'}, False)
        self.assert_observer('core.acknowledge', 'diacamma.payoff', 'bankAccountAddModify')

        self.factory.xfer = PayoffConf()
        self.calljson('/diacamma.payoff/payoffConf', {}, False)
        self.assert_count_equal('bankaccount', 0)

        self.factory.xfer = PayoffConf()
        self.calljson('/diacamma.payoff/payoffConf', {'show_only_enabled_bank': False}, False)
        self.assert_count_equal('bankaccount', 1)

        self.factory.xfer = BankAccountDelete()
        self.calljson('/diacamma.payoff/bankAccountDelete',
                      {'bankaccount': 1, 'CONFIRME': 'YES'}, False)
        self.assert_observer('core.acknowledge', 'diacamma.payoff', 'bankAccountDelete')

        self.factory.xfer = PayoffConf()
        self.calljson('/diacamma.payoff/payoffConf', {}, False)
        self.assert_count_equal('bankaccount', 0)

        self.factory.xfer = BankAccountAddModify()
        self.calljson('/diacamma.payoff/bankAccountAddModify',
                      {'designation': 'My bank', 'reference': '0123 456789 654 12', 'account_code': '512', 'bank_journal': 4, 'temporary_account_code': '581', 'temporary_journal': 5,
                       'fee_account_code': '627', 'is_disabled': 0, 'SAVE': 'YES'}, False)
        self.assert_observer('core.acknowledge', 'diacamma.payoff', 'bankAccountAddModify')

        self.factory.xfer = PayoffConf()
        self.calljson('/diacamma.payoff/payoffConf', {'show_only_enabled_bank': True}, False)
        self.assert_count_equal('bankaccount', 1)
        self.assert_json_equal('', 'bankaccount/@0/id', '2')
        self.assert_json_equal('', 'bankaccount/@0/designation', 'My bank')
        self.assert_json_equal('', 'bankaccount/@0/reference', '0123 456789 654 12')
        self.assert_json_equal('', 'bankaccount/@0/account_code', '512')
        self.assert_json_equal('', 'bankaccount/@0/temporary_account_code', '581')
        self.assert_json_equal('', 'bankaccount/@0/fee_account_code', '627')

    def test_method(self):
        self.factory.xfer = BankAccountAddModify()
        self.calljson('/diacamma.payoff/bankAccountAddModify',
                      {'designation': 'My bank', 'reference': '0123 456789 654 12', 'account_code': '512', 'SAVE': 'YES'}, False)

        self.factory.xfer = PayoffConf()
        self.calljson('/diacamma.payoff/payoffConf', {}, False)
        self.assert_observer('core.custom', 'diacamma.payoff', 'payoffConf')
        self.assertTrue('__tab_3' in self.json_data.keys(), self.json_data.keys())
        self.assert_count_equal('', 2 + 3 + 2 + 5)
        self.assert_grid_equal('paymentmethod', {'paytype': "type", 'bank_account': "compte bancaire", 'info': "paramètres"}, 0)

        self.factory.xfer = PaymentMethodAddModify()
        self.calljson('/diacamma.payoff/paymentMethodAddModify', {}, False)
        self.assert_observer('core.custom', 'diacamma.payoff', 'paymentMethodAddModify')
        self.assert_count_equal('', 5)
        self.assert_select_equal('bank_account', 1)  # nb=1
        self.assert_attrib_equal('item_1', 'description', 'IBAN')
        self.assert_json_equal('EDIT', 'item_1', '')
        self.assert_attrib_equal('item_2', 'description', 'BIC')
        self.assert_json_equal('EDIT', 'item_2', '')

        self.factory.xfer = PaymentMethodAddModify()
        self.calljson('/diacamma.payoff/paymentMethodAddModify', {'paytype': 0}, False)
        self.assert_observer('core.custom', 'diacamma.payoff', 'paymentMethodAddModify')
        self.assert_count_equal('', 5)
        self.assert_attrib_equal('item_1', 'description', 'IBAN')
        self.assert_json_equal('EDIT', 'item_1', '')
        self.assert_attrib_equal('item_2', 'description', 'BIC')
        self.assert_json_equal('EDIT', 'item_2', '')

        self.factory.xfer = PaymentMethodAddModify()
        self.calljson('/diacamma.payoff/paymentMethodAddModify', {'paytype': 1}, False)
        self.assert_observer('core.custom', 'diacamma.payoff', 'paymentMethodAddModify')
        self.assert_count_equal('', 5)
        self.assert_attrib_equal('item_1', 'description', "à l'ordre de")
        self.assert_json_equal('EDIT', 'item_1', "WoldCompany")
        self.assert_attrib_equal('item_2', 'description', 'adresse')
        self.assert_json_equal('MEMO', 'item_2', "Place des cocotiers{[newline]}97200 FORT DE FRANCE")

        self.factory.xfer = PaymentMethodAddModify()
        self.calljson('/diacamma.payoff/paymentMethodAddModify', {'paytype': 2}, False)
        self.assert_observer('core.custom', 'diacamma.payoff', 'paymentMethodAddModify')
        self.assert_count_equal('', 5)
        self.assert_attrib_equal('item_1', 'description', 'compte Paypal')
        self.assert_json_equal('EDIT', 'item_1', '')
        self.assert_attrib_equal('item_2', 'description', 'avec contrôle')
        self.assert_json_equal('CHECK', 'item_2', '0')

        self.factory.xfer = PaymentMethodAddModify()
        self.calljson('/diacamma.payoff/paymentMethodAddModify', {'paytype': 3}, False)
        self.assert_observer('core.custom', 'diacamma.payoff', 'paymentMethodAddModify')
        self.assert_count_equal('', 5)
        self.assert_attrib_equal('item_1', 'description', 'adresse web')
        self.assert_json_equal('EDIT', 'item_1', '')
        self.assert_attrib_equal('item_2', 'description', 'information')
        self.assert_json_equal('MEMO', 'item_2', '')

        self.factory.xfer = PaymentMethodAddModify()
        self.calljson('/diacamma.payoff/paymentMethodAddModify',
                      {'paytype': 0, 'bank_account': 1, 'item_1': '123456798', 'item_2': 'AADDVVCC', 'SAVE': 'YES'}, False)
        self.assert_observer('core.acknowledge', 'diacamma.payoff', 'paymentMethodAddModify')

        self.factory.xfer = PaymentMethodAddModify()
        self.calljson('/diacamma.payoff/paymentMethodAddModify',
                      {'paytype': 1, 'bank_account': 1, 'item_1': 'Truc', 'item_2': '1 rue de la Paix{[newline]}99000 LA-BAS', 'SAVE': 'YES'}, False)
        self.assert_observer('core.acknowledge', 'diacamma.payoff', 'paymentMethodAddModify')

        self.factory.xfer = PaymentMethodAddModify()
        self.calljson('/diacamma.payoff/paymentMethodAddModify',
                      {'paytype': 2, 'bank_account': 1, 'item_1': 'monney@truc.org', 'item_2': 'o', 'SAVE': 'YES'}, False)
        self.assert_observer('core.acknowledge', 'diacamma.payoff', 'paymentMethodAddModify')

        self.factory.xfer = PaymentMethodAddModify()
        self.calljson('/diacamma.payoff/paymentMethodAddModify',
                      {'paytype': 3, 'bank_account': 1, 'item_1': 'http://payement.online.com', 'item_2': 'Précisez le N° de devis ou de facture', 'SAVE': 'YES'}, False)
        self.assert_observer('core.acknowledge', 'diacamma.payoff', 'paymentMethodAddModify')

        self.factory.xfer = PaymentMethodAddModify()
        self.calljson('/diacamma.payoff/paymentMethodAddModify',
                      {'paytype': 4, 'bank_account': 1, 'item_1': '7979879878', 'item_2': 'ababab', 'item_3': '12345678901234567890', 'SAVE': 'YES'}, False)
        self.assert_observer('core.acknowledge', 'diacamma.payoff', 'paymentMethodAddModify')

        self.factory.xfer = PayoffConf()
        self.calljson('/diacamma.payoff/payoffConf', {}, False)
        self.assert_observer('core.custom', 'diacamma.payoff', 'payoffConf')
        self.assert_count_equal('paymentmethod', 5)
        self.assert_json_equal('', '#paymentmethod/headers/@0/@0', 'paytype')
        self.assert_json_equal('', '#paymentmethod/headers/@0/@1', 'type')
        self.assert_json_equal('', '#paymentmethod/headers/@0/@2', {'0': 'virement', '1': 'chèque', '2': 'PayPal', '3': 'en ligne', '4': 'MoneticoPaiement'})
        self.assert_json_equal('', '#paymentmethod/headers/@0/@4', "%s")

        self.assert_json_equal('', 'paymentmethod/@0/paytype', 0)
        self.assert_json_equal('', 'paymentmethod/@0/bank_account', "My bank")
        self.assert_json_equal('', 'paymentmethod/@0/info', '{[b]}IBAN{[/b]}{[br/]}123456798{[br/]}{[b]}BIC{[/b]}{[br/]}AADDVVCC{[br/]}')

        self.assert_json_equal('', 'paymentmethod/@1/paytype', 1)
        self.assert_json_equal('', 'paymentmethod/@1/bank_account', "My bank")
        self.assert_json_equal('', 'paymentmethod/@1/info', "{[b]}à l'ordre de{[/b]}{[br/]}Truc{[br/]}", True)

        self.assert_json_equal('', 'paymentmethod/@2/paytype', 2)
        self.assert_json_equal('', 'paymentmethod/@2/bank_account', "My bank")
        self.assert_json_equal('', 'paymentmethod/@2/info', '{[b]}compte Paypal{[/b]}{[br/]}monney@truc.org{[br/]}{[b]}avec contrôle{[/b]}{[br/]}Oui{[br/]}')

        self.assert_json_equal('', 'paymentmethod/@3/paytype', 3)
        self.assert_json_equal('', 'paymentmethod/@3/bank_account', "My bank")
        self.assert_json_equal('', 'paymentmethod/@3/info', '{[b]}adresse web{[/b]}{[br/]}http://payement.online.com{[br/]}{[b]}information{[/b]}{[br/]}Précisez le N° de devis ou de facture{[br/]}')

        self.assert_json_equal('', 'paymentmethod/@4/paytype', 4)
        self.assert_json_equal('', 'paymentmethod/@4/bank_account', "My bank")
        self.assert_json_equal('', 'paymentmethod/@4/info', '{[b]}code d\'entreprise{[/b]}{[br/]}7979879878{[br/]}{[b]}code TPE{[/b]}{[br/]}ababab{[br/]}{[b]}clef de sécuritée{[/b]}{[br/]}12345678901234567890{[br/]}')
