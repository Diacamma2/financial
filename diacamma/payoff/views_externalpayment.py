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
from django.http.response import HttpResponseRedirect

from lucterios.framework.tools import MenuManage
from lucterios.framework.xferbasic import XferContainerAbstract

from diacamma.payoff.models import BankTransaction, PaymentMethod, Supporting, Payoff
from diacamma.payoff.payment_type import PaymentType, PaymentTypePayPal
from lucterios.framework.error import LucteriosException, IMPORTANT


class ValidationPaymentGeneric(XferContainerAbstract):
    model = BankTransaction
    field_id = 'banktransaction'
    methods_allowed = ('GET', 'POST', 'PUT')

    def __init__(self, **kwargs):
        XferContainerAbstract.__init__(self, **kwargs)
        self.success = False

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
    def reference(self):
        return ""

    @property
    def bank_fee(self):
        return 0.0

    @property
    def payment_meth(self):
        return PaymentMethod(paytype=PaymentType.num, extra_data="")

    def fillresponse(self):
        try:
            self.item.contains = ""
            self.item.payer = self.payer
            self.item.amount = self.amount
            self.item.date = self.date
            if self.confirm():
                bank_account = self.payment_meth.bank_account
                if bank_account is None:
                    raise LucteriosException(IMPORTANT, "No account!")
                support = Supporting.objects.get(id=self.customid)
                new_payoff = Payoff()
                new_payoff.supporting = support.get_final_child().support_validated(self.item.date)
                new_payoff.date = self.item.date
                new_payoff.amount = self.item.amount
                new_payoff.payer = self.item.payer
                new_payoff.mode = Payoff.MODE_TRANSFER
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


class CheckPaymentGeneric(XferContainerAbstract):
    caption = _("Payment")
    icon = "payments.png"
    readonly = True
    methods_allowed = ('GET', )

    payment_name = ""

    @property
    def payid(self):
        return 0

    @property
    def payment_meth(self):
        return None

    def request_handling(self, request, *args, **kwargs):
        self._initialize(request, *args, **kwargs)
        root_url = self.getparam("url", self.request.META.get('HTTP_REFERER', self.request.build_absolute_uri()))
        try:
            support = Supporting.objects.get(id=self.payid).get_final_child()
            return HttpResponseRedirect(self.payment_meth.paymentType.get_redirect_url(root_url, self.language, support))
        except Exception:
            logging.getLogger('diacamma.payoff').exception("CheckPayment")
            from django.shortcuts import render
            dictionary = {}
            dictionary['title'] = str(settings.APPLIS_NAME)
            dictionary['subtitle'] = settings.APPLIS_SUBTITLE()
            dictionary['applogo'] = settings.APPLIS_LOGO
            dictionary['content1'] = _("It is not possible to pay-off this item with %s !") % self.payment_name
            dictionary['content2'] = _("This item is deleted, payed or disabled.")
            return render(request, 'info.html', context=dictionary)


@MenuManage.describ('')
class CheckPaymentPaypal(CheckPaymentGeneric):

    payment_name = "PayPal"

    @property
    def payid(self):
        return self.getparam("payid", 0)

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
        paypal_url = getattr(settings, 'DIACAMMA_PAYOFF_PAYPAL_URL', 'https://www.paypal.com/cgi-bin/webscr')
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
