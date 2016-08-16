#!/usr/bin/env python
# -*- coding: utf-8 -*-
##############################################################################
#
#    OpenERP, Open Source Management Solution
#    Copyright (C) 2011 TeMPO Consulting, MSF. All Rights Reserved
#    Developer: Olivier DOSSMANN
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU Affero General Public License as
#    published by the Free Software Foundation, either version 3 of the
#    License, or (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU Affero General Public License for more details.
#
#    You should have received a copy of the GNU Affero General Public License
#    along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
##############################################################################

from osv import osv
from osv import fields
from tools.translate import _
import time
from collections import defaultdict

class account_move_line_reconcile(osv.osv_memory):
    _inherit = 'account.move.line.reconcile'
    _name = 'account.move.line.reconcile'

    _columns = {
        'state': fields.selection([('total', 'Full Reconciliation'), ('partial', 'Partial Reconciliation'), 
            ('total_change', 'Full Reconciliation with change'), ('partial_change', 'Partial Reconciliation with change')], string="State", 
            required=True, readonly=True),
        'different_currencies': fields.boolean('Is this reconciliation in different currencies? (2 at most)'),
    }

    _defaults = {
        'state': lambda *a: 'total',
        'different_currencies': lambda *a: False,
    }

    def default_get(self, cr, uid, fields, context=None):
        """
        Add state field in res
        """
        # Some verifications
        if not context:
            context = {}
        # Default value
        res = super(account_move_line_reconcile, self).default_get(cr, uid, fields, context=context)
        # Retrieve some value
        data = self.trans_rec_get(cr, uid, context['active_ids'], context=context)
        # Get different currencies state
        if 'different_currencies' in fields and 'different_currencies' in data:
            res.update({'different_currencies': data['different_currencies']})
        # Update res with state value
        if 'state' in fields and 'state' in data:
            res.update({'state': data['state']})
        return res

    def trans_rec_get(self, cr, uid, ids, context=None):
        """
        Change default method:
        - take debit_currency and credit_currency instead of debit and credit (this is to pay attention to Booking Currency)
        - add some values:
          - state: if write off is 0.0, then 'total' else 'partial'
        - verify that lines come from a transfer account or not
        """
        # Some verifications
        if not context:
            context = {}
        if isinstance(ids, (int, long)):
            ids = [ids]
        # Prepare some values
        account_move_line_obj = self.pool.get('account.move.line')
        credit = debit = fcredit = fdebit = 0
        state = 'partial'
        account_id = False
        count = 0
        # Search salaries default account
        salary_account_id = False
        if self.pool.get('res.users').browse(cr, uid, uid).company_id.salaries_default_account:
            salary_account_id = self.pool.get('res.users').browse(cr, uid, uid).company_id.salaries_default_account.id
        # Search intermission default account
        intermission_default_account_id = False
        if self.pool.get('res.users').browse(cr, uid, uid).company_id.intermission_default_counterpart:
            intermission_default_account_id = self.pool.get('res.users').browse(cr, uid, uid).company_id.intermission_default_counterpart.id
        # Browse all lines and check currencies, journals, and transfers state
        currencies = defaultdict(list)
        journals = defaultdict(list)
        transfers = []
        transfer_with_change = False
        disregard_third_party = False
        transfer = False
        debits = 0
        credits = 0
        statements = []
        for line in account_move_line_obj.browse(cr, uid, context['active_ids']):
            if line.move_id and line.move_id.state == 'posted':
                # Prepare some infos needed for transfers with/without change
                currencies[(line.currency_id, line.transfer_journal_id and line.transfer_journal_id.currency or None)].append(line.id)
                journals[(line.journal_id.id, line.transfer_journal_id and line.transfer_journal_id.id or None)].append(line.id)
                if line.is_transfer_with_change:
                    transfers.append(line.id)
                if line.account_id.type_for_register == 'disregard_rec':
                    disregard_third_party = True
                debits += line.debit
                credits += line.credit
                statements.append(line.statement_id)
                continue
            raise osv.except_osv(_('Warning'), _('You can only do reconciliation on Posted Entries!'))
        # Check lines for transfers cases (this permit to do transfers with more than 2 lines!)
        if len(journals) == 2:
            keys = journals.keys()
            # Cross check on: "third parties" × "journals" (if YES, this is a transfer)
            if keys[0][1] == keys[1][0] and keys[0][0] == keys[1][1]:
                transfer = True
        if len(transfers) == len(context['active_ids']):
            transfer_with_change = True
        # Cross check on: "journal currency" × "transfer_journal currency" (should check all error cases to avoid transfer_with_change problems)
        if transfer_with_change:
            keys_c = currencies.keys()
            if len(currencies) != 2 or keys_c[0][1] != keys_c[1][0] or keys_c[0][0] != keys_c[1][1]:
                transfer_with_change = False
                # UTP-526: Do not raise next error if line comes from the same register and have same amount
                previous_st = None
                same = True
                for st in statements:
                    if not previous_st:
                        previous_st = st
                        continue
                    if st != previous_st:
                        same = False
                        break
                if not (same and debits == credits):
                    raise osv.except_osv(_('Warning'), _("Cannot reconcile entries : Cross check between transfer currencies fails."))
        prev_acc_id = None
        prev_third_party = None
        if transfer_with_change:
            # For transfer with change, we need to do a total reconciliation!
            state = 'total_change'
        currency_id = False
        currency2_id = False
        for line in account_move_line_obj.browse(cr, uid, context['active_ids'], context=context):
            # prepare some values
            account_id = line.account_id.id
            # some verifications
            if not line.account_id.reconcile:
                raise osv.except_osv(_('Warning'), _('This account is not reconciliable: %s') % (line.account_id.code,))
            # Check that currency id is the same unless transfer with change cases
            if not currency_id:
                currency_id = line.currency_id and line.currency_id.id or False
            if line.currency_id and line.currency_id.id != currency_id and not transfer_with_change:
                currency2_id = line.currency_id.id
            # verification that there's only one account for each line
            if not prev_acc_id:
                prev_acc_id = account_id
            if prev_acc_id != account_id:
                raise osv.except_osv(_('Error'), _('An account is different from others: %s') % (line.account_id.code,))
            # verification that there's only one 3rd party
            # The 3rd party verification is desactivated in case of transfer with change
            # UTP-1040: 3RD party is also desactivated in case of account that is "Disregard Third Party" as "type_for_register"
            if not transfer and not disregard_third_party:
                third_party = {
                        'partner_id': line.partner_id and line.partner_id.id or False, 
                        'employee_id': line.employee_id and line.employee_id.id or False, 
                        'transfer_journal_id': line.transfer_journal_id and line.transfer_journal_id.id or False}
                if not prev_third_party:
                    prev_third_party = third_party
                if prev_third_party != third_party:
                    # Do not raise an exception if salary_default_account is configured and this line account is equal to default salary account
                    # True + not (False + False) => True [ERROR message]
                    # True + not (True + False) or True + not (False + True) => True [ERROR message]
                    # True + not (True + True) => False [NO error]
                    # False + anything => False [NO error]
                    if line.account_id.id != salary_account_id and not (line.partner_id.partner_type == 'intermission' and line.account_id.id != intermission_default_account_id):
                        raise osv.except_osv(_('Error'), _('Third parties do not match or bad company configuration!'))
            # process necessary elements
            if not line.reconcile_id and not line.reconcile_id.id:
                count += 1
                credit += line.credit_currency
                debit += line.debit_currency
                fcredit += line.credit
                fdebit += line.debit
        # Adapt state value
        if (debit - credit) == 0.0:
            state = 'total'
        if transfer_with_change:
            debit = fdebit
            credit = fcredit
            if (fdebit - fcredit) == 0.0:
                state = 'total_change'
        # Currencies state
        different_currencies = False
        if currency_id and currency2_id and not transfer_with_change:
            different_currencies = True
            debit = fdebit
            credit = fcredit
        # For salaries, behaviour is the same as total_change: we use functional debit/credit
        if account_id == salary_account_id or (currency_id and currency2_id and not transfer_with_change):
            if (fdebit - fcredit) == 0.0:
                state = 'total'
            else:
                state = 'partial'
                # UF-2050: Do not allow partial reconciliation of entries in different currencies. We ALWAYS do total reconciliation
                if different_currencies and not transfer_with_change:
                    state = 'total'
        return {'trans_nbr': count, 'account_id': account_id, 'credit': credit, 'debit': debit, 'writeoff': debit - credit, 'state': state, 'different_currencies': different_currencies}

    def total_reconcile(self, cr, uid, ids, context=None):
        """
        Do a total reconciliation for given active_ids in context.
        Add another line to reconcile if some gain/loss of rate recalculation.
        """
        # Some verifications
        if not context:
            context = {}
        if isinstance(ids, (int, long)):
            ids = [ids]
        # Prepare some value
        to_reconcile = context['active_ids']
        self.pool.get('account.move.line').reconcile(cr, uid, to_reconcile, 'manual', False, False, False, context=context)
        return {'type': 'ir.actions.act_window_close'}

    def partial_reconcile(self, cr, uid, ids, context=None):
        """
        Do a partial reconciliation
        """
        # Some verifications
        if not context:
            context = {}
        if isinstance(ids, (int, long)):
            ids = [ids]
        # Do partial reconciliation
        self.pool.get('account.move.line').reconcile_partial(cr, uid, context['active_ids'], 'manual', context=context)
        return {'type': 'ir.actions.act_window_close'}

account_move_line_reconcile()
# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
