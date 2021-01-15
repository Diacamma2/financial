# -*- coding: utf-8 -*-
'''
Describe view for Django

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
from django.db.models.query import QuerySet
from django.db.models import Q
from django.utils import formats, timezone

from lucterios.framework.tools import MenuManage, FORMTYPE_NOMODAL, ActionsManage, SELECT_SINGLE, SELECT_MULTI, CLOSE_YES, \
    FORMTYPE_REFRESH, CLOSE_NO, SELECT_NONE, WrapAction, convert_date
from lucterios.framework.xferadvance import XferListEditor, XferAddEditor, XferDelete, XferShowEditor, TITLE_ADD, TITLE_MODIFY, \
    TITLE_DELETE, TITLE_EDIT, XferTransition, TITLE_PRINT, TITLE_OK, TITLE_CANCEL, TITLE_CREATE,\
    action_list_sorted, TITLE_CLOSE
from lucterios.framework.xfercomponents import XferCompLabelForm, XferCompSelect, XferCompCheck,\
    XferCompCheckList, XferCompButton, XferCompDate, XferCompEdit, XferCompImage
from lucterios.framework.xferbasic import NULL_VALUE
from lucterios.framework.xfergraphic import XferContainerAcknowledge
from lucterios.framework.error import LucteriosException, GRAVE
from lucterios.CORE.xferprint import XferPrintAction, XferPrintListing
from lucterios.CORE.views import ObjectImport
from lucterios.CORE.editors import XferSavedCriteriaSearchEditor

from diacamma.accounting.tools import format_with_devise,\
    get_amount_from_format_devise
from diacamma.invoice.models import StorageSheet, StorageDetail, Category, StorageArea, InventoryDetail, InventorySheet, AccountPosting,\
    ArticleSituation, ArticleSituationSet
from diacamma.invoice.editors import add_filters


MenuManage.add_sub("storage", "invoice", "diacamma.invoice/images/storage.png", _("Storage"), _("Manage of storage"), 10)


def right_to_storage(request):
    if StorageSheetShow.get_action().check_permission(request):
        return len(StorageArea.objects.all()) > 0
    else:
        return False


@MenuManage.describ(right_to_storage, FORMTYPE_NOMODAL, 'storage', _('Management of storage sheet list'))
class StorageSheetList(XferListEditor):
    icon = "storagesheet.png"
    model = StorageSheet
    field_id = 'storagesheet'
    caption = _("Storage sheet")

    def fillresponse_header(self):
        status_filter = self.getparam('status', 0)
        type_filter = self.getparam('sheet_type', -1)
        self.fill_from_model(0, 1, False, ['status', 'sheet_type'])
        sel_status = self.get_components('status')
        sel_status.select_list.insert(0, (-1, '---'))
        sel_status.set_value(status_filter)
        sel_status.set_action(self.request, self.return_action(), modal=FORMTYPE_REFRESH, close=CLOSE_NO)
        sel_type = self.get_components('sheet_type')
        sel_type.select_list.insert(0, (-1, '---'))
        sel_type.set_value(type_filter)
        sel_type.set_action(self.request, self.return_action(), modal=FORMTYPE_REFRESH, close=CLOSE_NO)
        self.filter = Q()
        if status_filter != -1:
            self.filter &= Q(status=status_filter)
        if type_filter != -1:
            self.filter &= Q(sheet_type=type_filter)


@ActionsManage.affect_list(_("Search"), "diacamma.invoice/images/storagesheet.png")
@MenuManage.describ('invoice.change_storagesheet')
class StorageSheetSearch(XferSavedCriteriaSearchEditor):
    icon = "storagesheet.png"
    model = StorageSheet
    field_id = 'storagesheet'
    caption = _("Search storage sheet")


@ActionsManage.affect_grid(TITLE_CREATE, "images/new.png", condition=lambda xfer, gridname='': xfer.getparam('status', -1) != StorageSheet.STATUS_VALID)
@ActionsManage.affect_show(TITLE_MODIFY, "images/edit.png", close=CLOSE_YES, condition=lambda xfer: xfer.item.status == StorageSheet.STATUS_BUILDING)
@MenuManage.describ('invoice.add_storagesheet')
class StorageSheetAddModify(XferAddEditor):
    icon = "storagesheet.png"
    model = StorageSheet
    field_id = 'storagesheet'
    caption_add = _("Add storage sheet")
    caption_modify = _("Modify storage sheet")


@ActionsManage.affect_grid(TITLE_EDIT, "images/show.png", unique=SELECT_SINGLE)
@MenuManage.describ('invoice.change_storagesheet')
class StorageSheetShow(XferShowEditor):
    caption = _("Show storage sheet")
    icon = "storagesheet.png"
    model = StorageSheet
    field_id = 'storagesheet'


@ActionsManage.affect_grid(TITLE_DELETE, "images/delete.png", unique=SELECT_MULTI, condition=lambda xfer, gridname='': xfer.getparam('status', -1) != StorageSheet.STATUS_VALID)
@MenuManage.describ('invoice.delete_storagesheet')
class StorageSheetDel(XferDelete):
    icon = "storagesheet.png"
    model = StorageSheet
    field_id = 'storagesheet'
    caption = _("Delete storage sheet")


@ActionsManage.affect_transition("status")
@MenuManage.describ('invoice.add_storagesheet')
class StorageSheetTransition(XferTransition):
    icon = "storagesheet.png"
    model = StorageSheet
    field_id = 'storagesheet'

    def fill_dlg(self):
        dlg = self.create_custom(StorageSheet)
        dlg.caption = _("Confirmation")
        icon = XferCompImage('img')
        icon.set_location(0, 0, 1, 6)
        icon.set_value(self.icon_path())
        dlg.add_component(icon)
        lbl = XferCompLabelForm('lb_title')
        lbl.set_value_as_infocenter(_("Do you want validate '%s'?") % self.item)
        lbl.set_location(1, 1)
        dlg.add_component(lbl)
        sel = XferCompSelect('target_area')
        sel.set_needed(True)
        sel.set_select_query(StorageArea.objects.exclude(id=self.item.storagearea_id))
        sel.set_location(1, 2)
        sel.description = _('target area')
        dlg.add_component(sel)
        dlg.add_action(self.return_action(TITLE_OK, 'images/ok.png'), params={"CONFIRME": "YES"})
        dlg.add_action(WrapAction(TITLE_CANCEL, 'images/cancel.png'))

    def fill_confirm(self, transition, trans):
        if (transition == 'valid') and (self.item.sheet_type == 2):
            target_area = self.getparam('target_area', 0)
            if (target_area != 0) and (self.getparam("CONFIRME") is not None):
                self.item.sheet_type = StorageSheet.TYPE_EXIT
                self.item.save()
                other_storage = self.item.create_oposit(target_area)
                self._confirmed(transition)
                other_storage.valid()
            else:
                self.fill_dlg()
        else:
            XferTransition.fill_confirm(self, transition, trans)


@MenuManage.describ('invoice.change_storagesheet')
@ActionsManage.affect_show(TITLE_PRINT, "images/print.png", condition=lambda xfer: int(xfer.item.status) == 1)
@ActionsManage.affect_grid(TITLE_PRINT, "images/print.png", unique=SELECT_SINGLE, condition=lambda xfer, gridname='': xfer.getparam('status', -1) == StorageSheet.STATUS_VALID)
class StorageSheetPrint(XferPrintAction):
    caption = _("Print storage sheet")
    icon = "report.png"
    model = StorageSheet
    field_id = 'bill'
    action_class = StorageSheetShow
    with_text_export = True


@ActionsManage.affect_grid(TITLE_ADD, "images/add.png", condition=lambda xfer, gridname='': hasattr(xfer.item, 'status') and (xfer.item.status == StorageSheet.STATUS_BUILDING))
@ActionsManage.affect_grid(TITLE_MODIFY, "images/edit.png", unique=SELECT_SINGLE, condition=lambda xfer, gridname='': hasattr(xfer.item, 'status') and (int(xfer.item.status) == StorageSheet.STATUS_BUILDING))
@MenuManage.describ('invoice.add_storagesheet')
class StorageDetailAddModify(XferAddEditor):
    icon = "storagesheet.png"
    model = StorageDetail
    field_id = 'storagedetail'
    caption_add = _("Add storage detail")
    caption_modify = _("Modify storage detail")


@ActionsManage.affect_grid(TITLE_DELETE, "images/delete.png", unique=SELECT_MULTI, condition=lambda xfer, gridname='': hasattr(xfer.item, 'status') and (int(xfer.item.status) == StorageSheet.STATUS_BUILDING))
@MenuManage.describ('invoice.delete_storagesheet')
class StorageDetailDel(XferDelete):
    icon = "storagesheet.png"
    model = StorageDetail
    field_id = 'storagedetail'
    caption = _("Delete storage detail")


@MenuManage.describ('contacts.add_vat')
@ActionsManage.affect_grid(_('Import'), "images/up.png", unique=SELECT_NONE, condition=lambda xfer, gridname='': hasattr(xfer.item, 'status') and (int(xfer.item.status) == 0))
class StorageDetailImport(ObjectImport):
    caption = _("Storage detail import")
    icon = "storagesheet.png"
    model = StorageDetail

    def get_select_models(self):
        return StorageDetail.get_select_contact_type(True)

    def _read_csv_and_convert(self):
        fields_description, csv_readed = ObjectImport._read_csv_and_convert(self)
        new_csv_readed = []
        for csv_readed_item in csv_readed:
            csv_readed_item['storagesheet_id'] = self.getparam("storagesheet", 0)
            new_csv_readed.append(csv_readed_item)
        return fields_description, new_csv_readed

    def _select_fields(self):
        ObjectImport._select_fields(self)
        storage_sheet = StorageSheet.objects.get(id=self.getparam('storagesheet', 0))
        if storage_sheet.sheet_type != StorageSheet.TYPE_RECEIPT:
            self.remove_component('fld_price')

    def fillresponse(self, modelname, quotechar="'", delimiter=";", encoding="utf-8", dateformat="%d/%m/%Y", step=0):
        ObjectImport.fillresponse(self, modelname, quotechar, delimiter, encoding, dateformat, step)
        if step != 3:
            self.move(0, 0, 1)
            self.tab = 0
            sheet = StorageSheet.objects.get(id=self.getparam("storagesheet", 0))
            lbl = XferCompLabelForm('sheet')
            lbl.set_value(str(sheet))
            lbl.set_location(1, 0, 2)
            lbl.description = _('storage sheet')
            self.add_component(lbl)


@MenuManage.describ(right_to_storage, FORMTYPE_NOMODAL, 'storage', _('Situation of storage'))
class StorageSituation(XferListEditor):
    icon = "storagereport.png"
    model = ArticleSituation
    field_id = 'articlesituation'
    caption = _("Situation")

    def __init__(self, **kwargs):
        XferListEditor.__init__(self, **kwargs)
        self.order_list = None

    def get_items_from_filter(self):
        return ArticleSituationSet(hints={'filter': self.filter, 'hide_empty': self.hide_empty, 'categories_filter': self.categories_filter})

    def fillresponse_header(self):
        self.get_components('title').colspan = 2
        show_storagearea = self.getparam('storagearea', 0)
        self.categories_filter = self.getparam('cat_filter', ())
        show_accountposting = self.getparam('accountposting', 0)
        show_datesituation = self.getparam('datesituation', 'NULL')
        self.hide_empty = self.getparam('hide_empty', True)
        ref_filter = self.getparam('ref_filter', '')

        sel_stock = XferCompSelect('storagearea')
        sel_stock.set_needed(False)
        sel_stock.set_select_query(StorageArea.objects.all())
        sel_stock.set_value(show_storagearea)
        sel_stock.set_action(self.request, self.return_action(), modal=FORMTYPE_REFRESH, close=CLOSE_NO)
        sel_stock.set_location(1, 4)
        sel_stock.description = StorageArea._meta.verbose_name
        self.add_component(sel_stock)

        edt = XferCompEdit("ref_filter")
        edt.set_value(ref_filter)
        edt.set_location(1, 5)
        edt.is_default = True
        edt.description = _('ref./designation')
        edt.set_action(self.request, self.return_action(), modal=FORMTYPE_REFRESH, close=CLOSE_NO)
        self.add_component(edt)

        sel_account = XferCompSelect('accountposting')
        sel_account.set_needed(False)
        sel_account.set_select_query(AccountPosting.objects.all())
        sel_account.set_value(show_accountposting)
        sel_account.set_action(self.request, self.return_action(), modal=FORMTYPE_REFRESH, close=CLOSE_NO)
        sel_account.set_location(1, 6)
        sel_account.description = AccountPosting._meta.verbose_name
        self.add_component(sel_account)

        date_situation = XferCompDate('datesituation')
        date_situation.set_needed(False)
        date_situation.set_value(show_datesituation)
        date_situation.set_action(self.request, self.return_action(), modal=FORMTYPE_REFRESH, close=CLOSE_NO)
        date_situation.set_location(2, 6)
        date_situation.description = _('date situation')
        self.add_component(date_situation)

        ckc = XferCompCheck("hide_empty")
        ckc.set_value(self.hide_empty)
        ckc.set_location(1, 7)
        ckc.description = _('hide articles without quantity')
        ckc.set_action(self.request, self.return_action(), modal=FORMTYPE_REFRESH, close=CLOSE_NO)
        self.add_component(ckc)

        cat_list = Category.objects.all()
        if len(cat_list) > 0:
            edt = XferCompCheckList("cat_filter")
            edt.set_select_query(cat_list)
            edt.set_value(self.categories_filter)
            edt.set_location(2, 4, 0, 2)
            edt.description = _('categories')
            edt.set_action(self.request, self.return_action(), modal=FORMTYPE_REFRESH, close=CLOSE_NO)
            self.add_component(edt)
        info_list = []
        self.filter = Q(storagesheet__status=1)
        if ref_filter != '':
            self.filter &= Q(article__reference__icontains=ref_filter) | Q(article__designation__icontains=ref_filter)
            info_list.append("{[b]}{[u]}%s{[/u]}{[/b]} : %s" % (_('ref./designation'), ref_filter))
        if show_storagearea != 0:
            self.filter &= Q(storagesheet__storagearea=show_storagearea)
            info_list.append("{[b]}{[u]}%s{[/u]}{[/b]} : %s" % (sel_stock.description, StorageArea.objects.get(id=show_storagearea)))
        if len(self.categories_filter) > 0:
            info_list.append("{[b]}{[u]}%s{[/u]}{[/b]} : %s" % (_('categories'), ", ".join([str(cat_item) for cat_item in Category.objects.filter(id__in=self.categories_filter)])))
        if show_accountposting != 0:
            self.filter &= Q(article__accountposting=show_accountposting)
            info_list.append("{[b]}{[u]}%s{[/u]}{[/b]} : %s" % (sel_account.description, AccountPosting.objects.get(id=show_accountposting)))
        if (show_datesituation is not None) and (show_datesituation != 'NULL'):
            self.filter &= Q(storagesheet__date__lte=show_datesituation)
        else:
            show_datesituation = timezone.now()
        info_list.append("{[b]}{[u]}%s{[/u]}{[/b]} : %s" % (_('date situation'), formats.date_format(convert_date(show_datesituation), "DATE_FORMAT")))
        self.params['INFO'] = '{[br]}'.join(info_list)

    def fillresponse_body(self):
        row_id = self.get_max_row()
        self.items = self.get_items_from_filter()
        self.fill_grid(row_id + 3, self.model, self.field_id, self.items)
        self.get_components(self.field_id).colspan = 3
        self.params['INFO'] = self.params['INFO'] + '{[br]}' + "{[b]}{[u]}%s{[/u]}{[/b]} : %s" % (_('total amount'), get_amount_from_format_devise(self.items.total_amount, 7))

        lbl = XferCompLabelForm("sep")
        lbl.set_value("{[hr/]}")
        lbl.set_location(0, row_id + 1, 3)
        self.add_component(lbl)

        btn = XferCompButton("refreshSituation")
        btn.set_action(self.request, self.return_action("", "images/refresh.png"), modal=FORMTYPE_REFRESH, close=CLOSE_NO)
        btn.set_is_mini(True)
        btn.set_location(0, row_id + 2)
        self.add_component(btn)

        lbl = XferCompLabelForm("nb")
        lbl.set_value(len(self.items))
        lbl.set_format('N0')
        lbl.set_location(1, row_id + 2)
        lbl.description = _('count of storage')
        self.add_component(lbl)

        lbl = XferCompLabelForm("total")
        lbl.set_value(self.items.total_amount)
        lbl.set_format(format_with_devise(5))
        lbl.set_location(2, row_id + 2)
        lbl.description = _('total amount')

        self.add_component(lbl)
        self.add_action(StorageSituationPrint.get_action(TITLE_PRINT, "images/print.png"), close=CLOSE_NO)


@MenuManage.describ('invoice.change_storagesheet')
class StorageSituationPrint(XferPrintListing):
    icon = "report.png"
    model = ArticleSituation
    field_id = 'articlesituation'
    caption = _("Situation")

    def fillresponse(self):
        show_storagearea = self.getparam('storagearea', 0)
        self.categories_filter = self.getparam('cat_filter', ())
        show_accountposting = self.getparam('accountposting', 0)
        show_datesituation = self.getparam('datesituation', 'NULL')
        self.hide_empty = self.getparam('hide_empty', True)
        ref_filter = self.getparam('ref_filter', '')
        self.filter = Q(storagesheet__status=1)
        if ref_filter != '':
            self.filter &= Q(article__reference__icontains=ref_filter) | Q(article__designation__icontains=ref_filter)
        if show_storagearea != 0:
            self.filter &= Q(storagesheet__storagearea=show_storagearea)
        if show_accountposting != 0:
            self.filter &= Q(article__accountposting=show_accountposting)
        if (show_datesituation is not None) and (show_datesituation != 'NULL'):
            self.filter &= Q(storagesheet__date__lte=show_datesituation)
        XferPrintListing.fillresponse(self)

    def filter_callback(self, items):
        return ArticleSituationSet(hints={'filter': self.filter, 'hide_empty': self.hide_empty, 'categories_filter': self.categories_filter})


@MenuManage.describ(right_to_storage, FORMTYPE_NOMODAL, 'storage', _('Historic of storage'))
class StorageHistoric(XferListEditor):
    icon = "storagereport.png"
    model = StorageDetail
    field_id = 'storagedetail'
    caption = _("Historic")

    def __init__(self, **kwargs):
        XferListEditor.__init__(self, **kwargs)
        self.fieldnames = ["article", "article.designation", "storagesheet.date", "storagesheet.storagearea",
                           "price", 'quantity']

    def get_items_from_filter(self):
        items = XferListEditor.get_items_from_filter(self)
        if len(self.categories_filter) > 0:
            for cat_item in Category.objects.filter(id__in=self.categories_filter):
                items = items.filter(article__categories__in=[cat_item])
        return items.order_by('-storagesheet__date')

    def fillresponse_header(self):
        date_begin = self.getparam('begin_date', 'NULL')
        date_end = self.getparam('end_date', 'NULL')
        show_storagearea = self.getparam('storagearea', 0)
        self.categories_filter = self.getparam('cat_filter', ())
        ref_filter = self.getparam('ref_filter', '')

        date_init = XferCompDate("begin_date")
        date_init.set_needed(False)
        date_init.set_value(date_begin)
        date_init.set_location(0, 3)
        date_init.description = _('begin date')
        date_init.set_action(self.request, self.return_action(), close=CLOSE_NO, modal=FORMTYPE_REFRESH)
        self.add_component(date_init)
        date_finish = XferCompDate("end_date")
        date_finish.set_needed(False)
        date_finish.set_value(date_end)
        date_finish.set_location(1, 3)
        date_finish.description = _('end date')
        date_finish.set_action(self.request, self.return_action(), close=CLOSE_NO, modal=FORMTYPE_REFRESH)
        self.add_component(date_finish)

        sel_stock = XferCompSelect('storagearea')
        sel_stock.set_needed(False)
        sel_stock.set_select_query(StorageArea.objects.all())
        sel_stock.set_value(show_storagearea)
        sel_stock.set_action(self.request, self.return_action(), modal=FORMTYPE_REFRESH, close=CLOSE_NO)
        sel_stock.set_location(0, 4)
        sel_stock.description = StorageArea._meta.verbose_name
        self.add_component(sel_stock)

        edt = XferCompEdit("ref_filter")
        edt.set_value(ref_filter)
        edt.set_location(0, 5)
        edt.is_default = True
        edt.description = _('ref./designation')
        edt.set_action(self.request, self.return_action(), modal=FORMTYPE_REFRESH, close=CLOSE_NO)
        self.add_component(edt)

        cat_list = Category.objects.all()
        if len(cat_list) > 0:
            edt = XferCompCheckList("cat_filter")
            edt.set_select_query(cat_list)
            edt.set_value(self.categories_filter)
            edt.set_location(1, 4, 0, 2)
            edt.description = _('categories')
            edt.set_action(self.request, self.return_action(), modal=FORMTYPE_REFRESH, close=CLOSE_NO)
            self.add_component(edt)
        self.filter = Q(storagesheet__status=1)
        if show_storagearea != 0:
            self.filter &= Q(storagesheet__storagearea=show_storagearea)
        if (date_begin is not None) and (date_begin != NULL_VALUE):
            self.filter &= Q(storagesheet__date__gte=date_begin)
        if (date_end is not None) and (date_end != NULL_VALUE):
            self.filter &= Q(storagesheet__date__lte=date_end)
        if ref_filter != '':
            self.filter &= Q(article__reference__icontains=ref_filter) | Q(article__designation__icontains=ref_filter)

    def fillresponse_body(self):
        XferListEditor.fillresponse_body(self)
        self.add_action(StorageHistoricPrint.get_action(TITLE_PRINT, "images/print.png"), close=CLOSE_NO)


@MenuManage.describ('invoice.change_storagesheet')
class StorageHistoricPrint(XferPrintAction):
    caption = _("Print historic")
    icon = "report.png"
    model = StorageSheet
    field_id = 'storagedetail'
    action_class = StorageHistoric
    with_text_export = True


def right_to_inventory(request):
    if InventorySheetShow.get_action().check_permission(request):
        return len(StorageArea.objects.all()) > 0
    else:
        return False


@MenuManage.describ(right_to_inventory, FORMTYPE_NOMODAL, 'storage', _('Management of inventory sheet list'))
class InventorySheetList(XferListEditor):
    icon = "inventorysheet.png"
    model = InventorySheet
    field_id = 'inventorysheet'
    caption = _("Inventory sheet")

    def fillresponse_header(self):
        status_filter = self.getparam('status', 0)
        self.fill_from_model(0, 1, False, ['status'])
        sel_status = self.get_components('status')
        sel_status.select_list.insert(0, (-1, '---'))
        sel_status.set_value(status_filter)
        sel_status.set_action(self.request, self.return_action(), modal=FORMTYPE_REFRESH, close=CLOSE_NO)
        self.filter = Q()
        if status_filter != -1:
            self.filter &= Q(status=status_filter)


@ActionsManage.affect_grid(TITLE_CREATE, "images/new.png", condition=lambda xfer, gridname='': xfer.getparam('status', -1) != InventorySheet.STATUS_VALID)
@ActionsManage.affect_show(TITLE_MODIFY, "images/edit.png", close=CLOSE_YES, condition=lambda xfer: xfer.item.status == StorageSheet.STATUS_BUILDING)
@MenuManage.describ('invoice.add_inventorysheet')
class InventorySheetAddModify(XferAddEditor):
    icon = "inventorysheet.png"
    model = InventorySheet
    field_id = 'inventorysheet'
    caption_add = _("Add storage sheet")
    caption_modify = _("Modify storage sheet")


@ActionsManage.affect_grid(TITLE_EDIT, "images/show.png", unique=SELECT_SINGLE)
@MenuManage.describ('invoice.change_inventorysheet')
class InventorySheetShow(XferListEditor):
    caption = _("Show inventory sheet")
    icon = "inventorysheet.png"
    model = InventorySheet
    field_id = 'inventorysheet'

    def show_sheetinfo(self):
        self.get_components('img').rowspan = 3
        self.get_components('title').colspan = 2
        self.old_item = self.item
        self.fill_from_model(1, 2, True, InventorySheet.get_show_fields())
        self.filter = Q(inventorysheet=self.item)
        self.model = InventoryDetail
        self.item = InventoryDetail()
        self.field_id = 'inventorydetail'
        lbl = XferCompLabelForm('sep_filter')
        lbl.set_value("{[hr/]}")
        lbl.set_location(0, 9, 3)
        self.add_component(lbl)

    def fillresponse_header(self):
        self.show_sheetinfo()
        add_filters(self, 1, 10, True)
        self.filter_entermode = self.getparam('enter_mode', 0)
        if self.old_item.status == InventorySheet.STATUS_BUILDING:
            select = XferCompSelect('enter_mode')
            select.set_select([(0, _('All')), (1, _('Only the non-entered')), (2, _('Only the entered')), (3, _('Only with quantity'))])
            select.set_value(self.filter_entermode)
            select.set_location(1, self.get_max_row() + 1, 2)
            select.description = _('Filter by elements')
            select.set_action(self.request, self.return_action('', ''), modal=FORMTYPE_REFRESH, close=CLOSE_NO)
            self.add_component(select)
        else:
            self.filter_entermode = 0

        filter_thirdid = self.getparam('third', 0)
        filter_ref = self.getparam('reference', '')
        filter_lib = self.getparam('ref_filter', '')
        if filter_thirdid != 0:
            self.filter &= Q(article__provider__third_id=filter_thirdid)
        if filter_ref != '':
            self.filter &= Q(article__provider__reference__icontains=filter_ref)
        if filter_lib != '':
            self.filter &= Q(article__reference__icontains=filter_lib) | Q(article__designation__icontains=filter_lib)
        if self.filter_entermode in (1, 2):
            self.filter &= Q(quantity__isnull=(self.filter_entermode == 1))

    def get_items_from_filter(self):
        items = XferListEditor.get_items_from_filter(self)
        filter_cat = self.getparam('cat_filter', ())
        if len(filter_cat) > 0:
            for cat_item in Category.objects.filter(id__in=filter_cat).distinct():
                items = items.filter(article__categories__in=[cat_item]).distinct()
        if (self.filter_entermode == 3):
            res = QuerySet(model=InventoryDetail)
            res._result_cache = [item for item in items if item.real_quantity > 1e-3]
            return res
        else:
            return items

    def fillresponse_body(self):
        XferListEditor.fillresponse_body(self)
        self.model = InventorySheet
        self.item = self.old_item
        inventorydetail_grid = self.get_components('inventorydetail')
        inventorydetail_grid.colspan = 3
        if int(self.item.status) == InventorySheet.STATUS_VALID:
            inventorydetail_grid.delete_header('real_quantity_txt')

    def fillresponse(self):
        XferListEditor.fillresponse(self)
        self.actions = []
        for act, opt in ActionsManage.get_actions(ActionsManage.ACTION_IDENT_SHOW, self, key=action_list_sorted):
            self.add_action(act, **opt)
        self.add_action(WrapAction(TITLE_CLOSE, 'images/close.png'))


@ActionsManage.affect_grid(TITLE_DELETE, "images/delete.png", unique=SELECT_MULTI, condition=lambda xfer, gridname='': xfer.getparam('status', -1) != InventorySheet.STATUS_VALID)
@MenuManage.describ('invoice.delete_inventorysheet')
class InventorySheetDel(XferDelete):
    icon = "inventorysheet.png"
    model = InventorySheet
    field_id = 'inventorysheet'
    caption = _("Delete inventory sheet")


@ActionsManage.affect_transition("status")
@MenuManage.describ('invoice.add_inventorysheet')
class InventorySheetTransition(XferTransition):
    icon = "inventorysheet.png"
    model = InventorySheet
    field_id = 'inventorysheet'


@MenuManage.describ('invoice.change_inventorysheet')
@ActionsManage.affect_show(TITLE_PRINT, "images/print.png")
@ActionsManage.affect_grid(TITLE_PRINT, "images/print.png", unique=SELECT_SINGLE)
class InventorySheetPrint(XferPrintAction):
    caption = _("Print inventory sheet")
    icon = "report.png"
    model = InventorySheet
    field_id = 'inventorysheet'
    action_class = InventorySheetShow
    with_text_export = True


@ActionsManage.affect_grid(TITLE_MODIFY, "images/edit.png", unique=SELECT_SINGLE, condition=lambda xfer, gridname='': hasattr(xfer.old_item, 'status') and (int(xfer.old_item.status) == InventorySheet.STATUS_BUILDING))
@MenuManage.describ('invoice.add_inventorysheet')
class InventoryDetailModify(XferAddEditor):
    icon = "inventorysheet.png"
    model = InventoryDetail
    field_id = 'inventorydetail'
    caption_modify = _("Modify inventory detail")

    def fillresponse(self):
        if self.item.id is None:
            raise LucteriosException(GRAVE, "insert InventoryDetail")
        XferAddEditor.fillresponse(self)


@ActionsManage.affect_grid(_('Copy'), "images/clone.png", unique=SELECT_MULTI, condition=lambda xfer, gridname='': hasattr(xfer.old_item, 'status') and (int(xfer.old_item.status) == InventorySheet.STATUS_BUILDING))
@MenuManage.describ('invoice.add_inventorysheet')
class InventoryDetailCopy(XferContainerAcknowledge):
    icon = "inventorysheet.png"
    model = InventoryDetail
    field_id = 'inventorydetail'
    caption = _("Copy quantity of inventory detail")

    def fillresponse(self):
        for item in self.items:
            item.copy_value()


@ActionsManage.affect_grid(_('Finalize'), "images/upload.png", unique=SELECT_NONE, condition=lambda xfer, gridname='': hasattr(xfer.old_item, 'status') and (int(xfer.old_item.status) == InventorySheet.STATUS_BUILDING) and not xfer.old_item.can_valid())
@MenuManage.describ('invoice.add_inventorysheet')
class InventoryDetailFinalize(XferContainerAcknowledge):
    icon = "inventorysheet.png"
    model = InventoryDetail
    field_id = 'inventorydetail'
    caption = _("Finalize quantity non-entered of inventory detail")

    def fillresponse(self, inventorysheet=0):
        if self.confirme(_("This action will report current quantity to article whose non-enterd.{[br/]}Do you want to do this action ?")):
            nb_article = 0
            sheet = InventorySheet.objects.get(id=inventorysheet)
            for detail in sheet.inventorydetail_set.filter(quantity__isnull=True):
                detail.copy_value()
                nb_article += 1
            self.message(_("%d articles are reported.") % nb_article)
