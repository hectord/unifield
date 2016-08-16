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
from register_tools import _get_third_parties
from register_tools import _set_third_parties
from register_tools import _get_third_parties_name
from lxml import etree

class account_move_line(osv.osv):
    _name = "account.move.line"
    _inherit = "account.move.line"

    def _get_fake(self, cr, uid, ids, field_name=None, arg=None, context=None):
        """
        Lines that have an account that come from a cheque register.
        """
        res = {}
        for i in ids:
            res[i] = False
        return res

    def _search_cheque(self, cr, uid, obj, name, args, context=None):
        """
        Search cheque move lines
        """
        if not args:
            return []
        if args[0][1] != '=' or not args[0][2]:
            raise osv.except_osv(_('Error'), _('Filter not implemented.'))
        j_obj = self.pool.get('account.journal')
        j_ids = j_obj.search(cr, uid, [('type', '=', 'cheque')])
        if not j_ids:
            return [('id', '=', 0)]
        res = []
        for j in j_obj.read(cr, uid, j_ids, ['default_debit_account_id', 'default_credit_account_id']):
            if j['default_debit_account_id']:
                res.append(j['default_debit_account_id'][0])
            if j['default_credit_account_id']:
                res.append(j['default_credit_account_id'][0])
        return [('account_id', 'in', res)]

    def _search_ready_for_import_in_register(self, cr, uid, obj, name, args, context=None):
        """
        Only permit to import invoice regarding some criteria (Cf. dom1 variable content).
        Add debit note default account filter for search (if this account have been selected)
        """
        if context is None:
            context = {}
        if not args:
            return []
        dom1 = [
            ('account_id.type','in',['receivable','payable']),
            ('reconcile_id','=',False),
            ('state', '=', 'valid'),
            ('move_state', '=', 'posted'), # UFTP-204: Exclude the Direct Invoice from the list
            ('journal_id.type', 'not in', ['migration']),  # US-70 Open the pending payment to receivable and payable entries from all journals except for the migration journal
            ('account_id.type_for_register', 'not in', ['down_payment', 'advance', 'donation', ]),
            # UTP-1088 exclude correction/reversal lines as can be in journal of type correction
            ('corrected_line_id', '=', False),  # is a correction line if has a corrected line
            ('reversal_line_id', '=', False),  # is a reversal line if a reversed line
            ('is_downpayment', '=', False),  # US-738/UC4
        ]

        # UFTP-358: do not allow to import an entry from November in an October
        # entry (from a future period)
        st_period_id = context.get('st_period_id', False)  # register period id
        if st_period_id:
            period_r = self.pool.get('account.period').read(cr, uid,
                [st_period_id], ['date_stop'], context=context)[0]
            if period_r:
                # exclude future periods
                dom1.append(('date', '<=', period_r['date_stop']))

        # verify debit note default account configuration
        default_account = self.pool.get('res.users').browse(cr, uid, uid, context).company_id.import_invoice_default_account
        if default_account:
            dom1.append(('account_id', '!=', default_account.id))
        return dom1+[('amount_residual_import_inv', '>', 0.001)]

    # @@override account.account_move_line _amount_residual()
    def _amount_residual_import_inv(self, cr, uid, ids, field_names, args, context=None):
        res = {}
        if context is None:
            context = {}
        cur_obj = self.pool.get('res.currency')
        for move_line in self.browse(cr, uid, ids, context=context):
            res[move_line.id] = 0.0

            if move_line.reconcile_id:
                continue
            if not move_line.account_id.type in ('payable', 'receivable'):
                #this function does not suport to be used on move lines not related to payable or receivable accounts
                continue

            move_line_total = move_line.amount_currency
            sign = move_line.amount_currency < 0 and -1 or 1

            context_unreconciled = context.copy()
            if move_line.reconcile_partial_id:
                for payment_line in move_line.reconcile_partial_id.line_partial_ids:
                    if payment_line.id == move_line.id:
                        continue
                    if payment_line.currency_id and move_line.currency_id and payment_line.currency_id.id == move_line.currency_id.id:
                            move_line_total += payment_line.amount_currency
                    else:
                        raise osv.except_osv(_('No Currency'),_("Payment line without currency %s")%(payment_line.id,))
                        if move_line.currency_id:
                            context_unreconciled.update({'date': payment_line.date})
                            amount_in_foreign_currency = cur_obj.compute(cr, uid, move_line.company_id.currency_id.id, move_line.currency_id.id, (payment_line.debit - payment_line.credit), round=False, context=context_unreconciled)
                            move_line_total += amount_in_foreign_currency
                        else:
                            raise osv.except_osv(_('No Currency'),_("Move line without currency %s")%(move_line.id,))
            for reg_line in move_line.imported_invoice_line_ids:
                if move_line_total == 0:
                    break
                if reg_line.state == 'temp':
                    if reg_line.currency_id.id != move_line.currency_id.id:
                        raise osv.except_osv(_('Error Currency'),_("Register line %s: currency not equal to invoice %s")%(reg_line.id,move_line.id,))
                    amount_reg = reg_line.amount
                    ignore_id = reg_line.first_move_line_id.id
                    for ml in sorted(reg_line.imported_invoice_line_ids, key=lambda x: abs(x.amount_currency)):
                        if ml.id == ignore_id:
                            continue
                        if ml.id == move_line.id:
                            if abs(move_line_total) < abs(amount_reg):
                                move_line_total = 0
                            else:
                                move_line_total = move_line_total-amount_reg
                            break
                        if abs(ml.amount_currency) > abs(amount_reg):
                            break
                        amount_reg -= ml.amount_currency

            result = move_line_total
            res[move_line.id] =  sign * (move_line.currency_id and self.pool.get('res.currency').round(cr, uid, move_line.currency_id.rounding, result) or result)
        return res

    def _get_reconciles(self, cr, uid, ids, context=None):
        return self.pool.get('account.move.line').search(cr, uid, ['|', ('reconcile_id','in',ids), ('reconcile_partial_id','in',ids)])

    def _get_linked_statement(self, cr, uid, ids, context=None):
        new_move = True
        r_move = {}
        while new_move:
            move = {}
            for reg in  self.read(cr, uid, ids, ['imported_invoice_line_ids']):
                for m in reg['imported_invoice_line_ids']:
                    move[m] = True
                    r_move[m] = True
            new_move = False
            if move:
                reg_ids = self.search(cr, uid, [('imported_invoice_line_ids', 'in', move.keys())])
                ids = self.pool.get('account.move.line').search(cr, uid, [('imported_invoice_line_ids', 'in', reg_ids), ('id', 'not in', r_move.keys())])
                if ids:
                    new_move = True
                    for i in ids:
                        r_move[i] = True
        return r_move.keys()

    _columns = {
        'transfer_journal_id': fields.many2one('account.journal', 'Journal', ondelete="restrict"),
        'employee_id': fields.many2one("hr.employee", "Employee", ondelete="restrict"),
        'partner_type': fields.function(_get_third_parties, fnct_inv=_set_third_parties, type='reference', method=True,
            string="Third Parties", selection=[('res.partner', 'Partner'), ('account.journal', 'Journal'), ('hr.employee', 'Employee')],
            multi="third_parties_key"),
        'partner_type_mandatory': fields.boolean('Third Party Mandatory'),
        'third_parties': fields.function(_get_third_parties, type='reference', method=True,
            string="Third Parties", selection=[('res.partner', 'Partner'), ('account.journal', 'Journal'), ('hr.employee', 'Employee')],
            help="To use for python code when registering", multi="third_parties_key"),
        'supplier_invoice_ref': fields.related('invoice', 'name', type='char', size=64, string="Supplier inv.ref.", store=False),
        'imported_invoice_line_ids': fields.many2many('account.bank.statement.line', 'imported_invoice', 'move_line_id', 'st_line_id',
            string="Imported Invoices", required=False, readonly=True),
        'from_import_invoice_ml_id': fields.many2one('account.move.line', 'From import invoice',
            help="Move line that have been used for an Pending Payments Wizard in order to generate the present move line"),
        'is_cheque': fields.function(_get_fake, fnct_search=_search_cheque, type="boolean", method=True, string="Come from a cheque register ?",
            help="True if this line come from a cheque register and especially from an account attached to a cheque register."),
        'ready_for_import_in_register': fields.function(_get_fake, fnct_search=_search_ready_for_import_in_register, type="boolean",
            method=True, string="Can be imported as invoice in register?",),
        'from_import_cheque_id': fields.one2many('account.bank.statement.line', 'from_import_cheque_id', string="Cheque Imported",
            help="This line has been created by a cheque import. This id is the move line imported."),
        'amount_residual_import_inv': fields.function(_amount_residual_import_inv, method=True, string='Residual Amount',
                        store={
                          'account.move.line': (lambda self, cr, uid, ids, c=None: ids, ['amount_currency','reconcile_id','reconcile_partial_id','imported_invoice_line_ids'], 10),
                          'account.move.reconcile': (_get_reconciles, None, 10),
                          'account.bank.statement.line': (_get_linked_statement, None, 10),
                        }),
        'partner_txt': fields.text(string="Third Parties", help="Help user to display and sort Third Parties"),
        'partner_identification': fields.related('employee_id', 'identification_id', type='char', string='Id No', size=32),
        'down_payment_id': fields.many2one('purchase.order', string="Purchase Order for Down Payment", readonly=True, ondelete='cascade'),
        'down_payment_amount': fields.float(string='Down Payment used amount', readonly=True),
        'transfer_amount': fields.float(string="Transfer amount", readonly=True, required=False),
        'is_transfer_with_change': fields.boolean(string="Is a line that come from a transfer with change?", readonly=True, required=False),
        'cheque_number': fields.char(string="Cheque Number", size=120, readonly=True),
        'is_downpayment': fields.boolean('Is downpayment'),  # US-738/UC4
    }

    _defaults = {
        'partner_txt': lambda *a: '',
        'down_payment_amount': lambda *a: 0.0,
        'is_transfer_with_change': lambda *a: False,
        'cheque_number': lambda *a: '',
        'is_downpayment': lambda *a: False,
    }

    def fields_view_get(self, cr, uid, view_id=None, view_type='form', context=None, toolbar=False, submenu=False):
        """
        Correct fields in order to have those from account_statement_from_invoice_lines (in case where account_statement_from_invoice is used)
        """
        if context is None:
            context = {}
        if 'from' in context:
            c_from = context.get('from')
            module = 'register_accounting'
            if c_from == 'wizard_import_invoice' or c_from == 'wizard_import_cheque':
                view_name = 'invoice_from_registers_tree'
                if c_from == 'wizard_import_cheque':
                    view_name = 'cheque_from_registers_tree'
                if view_type == 'search':
                    module = 'account'
                    view_name = 'view_account_move_line_filter'
                view = self.pool.get('ir.model.data').get_object_reference(cr, uid, module, view_name)
                if view:
                    view_id = view[1]
        result = super(osv.osv, self).fields_view_get(cr, uid, view_id, view_type, context=context, toolbar=toolbar, submenu=submenu)
        if view_type == 'search' and 'from' in context:
            if context.get('from') == 'wizard_import_invoice' or context.get('from') == 'wizard_import_cheque':
                search = etree.fromstring(result['arch'])
                tags = search.xpath('/search')
                for tag in tags:
                    tag.set('string', _("Account Entry Lines"))
                result['arch'] = etree.tostring(search)
        return result

    def onchange_account_id(self, cr, uid, ids, account_id=False, third_party=False):
        """
        Update some values and do this if a partner_id is given
        """
        # @@@override account.account_move_line.onchange_account_id
        account_obj = self.pool.get('account.account')
        partner_obj = self.pool.get('res.partner')
        fiscal_pos_obj = self.pool.get('account.fiscal.position')
        val = {}
        if isinstance(account_id, (list, tuple)):
            account_id = account_id[0]

        # Add partner_id variable in order to the function to works
        partner_id = False
        if third_party:
            third_vals = third_party.split(",")
            if third_vals[0] == "res.partner":
                partner_id = third_vals[1]
        # end of add
        if account_id:
            res = account_obj.browse(cr, uid, account_id)
            tax_ids = res.tax_ids
            if tax_ids and partner_id:
                part = partner_obj.browse(cr, uid, partner_id)
                tax_id = fiscal_pos_obj.map_tax(cr, uid, part and part.property_account_position or False, tax_ids)[0]
            else:
                tax_id = tax_ids and tax_ids[0].id or False
            val['account_tax_id'] = tax_id
        # @@@end

        # Prepare some values
        acc_obj = self.pool.get('account.account')
        third_type = [('res.partner', 'Partner'), ('hr.employee', 'Employee')] # UF-1022 By default should display Partner and employee
        third_required = False
        third_selection = 'res.partner,0'
        # if an account is given, then attempting to change third_type and information about the third required
        if account_id:
            account = acc_obj.browse(cr, uid, [account_id])[0]
            acc_type = account.type_for_register
            if acc_type  in ['transfer', 'transfer_same']:
                # UF-428: transfer type shows only Journals instead of Registers as before
                third_type = [('account.journal', 'Journal')]
                third_required = True
                third_selection = 'account.journal,0'

            elif acc_type == 'advance':
                third_type = [('hr.employee', 'Employee')]
                third_required = True
                third_selection = 'hr.employee,0'
        val.update({'partner_type_mandatory': third_required, 'partner_type': {'options': third_type, 'selection': third_selection}})
        return {'value': val}

    def onchange_partner_type(self, cr, uid, ids, partner_type=None, credit=None, debit=None, context=None):
        """
        Give the right account_id according partner_type and third parties choosed
        """
        ## TO BE FIXED listgrid.py
        if isinstance(partner_type, dict):
            partner_type = partner_type.get('selection')
        return self.pool.get('account.bank.statement.line').onchange_partner_type(cr, uid, ids, partner_type, credit, debit, context=context)

    def create(self, cr, uid, vals, context=None, check=True):
        """
        Add partner_txt to vals regarding partner_id, employee_id and transfer_journal_id
        """
        # Some verifications
        if not context:
            context = {}
        #UF-2214: if data comes from the sync, retrieve also the inactive
        if context.get('sync_update_execution', False):
            context.update({'active_test': False})

        # Retrieve third party name
        res = _get_third_parties_name(self, cr, uid, vals, context=context)
        if res:
            vals.update({'partner_txt': res})
        # If partner_type have been set to False (UF-1789)
        if 'partner_type' in vals and not vals.get('partner_type'):
            vals.update({'partner_txt': False})
        return super(account_move_line, self).create(cr, uid, vals, context=context, check=check)

    def write(self, cr, uid, ids, vals, context=None, check=True, update_check=True):
        """
        Add partner_txt to vals.
        """
        # Some verifications
        if not context:
            context = {}
        if isinstance(ids, (int, long)):
            ids = [ids]
        # Get third_parties_name
        res = _get_third_parties_name(self, cr, uid, vals, context=context)
        if res:
            vals.update({'partner_txt': res})
        # If partner_type have been set to False (UF-1789)
        if 'partner_type' in vals and not vals.get('partner_type'):
            vals.update({'partner_txt': False})
        return super(account_move_line, self).write(cr, uid, ids, vals, context=context, check=check, update_check=update_check)

account_move_line()
# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
