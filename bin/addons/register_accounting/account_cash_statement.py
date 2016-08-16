#!/usr/bin/env python
#-*- encoding:utf-8 -*-
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
from register_tools import create_cashbox_lines

class account_cash_statement(osv.osv):
    _name = "account.bank.statement"
    _inherit = "account.bank.statement"

    _defaults = {
        'name': False,
        'state': lambda *a: 'draft',
    }

    def _get_starting_balance(self, cr, uid, ids, context=None):
        """ Find starting balance
        @param name: Names of fields.
        @param arg: User defined arguments
        @return: Dictionary of values.
        """
        res = {}
        for statement in self.browse(cr, uid, ids, context=context):
            amount_total = 0.0

            if statement.journal_id.type not in('cash'):
                continue

            if not statement.prev_reg_id:
                for line in statement.starting_details_ids:
                    amount_total+= line.pieces * line.number
            else:
                if context and context.get('from_open'):
                    # US-948 carry other cashbox balance at open register
                    amount_total = statement.prev_reg_id.balance_end_cash
                else:
                    amount_total = statement.prev_reg_id.msf_calculated_balance

            res[statement.id] = {
                'balance_start': amount_total
            }
        return res

    def create(self, cr, uid, vals, context=None):
        """
        Create a Cash Register without an error overdue to having open two cash registers on the same journal
        """
        j_obj = self.pool.get('account.journal')
        journal = j_obj.browse(cr, uid, vals['journal_id'], context=context)
        # @@@override@account.account_cash_statement.create()

        # UFTP-116: Fixed a serious problem detected very late: the cashbox lines created by default even for the Cash Reg from sync!
        # This leads to the problem that each time, a Cash Reg is new from a sync, it added new 16 lines for the Cash Reg
        sync_update = context.get('sync_update_execution', False)
        if journal.type == 'cash' and not sync_update:
            open_close = self._get_cash_open_close_box_lines(cr, uid, context)
            if vals.get('starting_details_ids', False):
                for start in vals.get('starting_details_ids'):
                    dict_val = start[2]
                    for end in open_close['end']:
                        if end[2]['pieces'] == dict_val['pieces']:
                            end[2]['number'] += dict_val['number']
            vals.update({
#                'ending_details_ids': open_close['start'],
                'starting_details_ids': open_close['end'],
            })
        else:
            vals.update({
                'ending_details_ids': False,
                'starting_details_ids': False
            })

        # UF-2479: Block the creation of the register if the given period is not open, in sync context
        if 'period_id' in vals and sync_update:
            period = self.pool.get('account.period').browse(cr, uid, vals.get('period_id'), context)
            if period and period.state == 'created':
                raise osv.except_osv(_('Error !'), _('Period \'%s\' is not open! No Register is created') % (period.name,))

        # @@@end
        # Observe register state
        prev_reg = False
        prev_reg_id = vals.get('prev_reg_id', False)
        if prev_reg_id:
            prev_reg = self.browse(cr, uid, [prev_reg_id], context=context)[0]
            # if previous register closing balance is freezed, then retrieving previous closing balance
            # US_410: retrieving previous closing balance even closing balance is not freezed
            # if prev_reg.closing_balance_frozen:
            # US-948: carry over for bank, and always carry over bank
            # accountant manual field
            if journal.type == 'bank':
                vals.update({'balance_start': prev_reg.balance_end_real})
        res_id = osv.osv.create(self, cr, uid, vals, context=context)
        # take on previous lines if exists (or discard if they come from sync)
        if prev_reg_id and not sync_update:
            create_cashbox_lines(self, cr, uid, [prev_reg_id], ending=True, context=context)
        # update balance_end
        self._get_starting_balance(cr, uid, [res_id], context=context)
        return res_id

    def write(self, cr, uid, ids, vals, context=None):
        if context is None:
            context = {}

        if not context.get('sync_update_execution'):
            if 'balance_end_real' in vals:
                new_vals = {'balance_start': vals['balance_end_real']}
                # US-948/2: carry over end of month balance to next registers if
                # the source register is not 'end of month balance' frozen
                # note: the last carry over is processed via
                # 'button_confirm_closing_bank_balance' button
                to_write_id_list = []
                for r in self.read(cr, uid, ids,
                    [ 'closing_balance_frozen', 'journal_id', ],
                    context=context):
                    if not r['closing_balance_frozen']:
                        if r['journal_id']:
                            jtype = self.pool.get('account.journal').read(cr,
                                uid, [r['journal_id'][0]],
                                context=context)[0]['type']
                            if jtype != 'cash':
                                args = [('prev_reg_id', '=', r['id'])]
                                search_ids = self.search(cr, uid, args,
                                    context=context)
                                if search_ids:
                                    to_write_id_list.extend(search_ids)
                self.write(cr, uid, to_write_id_list, new_vals, context=context)

        return super(account_cash_statement, self).write(cr, uid, ids, vals,
            context=context)

    def button_open_cash(self, cr, uid, ids, context=None):
        if context is None:
            context = {}
        if isinstance(ids, (int, long)):
            ids = [ids] # Calculate the starting balance

        context['from_open'] = True
        res = self._get_starting_balance(cr, uid, ids, context=context)
        del context['from_open']
        for rs in res:
            self.write(cr, uid, [rs], res.get(rs)) # Verify that the starting balance is superior to 0 only if this register has prev_reg_id to False
            register = self.browse(cr, uid, [rs], context=context)[0]
            if register and not register.prev_reg_id:
                if not register.balance_start > 0:
                    return {'name' : "Open Empty CashBox Confirmation",
                            'type' : 'ir.actions.act_window',
                            'res_model' :"wizard.open.empty.cashbox",
                            'target': 'new',
                            'view_mode': 'form',
                            'view_type': 'form',
                            'context': {'active_id': ids[0],
                                        'active_ids': ids
                                        }
                            }

        # if the cashbox is valid for opening, just continue the method do open
        return self.do_button_open_cash(cr, uid, ids, context)

    def do_button_open_cash(self, cr, uid, ids, context=None):
        """
        when pressing 'Open CashBox' button : Open Cash Register and calculate the starting balance
        """
        if not context:
            context = {}
        if isinstance(ids, (int, long)):
            ids = [ids] # Calculate the starting balance

        # Prepare some values
        st = self.browse(cr, uid, ids, context=context)[0]

        # Complete closing balance with all elements of starting balance
        cashbox_line_obj = self.pool.get('account.cashbox.line')
        # Search lines from current register starting balance
        cashbox_line_ids = cashbox_line_obj.search(cr, uid, [('starting_id', '=', st.id)], context=context)
        # Search lines from current register ending balance and delete them
        cashbox_line_end_ids = cashbox_line_obj.search(cr, uid, [('ending_id', '=', st.id)], context=context)
        cashbox_line_obj.unlink(cr, uid, cashbox_line_end_ids, context=context)
        # Recreate all lines from starting to ending
        for line in cashbox_line_obj.browse(cr, uid, cashbox_line_ids, context=context):
            vals = {
                'ending_id': st.id,
                'pieces': line.pieces,
                'number': 0.0,
            }
            cashbox_line_obj.create(cr, uid, vals, context=context)
        # Give a Cash Register Name with the following composition :
        #+ Cash Journal Name
        if st.journal_id and st.journal_id.name:
            return self.write(cr, uid, ids, {'state' : 'open', 'name': st.journal_id.name})
        else:
            return False

    def button_confirm_cash(self, cr, uid, ids, context=None):
        """
        when you're attempting to close a CashBox via 'Close CashBox'
        """
        # First verify that all lines are in hard state
        for st in self.browse(cr, uid, ids, context=context):
            for line in st.line_ids:
                if line.state != 'hard':
                    raise osv.except_osv(_('Warning'), _('All entries must be hard posted before closing CashBox!'))
        # Then verify that another Cash Register exists
        for st in self.browse(cr, uid, ids, context=context):
            st_prev_ids = self.search(cr, uid, [('prev_reg_id', '=', st.id)], context=context)
            if len(st_prev_ids) > 1:
                raise osv.except_osv(_('Error'), _('A problem occured: More than one register have this one as previous register!'))
            # Verify that the closing balance have been freezed
            if not st.closing_balance_frozen:
                raise osv.except_osv(_('Error'), _("Please confirm closing balance before closing register named '%s'") % st.name or '')
            # Do not permit closing Cash Register if previous register is not closed! (confirm state)
            if st.prev_reg_id and st.prev_reg_id.state != 'confirm':
                raise osv.except_osv(_('Error'), _('Please close previous register before closing this one!'))
        # Then we open a wizard to permit the user to confirm that he want to close CashBox
        return {
            'name' : "Closing CashBox",
            'type' : 'ir.actions.act_window',
            'res_model' :"wizard.closing.cashbox",
            'target': 'new',
            'view_mode': 'form',
            'view_type': 'form',
            'context': {
                    'active_id': ids[0],
                    'active_ids': ids
                }
        }

    def _end_balance(self, cr, uid, ids, field_name=None, arg=None, context=None):
        """
        Calculate register's balance: call super, then add the Open Advance Amount to the end balance
        """
        res = super(account_cash_statement, self)._end_balance(cr, uid, ids, field_name, arg, context)
        for statement in self.browse(cr, uid, ids, context):
            # UF-425: Add the Open Advances Amount when calculating the "Calculated Balance" value
            res[statement.id] -= statement.open_advance_amount or 0.0
            # UF-810: Add a "Unrecorded Expenses" when calculating "Calculated Balance"
            res[statement.id] -= statement.unrecorded_expenses_amount or 0.0
        return res

    def _gap_compute(self, cursor, user, ids, name, attr, context=None):
        res = {}
        statements = self.browse(cursor, user, ids, context=context)
        for statement in statements:
            diff_amount = statement.balance_end - statement.balance_end_cash
            res[statement.id] = diff_amount
        return res

    def _msf_calculated_balance_compute(self, cr, uid, ids, field_name=None, arg=None, context=None):
        """
        Sum of opening balance (balance_start) and sum of cash transaction (total_entry_encoding)
        """
        # Prepare some values
        res = {}
        for st in self.browse(cr, uid, ids):
            amount = (st.balance_start or 0.0) + (st.total_entry_encoding or 0.0)
            res[st.id] = amount
            # Update next register opening balance
            if st.journal_id and st.journal_id.type == 'cash':
                next_st_ids = self.search(cr, uid, [('prev_reg_id', '=', st.id)])
                for next_st in self.browse(cr, uid, next_st_ids):
                    if next_st.state != 'confirm':
                        self.write(cr, uid, [next_st.id], {'balance_start': amount})
        return res

    def _get_sum_entry_encoding(self, cr, uid, ids, field_name=None, arg=None, context=None):
        """
        Sum of given register's transactions
        """
        res = {}
        if not ids:
            return res
        # Complete those that have no result
        for i in ids:
            res[i] = 0.0
        # COMPUTE amounts
        cr.execute("""
        SELECT statement_id, SUM(amount)
        FROM account_bank_statement_line
        WHERE statement_id in %s
        GROUP BY statement_id""", (tuple(ids,),))
        sql_res = cr.fetchall()
        if sql_res:
            res.update(dict(sql_res))
        return res

    _columns = {
            'balance_end': fields.function(_end_balance, method=True, store=False, string='Calculated Balance'),
            'state': fields.selection((('draft', 'Draft'), ('open', 'Open'), ('partial_close', 'Partial Close'), ('confirm', 'Closed')),
                readonly="True", string='State'),
            'name': fields.char('Register Name', size=64, required=False, readonly=True, states={'draft': [('readonly', False)]}),
            'period_id': fields.many2one('account.period', 'Period', required=True),
            'line_ids': fields.one2many('account.bank.statement.line', 'statement_id', 'Statement lines',
                states={'partial_close':[('readonly', True)], 'confirm':[('readonly', True)], 'draft':[('readonly', True)]}),
            'open_advance_amount': fields.float('Unrecorded Advances'),
            'unrecorded_expenses_amount': fields.float('Unrecorded expenses'),
            'closing_gap': fields.function(_gap_compute, method=True, string='Gap'),
            'comments': fields.char('Comments', size=64, required=False, readonly=False),
            'msf_calculated_balance': fields.function(_msf_calculated_balance_compute, method=True, readonly=True, string='Calculated Balance',
                help="Opening balance + Cash Transaction"),
            # Because of UTP-382, need to change store=True to FALSE for total_entry_encoding (which do not update fields at register line deletion/copy)
            'total_entry_encoding': fields.function(_get_sum_entry_encoding, method=True, store=False, string="Cash Transaction", help="Total cash transactions"),
    }

    def button_wiz_temp_posting(self, cr, uid, ids, context=None):
        """
        When pressing 'Temp Posting' button then opening a wizard to select some account_bank_statement_line and change them into temp posting state.
        """
        domain = [('statement_id', '=', ids[0]), ('state', '=', 'draft')]
        if context is None:
            context = {}
        context['type_posting'] = 'temp'
        # Prepare view
        view = self.pool.get('ir.model.data').get_object_reference(cr, uid, 'register_accounting', 'view_account_bank_statement_line_tree')
        view_id = view and view[1] or False
        # Prepare search view
        search_view = self.pool.get('ir.model.data').get_object_reference(cr, uid, 'register_accounting', 'view_account_bank_statement_line_filter')
        search_view_id = search_view and search_view[1] or False
        return {
            'name': 'Temp Posting from %s' % self.browse(cr, uid, ids[0]).name,
            'type': 'ir.actions.act_window',
            'res_model': 'account.bank.statement.line',
            'view_type': 'form',
            'view_mode': 'tree,form',
            'view_id': [view_id],
            'search_view_id': search_view_id,
            'domain': domain,
            'context': context,
            'target': 'crush', # use any word to crush the actual tab
        }

    def button_wiz_hard_posting(self, cr, uid, ids, context=None):
        """
        When pressing 'Hard Posting' button then opening a wizard to select some account_bank_statement_line and change them into hard posting state.
        """
        domain = [('statement_id', '=', ids[0]), ('state', 'in', ['draft','temp'])]
        if context is None:
            context = {}
        context['type_posting'] = 'hard'
        # Prepare view
        view = self.pool.get('ir.model.data').get_object_reference(cr, uid, 'register_accounting', 'view_account_bank_statement_line_tree')
        view_id = view and view[1] or False
        # Prepare search view
        search_view = self.pool.get('ir.model.data').get_object_reference(cr, uid, 'register_accounting', 'view_account_bank_statement_line_filter')
        search_view_id = search_view and search_view[1] or False
        return {
            'name': 'Hard Posting from %s' % self.browse(cr, uid, ids[0]).name,
            'type': 'ir.actions.act_window',
            'res_model': 'account.bank.statement.line',
            'view_type': 'form',
            'view_mode': 'tree,form',
            'view_id': [view_id],
            'search_view_id': search_view_id,
            'domain': domain,
            'context': context,
            'target': 'crush', # use any word to crush the actual tab
        }

account_cash_statement()


class account_cashbox_line(osv.osv):
    _inherit = "account.cashbox.line"
    _order = "pieces"

account_cashbox_line()


class account_bank_statement_line(osv.osv):
    _inherit = 'account.bank.statement.line'

    _columns = {
        # UTP-482 linked confirmed PO for an operational advance in cache register
        'cash_register_op_advance_po_id': fields.many2one('purchase.order', 'OPE ADV - LINK TO PO', required=False, help='Operational advance purchase order'),
    }

    def check_is_cash_register_op_advance_po_available(self, cr, uid, ids, context=None):
        """
            cash_register_op_advance_po_id m2o allowed
            for an Operational advance type for specific treatment account
        """
        if isinstance(ids, (int, long)):
            ids = [ids]
        for o in self.browse(cr, uid, ids, context=context):
            if o.cash_register_op_advance_po_id:
                if o.account_id and o.account_id.type_for_register != 'advance':
                    return False
        return True

    _constraints = [
        (check_is_cash_register_op_advance_po_available, 'You can only link to a purchase order for an Operation advance', ['account_id', 'cash_register_op_advance_po_id']),
    ]

    def create(self, cr, uid, values, context=None):
        if 'cash_register_op_advance_po_id' in values:
            if values['cash_register_op_advance_po_id']:
                domain = [
                    ('cash_register_op_advance_po_id', '=', values['cash_register_op_advance_po_id'])
                ]
                linked_po_ids = self.search(cr, uid, domain, context=context)
                if linked_po_ids:
                    raise osv.except_osv(_("Warning"),_("Selected 'OPE ADV - LINK TO PO' purchase order is already linked to another register line."))
        return super(account_bank_statement_line, self).create(cr, uid, values, context=context)

    def write(self, cr, uid, ids, values, context=None):
        if 'cash_register_op_advance_po_id' in values:
            if values['cash_register_op_advance_po_id']:
                domain = [
                    ('id', 'not in', ids),
                    ('cash_register_op_advance_po_id', '=', values['cash_register_op_advance_po_id'])
                ]
                linked_po_ids = self.search(cr, uid, domain, context=context)
                if linked_po_ids:
                    raise osv.except_osv(_("Warning"),_("Selected 'OPE ADV - LINK TO PO' purchase order is already linked to another register line."))
        return super(account_bank_statement_line, self).write(cr, uid, ids, values, context=context)

account_bank_statement_line()

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
