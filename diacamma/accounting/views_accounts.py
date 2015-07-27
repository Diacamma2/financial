# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.utils.translation import ugettext_lazy as _
from django.db.models import Q

from diacamma.accounting.models import ChartsAccount, FiscalYear

from lucterios.framework.xferadvance import XferListEditor
from lucterios.framework.xferadvance import XferAddEditor
from lucterios.framework.xferadvance import XferShowEditor
from lucterios.framework.xferadvance import XferDelete
from lucterios.framework.tools import FORMTYPE_NOMODAL, ActionsManage, MenuManage, \
    FORMTYPE_REFRESH, CLOSE_NO, SELECT_SINGLE, FORMTYPE_MODAL
from lucterios.framework.xfercomponents import XferCompLabelForm

MenuManage.add_sub("bookkeeping", "financial", "diacamma.accounting/images/accounting.png", _("Bookkeeping"), _("Manage of Bookkeeping"), 30)

@ActionsManage.affect('ChartsAccount', 'list')
@MenuManage.describ('accounting.change_chartsaccount', FORMTYPE_NOMODAL, 'bookkeeping', _('Editing and modifying of Charts of accounts for current fiscal year'))
class ChartsAccountList(XferListEditor):
    icon = "account.png"
    model = ChartsAccount
    field_id = 'chartsaccount'
    caption = _("charts of account")
    multi_page = False

    def fillresponse_header(self):
        select_year = self.getparam('year')
        select_type = self.getparam('type_of_account', 0)
        self.item.year = FiscalYear.get_current(select_year)
        self.fill_from_model(0, 1, False, ['year', 'type_of_account'])
        self.get_components('year').set_action(self.request, ChartsAccountList.get_action(), {'close':CLOSE_NO, 'modal':FORMTYPE_REFRESH})
        type_of_account = self.get_components('type_of_account')
        type_of_account.select_list.append((-1, '---'))
        type_of_account.set_action(self.request, ChartsAccountList.get_action(modal=FORMTYPE_REFRESH), {'close':CLOSE_NO, 'modal':FORMTYPE_REFRESH})
        q_filter = Q(year=self.item.year)
        if select_type != -1:
            q_filter &= Q(type_of_account=select_type)
        self.filter = [q_filter]

    def fillresponse(self):
        XferListEditor.fillresponse(self)
        if self.item.year.status == 2:
            grid_charts = self.get_components('chartsaccount')
            grid_charts.actions = []
            grid_charts.add_action(self.request, ActionsManage.get_act_changed('ChartsAccount', 'show', _("Edit"), "images/edit.png"), {'modal':FORMTYPE_MODAL, 'unique':SELECT_SINGLE})
        lbl = XferCompLabelForm("result")
        lbl.set_value_center(self.item.year.total_result_text)
        lbl.set_location(0, 10, 2)
        self.add_component(lbl)

@ActionsManage.affect('ChartsAccount', 'modify', 'add')
@MenuManage.describ('accounting.add_chartsaccount')
class ChartsAccountAddModify(XferAddEditor):
    icon = "account.png"
    model = ChartsAccount
    field_id = 'chartsaccount'
    caption_add = _("Add an account")
    caption_modify = _("Modify an account")

@ActionsManage.affect('ChartsAccount', 'show')
@MenuManage.describ('accounting.change_chartsaccount')
class ChartsAccountShow(XferShowEditor):
    icon = "account.png"
    model = ChartsAccount
    field_id = 'chartsaccount'
    caption = _("Show an account")

@ActionsManage.affect('ChartsAccount', 'delete')
@MenuManage.describ('accounting.delete_chartsaccount')
class ChartsAccountDel(XferDelete):
    icon = "account.png"
    model = ChartsAccount
    field_id = 'chartsaccount'
    caption = _("Delete an account")
