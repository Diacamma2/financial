# -*- coding: utf-8 -*-
'''
diacamma.invoice view package

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
from datetime import date

from django.utils.translation import ugettext_lazy as _
from django.utils import formats
from django.db.models.functions import Concat
from django.db.models import Q, Value
from django.db.models.aggregates import Sum, Count
from django.db.models.query import QuerySet

from lucterios.framework.xferadvance import TITLE_PRINT, TITLE_CLOSE, TITLE_DELETE, TITLE_MODIFY, TITLE_ADD, TITLE_CANCEL, TITLE_OK, TITLE_EDIT,\
    TITLE_LABEL, TITLE_CREATE
from lucterios.framework.xferadvance import XferListEditor, XferShowEditor, XferAddEditor, XferDelete, XferTransition
from lucterios.framework.xfercomponents import XferCompLabelForm, XferCompSelect, XferCompImage, XferCompGrid, XferCompCheck, XferCompEdit, XferCompCheckList, XferCompMemo,\
    XferCompButton
from lucterios.framework.tools import FORMTYPE_NOMODAL, ActionsManage, MenuManage, FORMTYPE_MODAL, CLOSE_YES, SELECT_SINGLE, FORMTYPE_REFRESH, CLOSE_NO, SELECT_MULTI, WrapAction,\
    get_format_from_field
from lucterios.framework.xfergraphic import XferContainerAcknowledge, XferContainerCustom
from lucterios.framework.error import LucteriosException, IMPORTANT
from lucterios.framework import signal_and_lock
from lucterios.framework.xfersearch import get_criteria_list, get_search_query_from_criteria
from lucterios.framework.xferprinting import XferContainerPrint
from lucterios.framework.model_fields import get_value_if_choices

from lucterios.CORE.xferprint import XferPrintAction, XferPrintListing, XferPrintLabel
from lucterios.CORE.parameters import Params
from lucterios.CORE.editors import XferSavedCriteriaSearchEditor
from lucterios.CORE.models import PrintModel, SavedCriteria, Preference
from lucterios.CORE.views import ObjectMerge

from lucterios.contacts.views_contacts import AbstractContactFindDouble
from lucterios.contacts.models import Individual, LegalEntity

from diacamma.invoice.models import Article, Bill, Detail, Category, Provider, StorageArea, AutomaticReduce
from diacamma.payoff.views import PayoffAddModify, PayableEmail, can_send_email, SupportingPrint
from diacamma.payoff.models import Payoff, DepositSlip
from diacamma.accounting.models import FiscalYear, Third, EntryLineAccount, EntryAccount
from diacamma.accounting.views import get_main_third
from diacamma.accounting.views_entries import EntryAccountOpenFromLine
from diacamma.accounting.tools import current_system_account, format_with_devise, get_amount_from_format_devise

MenuManage.add_sub("invoice", None, "diacamma.invoice/images/invoice.png", _("Invoice"), _("Manage of billing"), 45)


def _add_bill_filter(xfer, row, with_third=False):
    current_filter = Q()
    if with_third:
        third_filter = xfer.getparam('filter', '')
        comp = XferCompEdit('filter')
        comp.set_value(third_filter)
        comp.is_default = True
        comp.description = _('Filtrer by third')
        comp.set_action(xfer.request, xfer.return_action(), modal=FORMTYPE_REFRESH, close=CLOSE_NO)
        comp.set_location(0, row)
        xfer.add_component(comp)
        row += 1
        if third_filter != "":
            q_legalentity = Q(third__contact__legalentity__name__icontains=third_filter)
            # annotate(completename=Concat('third__contact__individual__lastname', Value(' '), 'third__contact__individual__firstname'))
            q_individual = Q(completename__icontains=third_filter)
            current_filter &= (q_legalentity | q_individual)
    status_filter = xfer.getparam('status_filter', Preference.get_value("invoice-status", xfer.request.user))
    xfer.params['status_filter'] = status_filter
    edt = XferCompSelect("status_filter")
    edt.set_select(Bill.SELECTION_STATUS)
    edt.description = _('Filter by status')
    edt.set_value(status_filter)
    edt.set_location(0, row)
    edt.set_action(xfer.request, xfer.return_action(), modal=FORMTYPE_REFRESH, close=CLOSE_NO)
    xfer.add_component(edt)

    type_filter = xfer.getparam('type_filter', Preference.get_value("invoice-billtype", xfer.request.user))
    xfer.params['type_filter'] = type_filter
    edt = XferCompSelect("type_filter")
    edt.set_select(Bill.SELECTION_BILLTYPES)
    edt.description = _('Filter by type')
    edt.set_value(type_filter)
    edt.set_location(0, row + 1)
    edt.set_action(xfer.request, xfer.return_action(), modal=FORMTYPE_REFRESH, close=CLOSE_NO)
    xfer.add_component(edt)

    if status_filter == Bill.STATUS_BUILDING_VALID:
        current_filter &= Q(status=Bill.STATUS_BUILDING) | Q(status=Bill.STATUS_VALID)
    elif status_filter != Bill.STATUS_ALL:
        current_filter &= Q(status=status_filter)
    if type_filter != Bill.BILLTYPE_ALL:
        current_filter &= Q(bill_type=type_filter)
    return current_filter, status_filter


@MenuManage.describ('invoice.change_bill', FORMTYPE_NOMODAL, 'invoice', _('Management of bill list'))
class BillList(XferListEditor):
    icon = "bill.png"
    model = Bill
    field_id = 'bill'
    caption = _("Bill")

    def fillresponse_header(self):
        self.filter, status_filter = _add_bill_filter(self, 3, True)
        self.fieldnames = Bill.get_default_fields(status_filter)

    def get_items_from_filter(self):
        items = self.model.objects.annotate(completename=Concat('third__contact__individual__lastname',
                                                                Value(' '), 'third__contact__individual__firstname')).filter(self.filter)
        sort_bill = self.getparam('GRID_ORDER%bill', '').split(',')
        sort_bill_third = self.getparam('GRID_ORDER%bill_third', '')
        if ((len(sort_bill) == 0) and (sort_bill_third != '')) or (sort_bill.count('third') + sort_bill.count('-third')) > 0:
            self.params['GRID_ORDER%bill'] = ""
            if sort_bill_third.startswith('+'):
                sort_bill_third = "-"
            else:
                sort_bill_third = "+"
            self.params['GRID_ORDER%bill_third'] = sort_bill_third
            items = sorted(items, key=lambda t: str(t.third).lower(), reverse=sort_bill_third.startswith('-'))
            res = QuerySet(model=Bill)
            res._result_cache = items
            return res
        else:
            self.params['GRID_ORDER%bill_third'] = ''
            return items

    def fillresponse(self):
        XferListEditor.fillresponse(self)
        grid = self.get_components(self.field_id)
        grid.colspan = 3
        if Params.getvalue("invoice-vat-mode") == 1:
            grid.headers[5].descript = _('total excl. taxes')
        elif Params.getvalue("invoice-vat-mode") == 2:
            grid.headers[5].descript = _('total incl. taxes')


@MenuManage.describ('invoice.change_bill', FORMTYPE_NOMODAL, 'invoice', _('To find a bill following a set of criteria.'))
class BillSearch(XferSavedCriteriaSearchEditor):
    icon = "bill.png"
    model = Bill
    field_id = 'bill'
    caption = _("Search bill")


@ActionsManage.affect_grid(TITLE_CREATE, "images/new.png", condition=lambda xfer, gridname='': xfer.getparam('status_filter', Preference.get_value("invoice-status", xfer.request.user)) in (Bill.STATUS_BUILDING, Bill.STATUS_BUILDING_VALID, Bill.STATUS_ALL))
@ActionsManage.affect_show(TITLE_MODIFY, "images/edit.png", close=CLOSE_YES, condition=lambda xfer: xfer.item.status == Bill.STATUS_BUILDING)
@MenuManage.describ('invoice.add_bill')
class BillAddModify(XferAddEditor):
    icon = "bill.png"
    model = Bill
    field_id = 'bill'
    caption_add = _("Add bill")
    caption_modify = _("Modify bill")


@ActionsManage.affect_grid(TITLE_EDIT, "images/show.png", unique=SELECT_SINGLE)
@MenuManage.describ('invoice.change_bill')
class BillShow(XferShowEditor):
    caption = _("Show bill")
    icon = "bill.png"
    model = Bill
    field_id = 'bill'

    def fillresponse(self):
        XferShowEditor.fillresponse(self)
        if self.item.parentbill is not None:
            auditlogbtn = self.get_components('auditlogbtn')
            if auditlogbtn is None:
                posx = 0
                posy = max(6, self.get_max_row()) + 20
            else:
                posx = 1
                posy = auditlogbtn.row
            btn = XferCompButton('parentbill')
            btn.set_action(self.request, self.return_action(_('origin'), "origin.png"), modal=FORMTYPE_MODAL, close=CLOSE_NO, params={'bill': self.item.parentbill_id})
            btn.set_is_mini(True)
            btn.set_location(posx, posy)
            self.add_component(btn)
        self.add_action(ActionsManage.get_action_url('payoff.Supporting', 'Show', self),
                        close=CLOSE_NO, params={'item_name': self.field_id}, pos_act=0)


@ActionsManage.affect_transition("status", multi_list=('archive', 'valid'))
@MenuManage.describ('invoice.add_bill')
class BillTransition(XferTransition):
    icon = "bill.png"
    model = Bill
    field_id = 'bill'

    def fill_dlg_payoff(self, withpayoff, sendemail):
        dlg = self.create_custom(Payoff)
        dlg.caption = _("Confirmation")
        icon = XferCompImage('img')
        icon.set_location(0, 0, 1, 6)
        icon.set_value(self.icon_path())
        dlg.add_component(icon)
        lbl = XferCompLabelForm('lb_title')
        lbl.set_value_as_infocenter(_("Do you want validate '%s'?") % self.item)
        lbl.set_location(1, 1, 2)
        dlg.add_component(lbl)
        if (self.item.bill_type != Bill.BILLTYPE_QUOTATION) and (abs(self.item.get_total_rest_topay()) > 0.0001):
            check_payoff = XferCompCheck('withpayoff')
            check_payoff.set_value(withpayoff)
            check_payoff.set_location(1, 2)
            check_payoff.java_script = """
    var type=current.getValue();
    parent.get('date_payoff').setEnabled(type);
    parent.get('amount').setEnabled(type);
    if (parent.get('payer')) {
        parent.get('payer').setEnabled(type);
    }
    parent.get('mode').setEnabled(type);
    if (parent.get('reference')) {
        parent.get('reference').setEnabled(type);
    }
    if (parent.get('bank_account')) {
        parent.get('bank_account').setEnabled(type);
    }
    """
            check_payoff.description = _("Payment of deposit or cash")
            dlg.add_component(check_payoff)
            dlg.item.supporting = self.item
            dlg.fill_from_model(2, 3, False)
            if dlg.get_components("bank_fee") is not None:
                check_payoff.java_script += "parent.get('bank_fee').setEnabled(type);\n"
            dlg.get_components("date").name = "date_payoff"
            dlg.get_components("mode").set_action(self.request, self.return_action(), close=CLOSE_NO, modal=FORMTYPE_REFRESH)
        if (self.item.bill_type != Bill.BILLTYPE_ASSET) and can_send_email(dlg) and self.item.can_send_email():
            row = dlg.get_max_row()
            check_payoff = XferCompCheck('sendemail')
            check_payoff.set_value(sendemail)
            check_payoff.set_location(1, row + 1)
            check_payoff.java_script = """
    var type=current.getValue();
    parent.get('subject').setEnabled(type);
    parent.get('message').setEnabled(type);
    parent.get('model').setEnabled(type);
    """
            check_payoff.description = _("Send email with PDF")
            dlg.add_component(check_payoff)
            edt = XferCompEdit('subject')
            edt.set_value(str(self.item))
            edt.set_location(2, row + 2)
            edt.description = _('subject')
            dlg.add_component(edt)
            contact = self.item.third.contact.get_final_child()
            memo = XferCompMemo('message')
            memo.description = _('message')
            email_message = Params.getvalue('payoff-email-message')
            email_message = email_message.replace('%(name)s', '#name')
            email_message = email_message.replace('%(doc)s', '#doc')
            email_message = email_message.replace('#name', contact.get_presentation())
            email_message = email_message.replace('#doc', self.item.get_docname())
            memo.set_value(email_message)
            memo.with_hypertext = True
            memo.set_size(130, 450)
            memo.set_location(2, row + 3)
            dlg.add_component(memo)
            if self.item.bill_type != Bill.BILLTYPE_QUOTATION:
                check_payoff.java_script += "parent.get('PRINT_PERSITENT').setEnabled(type);\n"
                presitent_report = XferCompCheck('PRINT_PERSITENT')
                presitent_report.set_value(True)
                presitent_report.set_location(2, row + 4)
                presitent_report.description = _('Send saved report')
                presitent_report.java_script = """
var is_persitent=current.getValue();
parent.get('model').setEnabled(!is_persitent);
parent.get('print_sep').setEnabled(!is_persitent);
"""
                dlg.add_component(presitent_report)
                sep = XferCompLabelForm('print_sep')
                sep.set_value_center(XferContainerPrint.PRINT_REGENERATE_MSG)
                sep.set_location(2, row + 5)
                dlg.add_component(sep)
            selectors = PrintModel.get_print_selector(2, self.item.__class__)[0]
            sel = XferCompSelect('model')
            sel.set_select(selectors[2])
            sel.set_location(2, row + 6)
            sel.description = selectors[1]
            dlg.add_component(sel)
        dlg.add_action(self.return_action(TITLE_OK, 'images/ok.png'), params={"CONFIRME": "YES"})
        dlg.add_action(WrapAction(TITLE_CANCEL, 'images/cancel.png'))

    def fill_confirm(self, transition, trans):
        withpayoff = self.getparam('withpayoff', False)
        sendemail = self.getparam('sendemail', False)
        if (transition != 'valid') or (len(self.items) > 1):
            if transition == 'undo':
                if self.confirme(_("Do you want to create an compensation (avoid or invoice) from this bill ?")):
                    self._confirmed(transition)
                if self.trans_result is not None:
                    self.redirect_action(ActionsManage.get_action_url('invoice.Bill', 'Show', self), params={self.field_id: self.trans_result})
            else:
                XferTransition.fill_confirm(self, transition, trans)
        elif self.getparam("CONFIRME") is None:
            self.fill_dlg_payoff(withpayoff, sendemail)
        else:
            if (self.item.bill_type != Bill.BILLTYPE_QUOTATION) and withpayoff:
                self.item.affect_num()
                self.item.save()
                new_payoff = Payoff()
                new_payoff.supporting = self.item
                new_payoff.amount = self.getparam('amount', 0.0)
                new_payoff.mode = self.getparam('mode', Payoff.MODE_CASH)
                new_payoff.payer = self.getparam('payer')
                new_payoff.reference = self.getparam('reference')
                if self.getparam('bank_account', 0) != 0:
                    new_payoff.bank_account_id = self.getparam('bank_account', 0)
                new_payoff.date = self.getparam('date_payoff')
                new_payoff.bank_fee = self.getparam('bank_fee', 0.0)
                new_payoff.editor.before_save(self)
                new_payoff.save()
            XferTransition.fill_confirm(self, transition, trans)
            if sendemail:
                self.redirect_action(PayableEmail.get_action("", ""), params={"item_name": self.field_id, "modelname": "", "OK": "YES"})


@ActionsManage.affect_grid(_('payoff'), "diacamma.payoff/images/payoff.png", close=CLOSE_NO, unique=SELECT_MULTI, condition=lambda xfer, gridname='': xfer.getparam('status_filter', Preference.get_value("invoice-status", xfer.request.user)) == Bill.STATUS_VALID)
@MenuManage.describ('payoff.add_payoff')
class BillMultiPay(XferContainerAcknowledge):
    caption = _("Multi-pay bill")
    icon = "bill.png"
    model = Bill
    field_id = 'bill'

    def fillresponse(self):
        bill_ids = [bill_item.id for bill_item in self.items if bill_item.bill_type != Bill.BILLTYPE_QUOTATION]
        if len(bill_ids) > 0:
            bill_ids.sort()
            self.redirect_action(PayoffAddModify.get_action("", ""), params={"supportings": ";".join([str(bill_id) for bill_id in bill_ids])})


@ActionsManage.affect_show(_("=> Bill"), "images/ok.png", close=CLOSE_YES, condition=lambda xfer: (xfer.item.status == Bill.STATUS_VALID) and (xfer.item.bill_type == Bill.BILLTYPE_QUOTATION))
@MenuManage.describ('invoice.add_bill')
class BillFromQuotation(XferContainerAcknowledge):
    caption = _("Convert to bill")
    icon = "bill.png"
    model = Bill
    field_id = 'bill'

    def fillresponse(self):
        if (self.item.bill_type == Bill.BILLTYPE_QUOTATION) and (self.item.status == Bill.STATUS_VALID) and self.confirme(_("Do you want convert '%s' to bill?") % self.item):
            new_bill = self.item.convert_to_bill()
            if new_bill is not None:
                self.redirect_action(ActionsManage.get_action_url('invoice.Bill', 'Show', self), params={self.field_id: new_bill.id})


@ActionsManage.affect_grid(TITLE_DELETE, "images/delete.png", unique=SELECT_MULTI, condition=lambda xfer, gridname='': xfer.getparam('status_filter', Preference.get_value("invoice-status", xfer.request.user)) in (Bill.STATUS_BUILDING, Bill.STATUS_BUILDING_VALID, Bill.STATUS_ALL))
@MenuManage.describ('invoice.delete_bill')
class BillDel(XferDelete):
    icon = "bill.png"
    model = Bill
    field_id = 'bill'
    caption = _("Delete bill")


@ActionsManage.affect_grid(_('Batch'), "images/upload.png", condition=lambda xfer, gridname='': xfer.getparam('status_filter', Preference.get_value("invoice-status", xfer.request.user)) in (Bill.STATUS_BUILDING, Bill.STATUS_BUILDING_VALID, Bill.STATUS_ALL))
@MenuManage.describ('payoff.add_payoff')
class BillBatch(XferContainerAcknowledge):
    caption = _("Batch bill")
    icon = "bill.png"
    model = Bill
    field_id = 'bill'

    def _fill_dlg_batch(self):
        dlg = self.create_custom(Detail)
        img = XferCompImage('img')
        img.set_value(self.icon_path())
        img.set_location(0, 0, 1, 6)
        dlg.add_component(img)
        dlg.item.set_context(dlg)
        dlg.fill_from_model(1, 1, False)
        dlg.move(0, 0, 10)
        dlg.model = Bill
        dlg._initialize(self.request)
        lbl = XferCompLabelForm('titlebill')
        lbl.set_value_as_title(_('bill'))
        lbl.set_location(1, 0, 2)
        dlg.add_component(lbl)
        sel = XferCompSelect('thirds')
        sel.description = _("thirds")
        sel.set_location(1, 1, 2)
        sel.set_needed(True)
        sel.set_select_query(SavedCriteria.objects.filter(modelname=Third.get_long_name()))
        dlg.add_component(sel)
        dlg.fill_from_model(1, 2, False, desc_fields=[("bill_type", "date"), "comment"])
        dlg.remove_component('third')
        lbl = XferCompLabelForm('sep_bill')
        lbl.set_value("{[hr/]}{[hr/]}")
        lbl.set_location(1, 8, 2)
        dlg.add_component(lbl)
        lbl = XferCompLabelForm('titleart')
        lbl.set_value_as_title(_('article'))
        lbl.set_location(1, 9, 2)
        dlg.add_component(lbl)
        dlg.add_action(self.return_action(TITLE_OK, 'images/ok.png'), params={"SAVE": "YES"})
        dlg.add_action(WrapAction(TITLE_CANCEL, 'images/cancel.png'))

    def fillresponse(self):
        if self.getparam("SAVE") != "YES":
            self._fill_dlg_batch()
        else:
            thirds_criteria = SavedCriteria.objects.get(id=self.getparam('thirds', 0))
            filter_result, _criteria_desc = get_search_query_from_criteria(thirds_criteria.criteria, Third)
            thirds_list = Third.objects.filter(filter_result)
            bill_comp = XferContainerAcknowledge()
            bill_comp.model = Bill
            bill_comp._initialize(self.request)
            bill_comp.item.id = 0
            detail_comp = XferContainerAcknowledge()
            detail_comp.model = Detail
            detail_comp._initialize(self.request)
            detail_comp.item.id = 0
            billtype = get_value_if_choices(bill_comp.item.bill_type, bill_comp.item.get_field_by_name('bill_type'))
            if self.confirme(_('Do you want create this invoice "%(type)s" of %(amount)s for %(nbthird)s cutomers ?') % {'type': billtype,
                                                                                                                         'amount': get_amount_from_format_devise(detail_comp.item.total, 7),
                                                                                                                         'nbthird': len(thirds_list)}):
                for third in thirds_list:
                    new_bill = Bill(third=third, bill_type=bill_comp.item.bill_type, date=bill_comp.item.date, comment=bill_comp.item.comment)
                    new_bill.save()
                    new_detail = detail_comp.item
                    new_detail.id = None
                    new_detail.bill = new_bill
                    new_detail.save()


def can_printing(xfer, gridname=''):
    if xfer.getparam('CRITERIA') is not None:
        for criteria_item in get_criteria_list(xfer.getparam('CRITERIA')):
            if (criteria_item[0] == 'status') and (criteria_item[2] in ('1', '3', '1;3')):
                return True
        return False
    else:
        return xfer.getparam('status_filter', Preference.get_value("invoice-status", xfer.request.user)) in (Bill.STATUS_VALID, Bill.STATUS_ARCHIVE)


@ActionsManage.affect_grid(_("Send"), "lucterios.mailing/images/email.png", close=CLOSE_NO, unique=SELECT_MULTI, condition=lambda xfer, gridname='': can_printing(xfer) and can_send_email(xfer))
@ActionsManage.affect_show(_("Send"), "lucterios.mailing/images/email.png", close=CLOSE_NO, condition=lambda xfer: xfer.item.status in (Bill.STATUS_VALID, Bill.STATUS_ARCHIVE) and can_send_email(xfer))
@MenuManage.describ('invoice.add_bill')
class BillPayableEmail(XferContainerAcknowledge):
    caption = _("Send by email")
    icon = "bill.png"
    model = Bill
    field_id = 'bill'

    def fillresponse(self):
        self.redirect_action(ActionsManage.get_action_url('payoff.Supporting', 'Email', self),
                             close=CLOSE_NO, params={'item_name': self.field_id, "modelname": ""})


@ActionsManage.affect_grid(_("Print"), "images/print.png", close=CLOSE_NO, unique=SELECT_MULTI, condition=can_printing)
@ActionsManage.affect_show(_("Print"), "images/print.png", close=CLOSE_NO, condition=lambda xfer: xfer.item.status in (Bill.STATUS_VALID, Bill.STATUS_ARCHIVE))
@MenuManage.describ('invoice.change_bill')
class BillPrint(SupportingPrint):
    icon = "bill.png"
    model = Bill
    field_id = 'bill'
    caption = _("Print bill")

    def get_print_name(self):
        if len(self.items) == 1:
            current_bill = self.items[0]
            return current_bill.get_document_filename()
        else:
            return str(self.caption)

    def items_callback(self):
        has_item = False
        for item in self.items:
            if item.status in (Bill.STATUS_ARCHIVE, Bill.STATUS_VALID):
                has_item = True
                yield item
        if not has_item:
            raise LucteriosException(IMPORTANT, _("No invoice to print!"))


@ActionsManage.affect_grid(TITLE_ADD, "images/add.png")
@ActionsManage.affect_grid(TITLE_MODIFY, "images/edit.png", unique=SELECT_SINGLE)
@MenuManage.describ('invoice.add_bill')
class DetailAddModify(XferAddEditor):
    icon = "article.png"
    model = Detail
    field_id = 'detail'
    caption_add = _("Add detail")
    caption_modify = _("Modify detail")


@ActionsManage.affect_grid(TITLE_DELETE, "images/delete.png", unique=SELECT_MULTI)
@MenuManage.describ('invoice.add_bill')
class DetailDel(XferDelete):
    icon = "article.png"
    model = Detail
    field_id = 'detail'
    caption = _("Delete detail")


@MenuManage.describ('invoice.change_article', FORMTYPE_NOMODAL, 'invoice', _('Management of article list'))
class ArticleList(XferListEditor):
    icon = "article.png"
    model = Article
    field_id = 'article'
    caption = _("Articles")

    STOCKABLE_WITH_STOCK = 3

    def __init__(self, **kwargs):
        XferListEditor.__init__(self, **kwargs)
        self.categories_filter = ()

    def get_items_from_filter(self):
        items = XferListEditor.get_items_from_filter(self)
        if len(self.categories_filter) > 0:
            for cat_item in Category.objects.filter(id__in=self.categories_filter):
                items = items.filter(categories__in=[cat_item])
        if self.show_stockable == self.STOCKABLE_WITH_STOCK:
            new_items = QuerySet(model=Article)
            new_items._result_cache = [item for item in items.distinct() if item.get_stockage_total_num() > 0]
            return new_items
        else:
            return items.distinct()

    def fillresponse_header(self):
        show_filter = self.getparam('show_filter', 0)
        self.show_stockable = self.getparam('stockable', -1)
        ref_filter = self.getparam('ref_filter', '')
        self.categories_filter = self.getparam('cat_filter', ())
        show_storagearea = self.getparam('storagearea', 0)

        edt = XferCompSelect("show_filter")
        edt.set_select([(0, _('Only activate')), (1, _('All'))])
        edt.set_value(show_filter)
        edt.set_location(0, 3, 2)
        edt.description = _('Show articles')
        edt.set_action(self.request, self.return_action(), modal=FORMTYPE_REFRESH, close=CLOSE_NO)
        self.add_component(edt)

        edt = XferCompEdit("ref_filter")
        edt.set_value(ref_filter)
        edt.set_location(0, 4)
        edt.is_default = True
        edt.description = _('ref./designation')
        edt.set_action(self.request, self.return_action(), modal=FORMTYPE_REFRESH, close=CLOSE_NO)
        self.add_component(edt)

        self.fill_from_model(0, 5, False, ['stockable'])
        sel_stock = self.get_components('stockable')
        sel_stock.select_list.insert(0, (-1, '---'))
        sel_stock.select_list.append((self.STOCKABLE_WITH_STOCK, _('with stock')))
        sel_stock.set_value(self.show_stockable)
        sel_stock.set_action(self.request, self.return_action(), modal=FORMTYPE_REFRESH, close=CLOSE_NO)

        cat_list = Category.objects.all()
        if len(cat_list) > 0:
            edt = XferCompCheckList("cat_filter")
            edt.set_select_query(cat_list)
            edt.set_value(self.categories_filter)
            edt.set_location(1, 4, 1, 2)
            edt.description = _('categories')
            edt.set_action(self.request, self.return_action(), modal=FORMTYPE_REFRESH, close=CLOSE_NO)
            self.add_component(edt)

        sel_stock = XferCompSelect('storagearea')
        sel_stock.set_needed(False)
        sel_stock.set_select_query(StorageArea.objects.all())
        sel_stock.set_value(show_storagearea)
        sel_stock.set_action(self.request, self.return_action(), modal=FORMTYPE_REFRESH, close=CLOSE_NO)
        sel_stock.set_location(0, 6)
        sel_stock.description = StorageArea._meta.verbose_name
        if len(sel_stock.select_list) > 1:
            self.add_component(sel_stock)

        self.filter = Q()
        if ref_filter != '':
            self.filter &= Q(reference__icontains=ref_filter) | Q(designation__icontains=ref_filter)
        if show_filter == 0:
            self.filter &= Q(isdisabled=False)
        if self.show_stockable != -1:
            if self.show_stockable != ArticleList.STOCKABLE_WITH_STOCK:
                self.filter &= Q(stockable=self.show_stockable)
            else:
                self.filter &= ~Q(stockable=Article.STOCKABLE_NO)
        if show_storagearea != 0:
            self.filter &= Q(storagedetail__storagesheet__storagearea=show_storagearea)
        self.add_action(ArticleSearch.get_action(_("Search"), "diacamma.invoice/images/article.png"), modal=FORMTYPE_NOMODAL, close=CLOSE_YES)


@ActionsManage.affect_list(TITLE_PRINT, "images/print.png", close=CLOSE_NO)
@MenuManage.describ('invoice.change_article')
class ArticlePrint(XferPrintListing):
    icon = "article.png"
    model = Article
    field_id = 'article'
    caption = _("Print articles")

    def filter_callback(self, items):
        categories_filter = self.getparam('cat_filter', ())
        if len(categories_filter) > 0:
            for cat_item in Category.objects.filter(id__in=categories_filter):
                items = items.filter(categories__in=[cat_item])
        return items.distinct()

    def get_filter(self):
        show_filter = self.getparam('show_filter', 0)
        show_stockable = self.getparam('stockable', -1)
        ref_filter = self.getparam('ref_filter', '')
        show_storagearea = self.getparam('storagearea', 0)
        new_filter = Q()
        if ref_filter != '':
            new_filter &= Q(reference__icontains=ref_filter) | Q(designation__icontains=ref_filter)
        if show_filter == 0:
            new_filter &= Q(isdisabled=False)
        if show_stockable != -1:
            if show_stockable != ArticleList.STOCKABLE_WITH_STOCK:
                new_filter &= Q(stockable=show_stockable)
            else:
                new_filter &= ~Q(stockable=Article.STOCKABLE_NO)
        if show_storagearea != 0:
            new_filter &= Q(storagedetail__storagesheet__storagearea=show_storagearea)
        return new_filter


@ActionsManage.affect_list(TITLE_LABEL, "images/print.png", close=CLOSE_NO)
@MenuManage.describ('invoice.change_article')
class ArticleLabel(XferPrintLabel):
    icon = "article.png"
    model = Article
    field_id = 'article'
    caption = _("Label articles")

    def filter_callback(self, items):
        categories_filter = self.getparam('cat_filter', ())
        if len(categories_filter) > 0:
            for cat_item in Category.objects.filter(id__in=categories_filter):
                items = items.filter(categories__in=[cat_item])
        return items.distinct()

    def get_filter(self):
        show_filter = self.getparam('show_filter', 0)
        show_stockable = self.getparam('stockable', -1)
        ref_filter = self.getparam('ref_filter', '')
        show_storagearea = self.getparam('storagearea', 0)
        new_filter = Q()
        if ref_filter != '':
            new_filter &= Q(reference__icontains=ref_filter) | Q(designation__icontains=ref_filter)
        if show_filter == 0:
            new_filter &= Q(isdisabled=False)
        if show_stockable != -1:
            if show_stockable != ArticleList.STOCKABLE_WITH_STOCK:
                self.filter &= Q(stockable=show_stockable)
            else:
                self.filter &= ~Q(stockable=Article.STOCKABLE_NO)
        if show_storagearea != 0:
            new_filter &= Q(storagedetail__storagesheet__storagearea=show_storagearea)
        return new_filter


@MenuManage.describ('accounting.change_article')
class ArticleSearch(XferSavedCriteriaSearchEditor):
    icon = "article.png"
    model = Article
    field_id = 'article'
    caption = _("Search article")

    def fillresponse(self):
        XferSavedCriteriaSearchEditor.fillresponse(self)
        if WrapAction.is_permission(self.request, 'invoice.add_article'):
            self.get_components(self.field_id).add_action(self.request, ObjectMerge.get_action(_("Merge"), "images/clone.png"),
                                                          close=CLOSE_NO, unique=SELECT_MULTI, params={'modelname': self.model.get_long_name(), 'field_id': self.field_id})
        self.add_action(AbstractContactFindDouble.get_action(_("duplicate"), "images/clone.png"),
                        params={'modelname': self.model.get_long_name(), 'field_id': self.field_id}, pos_act=0)


@ActionsManage.affect_grid(TITLE_EDIT, "images/show.png", unique=SELECT_SINGLE)
@MenuManage.describ('invoice.change_article')
class ArticleShow(XferShowEditor):
    caption = _("Show article")
    icon = "article.png"
    model = Article
    field_id = 'article'


@ActionsManage.affect_grid(TITLE_CREATE, "images/new.png")
@ActionsManage.affect_show(TITLE_MODIFY, "images/edit.png", close=CLOSE_YES)
@MenuManage.describ('invoice.add_article')
class ArticleAddModify(XferAddEditor):
    icon = "article.png"
    model = Article
    field_id = 'article'
    caption_add = _("Add article")
    caption_modify = _("Modify article")


@ActionsManage.affect_grid(TITLE_DELETE, "images/delete.png", unique=SELECT_MULTI)
@MenuManage.describ('invoice.delete_article')
class ArticleDel(XferDelete):
    icon = "article.png"
    model = Article
    field_id = 'article'
    caption = _("Delete article")


@ActionsManage.affect_grid(TITLE_ADD, "images/add.png")
@ActionsManage.affect_grid(TITLE_MODIFY, "images/edit.png", unique=SELECT_SINGLE)
@MenuManage.describ('invoice.add_article')
class ProviderAddModify(XferAddEditor):
    icon = "article.png"
    model = Provider
    field_id = 'provider'
    caption_add = _("Add provider")
    caption_modify = _("Modify provider")


@ActionsManage.affect_grid(TITLE_DELETE, "images/delete.png", unique=SELECT_MULTI)
@MenuManage.describ('invoice.delete_article')
class ProviderDel(XferDelete):
    icon = "article.png"
    model = Provider
    field_id = 'provider'
    caption = _("Delete provider")


@MenuManage.describ('invoice.change_bill', FORMTYPE_MODAL, 'invoice', _('Statistic of selling'))
class BillStatistic(XferContainerCustom):
    icon = "report.png"
    model = Bill
    field_id = 'bill'
    caption = _("Statistic")
    readonly = True
    methods_allowed = ('GET', )

    def fill_header(self):
        img = XferCompImage('img')
        img.set_value(self.icon_path())
        img.set_location(0, 0, 1, 2)
        self.add_component(img)
        select_year = self.getparam('fiscal_year')
        lbl = XferCompLabelForm('lbl_title')
        lbl.set_value_as_headername(_('Statistics in date of %s') % formats.date_format(date.today(), "DATE_FORMAT"))
        lbl.set_location(1, 0, 2)
        self.add_component(lbl)
        self.item.fiscal_year = FiscalYear.get_current(select_year)
        self.fill_from_model(1, 1, False, ['fiscal_year'])
        fiscal_year = self.get_components('fiscal_year')
        fiscal_year.set_needed(True)
        fiscal_year.set_action(self.request, self.return_action(), close=CLOSE_NO, modal=FORMTYPE_REFRESH)
        ck = XferCompCheck('without_reduct')
        ck.set_value(self.getparam('without_reduct', False))
        ck.set_location(1, 2, 2)
        ck.description = _('Without reduction')
        ck.set_action(self.request, self.return_action(), close=CLOSE_NO, modal=FORMTYPE_REFRESH)
        self.add_component(ck)

    def fill_customers(self):
        costumer_result = self.item.get_statistics_customer(self.getparam('without_reduct', False))
        grid = XferCompGrid("customers")
        grid.no_pager = True
        grid.add_header("customer", _("customer"))
        grid.add_header("amount", _("amount"), htype=format_with_devise(7))
        grid.add_header("ratio", _("ratio (%)"), htype='N2', formatstr='{0} %')
        index = 0
        for cust_val in costumer_result:
            grid.set_value(index, "customer", cust_val[0])
            grid.set_value(index, "amount", cust_val[1])
            grid.set_value(index, "ratio", cust_val[2])
            index += 1
        grid.set_location(0, 1, 3)
        grid.set_size(400, 800)
        self.add_component(grid)

    def fill_articles(self, for_quotation):
        articles_result = self.item.get_statistics_article(self.getparam('without_reduct', False), for_quotation)
        grid = XferCompGrid("articles" + ("_quote" if for_quotation else ""))
        grid.no_pager = True
        grid.add_header("article", _("article"))
        grid.add_header("amount", _("amount"), htype=format_with_devise(7))
        grid.add_header("number", _("number"), htype='N2')
        grid.add_header("mean", _("mean"), htype=format_with_devise(7))
        grid.add_header("ratio", _("ratio (%)"), htype='N2', formatstr='{0} %')
        index = 0
        for art_val in articles_result:
            grid.set_value(index, "article", art_val[0])
            grid.set_value(index, "amount", art_val[1])
            grid.set_value(index, "number", art_val[2])
            grid.set_value(index, "mean", art_val[3])
            grid.set_value(index, "ratio", art_val[4])
            index += 1
        grid.set_location(0, 2, 3)
        grid.set_size(400, 800)
        self.add_component(grid)

    def fill_month(self):
        month_result = self.item.get_statistics_month(self.getparam('without_reduct', False))
        grid = XferCompGrid("months")
        grid.no_pager = True
        grid.add_header("month", _("month"))
        grid.add_header("amount", _("amount"), htype=format_with_devise(7))
        grid.add_header("ratio", _("ratio (%)"), htype='N2', formatstr='{0} %')
        index = 0
        for month_val in month_result:
            grid.set_value(index, "month", month_val[0])
            grid.set_value(index, "amount", month_val[1])
            grid.set_value(index, "ratio", month_val[2])
            index += 1
        grid.set_location(0, 1, 3)
        grid.set_size(400, 800)
        self.add_component(grid)

    def fill_payoff(self, is_revenu, title):
        payoff_result = self.item.get_statistics_payoff(is_revenu)
        grid = XferCompGrid("payoffs_%s" % is_revenu)
        grid.no_pager = True
        grid.add_header("mode", _('mode'))
        grid.add_header("bank_account", _('bank account'))
        grid.add_header("number", _("number"), htype='N0')
        grid.add_header("amount", _("amount"), htype=format_with_devise(7))
        grid.add_header("ratio", _("ratio (%)"), htype='N2', formatstr='{0} %')
        index = 0
        for payoff_val in payoff_result:
            grid.set_value(index, "mode", payoff_val[0])
            grid.set_value(index, "bank_account", payoff_val[1])
            grid.set_value(index, "number", payoff_val[2])
            grid.set_value(index, "amount", payoff_val[3])
            grid.set_value(index, "ratio", payoff_val[4])
            index += 1
        grid.set_location(0, self.get_max_row() + 1, 3)
        grid.description = title
        if not is_revenu:
            grid.set_size(200, 800)
        self.add_component(grid)

    def fillresponse(self):
        self.fill_header()
        self.new_tab(_('Customers'))
        self.fill_customers()
        self.new_tab(_('Articles'))
        self.fill_articles(False)
        self.new_tab(_('By month'))
        self.fill_month()

        self.new_tab(_('By payoff'))
        self.fill_payoff(True, _('Payoff of bills and receipts'))
        self.fill_payoff(False, _('Payoff of assets'))

        self.new_tab(_('Quotations'))
        lbl = XferCompLabelForm('lbl_info_quot')
        lbl.set_value_center(_('Statistics of quotation in status "validated"'))
        lbl.set_location(0, 0, 3)
        self.add_component(lbl)
        self.fill_articles(True)

        self.add_action(BillAccountChecking.get_action(_('check'), "images/info.png"), close=CLOSE_YES)
        self.add_action(BillStatisticPrint.get_action(TITLE_PRINT, "images/print.png"), close=CLOSE_NO)
        self.add_action(WrapAction(TITLE_CLOSE, 'images/close.png'))


@MenuManage.describ('invoice.change_bill')
class BillStatisticPrint(XferPrintAction):
    caption = _("Print statistic")
    icon = "report.png"
    model = Bill
    field_id = 'bill'
    action_class = BillStatistic
    with_text_export = True


@MenuManage.describ('invoice.change_bill')
class BillOpenEntryAccount(XferContainerAcknowledge):
    icon = "report.png"
    model = Bill
    field_id = 'bill'
    caption = ""
    readonly = True
    methods_allowed = ('GET', )

    def fillresponse(self, payoff=None, showbill=False):
        if showbill and (payoff is not None):
            payoff_list = EntryAccount.objects.get(id=payoff).payoff_set.all()
            if len(payoff_list) == 1:
                bill_id = payoff_list.first().supporting.id
                self.redirect_action(BillShow.get_action(), params={'bill': bill_id})
            else:
                self.message(_('No editable: Payoff assign to many bills.'))
        else:
            if payoff is None:
                entry_id = self.item.entry_id
            else:
                entry_id = payoff
            if entry_id is None:
                self.message(_('No editable: Entry not found.'))
            else:
                self.redirect_action(EntryAccountOpenFromLine.get_action(), params={'entryaccount': entry_id})


@MenuManage.describ('invoice.change_bill')
class BillAccountChecking(XferContainerCustom):
    icon = "report.png"
    model = Bill
    field_id = 'bill'
    caption = _("Account checking")
    readonly = True
    methods_allowed = ('GET', )

    def fill_header(self):
        img = XferCompImage('img')
        img.set_value(self.icon_path())
        img.set_location(0, 0, 1, 2)
        self.add_component(img)
        select_year = self.getparam('fiscal_year')
        lbl = XferCompLabelForm('lbl_title')
        lbl.set_value_as_headername(self.caption)
        lbl.set_location(1, 0, 2)
        self.add_component(lbl)
        self.item.fiscal_year = FiscalYear.get_current(select_year)
        self.fill_from_model(1, 1, False, ['fiscal_year'])
        fiscal_year = self.get_components('fiscal_year')
        fiscal_year.set_needed(True)
        fiscal_year.set_action(self.request, self.return_action(), close=CLOSE_NO, modal=FORMTYPE_REFRESH)

    def fill_bill(self):
        lbl = XferCompLabelForm('lbl_bill')
        lbl.set_value_center(_('Bill with different amount in accounting.'))
        lbl.set_location(0, 0, 3)
        self.add_component(lbl)
        grid = XferCompGrid("bill")
        grid.no_pager = True
        grid.add_header("bill", _("bill"))
        grid.add_header("status", _('status'), htype=get_format_from_field(Bill.get_field_by_name('status')))
        grid.add_header("amount", _('total'), htype=format_with_devise(7))
        grid.add_header("account", _("account amount"), htype=format_with_devise(7))
        for bill in Bill.objects.filter(fiscal_year=self.item.fiscal_year, status__in=(Bill.STATUS_VALID, Bill.STATUS_ARCHIVE, Bill.STATUS_ARCHIVE),
                                        bill_type__in=(Bill.BILLTYPE_BILL, Bill.BILLTYPE_ASSET, Bill.BILLTYPE_RECEIPT)):
            account_amount = None
            if bill.entry is not None:
                account_amount = bill.entry.entrylineaccount_set.filter(account__code__regex=current_system_account().get_customer_mask()).aggregate(Sum('amount'))['amount__sum']
                if (bill.bill_type == Bill.BILLTYPE_ASSET):
                    account_amount = -1 * account_amount
            if ((account_amount is None) and (abs(bill.total) > 1e-4)) or ((account_amount is not None) and (abs(account_amount - bill.total) > 1e-4)):
                grid.set_value(bill.id, "bill", bill)
                grid.set_value(bill.id, "status", bill.status)
                grid.set_value(bill.id, "amount", bill.total)
                grid.set_value(bill.id, "account", account_amount)
        grid.add_action(self.request, BillShow.get_action(TITLE_EDIT, "images/show.png"), close=CLOSE_NO, unique=SELECT_SINGLE)
        grid.add_action(self.request, BillOpenEntryAccount.get_action(_('Entry'), "diacamma.accounting/images/financial.png"), close=CLOSE_NO, unique=SELECT_SINGLE)
        grid.set_location(0, 1, 3)
        grid.set_size(400, 800)
        self.add_component(grid)

    def fill_payoff(self):
        lbl = XferCompLabelForm('lbl_payoff')
        lbl.set_value_center(_('Payoff with different amount in accounting.'))
        lbl.set_location(0, 0, 3)
        self.add_component(lbl)
        grid = XferCompGrid("payoff")
        grid.no_pager = True
        payoff_nodeposit = DepositSlip().get_payoff_not_deposit("", "", None, self.item.fiscal_year.begin, self.item.fiscal_year.end)
        grid.add_header('bill', _('bill'))
        grid.add_header('payer', _('payer'), horderable=1)
        grid.add_header('amount', _('amount'), horderable=1, htype=format_with_devise(7))
        grid.add_header('date', _('date'), horderable=1, htype='D')
        grid.add_header('reference', _('reference'), horderable=1)
        grid.add_header("account", _("account amount"), htype=format_with_devise(7))
        for payoff in payoff_nodeposit:
            payoffid = payoff['id']
            account_amount = EntryAccount.objects.get(id=payoffid).entrylineaccount_set.filter(account__code__regex=current_system_account().get_customer_mask()).aggregate(Sum('amount'))['amount__sum']
            if payoff['is_revenu']:
                account_amount = -1 * account_amount
            if ((account_amount is None) and (abs(payoff['amount']) > 1e-4)) or ((account_amount is not None) and (abs(account_amount - float(payoff['amount'])) > 1e-4)):
                grid.set_value(payoffid, 'bill', payoff['bill'])
                grid.set_value(payoffid, 'payer', payoff['payer'])
                grid.set_value(payoffid, 'amount', payoff['amount'])
                grid.set_value(payoffid, 'date', payoff['date'])
                grid.set_value(payoffid, 'reference', payoff['reference'])
                grid.set_value(payoffid, "account", account_amount)
        grid.set_location(0, 3, 4)
        grid.add_action(self.request, BillOpenEntryAccount.get_action(TITLE_EDIT, "images/show.png"), close=CLOSE_NO, unique=SELECT_SINGLE, params={'showbill': True})
        grid.add_action(self.request, BillOpenEntryAccount.get_action(_('Entry'), "diacamma.accounting/images/financial.png"), close=CLOSE_NO, unique=SELECT_SINGLE)
        grid.set_location(0, 1, 3)
        grid.set_size(400, 800)
        self.add_component(grid)

    def fill_nobill(self):
        lbl = XferCompLabelForm('lbl_entryline')
        lbl.set_value_center(_('Entries of account no present in invoice.'))
        lbl.set_location(0, 0, 3)
        self.add_component(lbl)
        grid = XferCompGrid("entryline")
        entry_lines = EntryLineAccount.objects.filter(entry__journal__gt=1,
                                                      entry__year=self.item.fiscal_year,
                                                      account__code__regex=current_system_account().get_customer_mask()).annotate(billcount=Count('entry__bill')).annotate(payoffcount=Count('entry__payoff'))
        grid.set_model(entry_lines.filter(billcount=0, payoffcount=0), None)
        grid.add_action(self.request, EntryAccountOpenFromLine.get_action(_('Entry'), "diacamma.accounting/images/financial.png"), close=CLOSE_NO, unique=SELECT_SINGLE)
        grid.set_location(0, 1, 3)
        grid.set_size(400, 800)
        self.add_component(grid)

    def fillresponse(self):
        self.fill_header()
        self.new_tab(_('Bill'))
        self.fill_bill()
        self.new_tab(_('Payoff'))
        self.fill_payoff()
        self.new_tab(_('No bill'))
        self.fill_nobill()
        self.add_action(BillAccountCheckingPrint.get_action(TITLE_PRINT, "images/print.png"), close=CLOSE_NO)
        self.add_action(WrapAction(TITLE_CLOSE, 'images/close.png'))


@MenuManage.describ('invoice.change_bill')
class BillAccountCheckingPrint(XferPrintAction):
    caption = _("Print account checking")
    icon = "report.png"
    model = Bill
    field_id = 'bill'
    action_class = BillAccountChecking
    with_text_export = True


@MenuManage.describ('invoice.add_bill')
class BillCheckAutoreduce(XferContainerAcknowledge):
    caption = _("Check auto-reduce")
    icon = "bill.png"
    model = Third
    field_id = 'third'

    def fillresponse(self):
        if self.confirme(_('Do you want check auto-reduce ?')):
            filter_auto = Q(bill__third=self.item) & Q(bill__bill_type__in=(Bill.BILLTYPE_QUOTATION, Bill.BILLTYPE_BILL, Bill.BILLTYPE_RECEIPT)) & Q(bill__status=Bill.STATUS_BUILDING)
            for detail in Detail.objects.filter(filter_auto).distinct():
                detail.reduce = 0
                detail.save(check_autoreduce=False)
            for detail in Detail.objects.filter(filter_auto).distinct().order_by('-price', '-quantity'):
                detail.save(check_autoreduce=True)


@signal_and_lock.Signal.decorate('situation')
def situation_invoice(xfer):
    if not hasattr(xfer, 'add_component'):
        contacts = []
        if not xfer.user.is_anonymous:
            for contact in Individual.objects.filter(user=xfer.user).distinct():
                contacts.append(contact.id)
            for contact in LegalEntity.objects.filter(responsability__individual__user=xfer.user).distinct():
                contacts.append(contact.id)
        return len(contacts) > 0
    else:
        contacts = []
        if not xfer.request.user.is_anonymous:
            for contact in Individual.objects.filter(user=xfer.request.user).distinct():
                contacts.append(contact.id)
            for contact in LegalEntity.objects.filter(responsability__individual__user=xfer.request.user).distinct():
                contacts.append(contact.id)
        if len(contacts) > 0:
            row = xfer.get_max_row() + 1
            lab = XferCompLabelForm('invoicetitle')
            lab.set_value_as_infocenter(_("Invoice"))
            lab.set_location(0, row, 4)
            xfer.add_component(lab)
            nb_build = len(Bill.objects.filter(third__contact_id__in=contacts).distinct())
            lab = XferCompLabelForm('invoicecurrent')
            lab.set_value_as_header(_("You are %d bills") % nb_build)
            lab.set_location(0, row + 1, 4)
            xfer.add_component(lab)
            lab = XferCompLabelForm('invoicesep')
            lab.set_value_as_infocenter("{[hr/]}")
            lab.set_location(0, row + 2, 4)
            xfer.add_component(lab)
            return True
        else:
            return False


@signal_and_lock.Signal.decorate('summary')
def summary_invoice(xfer):
    if not hasattr(xfer, 'add_component'):
        return WrapAction.is_permission(xfer, 'invoice.change_bill')
    else:
        if WrapAction.is_permission(xfer.request, 'invoice.change_bill'):
            row = xfer.get_max_row() + 1
            lab = XferCompLabelForm('invoicetitle')
            lab.set_value_as_infocenter(_("Invoice"))
            lab.set_location(0, row, 4)
            xfer.add_component(lab)
            nb_build = len(Bill.objects.filter(status=Bill.STATUS_BUILDING, bill_type__in=(Bill.BILLTYPE_BILL, Bill.BILLTYPE_ASSET, Bill.BILLTYPE_RECEIPT)))
            nb_valid = len(Bill.objects.filter(status=Bill.STATUS_VALID, bill_type__in=(Bill.BILLTYPE_BILL, Bill.BILLTYPE_ASSET, Bill.BILLTYPE_RECEIPT)))
            lab = XferCompLabelForm('invoiceinfo1')
            lab.set_value_as_header(_("There are %(build)d bills, assets or receipts in building and %(valid)d validated") % {'build': nb_build, 'valid': nb_valid})
            lab.set_location(0, row + 1, 4)
            xfer.add_component(lab)
            nb_build = len(Bill.objects.filter(status=Bill.STATUS_BUILDING, bill_type=Bill.BILLTYPE_QUOTATION))
            nb_valid = len(Bill.objects.filter(status=Bill.STATUS_VALID, bill_type=Bill.BILLTYPE_QUOTATION))
            lab = XferCompLabelForm('invoiceinfo2')
            lab.set_value_as_header(_("There are %(build)d quotations in building and %(valid)d validated") % {'build': nb_build, 'valid': nb_valid})
            lab.set_location(0, row + 2, 4)
            xfer.add_component(lab)
            lab = XferCompLabelForm('invoicesep')
            lab.set_value_as_infocenter("{[hr/]}")
            lab.set_location(0, row + 3, 4)
            xfer.add_component(lab)
            return True
        else:
            return False


@signal_and_lock.Signal.decorate('third_addon')
def thirdaddon_invoice(item, xfer):
    if WrapAction.is_permission(xfer.request, 'invoice.change_bill'):
        try:
            FiscalYear.get_current()
            xfer.new_tab(_('Invoice'))
            current_filter, status_filter = _add_bill_filter(xfer, 1)
            contacts = [item.contact.id]
            if getattr(xfer, 'with_individual', False) and isinstance(item.contact.get_final_child(), LegalEntity):
                for contact in Individual.objects.filter(responsability__legal_entity=item.contact).distinct():
                    contacts.append(contact.id)
            current_filter &= Q(third__contact_id__in=contacts)
            bills = Bill.objects.filter(current_filter).distinct()
            bill_grid = XferCompGrid('bill')
            bill_grid.set_model(bills, Bill.get_default_fields(status_filter), xfer)
            bill_grid.add_action_notified(xfer, Bill)
            bill_grid.set_location(0, 3, 2)
            xfer.add_component(bill_grid)
            if len(bills) > 0:
                reduce_sum = 0.0
                total_sum = 0.0
                for bill in bills:
                    if ((bill.bill_type == Bill.BILLTYPE_QUOTATION) and (bill.status == Bill.STATUS_CANCEL)) or (bill.status == Bill.STATUS_ARCHIVE):
                        continue
                    direction = -1 if bill.bill_type == Bill.BILLTYPE_ASSET else 1
                    total_sum += direction * bill.get_total()
                    for detail in bill.detail_set.all():
                        reduce_sum += direction * detail.get_reduce()
                gross_sum = total_sum + reduce_sum
                lab = XferCompLabelForm('sum_summary')
                format_string = _("{[b]}Gross total{[/b]} : %(grosstotal)s - {[b]}total of reduces{[/b]} : %(reducetotal)s = {[b]}total to pay{[/b]} : %(total)s") % {'grosstotal': '{0}', 'reducetotal': '{1}', 'total': '{2}'}
                lab.set_value([gross_sum, reduce_sum, total_sum])
                lab.set_format(format_with_devise(7) + ';' + format_string)
                lab.set_location(0, 4, 2)
                xfer.add_component(lab)
                if AutomaticReduce.objects.all().count() > 0:
                    btn = XferCompButton('btn_autoreduce')
                    btn.set_action(xfer.request, BillCheckAutoreduce.get_action(_('Reduce'), ''), modal=FORMTYPE_MODAL, close=CLOSE_NO, params={'third': item.id})
                    btn.set_location(0, 5, 2)
                    xfer.add_component(btn)
        except LucteriosException:
            pass


@signal_and_lock.Signal.decorate('show_contact')
def show_contact_invoice(contact, xfer):
    if WrapAction.is_permission(xfer.request, 'invoice.change_bill'):
        third = get_main_third(contact)
        if third is not None:
            accounts = third.accountthird_set.filter(Q(code__regex=current_system_account().get_customer_mask()))
            if len(accounts) > 0:
                xfer.new_tab(_("Financial"))
                nb_build = len(Bill.objects.filter(third=third, status=Bill.STATUS_BUILDING))
                nb_valid = len(Bill.objects.filter(third=third, status=Bill.STATUS_VALID))
                lab = XferCompLabelForm('invoiceinfo')
                lab.set_value_as_header(_("There are %(build)d bills in building and %(valid)d validated") % {'build': nb_build, 'valid': nb_valid})
                lab.set_location(0, 5, 2)
                xfer.add_component(lab)
                xfer.params['third'] = third.id
                xfer.with_individual = True
                thirdaddon_invoice(third, xfer)
