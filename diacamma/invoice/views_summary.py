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

from django.utils.translation import ugettext_lazy as _
from django.db.models import Q
from django.utils import timezone

from lucterios.framework.tools import MenuManage, FORMTYPE_MODAL, SELECT_SINGLE, CLOSE_NO, WrapAction, FORMTYPE_REFRESH, CLOSE_YES
from lucterios.framework.xferadvance import XferListEditor, TITLE_CLOSE, TITLE_DELETE, XferTransition

from lucterios.contacts.models import Individual, LegalEntity
from lucterios.CORE.parameters import Params

from diacamma.invoice.models import Bill, Category, get_or_create_customer, Article, Detail, CategoryBill
from diacamma.invoice.views import BillPrint, BillShow, DetailDel
from diacamma.payoff.models import PaymentMethod
from diacamma.payoff.views import PayableShow
from lucterios.framework.xfergraphic import XferContainerCustom, XferContainerAcknowledge
from lucterios.framework.xfercomponents import XferCompLabelForm, XferCompSelect, XferCompEdit, XferCompButton, XferCompFloat, XferCompImage
from diacamma.accounting.tools import get_amount_from_format_devise, format_with_devise


def current_bill_right(request):
    right = False
    if not request.user.is_anonymous:
        contacts = Individual.objects.filter(user=request.user).distinct()
        right = len(contacts) > 0
    return right


@MenuManage.describ(current_bill_right, FORMTYPE_MODAL, 'core.general', _('View your invoices.'))
class CurrentBill(XferListEditor):
    icon = "bill.png"
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

    def fillresponse(self):
        XferListEditor.fillresponse(self)
        bill_grid = self.get_components('bill')
        bill_grid.add_action(self.request, CurrentBillPrint.get_action(_("Print"), "images/print.png"), unique=SELECT_SINGLE, close=CLOSE_NO)
        if (len(PaymentMethod.objects.all()) > 0):
            bill_grid.add_action(self.request, CurrentPayableShow.get_action(_("Payment"), "diacamma.payoff/images/payments.png"),
                                 unique=SELECT_SINGLE, close=CLOSE_NO, params={'item_name': self.field_id})


@MenuManage.describ(current_bill_right)
class CurrentBillPrint(BillPrint):
    pass


@MenuManage.describ(current_bill_right)
class CurrentPayableShow(PayableShow):
    pass


def current_cart_right(request):
    if not request.user.is_anonymous:
        contacts = Individual.objects.filter(user=request.user).first()
    else:
        contacts = None
    if (contacts is not None) and WrapAction(caption='', icon_path='', is_view_right='invoice.cart_bill').check_permission(request):
        return True
    else:
        return False


@MenuManage.describ(current_cart_right, FORMTYPE_MODAL, 'core.general', _('To fill your shopping cart'))
class CurrentCart(XferContainerCustom):
    icon = "storage.png"
    model = Bill
    field_id = 'bill'
    caption = _("Purchasing center")

    size_by_page = 5

    def show_cart(self):
        contacts = Individual.objects.filter(user=self.request.user).first()
        third = get_or_create_customer(contacts.id)
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
        btn.set_action(self.request, CurrentCartDel.get_action(), close=CLOSE_NO, params={'bill': self.item.id})
        self.add_component(btn)
        lbl = XferCompLabelForm('cart_sep')
        lbl.set_location(0, row + 4, 10)
        lbl.set_value("{[hr/]}")
        self.add_component(lbl)

    def filter_selector(self):
        row = self.get_max_row() + 1
        cat_list = Category.objects.all()
        if len(cat_list) > 0:
            filter_cat = self.getparam('cat_filter', 0)
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
        lbl.set_value(article.price)
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
            ed_page.set_value(self.getparam('qty_article_%d' % article.id, 0))
            ed_page.description = _('quantity')
            self.add_component(ed_page)
            lbl = XferCompLabelForm('unit_article_%d' % article.id)
            lbl.set_location(3, row + 2)
            lbl.set_value(article.unit)
            self.add_component(lbl)
            btn = XferCompButton('add_article_%d' % article.id)
            btn.set_location(4, row + 2, 4, 2)
            btn.set_action(self.request, CurrentCartAddArticle.get_action(_("add in cart"), "images/add.png"), modal=FORMTYPE_MODAL, close=CLOSE_NO, params={'article': article.id, "bill": self.item.id})
            self.add_component(btn)

    def search_articles(self):
        art_filter = Q(isdisabled=False)
        filter_cat = self.getparam('cat_filter', 0)
        if filter_cat != 0:
            art_filter &= Q(categories__in=[Category.objects.get(id=filter_cat)])
        for ref_filter in self.getparam('ref_filter', '').split(' '):
            art_filter &= Q(designation__icontains=ref_filter) | Q(reference__icontains=ref_filter)
        return Article.objects.filter(art_filter)

    def show_articles(self):
        articles = self.search_articles()

        nb_lines = len(articles)
        page_max = int(nb_lines / self.size_by_page) + 1
        num_page = max(1, min(self.getparam('num_page', 0), page_max))
        record_min = int((num_page - 1) * self.size_by_page)
        record_max = int(num_page * self.size_by_page)

        row = self.get_max_row() + 1
        btn = XferCompButton('before')
        btn.set_is_mini(True)
        btn.set_location(0, row)
        btn.set_action(self.request, self.return_action("<", "images/left.png"), modal=FORMTYPE_REFRESH, close=CLOSE_NO, params={'num_page': max(1, num_page - 1)})
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
        btn.set_action(self.request, self.return_action(">", "images/right.png"), modal=FORMTYPE_REFRESH, close=CLOSE_NO, params={'num_page': min(num_page + 1, page_max)})
        self.add_component(btn)
        for article in articles[record_min: record_max]:
            row += 5
            self.show_article(article, row)

    def fillresponse(self):
        self.show_cart()
        self.filter_selector()
        self.show_articles()
        img = XferCompImage('img')
        img.set_value(self.icon_path())
        img.set_location(0, 1, 1, 3)
        self.add_component(img)
        lbl = XferCompLabelForm('title')
        lbl.set_value_as_title(_("Add your articles in your cart"))
        lbl.set_location(1, 1, 4, 3)
        self.add_component(lbl)
        self.add_action(WrapAction(TITLE_CLOSE, 'images/close.png'))


@MenuManage.describ(current_cart_right)
class CurrentCartDel(XferContainerAcknowledge):
    icon = "images/delete.png"
    model = Bill
    field_id = 'bill'
    caption = _("Clear")

    def fillresponse(self):
        if (self.item.status == Bill.STATUS_BUILDING) and (self.item.bill_type == Bill.BILLTYPE_CART):
            self.item.delete()


@MenuManage.describ(current_cart_right)
class CurrentCartAddArticle(XferContainerAcknowledge):
    icon = "storage.png"
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
            for val in article.get_stockage_values():
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
            storagearea_qty[0] = quantity
        for storagearea_id, qty in storagearea_qty.items():
            det = Detail.objects.filter(bill=self.item, article=article, storagearea_id=storagearea_id).first()
            if det is None:
                Detail.objects.create(bill=self.item, article=article, designation=article.designation,
                                      price=article.price, unit=article.unit,
                                      quantity=qty,
                                      storagearea_id=storagearea_id)
            else:
                det.quantity = float(det.quantity) + qty
                det.save()


@MenuManage.describ(current_cart_right)
class CurrentCartShow(BillShow):
    icon = "storage.png"
    caption = _("Cart")

    def fillresponse(self):
        BillShow.fillresponse(self)
        self.remove_component("comment")
        self.remove_component("status")
        self.remove_component("categoryBill")
        self.remove_component("bill_type")
        detail = self.get_components("detail")
        detail.actions = []
        if self.item.status == Bill.STATUS_BUILDING:
            detail.add_action(self.request, CurrentCartDelDetail.get_action(TITLE_DELETE, "images/delete.png"), modal=FORMTYPE_MODAL, close=CLOSE_NO, unique=SELECT_SINGLE)
        self.actions = []
        if self.item.status == Bill.STATUS_BUILDING:
            self.add_action(CurrentCartValid.get_action(Bill.transitionname__valid, "images/transition.png"), modal=FORMTYPE_MODAL, close=CLOSE_NO, params={"TRANSITION": "valid"})
        self.add_action(CurrentCart.get_action(caption=_("Return")), modal=FORMTYPE_MODAL, close=CLOSE_YES)
        self.add_action(WrapAction(TITLE_CLOSE, 'images/close.png'))


@MenuManage.describ(current_cart_right)
class CurrentCartDelDetail(DetailDel):
    pass


@MenuManage.describ(current_cart_right)
class CurrentCartValid(XferTransition):
    icon = "bill.png"
    model = Bill
    field_id = 'bill'

    def fillresponse(self):
        self.fill_confirm()

    def fill_confirm(self):
        if self.confirme(_("Do you want to validate this cart ?")):
            self.item.date = timezone.now()
            self._confirmed("valid")
