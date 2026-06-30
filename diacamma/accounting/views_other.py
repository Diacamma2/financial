# -*- coding: utf-8 -*-
from __future__ import unicode_literals
from json import dumps, loads
from time import sleep
from io import BytesIO
from digitalInvoice.reader import ReaderInvoice

from django.utils.translation import gettext_lazy as _
from django.utils import timezone
from django.db.models import Q

from lucterios.framework.xferadvance import XferDelete, XferShowEditor, TITLE_ADD, TITLE_MODIFY, TITLE_DELETE, TITLE_EDIT, TITLE_CANCEL, TITLE_OK, \
    TITLE_CREATE, TITLE_CLOSE
from lucterios.framework.tools import FORMTYPE_NOMODAL, SELECT_SINGLE, FORMTYPE_REFRESH, SELECT_MULTI, SELECT_NONE, CLOSE_NO, CLOSE_YES, FORMTYPE_MODAL
from lucterios.framework.tools import ActionsManage, MenuManage, WrapAction
from lucterios.framework.signal_and_lock import Signal
from lucterios.framework.xfercomponents import XferCompImage, XferCompLabelForm, XferCompDate,\
    XferCompStep, XferCompUpLoad, XferCompCheck, XferCompSelect, XferCompButton,\
    XferCompGrid
from lucterios.framework.xferadvance import XferListEditor
from lucterios.framework.xferadvance import XferAddEditor
from lucterios.framework.xfergraphic import XferContainerAcknowledge, XFER_DBOX_WARNING, XferContainerCustom
from lucterios.framework.error import LucteriosException, IMPORTANT
from lucterios.CORE.parameters import Params
from lucterios.contacts.models import LegalEntity

from diacamma.accounting.models import CostAccounting, ModelLineEntry, ModelEntry, FiscalYear, ChartsAccount,\
    EntryAccount, Journal, Third, AccountThird, EntryLineAccount, get_meta_currency_iso_list
from diacamma.accounting.views_reports import CostAccountingIncomeStatement
from diacamma.accounting.views_entries import EntryAccountValidate
from diacamma.accounting.tools import get_amount_from_format_devise, currency_round, current_system_account
from diacamma.accounting.einvoicing_flow import get_einvoice_config, get_einvoicing_flow


@MenuManage.describ('accounting.change_entryaccount', FORMTYPE_NOMODAL, 'bookkeeping', _('Edition of costs accounting'))
class CostAccountingList(XferListEditor):
    short_icon = "mdi:mdi-chart-box"
    model = CostAccounting
    field_id = 'costaccounting'
    caption = _("Costs accounting")

    def fillresponse_header(self):
        self.filter = Q()

        status_filter = self.getparam('status', 0)
        if status_filter != -1:
            self.filter &= Q(status=status_filter)
        self.status = status_filter

        select_year = self.getparam('year', 0)
        if select_year > 0:
            self.filter &= Q(year_id=select_year)
        if select_year == -1:
            self.filter &= Q(year__isnull=True)
        self.fill_from_model(0, 4, False, ['status', 'year'])
        comp_year = self.get_components('year')
        comp_year.select_list.append((-1, _('- without fiscal year -')))
        comp_year.set_value(select_year)
        comp_year.set_action(self.request, self.return_action(), close=CLOSE_NO, modal=FORMTYPE_REFRESH)
        comp_year.colspan = 2
        comp_status = self.get_components('status')
        comp_status.select_list.insert(0, (-1, None))
        comp_status.set_value(status_filter)
        comp_status.set_action(self.request, self.return_action(), close=CLOSE_NO, modal=FORMTYPE_REFRESH)
        comp_status.colspan = 2

    def fillresponse(self):
        XferListEditor.fillresponse(self)
        self.get_components('title').colspan += 1
        self.get_components('costaccounting').colspan += 1


@ActionsManage.affect_list(_("By date"), short_icon='mdi:mdi-printer-outline')
@MenuManage.describ('accounting.add_fiscalyear')
class CostAccountingReportByDate(XferContainerAcknowledge):
    short_icon = "mdi:mdi-chart-box"
    model = CostAccounting
    field_id = 'costaccounting'
    caption = _("Print by date")

    def fillresponse(self):
        begin_date = self.getparam('begin_date')
        end_date = self.getparam('end_date')
        if (begin_date is None) or (end_date is None):
            year = FiscalYear.get_current()
            dlg = self.create_custom()
            img = XferCompImage('img')
            img.set_value(self.short_icon, '#')
            img.set_location(0, 0)
            dlg.add_component(img)
            lbl = XferCompLabelForm('title')
            lbl.set_value_as_title(_('Define date range to determine accounting cost list.'))
            lbl.set_location(1, 0, 2)
            begin_filter = XferCompDate('begin_date')
            begin_filter.set_location(1, 1)
            begin_filter.set_needed(True)
            begin_filter.set_value(year.begin)
            begin_filter.description = _('begin')
            dlg.add_component(begin_filter)
            end_filter = XferCompDate('end_date')
            end_filter.set_location(2, 1)
            end_filter.set_needed(True)
            end_filter.set_value(year.end)
            end_filter.description = _('end')
            dlg.add_component(end_filter)
            dlg.add_component(lbl)
            dlg.add_action(self.return_action(TITLE_OK, short_icon='mdi:mdi-check'))
            dlg.add_action(WrapAction(TITLE_CANCEL, short_icon='mdi:mdi-cancel'))
        else:
            list_cost = []
            for cost_item in CostAccounting.objects.filter(Q(entrylineaccount__entry__date_value__gte=begin_date) & Q(entrylineaccount__entry__date_value__lte=end_date)).distinct():
                list_cost.append(str(cost_item.id))
            list_cost = set(list_cost)
            if len(list_cost) == 0:
                raise LucteriosException(IMPORTANT, _("No cost accounting finds for this range !"))
            self.redirect_action(CostAccountingIncomeStatement.get_action(), modal=FORMTYPE_NOMODAL, close=CLOSE_YES, params={'begin_date': begin_date, 'end_date': end_date, 'datereadonly': True, 'costaccounting': ";".join(list_cost)})


@ActionsManage.affect_grid(_("Default"), short_icon='mdi:mdi-star-outline', unique=SELECT_SINGLE, condition=lambda xfer, gridname='': xfer.getparam('status', 0) != 1)
@MenuManage.describ('accounting.add_fiscalyear')
class CostAccountingDefault(XferContainerAcknowledge):
    short_icon = 'mdi:mdi-star-outline'
    model = CostAccounting
    field_id = 'costaccounting'
    caption = _("Default")
    readonly = True

    def fillresponse(self):
        self.item.change_has_default()


@ActionsManage.affect_grid(_("Close"), short_icon="mdi:mdi-check", unique=SELECT_SINGLE, condition=lambda xfer, gridname='': xfer.getparam('status', 0) != 1)
@MenuManage.describ('accounting.add_fiscalyear')
class CostAccountingClose(XferContainerAcknowledge):
    short_icon = "mdi:mdi-check"
    model = CostAccounting
    field_id = 'costaccounting'
    caption = _("Close")
    readonly = True

    def fillresponse(self):
        if self.item.status == CostAccounting.STATUS_OPENED:
            if self.item.is_protected:
                raise LucteriosException(IMPORTANT, _("This cost accounting is protected by other modules!"))
            self.item.check_before_close()
            if self.confirme(_("Do you want to close this cost accounting?")):
                self.item.close()


@ActionsManage.affect_grid(TITLE_ADD, short_icon='mdi:mdi-pencil-plus-outline', unique=SELECT_NONE, condition=lambda xfer, gridname='': xfer.getparam('status', 0) != 1)
@ActionsManage.affect_grid(TITLE_MODIFY, short_icon='mdi:mdi-pencil-outline', unique=SELECT_SINGLE, condition=lambda xfer, gridname='': xfer.getparam('status', 0) != 1)
@MenuManage.describ('accounting.add_entryaccount')
class CostAccountingAddModify(XferAddEditor):
    short_icon = "mdi:mdi-chart-box"
    model = CostAccounting
    field_id = 'costaccounting'
    caption_add = _("Add cost accounting")
    caption_modify = _("Modify cost accounting")

    def fillresponse(self):
        if 'status' in self.params.keys():
            del self.params['status']
        if (self.item.id is not None) and self.item.is_protected:
            raise LucteriosException(IMPORTANT, _("This cost accounting is protected by other modules!"))
        XferAddEditor.fillresponse(self)


@ActionsManage.affect_grid(TITLE_DELETE, short_icon='mdi:mdi-delete-outline', unique=SELECT_MULTI, condition=lambda xfer, gridname='': xfer.getparam('status', 0) != 1)
@MenuManage.describ('accounting.delete_entryaccount')
class CostAccountingDel(XferDelete):
    short_icon = "mdi:mdi-chart-box"
    model = CostAccounting
    field_id = 'costaccounting'
    caption = _("Delete cost accounting")


def condition_recreate(xfer):
    select_year = xfer.getparam('year', 0)
    if select_year <= 0:
        return False
    last_year = FiscalYear.objects.get(id=select_year).last_fiscalyear
    if last_year is None:
        return False
    cost_list = CostAccounting.objects.filter(year=last_year, year__next_fiscalyear__status=FiscalYear.STATUS_BUILDING, is_protected=False, next_costaccounting__isnull=True)
    return len(cost_list) > 0


@ActionsManage.affect_list(_("Recreate"), short_icon='mdi:mdi-pencil-plus-outline', condition=condition_recreate)
@MenuManage.describ('accounting.add_fiscalyear')
class CostAccountingRecreate(XferContainerAcknowledge):
    short_icon = 'mdi:mdi-pencil-plus-outline'
    model = CostAccounting
    field_id = 'costaccounting'
    caption = _("Recreate")
    readonly = True

    def fillresponse(self, year=0):
        current_year = FiscalYear.objects.get(id=year)
        cost_nb = CostAccounting.objects.filter(year__next_fiscalyear__in=(current_year,), year__next_fiscalyear__status=FiscalYear.STATUS_BUILDING, is_protected=False, next_costaccounting__isnull=True).count()
        if self.confirme(_('Do you want to try to import %d old cost accounting in this fiscal year ?') % cost_nb):
            error = CostAccounting.create_costs_from_lastyear(year)
            if len(error) > 0:
                self.message(_('Some last cost accounting have not be imported:{[br]}%s') % "{[br]}".join(error), XFER_DBOX_WARNING)
            else:
                self.message(_('All last cost accounting have be imported.'))


@MenuManage.describ('accounting.change_entryaccount', FORMTYPE_NOMODAL, 'bookkeeping', _('Edition of entry model'),)
class ModelEntryList(XferListEditor):
    short_icon = "mdi:mdi-format-list-text"
    model = ModelEntry
    field_id = 'modelentry'
    caption = _("Models of entry")


@ActionsManage.affect_grid(TITLE_CREATE, short_icon='mdi:mdi-pencil-plus', unique=SELECT_NONE)
@ActionsManage.affect_show(TITLE_MODIFY, short_icon='mdi:mdi-pencil-outline', close=CLOSE_YES)
@MenuManage.describ('accounting.add_entryaccount')
class ModelEntryAddModify(XferAddEditor):
    short_icon = "mdi:mdi-format-list-text"
    model = ModelEntry
    field_id = 'modelentry'
    caption_add = _("Add model of entry")
    caption_modify = _("Modify model of entry")


@ActionsManage.affect_grid(TITLE_EDIT, short_icon='mdi:mdi-text-box-outline', unique=SELECT_SINGLE)
@MenuManage.describ('accounting.change_entryaccount')
class ModelEntryShow(XferShowEditor):
    short_icon = "mdi:mdi-format-list-text"
    model = ModelEntry
    field_id = 'modelentry'
    caption = _("Show Model of entry")


@ActionsManage.affect_grid(TITLE_DELETE, short_icon='mdi:mdi-delete-outline', unique=SELECT_MULTI)
@MenuManage.describ('accounting.delete_entryaccount')
class ModelEntryDel(XferDelete):
    short_icon = "mdi:mdi-format-list-text"
    model = ModelEntry
    field_id = 'modelentry'
    caption = _("Delete Model of entry")


@ActionsManage.affect_grid(TITLE_ADD, short_icon='mdi:mdi-pencil-plus-outline', unique=SELECT_NONE)
@ActionsManage.affect_grid(TITLE_MODIFY, short_icon='mdi:mdi-pencil-outline', unique=SELECT_SINGLE)
@MenuManage.describ('accounting.add_entryaccount')
class ModelLineEntryAddModify(XferAddEditor):
    short_icon = "mdi:mdi-format-list-text"
    model = ModelLineEntry
    field_id = 'modellineentry'
    caption_add = _("Add model line  of entry")
    caption_modify = _("Modify model line  of entry")


@ActionsManage.affect_grid(TITLE_DELETE, short_icon='mdi:mdi-delete-outline', unique=SELECT_MULTI)
@MenuManage.describ('accounting.delete_entryaccount')
class ModelLineEntryDel(XferDelete):
    short_icon = "mdi:mdi-format-list-text"
    model = ModelLineEntry
    field_id = 'modellineentry'
    caption = _("Delete Model line  of entry")


def get_contact_from_json(contact_json):
    new_contact = LegalEntity()
    new_contact.name = contact_json['name']
    new_contact.legal_identification = contact_json['legal_ident']
    new_contact.vat_identification = contact_json['vat_ident']
    new_contact.address = '\n'.join(contact_json['address']).strip().replace('\n', '{[br/]}')
    new_contact.postal_code = contact_json['postalcode']
    new_contact.city = contact_json['city']
    new_contact.country = contact_json['country_id']
    new_contact.tel1 = contact_json['phone']
    new_contact.email = contact_json['email']
    return new_contact


@MenuManage.describ('contacts.add_abstractcontact')
class EInvoiceAddSeller(XferContainerAcknowledge):
    short_icon = "mdi:mdi-pencil-plus-outline"
    caption = _("add this seller")
    model = LegalEntity
    field_id = 'legal_entity'

    def fillresponse(self, legal_entity=None):
        einvoice_content = loads(self.getparam('einvoice', 'null'))
        if 'seller' in einvoice_content:
            new_contact = get_contact_from_json(einvoice_content['seller'])
            new_contact.id = legal_entity
            new_contact.save()


def right_importEinvoice(request):
    if EntryAccountValidate.get_action().check_permission(request):
        current_contact = LegalEntity.objects.get(id=1)
        return (current_contact.legal_identification != '') and (current_system_account().get_einvoice_format() != '')
    else:
        return False


@MenuManage.describ(right_importEinvoice)
class ImportEInvoice(XferContainerCustom):
    short_icon = "mdi:mdi-invoice-import-outline"
    caption = _("Import e-invoice")

    def _select_einvoice(self):
        upld = XferCompUpLoad('importcontent')
        upld.http_file = True
        upld.withcam = False
        upld.set_needed(True)
        upld.add_filter('*.pdf,*.xml')
        upld.set_location(0, 2, 9)
        upld.description = _('e-invoice file')
        self.add_component(upld)

    def _add_contact(self, contact_json, col, label):
        new_contact = get_contact_from_json(contact_json)
        lbl = XferCompLabelForm(f'contact-{col}')
        lbl.set_value_as_title(label)
        lbl.set_location(col, 2, 4)
        self.add_component(lbl)
        self.model = LegalEntity
        self.item = new_contact
        fields = LegalEntity.get_show_fields()
        self.fill_from_model(col, 3, True, desc_fields=list(fields.values())[0], prefix=f'{col}_')
        return new_contact

    def _assign_buyer(self, einvoice_content):
        buyer = self._add_contact(einvoice_content['buyer'], 1, _('buyer'))
        current_contact = LegalEntity.objects.get(id=1)
        if (current_contact.legal_identification != '') and (current_contact.get_legal_identification() == buyer.get_legal_identification()):
            lbl = XferCompLabelForm('buyer_ok')
            lbl.set_value(_('Our structure is well referenced as a buyer'))
            lbl.set_color('blue')
            lbl.set_location(1, 20, 4)
            self.add_component(lbl)
            buyer_valid = True
        else:
            buyer_valid = self.getparam('buyer_valid', False)
            chk = XferCompCheck('buyer_valid')
            chk.set_needed(True)
            chk.set_value(buyer_valid)
            chk.description = ('{[font color="red"]}%s{[/font]}' if not buyer_valid else '%s') % _('Our structure is not defined as a buyer:{[br/]}force this import anyway ?')
            chk.set_location(1, 20, 4)
            chk.set_action(self.request, self.return_action(), modal=FORMTYPE_REFRESH, close=CLOSE_NO)
            self.add_component(chk)
        return buyer_valid

    def _assign_seller(self, einvoice_content):
        seller_select = self.getparam('seller_select', 0)
        seller = self._add_contact(einvoice_content['seller'], 5, _('seller'))
        seller_filter = Q(name__icontains=seller.name)
        if seller.legal_identification != '':
            seller_filter |= Q(legal_identification=seller.legal_identification)
        select_list = [(seller_contact.id, f"{seller_contact} (ID={seller_contact.legal_identification})") for seller_contact in LegalEntity.objects.filter(seller_filter)]
        select_list.insert(0, (0, None))
        sel = XferCompSelect("seller_select")
        sel.set_needed(False)
        sel.set_value(seller_select)
        sel.set_select(select_list)
        sel.description = ('{[font color="red"]}%s{[/font]}' if seller_select == 0 else '%s') % _('Select the seller in the contacts')
        sel.set_action(self.request, self.return_action(), modal=FORMTYPE_REFRESH, close=CLOSE_NO)
        sel.set_location(5, 20, 3)
        self.add_component(sel)
        if seller_select != 0:
            btn = XferCompButton('add_seller')
            btn.set_location(8, 20, 1)
            btn.set_is_mini(True)
            btn.set_action(self.request, EInvoiceAddSeller.get_action(caption=_("update this seller"), short_icon="mdi:mdi-pencil-outline"), close=CLOSE_NO, params={'legal_entity': seller_select})
            self.add_component(btn)
        elif f"{seller} (ID={seller.legal_identification})" not in dict(select_list).values():
            btn = XferCompButton('add_seller')
            btn.set_location(8, 20, 1)
            btn.set_is_mini(True)
            btn.set_action(self.request, EInvoiceAddSeller.get_action(caption=_("add this seller"), short_icon="mdi:mdi-pencil-plus-outline"), close=CLOSE_NO)
            self.add_component(btn)
        return seller_select

    def _assign_detail(self, einvoice_content):
        row = self.get_max_row()
        lbl = XferCompLabelForm('detail')
        lbl.set_value_as_title(_('detail'))
        lbl.set_location(0, row + 1, 4)
        self.add_component(lbl)
        row += 2
        sum_total = 0.0
        query = FiscalYear.get_current().chartsaccount_set.filter(type_of_account=ChartsAccount.TYPE_EXPENSE)
        for detail_idx, detail_json in enumerate(einvoice_content['bill']['detail']):
            lbl = XferCompLabelForm(f'detail1_{detail_idx}')
            lbl.set_value("{[b]}%s{[/b]}{[br/]}{[i]}%s{[/i]}" % (detail_json['designation'], detail_json['reference']))
            lbl.set_location(1, row)
            self.add_component(lbl)
            lbl = XferCompLabelForm(f'detail2_{detail_idx}')
            detail_amount = "%s x %.2f" % (get_amount_from_format_devise(detail_json['price'], 7), detail_json['quantity'])
            if abs(detail_json['reduce']) > 1e-3:
                detail_amount += " - %s" % get_amount_from_format_devise(detail_json['reduce'], 7)
            if abs(detail_json['vat_rate']) > 1e-3:
                detail_amount += " (%s  %.2f%%)" % (_('vat'), detail_json['vat_rate'])
            lbl.set_value(detail_amount)
            lbl.set_location(2, row)
            self.add_component(lbl)
            if Params.getvalue("accounting-VAT-arrangements") == FiscalYear.VAT_ARRANGEMENTS_NOT_APPLICABLE:
                detail_total = currency_round(detail_json['total'] * (1 + detail_json['vat_rate'] / 100))
            else:
                detail_total = detail_json['total']
            sum_total += detail_total
            lbl = XferCompLabelForm(f'detail3_{detail_idx}')
            lbl.set_value(get_amount_from_format_devise(detail_total, 7))
            lbl.set_bold()
            lbl.set_location(3, row)
            self.add_component(lbl)

            sel = XferCompSelect(f'detail_{detail_idx}')
            sel.set_needed(True)
            sel.set_select_query(query)
            sel.set_location(4, row)
            self.add_component(sel)
            row += 1
        return sum_total

    def _assign_vat(self, einvoice_content):
        row = self.get_max_row()
        lbl = XferCompLabelForm('vat')
        lbl.set_value_as_title(_('VAT'))
        lbl.set_location(0, row + 1, 4)
        self.add_component(lbl)
        row += 2
        sum_tva = 0.0
        query = FiscalYear.get_current().chartsaccount_set.filter(code__regex=current_system_account().get_vat_deductible_mask())
        if Params.getvalue("accounting-VAT-arrangements") != FiscalYear.VAT_ARRANGEMENTS_NOT_APPLICABLE:
            for vat_idx, vat_info in enumerate(einvoice_content["bill"]['vat_info']):
                lbl = XferCompLabelForm(f'vat1_{vat_idx}')
                lbl.set_value("%s x %.2f%%" % (get_amount_from_format_devise(vat_info['basic'], 7), vat_info['rate']))
                lbl.set_location(2, row)
                self.add_component(lbl)
                lbl = XferCompLabelForm(f'vat2_{vat_idx}')
                lbl.set_value(get_amount_from_format_devise(vat_info['calculate'], 7))
                lbl.set_bold()
                lbl.set_location(3, row)
                self.add_component(lbl)
                if abs(vat_info['calculate']) > 1e-3:
                    sel = XferCompSelect(f'vat_{vat_idx}')
                    sel.set_needed(True)
                    sel.set_select_query(query)
                    sel.set_location(4, row)
                    self.add_component(sel)
                sum_tva += vat_info['calculate']
                row += 1
        else:
            lbl = XferCompLabelForm('novat')
            lbl.set_value(_('VAT is not recoverable'))
            lbl.set_location(2, row, 4)
            self.add_component(lbl)
        return sum_tva

    def _assign_expences(self, einvoice_content):
        seller = LegalEntity.objects.get(id=self.getparam('seller_select', 0))
        lbl = XferCompLabelForm('seller')
        lbl.description = _('seller')
        lbl.set_value(str(seller))
        lbl.set_location(1, 2, 4)
        self.add_component(lbl)

        self._assign_detail(einvoice_content)
        if Params.getvalue("accounting-VAT-arrangements") != FiscalYear.VAT_ARRANGEMENTS_NOT_APPLICABLE:
            lbl = XferCompLabelForm('total_excltax')
            lbl.description = _('Total excl')
            lbl.set_value(get_amount_from_format_devise(einvoice_content["bill"]['total']['excltax'], 7))
            lbl.set_italic()
            lbl.set_location(3, self.get_max_row() + 1)
            self.add_component(lbl)
        sum_tva = self._assign_vat(einvoice_content)
        if Params.getvalue("accounting-VAT-arrangements") != FiscalYear.VAT_ARRANGEMENTS_NOT_APPLICABLE:
            lbl = XferCompLabelForm('total_vat')
            lbl.description = _('Total VAT')
            lbl.set_value(get_amount_from_format_devise(sum_tva, 7))
            lbl.set_italic()
            lbl.set_location(3, self.get_max_row() + 1)
            self.add_component(lbl)

        row = self.get_max_row()
        lbl = XferCompLabelForm('total')
        lbl.description = _('Total')
        lbl.set_value(get_amount_from_format_devise(einvoice_content["bill"]['total']['incltax'], 7))
        lbl.set_bold()
        lbl.set_location(3, row + 1)
        self.add_component(lbl)

    def _set_entry(self, einvoice_content):
        entry_id = self.getparam("entryaccount", 0)
        self.model = EntryAccount
        if entry_id == 0:
            self.item = EntryAccount.objects.create(year=FiscalYear.get_current(), journal=Journal.objects.get(id=self.getparam('journal', Journal.DEFAULT_BUYING)),
                                                    date_value=timezone.now().date(),
                                                    designation=_('e-invoice import ref. %s') % einvoice_content['bill']['num'])
            self.params["year"] = self.item.year.id
            self.params["entryaccount"] = self.item.id
        else:
            self.item = EntryAccount.objects.get(id=entry_id)

    def _get_third(self):
        third, _new = Third.objects.get_or_create(contact_id=self.getparam('seller_select', 0), status=Third.STATUS_ENABLE)
        accountthirds = third.accountthird_set.filter(code__regex=current_system_account().get_provider_mask())
        if accountthirds.count() == 0:
            charts_sell = FiscalYear.get_current().chartsaccount_set.filter(code__regex=current_system_account().get_provider_mask()).first()
            AccountThird.objects.create(third=third, code=charts_sell.code)
        else:
            charts_sell = FiscalYear.get_current().chartsaccount_set.filter(code__in=[accountthird.code for accountthird in accountthirds]).first()
        return third, charts_sell

    def _fill_serial_entry(self, einvoice_content):
        third, charts_sell = self._get_third()
        serial_entry = self.item.add_new_entryline("", 0, charts_sell.id, einvoice_content["bill"]['total']['incltax'], 0.0, third.id, 0, '')
        sleep(0.05)
        for detail_idx, detail_json in enumerate(einvoice_content['bill']['detail']):
            if Params.getvalue("accounting-VAT-arrangements") == FiscalYear.VAT_ARRANGEMENTS_NOT_APPLICABLE:
                detail_total = currency_round(detail_json['total'] * (1 + detail_json['vat_rate'] / 100))
            else:
                detail_total = detail_json['total']
            serial_entry = self.item.add_new_entryline(serial_entry, 0, self.getparam(f'detail_{detail_idx}', 0),
                                                       0.0, detail_total, 0, 0, detail_json['designation'])
            sleep(0.05)

        if Params.getvalue("accounting-VAT-arrangements") != FiscalYear.VAT_ARRANGEMENTS_NOT_APPLICABLE:
            for vat_idx, vat_info in enumerate(einvoice_content["bill"]['vat_info']):
                if abs(vat_info['calculate']) > 1e-3:
                    serial_entry = self.item.add_new_entryline(serial_entry, 0, self.getparam(f'vat_{vat_idx}', 0),
                                                               0.0, vat_info['calculate'], 0, 0, "%.2f%%" % vat_info['rate'])
                    sleep(0.05)

        return serial_entry

    def _create_entity(self, einvoice_content):
        self._set_entry(einvoice_content)
        serial_entry = self._fill_serial_entry(einvoice_content)
        self.filltab_from_model(2, 3, False, EntryAccount.get_edit_fields())
        new_grid_lines = XferCompGrid('entrylineaccount_serial')
        new_grid_lines.set_model(self.item.get_entrylineaccounts(serial_entry), EntryLineAccount.get_other_fields(), self)
        new_grid_lines.set_location(2, 10)
        new_grid_lines.add_action_notified(self, EntryLineAccount)
        self.add_component(new_grid_lines)
        return serial_entry

    def _fill_header(self, step):
        img = XferCompImage('img')
        img.set_value(self.short_icon, '#')
        img.set_location(0, 0)
        self.add_component(img)
        lbl = XferCompLabelForm('title')
        lbl.set_value_as_title(self.caption)
        lbl.set_location(1, 0, 9)
        self.add_component(lbl)
        stepcomp = XferCompStep('step', 4)
        stepcomp.set_value(step)
        stepcomp.set_action(self.request, self.return_action(), modal=FORMTYPE_REFRESH, close=CLOSE_NO)
        stepcomp.set_location(2, 1, 7)
        stepcomp.description = _('import progression')
        self.add_component(stepcomp)
        return stepcomp

    def fillresponse(self, step=1, import_flow=None):
        if (import_flow is not None) and (step == 1):
            flow = get_einvoicing_flow()
            reader = ReaderInvoice()
            reader.run(BytesIO(flow.get_flow(import_flow, doc_type='Original')))
            einvoice_content = reader.data
            self.params['einvoice'] = dumps(einvoice_content, default=str)
            step = 2
        elif 'importcontent' in self.request.FILES:
            reader = ReaderInvoice()
            reader.run(self.request.FILES['importcontent'])
            einvoice_content = reader.data
            self.params['einvoice'] = dumps(einvoice_content, default=str)
        else:
            einvoice_content = loads(self.getparam('einvoice', 'null'))

        if step != 1:
            if einvoice_content is None:
                raise LucteriosException(IMPORTANT, _('No e-invoice file found !'))
            if 'error' in einvoice_content:
                raise LucteriosException(IMPORTANT, einvoice_content['error'])
            if einvoice_content["currency_code"] != Params.getvalue('accounting-devise-iso'):
                currency_iso = dict(get_meta_currency_iso_list())
                raise LucteriosException(IMPORTANT, _('This e-invoice uses the currency "%s" while it is "%s" that is supported !') % (currency_iso[einvoice_content["currency_code"]], currency_iso[Params.getvalue('accounting-devise-iso')]))

        stepcomp = self._fill_header(step)
        if step == 1:
            self._select_einvoice()
        elif step == 2:
            buyer_valid = self._assign_buyer(einvoice_content)
            seller_select = self._assign_seller(einvoice_content)
            stepcomp.set_enabled((buyer_valid is True) and (seller_select != 0))
        elif step == 3:
            self._assign_expences(einvoice_content)
        elif step == 4:
            serial_entry = self._create_entity(einvoice_content)
            _nochange, debit_rest, credit_rest = self.item.serial_control(serial_entry)
            if (debit_rest < 0.0001) and (credit_rest < 0.0001):
                self.add_action(EntryAccountValidate.get_action(TITLE_OK, short_icon='mdi:mdi-check'), params={'serial_entry': serial_entry})
        self.add_action(WrapAction(TITLE_CANCEL, short_icon='mdi:mdi-cancel'))


@MenuManage.describ(right_importEinvoice, FORMTYPE_NOMODAL, 'financial', _('Manage e-invoicing from platform connecting'))
class EInvoicingManage(XferContainerCustom):
    short_icon = "mdi:mdi-invoice-import-outline"
    caption = _("E-invoicing")

    def fillresponse(self):
        try:
            flow = get_einvoicing_flow()
            flow.healthcheck()
            Signal.call_signal("EInvoicing", self, flow)
        except Exception:
            lbl = XferCompLabelForm('title')
            lbl.set_value_as_infocenter(_('No e-invoicing platform is avalable !'))
            lbl.set_location(0, 0)
            self.add_component(lbl)

            act = XferCompButton('btn')
            act.set_location(0, 1)
            act.set_action(self.request, ImportEInvoice.get_action(_("Manual import")), modal=FORMTYPE_MODAL, close=CLOSE_YES)
            self.add_component(act)
        self.add_action(WrapAction(TITLE_CLOSE, short_icon='mdi:mdi-close'))


@Signal.decorate('EInvoicing')
def accounting_EInvoicing(xfer, flow):
    year = FiscalYear.get_current()
    xfer.new_tab(_("Import"))
    data_to_import = flow.search_flows(flow_direction=['In'], flow_type=['SupplierInvoice'], updated_after=str(year.begin) + 'T00:00:00Z', updated_before=str(year.end) + 'T23:59:59Z')
    grid = XferCompGrid('import_flow')
    grid.no_pager = True
    grid.description = _('Supplier invoices available on the platform')
    grid.add_header('flowId', _('ID'))
    grid.add_header('flowSyntax', _('syntax'))
    grid.add_header('submittedAt', _('submitted at'), 'H')
    grid.add_header('updatedAt', _('updated at'), 'H')
    grid.add_header('acknowledgement', _('acknowledgement'))
    for record in data_to_import['results']:
        grid.set_value(record['flowId'], 'flowId', record['flowId'])
        grid.set_value(record['flowId'], 'flowSyntax', record['flowSyntax'])
        grid.set_value(record['flowId'], 'submittedAt', record['submittedAt'])
        grid.set_value(record['flowId'], 'updatedAt', record['updatedAt'])
        grid.set_value(record['flowId'], 'acknowledgement', [f"{key}={val}" for key, val in record['acknowledgement'].items()])
    grid.set_location(0, 0)
    grid.add_action(xfer.request, ImportEInvoice.get_action(_('Download e-invoice'), 'mdi:mdi-invoice-import-outline'), close=CLOSE_NO, unique=SELECT_SINGLE)
    xfer.add_component(grid)
