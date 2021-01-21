# -*- coding: utf-8 -*-
'''
diacamma.payoff views package

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
from datetime import datetime, timedelta
import logging

from django.utils import timezone
from django.conf import settings
from django.utils.translation import ugettext_lazy as _
from django.http.response import HttpResponse
from django.core.exceptions import ObjectDoesNotExist

from lucterios.framework.tools import MenuManage, toHtml
from lucterios.framework.xferbasic import XferContainerAbstract
from lucterios.framework.error import LucteriosException, IMPORTANT

from diacamma.payoff.models import BankTransaction, PaymentMethod, Supporting, Payoff
from diacamma.payoff.payment_type import PaymentType, PaymentTypePayPal, PaymentTypeMoneticoPaiement


class ValidationPaymentGeneric(XferContainerAbstract):
    model = BankTransaction
    field_id = 'banktransaction'
    methods_allowed = ('GET', 'POST', 'PUT')

    def __init__(self, **kwargs):
        XferContainerAbstract.__init__(self, **kwargs)
        self.success = False
        self.reponse_content = b''

    @property
    def payer(self):
        return ""

    @property
    def amount(self):
        return 0.0

    @property
    def date(self):
        return timezone.now()

    def confirm(self):
        return True

    @property
    def customid(self):
        return 0

    @property
    def supporting(self):
        if not hasattr(self, '_supporting'):
            try:
                self._supporting = Supporting.objects.get(id=self.customid).get_final_child()
            except ObjectDoesNotExist:
                self._supporting = None
        return self._supporting

    @property
    def reference(self):
        return ""

    @property
    def bank_fee(self):
        return 0.0

    @property
    def payment_meth(self):
        return PaymentMethod(paytype=PaymentType.num, extra_data="")

    def fillresponse(self):
        if self.supporting is None:
            return
        try:
            self.item.contains = ""
            self.item.payer = self.payer
            self.item.amount = self.amount
            self.item.date = self.date
            if self.confirm():
                bank_account = self.payment_meth.bank_account
                if bank_account is None:
                    raise LucteriosException(IMPORTANT, "No account!")
                new_payoff = Payoff()
                new_payoff.supporting = self.supporting.support_validated(self.item.date)
                new_payoff.date = self.item.date
                new_payoff.amount = self.item.amount
                new_payoff.payer = self.item.payer
                new_payoff.mode = Payoff.MODE_CREDITCARD
                new_payoff.bank_account = bank_account
                new_payoff.reference = self.reference
                new_payoff.bank_fee = self.bank_fee
                new_payoff.save()
                self.item.status = BankTransaction.STATUS_SUCCESS
                self.success = True
        except Exception as err:
            logging.getLogger('diacamma.payoff').exception("ValidationPayment")
            self.item.contains += "{[newline]}"
            self.item.contains += str(err)
        self.item.save()

    def get_response(self):
        if self.supporting is None:
            from django.shortcuts import render
            dictionary = {}
            dictionary['title'] = str(settings.APPLIS_NAME)
            dictionary['subtitle'] = settings.APPLIS_SUBTITLE()
            dictionary['applogo'] = settings.APPLIS_LOGO.decode()
            if self.getparam('ret', 'none') == 'OK':
                dictionary['content1'] = _("Payoff terminate.")
                dictionary['content2'] = _("Thanks you.")
            else:
                dictionary['content1'] = _("Payoff aborded.")
                dictionary['content2'] = ''
            return render(self.request, 'info.html', context=dictionary)
        else:
            return HttpResponse(self.reponse_content)


class CheckPaymentGeneric(XferContainerAbstract):
    caption = _("Payment")
    icon = "payments.png"
    readonly = True
    methods_allowed = ('GET', )

    payment_name = ""

    @property
    def payid(self):
        return self.getparam("payid", 0)

    @property
    def payment_meth(self):
        return None

    def request_handling(self, request, *args, **kwargs):
        from django.shortcuts import render
        dictionary = {}
        dictionary['title'] = str(settings.APPLIS_NAME)
        dictionary['subtitle'] = settings.APPLIS_SUBTITLE()
        dictionary['applogo'] = settings.APPLIS_LOGO.decode()
        self._initialize(request, *args, **kwargs)
        absolute_uri = self.getparam("url", self.request.META.get('HTTP_REFERER', self.request.build_absolute_uri()))
        try:
            support = Supporting.objects.get(id=self.payid).get_final_child()
            dictionary['content1'] = ''
            dictionary['content2'] = toHtml(self.payment_meth.paymentType.get_form(absolute_uri, self.language, support), withclean=False)
        except Exception:
            logging.getLogger('diacamma.payoff').exception("CheckPayment")
            dictionary['content1'] = _("It is not possible to pay-off this item with %s !") % self.payment_name
            dictionary['content2'] = _("This item is deleted, payed or disabled.")
        return render(request, 'info.html', context=dictionary)


@MenuManage.describ('')
class CheckPaymentPaypal(CheckPaymentGeneric):

    payment_name = "PayPal"

    @property
    def payment_meth(self):
        return PaymentMethod.objects.filter(paytype=PaymentTypePayPal.num).first()


@MenuManage.describ('')
class ValidationPaymentPaypal(ValidationPaymentGeneric):
    observer_name = 'PayPal'
    caption = 'ValidationPaymentPaypal'

    @property
    def payer(self):
        return self.getparam('first_name', '') + " " + self.getparam('last_name', '')

    @property
    def amount(self):
        return self.getparam('mc_gross', 0.0)

    @property
    def date(self):
        import locale
        saved = locale.setlocale(locale.LC_ALL)
        locale.setlocale(locale.LC_ALL, 'en_US.UTF-8')
        try:
            payoff_date = datetime.strptime(self.getparam("payment_date", '').replace('PDT', 'GMT'), '%H:%M:%S %b %d, %Y %Z')
            payoff_date += timedelta(hours=7)
            return timezone.make_aware(payoff_date)
        except Exception:
            logging.getLogger('diacamma.payoff').exception("problem of date %s" % self.getparam("payment_date", ''))
            return timezone.now()
        finally:
            locale.setlocale(locale.LC_ALL, saved)

    def confirm(self):
        from urllib.parse import quote_plus
        from requests import post
        paypal_url = PaymentTypePayPal.get_url("")
        fields = 'cmd=_notify-validate'
        try:
            for key, value in self.request.POST.items():
                fields += "&%s=%s" % (key, quote_plus(value))
                if key != 'FORMAT':
                    self.item.contains += "%s = %s{[newline]}" % (key, value)
            res = post(paypal_url, data=fields.encode(), headers={"Content-Type": "application/x-www-form-urlencoded", 'Content-Length': str(len(fields))}).text
        except Exception:
            logging.getLogger('diacamma.payoff').warning(paypal_url)
            logging.getLogger('diacamma.payoff').warning(fields)
            raise
        if res == 'VERIFIED':
            return True
        elif res == 'INVALID':
            self.item.contains += "{[newline]}--- INVALID ---{[newline]}"
            return False
        else:
            self.item.contains += "{[newline]}"
            if res != 'VERIFIED':
                self.item.contains += "NO VALID:"
            self.item.contains += res.replace('\n', '{[newline]}')
            return False

    @property
    def payment_meth(self):
        for payment_meth in PaymentMethod.objects.filter(paytype=PaymentTypePayPal.num):
            if payment_meth.get_items()[0] == self.getparam('receiver_email', ''):
                return payment_meth
        return PaymentMethod(paytype=PaymentType.num, extra_data="")

    @property
    def customid(self):
        return self.getparam('custom', 0)

    @property
    def reference(self):
        return "PayPal " + self.getparam('txn_id', '')

    @property
    def bank_fee(self):
        return self.getparam('mc_fee', 0.0)


@MenuManage.describ('')
class CheckPaymentMoneticoPaiement(CheckPaymentGeneric):

    payment_name = "MoneticoPaiement"

    @property
    def payment_meth(self):
        return PaymentMethod.objects.filter(paytype=PaymentTypeMoneticoPaiement.num).first()


@MenuManage.describ('')
class ValidationPaymentMoneticoPaiement(ValidationPaymentGeneric):
    observer_name = 'MoneticoPaiement'
    caption = 'ValidationPaymentMoneticoPaiement'

    @property
    def payer(self):
        return str(self.supporting.third)

    @property
    def amount(self):
        return float(self.getparam('montant', '0EUR')[:-3])

    @property
    def date(self):
        try:
            payoff_date = datetime.strptime(self.getparam("date", ''), '%d/%m/%Y_a_%H:%M:%S')
            return timezone.make_aware(payoff_date)
        except Exception:
            logging.getLogger('diacamma.payoff').exception("problem of date %s" % self.getparam("date", ''))
            return timezone.now()

    def confirm(self):
        try:
            parameters = {key: value[0] if isinstance(value, list) else value for key, value in self.request.POST.items()}
            for key, value in parameters.items():
                if key != 'MAC':
                    self.item.contains += "%s = %s{[newline]}" % (key, value)
            if self.payment_meth.paymentType.is_valid_mac(parameters):
                code_retour = parameters['code-retour']
                res = (code_retour.lower() != 'annulation')
                if not res:
                    self.item.contains += "{[newline]}--- NO VALID ---{[newline]}"
            else:
                self.item.contains += "{[newline]}--- INVALID ---{[newline]}"
                res = False
        except Exception:
            logging.getLogger('diacamma.payoff').warning(parameters)
            raise
        if res:
            self.reponse_content = b"version=2\ncdr=0\n"
        else:
            self.reponse_content = b"version=2\ncdr=1\n"
        return res

    @property
    def payment_meth(self):
        return PaymentMethod.objects.filter(paytype=PaymentTypeMoneticoPaiement.num).first()

    @property
    def customid(self):
        return int(self.getparam('reference', 'REF0000000')[3:])

    @property
    def reference(self):
        return "MoneticoPaiement " + self.getparam('numauto', '')

    @property
    def bank_fee(self):
        return 0.0
