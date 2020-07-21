# -*- coding: utf-8 -*-
'''
@author: Laurent GAY
@organization: sd-libre.fr
@contact: info@sd-libre.fr
@copyright: 2020 sd-libre.fr
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
from django.conf import settings
from django.utils.translation import ugettext_lazy as _

from lucterios.framework.tools import get_bool_textual
from lucterios.framework.error import LucteriosException, IMPORTANT
from lucterios.framework.filetools import remove_accent
from lucterios.CORE.parameters import Params

from lucterios.contacts.models import LegalEntity


class PaymentType(object):

    name = ''

    def __init__(self, extra_data):
        self.extra_data = extra_data

    def get_extra_fields(self):
        return []

    def get_default_items(self):
        items = self.extra_data.split("\n")
        return items

    def get_items(self):
        items = self.get_default_items()
        size = len(self.get_extra_fields())
        while len(items) < size:
            items.append("")
        return items

    def get_info(self):
        res = ""
        items = self.get_items()
        for fieldid, fieldtitle, fieldtype in self.get_extra_fields():
            res += "{[b]}%s{[/b]}{[br/]}" % fieldtitle
            if fieldtype == 2:
                res += str(get_bool_textual((items[fieldid - 1] == 'o') or (items[fieldid - 1] == 'True')))
            else:
                res += items[fieldid - 1]
            res += "{[br/]}"
        return res

    def set_items(self, items):
        size = len(self.get_extra_fields())
        while len(items) < size:
            items.append("")
        self.extra_data = "\n".join(items)

    def show_pay(self, absolute_uri, lang, supporting):
        return ""


class PaymentTypeTransfer(PaymentType):
    name = _('transfer')

    def get_extra_fields(self):
        return [(1, _('IBAN'), 0), (2, _('BIC'), 0)]

    def show_pay(self, absolute_uri, lang, supporting):
        items = self.get_items()
        formTxt = "{[center]}"
        formTxt += "{[table width='100%']}{[tr]}"
        formTxt += "    {[td]}{[u]}{[i]}%s{[/i]}{[/u]}{[/td]}" % _('IBAN')
        formTxt += "    {[td]}%s{[/td]}" % items[0]
        formTxt += "{[/tr]}{[tr]}"
        formTxt += "    {[td]}{[u]}{[i]}%s{[/i]}{[/u]}{[/td]}" % _('BIC')
        formTxt += "    {[td]}%s{[/td]}" % items[1]
        formTxt += "{[/tr]}{[/table]}"
        formTxt += "{[/center]}"
        return formTxt


class PaymentTypeCheque(PaymentType):
    name = _('cheque')

    def get_extra_fields(self):
        return [(1, _('payable to'), 0), (2, _('address'), 1)]

    def get_default_items(self):
        if (self.extra_data == ''):
            current_legal = LegalEntity.objects.get(id=1)
            items = [current_legal.name, "%s{[newline]}%s %s" % (current_legal.address, current_legal.postal_code, current_legal.city)]
        else:
            items = self.extra_data.split("\n")
        return items

    def show_pay(self, absolute_uri, lang, supporting):
        items = self.get_items()
        formTxt = "{[center]}"
        formTxt += "{[table width='100%%']}"
        formTxt += "    {[tr]}"
        formTxt += "        {[td]}{[u]}{[i]}%s{[/i]}{[/u]}{[/td]}" % _('payable to')
        formTxt += "        {[td]}%s{[/td]}" % items[0]
        formTxt += "    {[/tr]}"
        formTxt += "    {[tr]}"
        formTxt += "        {[td]}{[u]}{[i]}%s{[/i]}{[/u]}{[/td]}" % _('address')
        formTxt += "        {[td]}%s{[/td]}" % items[1]
        formTxt += "    {[/tr]}"
        formTxt += "{[/table]}"
        formTxt += "{[/center]}"
        return formTxt


class PaymentTypePayPal(PaymentType):
    name = _('PayPal')

    def get_extra_fields(self):
        return [(1, _('Paypal account'), r"^[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+$"), (2, _('With control'), 2)]

    def get_paypal_dict(self, absolute_uri, lang, supporting):
        from urllib.parse import quote_plus
        if abs(supporting.get_payable_without_tax()) < 0.0001:
            raise LucteriosException(IMPORTANT, _("This item can't be validated!"))
        abs_url = absolute_uri.split('/')
        items = self.get_items()
        paypal_dict = {}
        paypal_dict['business'] = items[0]
        paypal_dict['currency_code'] = Params.getvalue("accounting-devise-iso")
        paypal_dict['lc'] = lang
        paypal_dict['return'] = '/'.join(abs_url[:-2])
        paypal_dict['cancel_return'] = '/'.join(abs_url[:-2])
        paypal_dict['notify_url'] = paypal_dict['return'] + '/diacamma.payoff/validationPaymentPaypal'
        paypal_dict['item_name'] = remove_accent(supporting.get_payment_name())
        paypal_dict['custom'] = str(supporting.id)
        paypal_dict['tax'] = str(supporting.get_tax())
        paypal_dict['amount'] = str(supporting.get_payable_without_tax())
        paypal_dict['cmd'] = '_xclick'
        paypal_dict['no_note'] = '1'
        paypal_dict['no_shipping'] = '1'
        args = ""
        for key, val in paypal_dict.items():
            args += "&%s=%s" % (key, quote_plus(val))
        return args[1:]

    def show_pay(self, absolute_uri, lang, supporting):
        items = self.get_items()
        abs_url = absolute_uri.split('/')
        root_url = '/'.join(abs_url[:-2])
        if (items[1] == 'o') or (items[1] == 'True'):
            import urllib.parse
            formTxt = "{[center]}"
            formTxt += "{[a href='%s/%s?payid=%d&url=%s' target='_blank']}" % (root_url, 'diacamma.payoff/checkPaymentPaypal',
                                                                               supporting.id, urllib.parse.quote(root_url + '/diacamma.payoff/checkPaymentPaypal'))
            formTxt += "{[img src='%s/static/diacamma.payoff/images/pp_cc_mark_74x46.jpg' title='PayPal' alt='PayPal' /]}" % root_url
            formTxt += "{[/a]}"
            formTxt += "{[/center]}"
        else:
            paypal_url = getattr(settings, 'DIACAMMA_PAYOFF_PAYPAL_URL', 'https://www.paypal.com/cgi-bin/webscr')
            paypal_dict = self.get_paypal_dict(absolute_uri, lang, supporting)
            formTxt = "{[center]}"
            formTxt += "{[a href='%s?%s' target='_blank']}" % (paypal_url, paypal_dict)
            formTxt += "{[img src='%s/static/diacamma.payoff/images/pp_cc_mark_74x46.jpg' title='PayPal' alt='PayPal' /]}" % root_url
            formTxt += "{[/a]}"
            formTxt += "{[/center]}"
        return formTxt


class PaymentTypeOnline(PaymentType):
    name = _('online')

    def get_extra_fields(self):
        return [(1, _('web address'), r"^(?:http(s)?:\/\/)?[\w.-]+(?:\.[\w\.-]+)+[\w\-\._~:/?#[\]@!\$&'\(\)\*\+,;=.]+$"), (2, _('info'), 1)]

    def show_pay(self, absolute_uri, lang, supporting):
        items = self.get_items()
        formTxt = "{[center]}"
        formTxt += "{[table width='100%%']}"
        formTxt += "    {[tr]}"
        formTxt += "        {[td]}{[u]}{[i]}%s{[/i]}{[/u]}{[/td]}" % _('web address')
        formTxt += "        {[td]}{[a href='%s' target='_blank']}%s{[/a]}{[/td]}" % (items[0], items[0])
        formTxt += "    {[/tr]}"
        formTxt += "    {[tr]}"
        formTxt += "        {[td]}{[u]}{[i]}%s{[/i]}{[/u]}{[/td]}" % _('info')
        formTxt += "        {[td]}%s{[/td]}" % items[1]
        formTxt += "    {[/tr]}"
        formTxt += "{[/table]}"
        formTxt += "{[/center]}"
        return formTxt


PAYMENTTYPE_LIST = (PaymentTypeTransfer, PaymentTypeCheque, PaymentTypePayPal, PaymentTypeOnline)
