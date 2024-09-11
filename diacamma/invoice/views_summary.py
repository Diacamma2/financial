# -*- coding: utf-8 -*-
'''
lucterios.contacts package

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
from json import loads, dumps
from datetime import datetime

from django.utils.translation import gettext_lazy as _
from django.db.models import Q
from django.utils import timezone

from lucterios.framework.tools import MenuManage, FORMTYPE_MODAL, SELECT_SINGLE, CLOSE_NO, WrapAction, FORMTYPE_REFRESH, CLOSE_YES, \
    get_date_formating, get_url_from_request
from lucterios.framework.error import LucteriosException, IMPORTANT
from lucterios.framework.model_fields import get_value_if_choices
from lucterios.framework.xferadvance import XferListEditor, TITLE_CLOSE, TITLE_DELETE, XferTransition, \
    TITLE_NO
from lucterios.framework.xferprinting import PRINT_PDF_FILE
from lucterios.framework.xfergraphic import XferContainerCustom, XferContainerAcknowledge
from lucterios.framework.xfercomponents import XferCompLabelForm, XferCompSelect, XferCompEdit, XferCompButton, XferCompFloat, XferCompImage, XferCompMemo
from lucterios.framework.xfersearch import get_search_query_from_criteria

from lucterios.contacts.models import Individual, LegalEntity
from lucterios.CORE.parameters import Params
from lucterios.CORE.xferprint import XferPrintListing

from diacamma.invoice.models import Bill, Category, get_or_create_customer, Article, Detail, CategoryBill, StorageArea
from diacamma.invoice.views import BillPrint, BillShow, DetailDel, _add_type_filter_selector
from diacamma.payoff.models import PaymentMethod
from diacamma.payoff.views import PayableShow
from diacamma.payoff.views_externalpayment import CheckPaymentGeneric
from diacamma.accounting.tools import get_amount_from_format_devise, format_with_devise


def current_bill_right(request):
    right = False
    if not request.user.is_anonymous:
        contacts = Individual.objects.filter(user=request.user).distinct()
        right = len(contacts) > 0
    return right


@MenuManage.describ(current_bill_right, FORMTYPE_MODAL, 'core.general', _('View your invoices.'))
class CurrentBill(XferListEditor):
    short_icon = 'mdi:mdi-invoice-edit-outline'
    model = Bill
    field_id = 'bill'
    caption = _("Your invoices")

    def fillresponse_header(self):
        contacts = []
        for contact in Individual.objects.filter(user=self.request.user).distinct():
            contacts.append(contact.id)
        for contact in LegalEntity.objects.filter(responsability__individual__user=self.request.user).distinct():
            contacts.append(contact.id)
        self.filter = Q(third__contact_id__in=contacts) & ~Q(status=Bill.STATUS_BUILDING)

    def change_grid_action(self):
        bill_grid = self.get_components('bill')
        old_actions = bill_grid.actions
        bill_grid.actions = []
        for action in old_actions:
            if action[0].method != 'POST':
                bill_grid.actions.append(action)
        return bill_grid

    def fillresponse(self):
        XferListEditor.fillresponse(self)
        bill_grid = self.change_grid_action()
        bill_grid.add_action(self.request, CurrentBillPrint.get_action(_("Print"), short_icon='mdi:mdi-printer-pos-edit-outline'), unique=SELECT_SINGLE, close=CLOSE_NO)
        if (len(PaymentMethod.objects.all()) > 0):
            bill_grid.add_action(self.request, CurrentPayableShow.get_action(_("Payment"), short_icon='mdi:mdi-account-cash-outline'),
                                 unique=SELECT_SINGLE, close=CLOSE_NO, params={'item_name': self.field_id})


@MenuManage.describ(current_bill_right)
class CurrentBillPrint(BillPrint):
    pass


@MenuManage.describ(current_bill_right)
class CurrentPayableShow(PayableShow):
    pass


@MenuManage.describ(lambda request: Params.getvalue('invoice-order-mode') == Bill.INVOICE_ORDER_LINK)
class InvoiceValidQuotation(CheckPaymentGeneric):
    methods_allowed = ('GET', 'POST')
    caption = _("Validation")

    class PaymentMethodValidate(object):
        def __init__(self, bill):
            self.bill = bill

        @property
        def id(self):
            return -100

        @property
        def paytypetext(self):
            return _('validation of %s without payment') % self.bill.billtype

        def show_pay(self, absolute_uri, lang, supporting):
            return """{[center]}
%(validation_text)s{[br]}
{[a href='%(uri)s/diacamma.invoice/invoiceValidQuotation?payid=%(billid)s' name='validate' target='_blank']}
{[button]}
{[img src="%(uri)s/static/lucterios.CORE/images/ok.png" title="Ok" alt="Ok"]} %(validation)s
{[/button]}
{[/a]}
{[/center]}""" % {
                'uri': absolute_uri,
                'billid': self.bill.id,
                'validation_text': _('By clicking here, you accept this %s, you will have to send the payment later.') % self.bill.billtype,
                'validation': _('validation')
            }

    def get_form(self):
        root_url = self.getparam("url", get_url_from_request(self.request))
        if self.getparam("CONFIRME") is None:
            if (self.support.status != Bill.STATUS_VALID) or (self.support.bill_type != Bill.BILLTYPE_QUOTATION):
                raise LucteriosException(IMPORTANT, _("This item can not be validated !"))
            invoice_data = {'type': self.support.billtype, 'num': self.support.num_txt,
                            'url': root_url, 'firstname': _('your firstname'), 'lastname': _('your lastname'),
                            'payid': self.support.id, 'title': self.caption,
                            'client': str(self.support.third), 'amount': get_amount_from_format_devise(self.support.total, 5).replace("{[p", "{[span").replace("{[/p", "{[/span"),
                            'fromtxt': _('from'), 'amounttxt': _('amount'),
                            }
            return """
{[form method="post" id="validation" name="validation" action="%(url)s/diacamma.invoice/invoiceValidQuotation"]}
{[input type="hidden" name="payid" value="%(payid)s"]}
{[input type="hidden" name="CONFIRME" value="True"]}
{[table style="margin-left: auto;margin-right: auto;margin-bottom:10px;"]}
    {[tr]}{[td colspan="2" style="text-align: left;"padding: 10px;"]}
%(type)s %(num)s{[br]}
- %(fromtxt)s: %(client)s{[br]}
- %(amounttxt)s: %(amount)s{[br]}
{[/td]}{[/tr]}
    {[tr]}{[th style="padding: 10px;"]}%(firstname)s{[/th]}{[td style="padding: 10px;"]}{[input type="text" name="firstname" required="required"]}{[/td]}{[/tr]}
    {[tr]}{[th style="padding: 10px;"]}%(lastname)s{[/th]}{[td style="padding: 10px;"]}{[input type="text" name="lastname" required="required"]}{[/td]}{[/tr]}
    {[tr]}{[td colspan="2" style="text-align: left;"padding: 10px;"]}
{[/table]}
{[button type="submit" style="margin:auto;"]}
    {[img src="%(url)s/static/lucterios.CORE/images/ok.png" title="Ok" alt="Ok"]}%(title)s
{[/button]}
{[/form]}
""" % invoice_data
        else:
            if self.support.categoryBill_id is None:
                typetarget = get_value_if_choices(Bill.BILLTYPE_ORDER, Bill.get_field_by_name("bill_type"))
            else:
                typetarget = self.support.categoryBill.get_title(Bill.BILLTYPE_ORDER)
            validate_comment = "{[i]}%s{[/i]}" % (_("%(typetarget)s from the validation of the %(typesource)s %(num)s by %(firstname)s %(lastname)s on %(date)s") % {
                'typetarget': typetarget,
                'typesource': self.support.billtype,
                'num': self.support.num_txt,
                'firstname': self.getparam("firstname", ''),
                'lastname': self.getparam("lastname", ''),
                'date': get_date_formating(datetime.now())
            },)
            if self.support.comment != '':
                validate_comment = self.support.comment + '{[br]}' + validate_comment
            new_order = self.support.convert_to_order(validate_comment)
            new_order.send_email_by_type()
            return _("%(typesource)s validated by %(firstname)s %(lastname)s") % {
                'typesource': self.support.billtype,
                'firstname': self.getparam("firstname", ''),
                'lastname': self.getparam("lastname", '')}

    @property
    def sub_title_default(self):
        if self.getparam("CONFIRME") is None:
            return _("Do you want validate this %(type)s?") % {"type": self.support.billtype}
        else:
            return ""

    @property
    def sub_title_error(self):
        return _("It is not possible to validate this %(type)s !") % {"type": self.support.billtype}


def current_cart_right(request):
    if not Params.getvalue('invoice-cart-active'):
        return False
    if not request.user.is_anonymous:
        contacts = Individual.objects.filter(user=request.user).first()
    else:
        contacts = None
    if (contacts is not None) and WrapAction(caption='', short_icon='mdi:mdi-check', is_view_right='invoice.cart_bill').check_permission(request):
        return True
    else:
        return False


@MenuManage.describ(current_cart_right, FORMTYPE_MODAL, 'core.general', _('To fill your shopping cart'))
class CurrentCart(XferContainerCustom):
    short_icon = 'mdi:mdi-cart-variant'
    model = Bill
    field_id = 'bill'
    caption = _("Shopping cart")

    size_by_page = 5

    def show_cart(self):
        contacts = Individual.objects.filter(user=self.request.user).first()
        third = get_or_create_customer(contacts.id)
        Bill.clean_timeout_cart(third)
        self.item = Bill.objects.filter(bill_type=Bill.BILLTYPE_CART, status=Bill.STATUS_BUILDING, third=third).first()
        if self.item is None:
            self.item = Bill.objects.create(bill_type=Bill.BILLTYPE_CART, status=Bill.STATUS_BUILDING,
                                            third=third, date=timezone.now(), categoryBill=CategoryBill.objects.all().order_by("-is_default").first())
        cart_info = _("{[center]}%(nb_art)d article(s){[center]}{[i]}%(amount)s{[/i]}") % {"nb_art": self.item.detail_set.count(),
                                                                                           "amount": get_amount_from_format_devise(self.item.total, 5)}

        row = self.get_max_row() + 1
        lbl = XferCompLabelForm('cart_title')
        lbl.set_location(5, row, 2)
        lbl.set_value_as_infocenter(_('Cart'))
        self.add_component(lbl)
        lbl = XferCompLabelForm('cart_info')
        lbl.set_location(5, row + 1, 2)
        lbl.set_value(cart_info)
        self.add_component(lbl)
        btn = XferCompButton('cart_btn')
        btn.set_location(5, row + 2, 0)
        btn.set_action(self.request, CurrentCartShow.get_action(), close=CLOSE_YES, params={'bill': self.item.id})
        self.add_component(btn)
        btn = XferCompButton('cart_del_btn')
        btn.set_location(5, row + 3, 0)
        btn.set_action(self.request, CurrentCartDel.get_action(TITLE_DELETE, short_icon='mdi:mdi-delete-outline'), close=CLOSE_NO, params={'bill': self.item.id})
        self.add_component(btn)
        lbl = XferCompLabelForm('cart_sep')
        lbl.set_location(0, row + 4, 10)
        lbl.set_value("{[hr/]}")
        self.add_component(lbl)

    def filter_selector(self):
        row = self.get_max_row() + 1
        cat_list = Category.objects.filter(self.category_filter)
        if len(cat_list) > 0:
            filter_cat = self.getparam('cat_filter', Params.getvalue('invoice-cart-default-category'))
            edt = XferCompSelect("cat_filter")
            edt.set_select_query(cat_list)
            edt.set_value(filter_cat)
            edt.set_location(0, row, 5)
            edt.set_needed(False)
            edt.description = _('categories')
            edt.set_action(self.request, self.return_action('', ''), modal=FORMTYPE_REFRESH, close=CLOSE_NO)
            self.add_component(edt)
        ref_filter = self.getparam('ref_filter', '')
        edt = XferCompEdit("ref_filter")
        edt.set_value(ref_filter)
        edt.set_location(0, row + 1, 5)
        edt.set_needed(False)
        edt.description = _('keyword')
        edt.set_action(self.request, self.return_action(), modal=FORMTYPE_REFRESH, close=CLOSE_NO)

        self.add_component(edt)

    def show_article(self, article, row):
        lbl = XferCompLabelForm('sep_article_%d' % article.id)
        lbl.set_location(0, row, 7)
        lbl.set_value("{[hr/]}")
        self.add_component(lbl)
        if Params.getvalue("invoice-article-with-picture"):
            img = XferCompImage('img_article_%d' % article.id)
            img.type = 'jpg'
            img.set_value(article.image)
            img.set_location(0, row + 1, 1, 3)
            self.add_component(img)
        lbl = XferCompLabelForm('ref_article_%d' % article.id)
        lbl.set_location(1, row + 1)
        lbl.set_value(article.reference)
        lbl.description = _('reference')
        self.add_component(lbl)
        lbl = XferCompLabelForm('design_article_%d' % article.id)
        lbl.set_location(1, row + 2)
        lbl.set_value(article.designation)
        lbl.description = _('designation')
        self.add_component(lbl)
        lbl = XferCompLabelForm('categories_article_%d' % article.id)
        lbl.set_location(2, row + 1)
        lbl.set_value([str(cat) for cat in article.categories.all()])
        lbl.description = _('categories')
        self.add_component(lbl)
        lbl = XferCompLabelForm('price_article_%d' % article.id)
        lbl.set_location(4, row + 1, 2)
        lbl.set_value(article.get_price_from_third(self.item.third_id))
        lbl.set_format(format_with_devise(5))
        lbl.description = _('price')
        self.add_component(lbl)

        if article.stockable != Article.STOCKABLE_NO:
            max_qty = 0
            for val in article.get_stockage_values():
                if val[0] == 0:
                    continue
                area_qty = val[2]
                det = Detail.objects.filter(bill=self.item, article=article, storagearea_id=val[0]).first()
                if det is not None:
                    area_qty = max(0.0, area_qty - float(det.quantity))
                max_qty += area_qty
        else:
            max_qty = 100_000_000
        epsilone = 0.1**(article.qtyDecimal + 1)
        if abs(max_qty) < epsilone:
            lbl = XferCompLabelForm('no_article_%d' % article.id)
            lbl.set_location(2, row + 2, 6)
            lbl.set_color('red')
            lbl.set_value_as_headername(_("sold out"))
            self.add_component(lbl)
        else:
            ed_page = XferCompFloat('qty_article_%d' % article.id, 0, max_qty, article.qtyDecimal)
            ed_page.set_location(2, row + 2)
            ed_page.set_value(self.getparam('qty_article_%d' % article.id, 1))
            ed_page.description = _('quantity')
            self.add_component(ed_page)
            lbl = XferCompLabelForm('unit_article_%d' % article.id)
            lbl.set_location(3, row + 2)
            lbl.set_value(article.unit)
            self.add_component(lbl)
            btn = XferCompButton('add_article_%d' % article.id)
            btn.set_location(4, row + 2, 4, 2)
            btn.set_action(self.request, CurrentCartAddArticle.get_action(_("add in cart"), short_icon='mdi:mdi-pencil-plus-outline'), modal=FORMTYPE_MODAL, close=CLOSE_NO, params={'article': article.id, "bill": self.item.id})
            self.add_component(btn)

    def search_articles(self):
        art_filter = Q(isdisabled=False)
        savecritera_article = Params.getobject("invoice-cart-article-filter")
        self.category_filter = Q()
        if savecritera_article is not None:
            category_criteria = dumps([cirteria_item for cirteria_item in loads(savecritera_article.criteria) if cirteria_item[0].startswith('categories')])
            category_criteria = category_criteria.replace('categories.', '').replace('categories', 'id')
            self.category_filter, _desc = get_search_query_from_criteria(category_criteria, Category)
            filter_result, _desc = get_search_query_from_criteria(savecritera_article.criteria, Article)
            art_filter &= filter_result
        filter_cat = self.getparam('cat_filter', Params.getvalue('invoice-cart-default-category'))
        if filter_cat != 0:
            art_filter &= Q(categories__in=[Category.objects.get(id=filter_cat)])
        for ref_filter in self.getparam('ref_filter', '').split(' '):
            art_filter &= Q(designation__icontains=ref_filter) | Q(reference__icontains=ref_filter)
        return Article.objects.filter(art_filter)

    def show_articles(self):
        nb_lines = len(self.articles)
        page_max = int(nb_lines / self.size_by_page) + 1
        num_page = max(1, min(self.getparam('num_page', 0), page_max))
        record_min = int((num_page - 1) * self.size_by_page)
        record_max = int(num_page * self.size_by_page)

        lbl = XferCompLabelForm('search_result')
        lbl.set_location(5, self.get_max_row() - 1, 3, 2)
        lbl.set_value_as_header(_("%s items match your search") % nb_lines)
        self.add_component(lbl)

        row = self.get_max_row() + 1
        btn = XferCompButton('before')
        btn.set_is_mini(True)
        btn.set_location(0, row)
        btn.set_action(self.request, self.return_action("<", short_icon='mdi:mdi-page-previous-outline'), modal=FORMTYPE_REFRESH, close=CLOSE_NO, params={'num_page': max(1, num_page - 1)})
        self.add_component(btn)
        ed_page = XferCompFloat('num_page', 1, page_max, 0)
        ed_page.set_location(1, row)
        ed_page.set_value(num_page)
        ed_page.set_action(self.request, self.return_action(), modal=FORMTYPE_REFRESH, close=CLOSE_NO)
        ed_page.description = _("page")
        self.add_component(ed_page)
        lbl = XferCompLabelForm('article_range')
        lbl.set_location(2, row)
        lbl.set_value_as_name("/ %s" % page_max)
        self.add_component(lbl)
        btn = XferCompButton('after')
        btn.set_is_mini(True)
        btn.set_location(3, row)
        btn.set_action(self.request, self.return_action(">", short_icon='mdi:mdi-page-next-outline'), modal=FORMTYPE_REFRESH, close=CLOSE_NO, params={'num_page': min(num_page + 1, page_max)})
        self.add_component(btn)
        for article in self.articles[record_min: record_max]:
            row += 5
            self.show_article(article, row)

    def fillresponse(self):
        self.articles = self.search_articles()
        self.show_cart()
        self.filter_selector()
        self.show_articles()
        img = XferCompImage('img')
        img.set_value(self.short_icon, '#')
        img.set_location(0, 1, 1, 3)
        self.add_component(img)
        lbl = XferCompLabelForm('title')
        lbl.set_value_as_title(_("Add your articles in your cart"))
        lbl.set_location(1, 1, 4)
        self.add_component(lbl)
        btn = XferCompButton('catalog')
        btn.set_location(1, 2, 4)
        btn.set_action(self.request, CurrentCartCatalog.get_action(_("Print full catalog"), short_icon='mdi:mdi-printer-pos-edit-outline'), modal=FORMTYPE_MODAL, close=CLOSE_NO)
        self.add_component(btn)
        self.add_action(WrapAction(TITLE_CLOSE, short_icon='mdi:mdi-close'))


@MenuManage.describ(current_cart_right)
class CurrentCartDel(XferContainerAcknowledge):
    short_icon = 'mdi:mdi-cart-variant'
    model = Bill
    field_id = 'bill'
    caption = _("Clear")

    def fillresponse(self):
        if (self.item.status == Bill.STATUS_BUILDING) and (self.item.bill_type == Bill.BILLTYPE_CART):
            self.item.delete()


@MenuManage.describ(current_cart_right)
class CurrentCartAddArticle(XferContainerAcknowledge):
    short_icon = 'mdi:mdi-cart-variant'
    caption = _("Add article")
    model = Bill
    field_id = 'bill'

    def fillresponse(self, article):
        article = Article.objects.get(id=article)
        epsilone = 0.1**(article.qtyDecimal + 1)
        quantity = self.getparam('qty_article_%d' % article.id, 0.0)
        if abs(quantity) < epsilone:
            return
        storagearea_qty = {}
        if article.stockable != Article.STOCKABLE_NO:
            stockage_values = article.get_stockage_values()
            stockage_values.sort(key=lambda item: item[2], reverse=True)
            for val in stockage_values:
                if val[0] == 0:
                    continue
                area_qty = val[2]
                det = Detail.objects.filter(bill=self.item, article=article, storagearea_id=val[0]).first()
                if det is not None:
                    area_qty = area_qty - float(det.quantity)
                if abs(area_qty) > epsilone:
                    storagearea_qty[val[0]] = min(area_qty, quantity)
                    quantity -= storagearea_qty[val[0]]
                if abs(quantity) < epsilone:
                    break
            if len(storagearea_qty) == 0:
                return
        else:
            storagearea_qty[None] = quantity
        for storagearea_id, qty in storagearea_qty.items():
            det = Detail.objects.filter(bill=self.item, article=article, storagearea_id=storagearea_id).first()
            if det is None:
                Detail.objects.create(bill=self.item, article=article, designation=article.designation,
                                      price=article.get_price_from_third(self.item.third_id), unit=article.unit,
                                      quantity=qty,
                                      storagearea_id=storagearea_id)
            else:
                det.quantity = float(det.quantity) + qty
                det.save()


@MenuManage.describ(current_cart_right)
class CurrentCartShow(BillShow):
    short_icon = 'mdi:mdi-cart-variant'
    caption = _("Cart")

    def fillresponse(self):
        BillShow.fillresponse(self)
        if self.item.status == Bill.STATUS_BUILDING:
            self.remove_component("comment")
        self.remove_component("status")
        self.remove_component("categoryBill")
        self.remove_component("bill_type")
        detail = self.get_components("detail")
        detail.actions = []
        if self.item.status == Bill.STATUS_BUILDING:
            detail.add_action(self.request, CurrentCartDelDetail.get_action(TITLE_DELETE, short_icon='mdi:mdi-delete-outline'), modal=FORMTYPE_MODAL, close=CLOSE_NO, unique=SELECT_SINGLE)
        self.actions = []
        if self.item.status == Bill.STATUS_BUILDING:
            self.add_action(CurrentCartValid.get_action(Bill.transitionname__valid, short_icon='mdi:mdi-share'), modal=FORMTYPE_MODAL, close=CLOSE_NO, params={"TRANSITION": "valid"})
        self.add_action(CurrentCart.get_action(caption=_("Return")), modal=FORMTYPE_MODAL, close=CLOSE_YES)
        self.add_action(WrapAction(TITLE_CLOSE, short_icon='mdi:mdi-close'))


@MenuManage.describ(current_cart_right)
class CurrentCartCatalog(XferPrintListing):
    short_icon = 'mdi:mdi-invoice-list-outline'
    model = Article
    field_id = 'article'
    caption = _("Full catalog")

    def filter_callback(self, items):
        art_filter = Q(isdisabled=False)
        savecritera_article = Params.getobject("invoice-cart-article-filter")
        if savecritera_article is not None:
            filter_result, _desc = get_search_query_from_criteria(savecritera_article.criteria, Article)
            art_filter &= filter_result
        return items.filter(art_filter)

    def _initialize(self, request, *args, **kwargs):
        XferPrintListing._initialize(self, request, *args, **kwargs)
        self.params["PRINT_MODE"] = PRINT_PDF_FILE
        self.params['WITHNUM'] = False
        self.params['INFO'] = _("{[b]}Catalog dated{[/b]} %s") % get_date_formating(timezone.now().date())


@MenuManage.describ(current_cart_right)
class CurrentCartDelDetail(DetailDel):
    pass


@MenuManage.describ(current_cart_right)
class CurrentCartValid(XferTransition):
    short_icon = 'mdi:mdi-invoice-edit-outline'
    model = Bill
    field_id = 'bill'

    def fillresponse(self):
        self.fill_confirm()

    def confirme_with_comment(self):
        if self.getparam("CONFIRME") is not None:
            return self.params["CONFIRME"] != ""
        else:
            dlg = self.create_custom(Bill)
            dlg.caption = _("Confirmation")
            icon = XferCompImage('img')
            icon.set_location(0, 0, 1, 6)
            icon.set_value('mdi:mdi-help-circle-outline', '#')
            dlg.add_component(icon)
            lbl = XferCompLabelForm('lb_title')
            lbl.set_value_as_headername(_("Do you want to validate this cart ?"))
            lbl.set_location(1, 0)
            dlg.add_component(lbl)
            commentcmp = XferCompMemo('comment')
            commentcmp.description = _('comment on your cart and its delivery')
            commentcmp.set_location(1, 2)
            commentcmp.set_needed(True)
            commentcmp.with_hypertext = True
            commentcmp.set_value(Params.getvalue('invoice-cart-default-comment'))
            dlg.add_component(commentcmp)
            dlg.add_action(self.return_action(_('Yes'), short_icon='mdi:mdi-check'), params={"CONFIRME": "YES"})
            dlg.add_action(WrapAction(TITLE_NO, short_icon='mdi:mdi-cancel'))
            return False

    def fill_confirm(self):
        if self.confirme_with_comment():
            self.item.date = timezone.now()
            self.item.comment = self.getparam('comment', '')
            self._confirmed("valid")


def referent_storage(request):
    right = False
    if not request.user.is_anonymous:
        contact = Individual.objects.filter(user=request.user).first()
        if contact is not None:
            right = StorageArea.objects.filter(contact=contact).count() > 0
    return right


@MenuManage.describ(referent_storage, FORMTYPE_MODAL, 'core.general', _('View invoices of storage managed.'))
class CurrentBillForStorageManager(CurrentBill):
    short_icon = 'mdi:mdi-store-outline'
    model = Bill
    field_id = 'bill'
    caption = _("Storage managed")

    def fillresponse_header(self):
        bill_type, category = _add_type_filter_selector(self, self.get_max_row() + 1, 1)
        contact = Individual.objects.filter(user=self.request.user).first()
        self.filter = Q(detail__storagearea__contact=contact) & ~Q(status=Bill.STATUS_ARCHIVE) & ~Q(status=Bill.STATUS_CANCEL)
        if bill_type != Bill.BILLTYPE_ALL:
            self.filter &= Q(bill_type=bill_type) & Q(categoryBill_id=category)

    def fillresponse(self):
        XferListEditor.fillresponse(self)
        self.change_grid_action()
