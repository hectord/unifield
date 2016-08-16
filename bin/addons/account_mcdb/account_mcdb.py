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
from tools import flatten

class account_mcdb(osv.osv):
    _name = 'account.mcdb'

    _columns = {
        'description': fields.char("Query name", required=False, readonly=False, size=255),
        'journal_ids': fields.many2many(obj='account.journal', rel='account_journal_mcdb', id1='mcdb_id', id2='journal_id', string="Journal Code", domain="[('code', '!=', 'IB')]"),  # exclude year closing initial balance journal
        'instance_ids': fields.many2many('msf.instance', 'instance_mcdb', 'mcdb_id', 'instance_id', string="Proprietary instance"),
        'analytic_journal_ids': fields.many2many(obj='account.analytic.journal', rel='account_analytic_journal_mcdb', id1='mcdb_id', id2='analytic_journal_id', string="Analytic journal code"),
        'abs_id': fields.many2one('account.bank.statement', string="Register name"), # Change into many2many ?
        'posting_date_from': fields.date('First posting date'),
        'posting_date_to': fields.date('Ending posting date'),
        'document_date_from': fields.date('First document date'),
        'document_date_to': fields.date('Ending document date'),
        'document_code': fields.char(string='Sequence number', size=255),
        'document_state': fields.selection([('posted', 'Posted'), ('draft', 'Unposted')], string="Entry Status"),
        'period_ids': fields.many2many(obj='account.period', rel="account_period_mcdb", id1="mcdb_id", id2="period_id", string="Accounting Period"),
        'account_ids': fields.many2many(obj='account.account', rel='account_account_mcdb', id1='mcdb_id', id2='account_id', string="Account Code"),
        'partner_id': fields.many2one('res.partner', string="Partner"),
        'employee_id': fields.many2one('hr.employee', string="Employee"),
        'transfer_journal_id': fields.many2one('account.journal', string="Journal", domain="[('code', '!=', 'IB')]"),  # exclude year closing initial balance journal
        'reconciled': fields.selection([('reconciled', 'Reconciled'), ('unreconciled', 'NOT reconciled')], string='Reconciled?'),
        'functional_currency_id': fields.many2one('res.currency', string="Functional currency", readonly=True),
        'amount_func_from': fields.float('Begin amount in functional currency'),
        'amount_func_to': fields.float('Ending amount in functional currency'),
        'booking_currency_id': fields.many2one('res.currency', string="Booking currency"),
        'amount_book_from': fields.float('Begin amount in booking currency'),
        'amount_book_to': fields.float('Ending amount in booking currency'),
        'currency_choice': fields.selection([('booking', 'Booking'), ('functional', 'Functional')], string="Currency type"),
        'currency_id': fields.many2one('res.currency', string="Currency"),
        'amount_from': fields.float('Begin amount in given currency type'),
        'amount_to': fields.float('Ending amount in given currency type'),
        'account_type_ids': fields.many2many(obj='account.account.type', rel='account_account_type_mcdb', id1='mcdb_id', id2='account_type_id',
            string="Account type"),
        'reconcile_id': fields.many2one('account.move.reconcile', string="Reconcile Reference"),
        'ref': fields.char(string='Reference', size=255),
        'name': fields.char(string='Description', size=255),
        'rev_account_ids': fields.boolean('Exclude account selection'),
        'model': fields.selection([('account.move.line', 'Journal Items'), ('account.analytic.line', 'Analytic Journal Items')], string="Type"),
        'display_in_output_currency': fields.many2one('res.currency', string='Display in output currency'),
        'fx_table_id': fields.many2one('res.currency.table', string="FX Table"),
        'analytic_account_cc_ids': fields.many2many(obj='account.analytic.account', rel="account_analytic_cc_mcdb", id1="mcdb_id", id2="analytic_account_id",
            string="Cost Center"),
        'rev_analytic_account_cc_ids': fields.boolean('Exclude Cost Center selection'),
        'analytic_account_fp_ids': fields.many2many(obj='account.analytic.account', rel="account_analytic_fp_mcdb", id1="mcdb_id", id2="analytic_account_id",
            string="Funding Pool"),
        'rev_analytic_account_fp_ids': fields.boolean('Exclude Funding Pool selection'),
        'analytic_account_f1_ids': fields.many2many(obj='account.analytic.account', rel="account_analytic_f1_mcdb", id1="mcdb_id", id2="analytic_account_id",
            string="Free 1"),
        'rev_analytic_account_f1_ids': fields.boolean('Exclude free 1 selection'),
        'analytic_account_f2_ids': fields.many2many(obj='account.analytic.account', rel="account_analytic_f2_mcdb", id1="mcdb_id", id2="analytic_account_id",
            string="Free 2"),
        'rev_analytic_account_f2_ids': fields.boolean('Exclude free 2 selection'),
        'reallocated': fields.selection([('reallocated', 'Reallocated'), ('unreallocated', 'NOT reallocated')], string='Reallocated?'),
        'reversed': fields.selection([('reversed', 'Reversed'), ('notreversed', 'NOT reversed')], string='Reversed?'),
        'rev_journal_ids': fields.boolean('Exclude journal selection'),
        'rev_period_ids': fields.boolean('Exclude period selection'),
        'rev_account_type_ids': fields.boolean('Exclude account type selection'),
        'rev_analytic_journal_ids': fields.boolean('Exclude analytic journal selection'),
        'rev_instance_ids': fields.boolean('Exclude instance selection'),
        'analytic_axis': fields.selection([('fp', 'Funding Pool'), ('f1', 'Free 1'), ('f2', 'Free 2')], string='Display'),
        'rev_analytic_account_dest_ids': fields.boolean('Exclude Destination selection'),
        'analytic_account_dest_ids': fields.many2many(obj='account.analytic.account', rel="account_analytic_dest_mcdb", id1="mcdb_id", id2="analytic_account_id",
            string="Destination"),
        'display_journal': fields.boolean('Display journals?'),
        'display_period': fields.boolean('Display periods?'),
        'display_instance': fields.boolean('Display instances?'),
        'display_account': fields.boolean('Display accounts?'),
        'display_analytic_account': fields.boolean('Display analytic accounts?'),
        'display_type': fields.boolean('Display account types?'),
        'display_analytic_period': fields.boolean('Display analytic periods?'),
        'display_analytic_journal': fields.boolean('Display analytic journals?'),
        'display_funding_pool': fields.boolean('Display funding pools?'),
        'display_cost_center': fields.boolean('Display cost centers?'),
        'display_destination': fields.boolean('Display destinations?'),
        'display_free1': fields.boolean('Display Free 1?'),
        'display_free2': fields.boolean('Display Free 2?'),
        'user': fields.many2one('res.users', "User"),
        'cheque_number': fields.char('Cheque Number', size=120),  # BKLG-7
        'partner_txt': fields.char('Third Party', size=120),  # BKLG-7
    }

    _defaults = {
        'model': lambda self, cr, uid, c: c.get('from', 'account.move.line'),
        'functional_currency_id': lambda self, cr, uid, c: self.pool.get('res.users').browse(cr, uid, uid, c).company_id.currency_id.id,
        'currency_choice': lambda *a: 'booking',
        'analytic_axis': lambda *a: 'fp',
        'display_journal': lambda *a: False,
        'display_period': lambda *a: False,
        'display_instance': lambda *a: False,
        'display_account': lambda *a: False,
        'display_analytic_account': lambda *a: False,
        'display_type': lambda *a: False,
        'display_analytic_period': lambda *a: False,
        'display_analytic_journal': lambda *a: False,
        'display_funding_pool': lambda *a: False,
        'display_cost_center': lambda *a: False,
        'display_destination': lambda *a: False,
        'user': lambda self, cr, uid, c: uid or False,
    }

    def onchange_currency_choice(self, cr, uid, ids, choice, func_curr=False, mnt_from=0.0, mnt_to=0.0, context=None):
        """
        Permit to give default company currency if 'functional' has been choosen.
        Delete all currency and amount fields (to not disturb normal mechanism)
        """
        # Some verifications
        if isinstance(ids, (int, long)):
            ids = [ids]
        if not choice:
            return {}
        # Prepare some values
        vals = {}
        # Reset fields
        for field in ['amount_book_from', 'amount_book_to', 'amount_func_from', 'amount_func_to', 'booking_currency_id']:
            vals[field] = 0.0
        # Fill in values
        if choice == 'functional':
            vals.update({'currency_id': func_curr or False})
        elif choice == 'booking':
            vals.update({'currency_id': False})
        # Update amounts 'from' and 'to'.
        update_from = self.onchange_amount(cr, uid, ids, choice, mnt_from, 'from', context=context)
        update_to = self.onchange_amount(cr, uid, ids, choice, mnt_to, 'to', context=context)
        if update_from:
            vals.update(update_from.get('value'))
        if update_to:
            vals.update(update_to.get('value'))
        return {'value': vals}

    def onchange_currency(self, cr, uid, ids, choice, currency, context=None):
        """
        Fill in right field regarding choice and currency
        """
        # Prepare some values
        vals = {}
        # Some verifications
        if not choice:
            return {}
        # Fill in field
        if choice == 'functional':
            vals['functional_currency_id'] = currency
        elif choice == 'booking':
            vals['booking_currency_id'] = currency
        return {'value': vals}

    def onchange_amount(self, cr, uid, ids, choice, amount, amount_type=None, context=None):
        """
        Fill in right amount field regarding choice
        """
        # Prepare some values
        vals = {}
        # Some verifications
        if not choice:
            return {}
        if not amount:
            amount = 0.0
        if choice == 'functional':
            if amount_type == 'from':
                vals['amount_func_from'] = amount
            elif amount_type == 'to':
                vals ['amount_func_to'] = amount
        elif choice == 'booking':
            if amount_type == 'from':
                vals['amount_book_from'] = amount
            elif amount_type == 'to':
                vals['amount_book_to'] = amount
        return {'value': vals}

    def onchange_fx_table(self, cr, uid, ids, fx_table_id, context=None):
        """
        Update output currency domain in order to show right currencies attached to given fx table
        """
        res = {}
        # Some verifications
        if not context:
            context = {}
        if fx_table_id:
            res.update({'value': {'display_in_output_currency' : False}})
        return res

    def onchange_analytic_axis(self, cr, uid, ids, analytic_axis, context=None):
        """
        Clean up Cost Center / Destination / Funding Pool / Free 1 and Free 2 frames
        """
        vals = {}
        if not analytic_axis:
            return {}
        vals.update({'analytic_account_fp_ids': False, 'analytic_account_cc_ids': False, 'analytic_account_dest_ids': False, 'analytic_account_f1_ids': False, 'analytic_account_f2_ids': False})
        return {'value': vals}

    def button_validate(self, cr, uid, ids, context=None):
        """
        Validate current forms and give result
        """
        # Some verifications
        if not context:
            context = {}
        if isinstance(ids, (int, long)):
            ids = [ids]
        # Prepare some values
        domain = []
        wiz = self.browse(cr, uid, [ids[0]], context=context)[0]
        res_model = wiz and wiz.model or False
        if res_model:
            # Prepare domain values
            # First MANY2MANY fields
            m2m_fields = [('period_ids', 'period_id'), ('journal_ids', 'journal_id'), ('analytic_journal_ids', 'journal_id'),
                ('analytic_account_fp_ids', 'account_id'), ('analytic_account_cc_ids', 'cost_center_id'),
                ('analytic_account_f1_ids', 'account_id'), ('analytic_account_f2_ids', 'account_id'), ('analytic_account_dest_ids', 'destination_id'),
                ('instance_ids', 'instance_id')]
            if res_model == 'account.analytic.line':
                m2m_fields.append(('account_ids', 'general_account_id'))
                m2m_fields.append(('account_type_ids', 'general_account_id.user_type'))
            else:
                m2m_fields.append(('account_ids', 'account_id'))
                m2m_fields.append(('account_type_ids', 'account_id.user_type'))
            for m2m in m2m_fields:
                if getattr(wiz, m2m[0]):
                    operator = 'in'
                    # Special fields
                    # account_ids with reversal
                    if m2m[0] == 'account_ids' and wiz.rev_account_ids:
                        operator = 'not in'
                    # analytic_account_fp_ids with reversal
                    if m2m[0] == 'analytic_account_fp_ids' and wiz.rev_analytic_account_fp_ids:
                        operator = 'not in'
                    # analytic_account_cc_ids with reversal
                    if m2m[0] == 'analytic_account_cc_ids' and wiz.rev_analytic_account_cc_ids:
                        operator = 'not in'
                    # analytic_account_f1_ids with reversal
                    if m2m[0] == 'analytic_account_f1_ids' and wiz.rev_analytic_account_f1_ids:
                        operator = 'not in'
                    # analytic_account_f2_ids with reversal
                    if m2m[0] == 'analytic_account_f2_ids' and wiz.rev_analytic_account_f2_ids:
                        operator = 'not in'
                    # analytic_account_dest_ids with reversal
                    if m2m[0] == 'analytic_account_dest_ids' and wiz.rev_analytic_account_dest_ids:
                        operator = 'not in'
                    # period_ids with reversal
                    if m2m[0] == 'period_ids' and wiz.rev_period_ids:
                        operator = 'not in'
                    # journal_ids with reversal
                    if m2m[0] == 'journal_ids' and wiz.rev_journal_ids:
                        operator = 'not in'
                    # account_type_ids with reversal
                    if m2m[0] == 'account_type_ids' and wiz.rev_account_type_ids:
                        operator = 'not in'
                    # analytic_journal_ids with reversal
                    if m2m[0] == 'analytic_journal_ids' and wiz.rev_analytic_journal_ids:
                        operator = 'not in'
                    # instance_ids with reversal
                    if m2m[0] == 'instance_ids' and wiz.rev_instance_ids:
                        operator = 'not in'
                    # Search if a view account is given
                    if m2m[0] in ['account_ids', 'analytic_account_fp_ids', 'analytic_account_cc_ids', 'analytic_account_f1_ids', 'analytic_account_f2_ids']:
                        account_ids = []
                        account_obj = 'account.account'
                        if m2m[0] in ['analytic_account_fp_ids', 'analytic_account_cc_ids', 'analytic_account_f1_ids', 'analytic_account_f2_ids']:
                            account_obj = 'account.analytic.account'
                        for account in getattr(wiz, m2m[0]):
                            if account.type == 'view':
                                search_ids = self.pool.get(account_obj).search(cr, uid, [('id', 'child_of', [account.id])])
                                account_ids.append(search_ids)
                        if account_ids:
                            # Add default account_ids from wizard
                            account_ids.append([x.id for x in getattr(wiz, m2m[0])])
                            # Convert list in a readable list for openerp
                            account_ids = flatten(account_ids)
                            # Create domain and NEXT element (otherwise this give a bad domain)
                            domain.append((m2m[1], operator, tuple(account_ids)))
                            continue
                    domain.append((m2m[1], operator, tuple([x.id for x in getattr(wiz, m2m[0])])))
            # Then MANY2ONE fields
            for m2o in [('abs_id', 'statement_id'), ('partner_id', 'partner_id'), ('employee_id', 'employee_id'),
                ('transfer_journal_id', 'transfer_journal_id'), ('booking_currency_id', 'currency_id')]:
                if getattr(wiz, m2o[0]):
                    domain.append((m2o[1], '=', getattr(wiz, m2o[0]).id))
            # Finally others fields
            # LOOKS LIKE fields
            for ll in [('ref', 'ref'), ('name', 'name'), ('cheque_number', 'cheque_number'), ('partner_txt', 'partner_txt')]:
                if getattr(wiz, ll[0]):
                    domain.append((ll[1], 'ilike', '%%%s%%' % getattr(wiz, ll[0])))
                    if ll[0] == 'cheque_number':
                        context['selector_display_cheque_number'] = True
            # DOCUMENT CODE fields
            if wiz.document_code and wiz.document_code != '':
                document_code_field = 'move_id.name'
                if res_model == 'account.analytic.line':
                    domain.append('|')
                    domain.append('|')
                    domain.append(('move_id.move_id.name', 'ilike', '%%%s%%' % wiz.document_code))
                    domain.append(('commitment_line_id.commit_id.name', 'ilike', '%%%s%%' % wiz.document_code))
                    domain.append(('entry_sequence', 'ilike', '%s' % wiz.document_code))
                else:
                    domain.append((document_code_field, 'ilike', '%%%s%%' % wiz.document_code))
            if wiz.document_state and wiz.document_state != '':
                domain.append(('move_id.state', '=', wiz.document_state))
            # DATE fields
            for sup in [('posting_date_from', 'date'), ('document_date_from', 'document_date')]:
                if getattr(wiz, sup[0]):
                    domain.append((sup[1], '>=', getattr(wiz, sup[0])))
            for inf in [('posting_date_to', 'date'), ('document_date_to', 'document_date')]:
                if getattr(wiz, inf[0]):
                    domain.append((inf[1], '<=', getattr(wiz, inf[0])))
            # RECONCILE field
            if wiz.reconcile_id:
                # total or partial and override  reconciled status
                domain.append(('reconcile_total_partial_id', '=', wiz.reconcile_id.id))
            elif wiz.reconciled:
                if wiz.reconciled == 'reconciled':
                    domain.append(('reconcile_id', '!=', False))  # only full reconcile
                elif wiz.reconciled == 'unreconciled':
                    domain.append(('reconcile_id', '=', False))   # partial or not reconcile (dont take care of reconcile_partial_id state)

            # REALLOCATION field
            if wiz.reallocated:
                if wiz.reallocated == 'reallocated':
                    domain.append(('is_reallocated', '=', True))
                elif wiz.reallocated == 'unreallocated':
                    domain.append(('is_reallocated', '=', False))
            # REVERSED field
            if wiz.reversed:
                if wiz.reversed == 'reversed':
                    domain.append(('is_reversal', '=', True))
                elif wiz.reversed == 'notreversed':
                    domain.append(('is_reversal', '=', False))
            # ANALYTIC AXIS FIELD
            if res_model == 'account.analytic.line':
                if wiz.analytic_axis == 'fp':
                    context.update({'display_fp': True, 'categ': 'FUNDING'})
                    domain.append(('account_id.category', '=', 'FUNDING'))
                elif wiz.analytic_axis == 'f1':
                    context.update({'categ': 'FREE1'})
                    domain.append(('account_id.category', '=', 'FREE1'))
                elif wiz.analytic_axis == 'f2':
                    context.update({'categ': 'FREE2'})
                    domain.append(('account_id.category', '=', 'FREE2'))
                else:
                    raise osv.except_osv(_('Warning'), _('Display field is mandatory!'))
            ## SPECIAL fields
            #
            # AMOUNTS fields
            #
            # NB: Amount problem has been resolved as this
            #+ There is 4 possibilities for amounts:
            #+ 1/ NO amount given: nothing to do
            #+ 2/ amount FROM AND amount TO is given
            #+ 3/ amount FROM is filled in but NOT amount TO
            #+ 4/ amount TO is filled in but NOT amount FROM
            #+
            # NB: on US-650 we agree that the "From" value is always the smallest and the "To" value is the biggest,
            # no matter if amounts are positive or negative
            #+ For each case, here is what domain should be look like:
            #+ 1/ FROM is 0.0, TO is 0,0. Domain is []
            #+ 2/ FROM is 400, TO is 600. Domain is ['&', (balance, '>=', 400), ('balance', '<=', 600)]
            #+ 3/ FROM is 400, TO is 0.0. Domain is [('balance', '>=', 400)]
            #+ 4/ FROM is 0.0, TO is 600. Domain is [('balance', '<=', 600)]

            # prepare tuples that would be processed
            booking = ('amount_book_from', 'amount_book_to', 'amount_currency')
            functional = ('amount_func_from', 'amount_func_to', 'balance')
            for curr in [booking, functional]:
                # Prepare some values
                mnt_from = getattr(wiz, curr[0]) or False
                mnt_to = getattr(wiz, curr[1]) or False
                # display a warning when amount FROM > amount TO
                if mnt_from and mnt_to and mnt_from > mnt_to:
                    raise osv.except_osv(_('Warning'),
                                         _('In the amount selector (from-to), the "from" value must be the smallest one.'))
                field = curr[2]
                # specific behaviour for functional in analytic MCDB
                if field == 'balance' and res_model == 'account.analytic.line':
                    field = 'amount'
                # domain elements initialisation
                domain_elements = []
                if mnt_from and mnt_to:
                    if mnt_from == mnt_to:
                        domain_elements = [(field, '=', mnt_from)]
                    else:
                        domain_elements = ['&', (field, '>=', mnt_from), (field, '<=', mnt_to)]
                elif mnt_from:
                    domain_elements = [(field, '>=', mnt_from)]
                elif mnt_to:
                    domain_elements = [(field, '<=', mnt_to)]
                # Add elements to domain which would be use for filtering
                for el in domain_elements:
                    domain.append(el)
            # Output currency display (with fx_table)
            if wiz.fx_table_id:
                context.update({'fx_table_id': wiz.fx_table_id.id, 'currency_table_id': wiz.fx_table_id.id})
            if wiz.display_in_output_currency:
                context.update({'output_currency_id': wiz.display_in_output_currency.id})
            # Return result in a search view
            view = 'account_move_line_mcdb_search_result'
            search_view = 'mcdb_view_account_move_line_filter'
            search_model = 'account_mcdb'
            name = _('Selector - G/L')
            if res_model == 'account.analytic.line':
                view = 'account_analytic_line_mcdb_search_result'
                search_view = 'view_account_analytic_line_filter'
                search_model = 'account'
                name = _('Selector - Analytic')
            view_id = self.pool.get('ir.model.data').get_object_reference(cr, uid, 'account_mcdb', view)
            view_id = view_id and view_id[1] or False
            search_view_id = self.pool.get('ir.model.data').get_object_reference(cr, uid, search_model, search_view)
            search_view_id = search_view_id and search_view_id[1] or False

            if res_model == 'account.move.line':
                # US-1290: JI export search result always exclude IB entries
                domain = [ ('period_id.number', '>', 0), ] + domain

            context['target_filename_prefix'] = name

            return {
                'name': name,
                'type': 'ir.actions.act_window',
                'res_model': res_model,
                'view_type': 'form',
                'view_mode': 'tree,form',
                'view_id': [view_id],
                'search_view_id': search_view_id,
                'domain': domain,
                'context': context,
                'target': 'current',
            }
        return False

    def button_clear(self, cr, uid, ids, field=False, context=None):
        """
        Delete all fields from this object
        """
        # Some verifications
        if not context:
            context = {}
        if isinstance(ids, (int, long)):
            ids = [ids]
        # Prepare some value
        res_id = ids[0]
        all_fields = True
        # Search model
        wiz = self.browse(cr, uid, res_id)
        res_model = wiz and wiz.model or False
        if field and field in (self._columns and self._columns.keys()):
            if self._columns[field]._type == 'many2many':
                # Don't clear all other fields
                all_fields = False
                # Clear this many2many field
                self.write(cr, uid, ids, {field: [(6,0,[])]}, context=context)
        # Clear all fields if necessary
        if all_fields:
            res_id = self.create(cr, uid, {'model': res_model}, context=context)
        # Update context
        context.update({
            'active_id': ids[0],
            'active_ids': ids,
        })
        # Prepare some values
        name = _('Selector')
        view_name = False
        if res_model == 'account.move.line':
            name = _('Selector - G/L')
            view_name = 'account_mcdb_form'
        elif res_model == 'account.analytic.line':
            name = _('Selector - Analytic')
            view_name = 'account_mcdb_analytic_form'
        if not view_name or not name:
            raise osv.except_osv(_('Error'), _('Error: System does not know from where you come from.'))
        # Search view_id
        view_id = self.pool.get('ir.model.data').get_object_reference(cr, uid, 'account_mcdb', view_name)
        view_id = view_id and view_id[1] or False
        return {
            'name': name,
            'type': 'ir.actions.act_window',
            'res_model': 'account.mcdb',
            'res_id': res_id,
            'view_type': 'form',
            'view_mode': 'form',
            'view_id': [view_id],
            'context': context,
            'target': 'crush',
        }

    def _button_add(self, cr, uid, ids, obj=False, field=False, args=None, context=None):
        """
        Search all elements of an object (obj) regarding criteria (args). Then return wizard and complete given field (field).
        NB: We consider field is always a MANY2ONE field! (no sense to add all elements of another field...)
        """
        if args is None:
            args = []
        # Some verifications
        if not context:
            context = {}
        if isinstance(ids, (int, long)):
            ids = [ids]
        # Prepare some values
        context.update({
            'active_id': ids[0],
            'active_ids': ids,
        })
        res_id = ids[0]
        # Do search
        if obj and field:
            # Search all elements
            element_ids = self.pool.get(obj).search(cr, uid, args)
            if element_ids:
                self.write(cr, uid, ids, {field: [(6, 0, element_ids)]})
        # Search model
        wiz = self.browse(cr, uid, res_id)
        res_model = wiz and wiz.model or False
        # Prepare some values
        name = _('Selector')
        view_name = False
        if res_model == 'account.move.line':
            name = _('Selector - G/L')
            view_name = 'account_mcdb_form'
        elif res_model == 'account.analytic.line':
            name = _('Selector - Analytic')
            view_name = 'account_mcdb_analytic_form'
        if not view_name or not name:
            raise osv.except_osv(_('Error'), _('Error: System does not know from where you come from.'))
        # Search view_id
        view_id = self.pool.get('ir.model.data').get_object_reference(cr, uid, 'account_mcdb', view_name)
        view_id = view_id and view_id[1] or False
        return {
            'name': name,
            'type': 'ir.actions.act_window',
            'res_model': 'account.mcdb',
            'res_id': res_id,
            'view_type': 'form',
            'view_mode': 'form',
            'view_id': [view_id],
            'context': context,
            'target': 'crush',
        }

    def button_journal_clear(self, cr, uid, ids, context=None):
        """
        Delete journal_ids field content
        """
        # Some verifications
        if not context:
            context = {}
        if isinstance(ids, (int, long)):
            ids = [ids]
        # Return default behaviour with 'journal_ids' field
        return self.button_clear(cr, uid, ids, field='journal_ids', context=context)

    def button_journal_add(self, cr, uid, ids, context=None):
        """
        Add all journals in journal_ids field content
        """
        # Some verifications
        if not context:
            context = {}
        if isinstance(ids, (int, long)):
            ids = [ids]
        # Prepare some values
        obj = 'account.journal'
        args = []
        field = 'journal_ids'
        return self._button_add(cr, uid, ids, obj, field, args, context=context)

    def button_period_clear(self, cr, uid, ids, context=None):
        """
        Delete period_ids field content
        """
        # Some verifications
        if not context:
            context = {}
        if isinstance(ids, (int, long)):
            ids = [ids]
        # Return default behaviour with 'period_ids' field
        return self.button_clear(cr, uid, ids, field='period_ids', context=context)

    def button_period_add(self, cr, uid, ids, context=None):
        """
        Add all periods in period_ids field content
        """
        # Some verifications
        if not context:
            context = {}
        if isinstance(ids, (int, long)):
            ids = [ids]
        # Prepare some values
        obj = 'account.period'
        args = []
        field = 'period_ids'
        return self._button_add(cr, uid, ids, obj, field, args, context=context)

    def button_analytic_journal_clear(self, cr, uid, ids, context=None):
        """
        Delete analytic_journal_ids field content
        """
        # Some verifications
        if not context:
            context = {}
        if isinstance(ids, (int, long)):
            ids = [ids]
        # Return default behaviour with 'analytic_journal_ids' field
        return self.button_clear(cr, uid, ids, field='analytic_journal_ids', context=context)

    def button_analytic_journal_add(self, cr, uid, ids, context=None):
        """
        Add all Analytic journals in analytic_journal_ids field content
        """
        # Some verifications
        if not context:
            context = {}
        if isinstance(ids, (int, long)):
            ids = [ids]
        # Prepare some values
        obj = 'account.analytic.journal'
        args = []
        field = 'analytic_journal_ids'
        return self._button_add(cr, uid, ids, obj, field, args, context=context)

    def button_account_clear(self, cr, uid, ids, context=None):
        """
        Delete account_ids field content
        """
        # Some verifications
        if not context:
            context = {}
        if isinstance(ids, (int, long)):
            ids = [ids]
        # Return default behaviour with 'account_ids' field
        return self.button_clear(cr, uid, ids, field='account_ids', context=context)

    def button_account_add(self, cr, uid, ids, context=None):
        """
        Add all Accounts in account_ids field content
        """
        # Some verifications
        if not context:
            context = {}
        if isinstance(ids, (int, long)):
            ids = [ids]
        # Prepare some values
        obj = 'account.account'
        args = [('parent_id', '!=', False)]
        field = 'account_ids'
        return self._button_add(cr, uid, ids, obj, field, args, context=context)

    def button_account_type_clear(self, cr, uid, ids, context=None):
        """
        Delete account_type_ids field content
        """
        # Some verifications
        if not context:
            context = {}
        if isinstance(ids, (int, long)):
            ids = [ids]
        # Return default behaviour with 'account_type_ids' field
        return self.button_clear(cr, uid, ids, field='account_type_ids', context=context)

    def button_account_type_add(self, cr, uid, ids, context=None):
        """
        Add all Account Type in account_type_ids field content
        """
        # Some verifications
        if not context:
            context = {}
        if isinstance(ids, (int, long)):
            ids = [ids]
        # Prepare some values
        obj = 'account.account.type'
        args = []
        field = 'account_type_ids'
        return self._button_add(cr, uid, ids, obj, field, args, context=context)

    def button_funding_pool_clear(self, cr, uid, ids, context=None):
        """
        Delete analytic_account_fp_ids field content
        """
        # Some verifications
        if not context:
            context = {}
        if isinstance(ids, (int, long)):
            ids = [ids]
        # Return default behaviour with 'analytic_account_fp_ids' field
        return self.button_clear(cr, uid, ids, field='analytic_account_fp_ids', context=context)

    def button_funding_pool_add(self, cr, uid, ids, context=None):
        """
        Add all Funding Pool in analytic_account_fp_ids field content
        """
        # Some verifications
        if not context:
            context = {}
        if isinstance(ids, (int, long)):
            ids = [ids]
        # Prepare some values
        obj = 'account.analytic.account'
        args = [('type', '!=', 'view'), ('category', '=', 'FUNDING')]
        field = 'analytic_account_fp_ids'
        return self._button_add(cr, uid, ids, obj, field, args, context=context)

    def button_cost_center_clear(self, cr, uid, ids, context=None):
        """
        Delete analytic_account_cc_ids field content
        """
        # Some verifications
        if not context:
            context = {}
        if isinstance(ids, (int, long)):
            ids = [ids]
        # Return default behaviour with 'analytic_account_cc_ids' field
        return self.button_clear(cr, uid, ids, field='analytic_account_cc_ids', context=context)

    def button_cost_center_add(self, cr, uid, ids, context=None):
        """
        Add all Cost Center in analytic_account_cc_ids field content
        """
        # Some verifications
        if not context:
            context = {}
        if isinstance(ids, (int, long)):
            ids = [ids]
        # Prepare some values
        obj = 'account.analytic.account'
        args = [('type', '!=', 'view'), ('category', '=', 'OC')]
        field = 'analytic_account_cc_ids'
        return self._button_add(cr, uid, ids, obj, field, args, context=context)

    def button_free_1_clear(self, cr, uid, ids, context=None):
        """
        Delete analytic_account_f1_ids field content
        """
        # Some verifications
        if not context:
            context = {}
        if isinstance(ids, (int, long)):
            ids = [ids]
        # Return default behaviour with 'analytic_account_f1_ids' field
        return self.button_clear(cr, uid, ids, field='analytic_account_f1_ids', context=context)

    def button_free_1_add(self, cr, uid, ids, context=None):
        """
        Add all Free 1 in analytic_account_f1_ids field content
        """
        # Some verifications
        if not context:
            context = {}
        if isinstance(ids, (int, long)):
            ids = [ids]
        # Prepare some values
        obj = 'account.analytic.account'
        args = [('type', '!=', 'view'), ('category', '=', 'FREE1')]
        field = 'analytic_account_f1_ids'
        return self._button_add(cr, uid, ids, obj, field, args, context=context)

    def button_free_2_clear(self, cr, uid, ids, context=None):
        """
        Delete analytic_account_f2_ids field content
        """
        # Some verifications
        if not context:
            context = {}
        if isinstance(ids, (int, long)):
            ids = [ids]
        # Return default behaviour with 'analytic_account_f2_ids' field
        return self.button_clear(cr, uid, ids, field='analytic_account_f2_ids', context=context)

    def button_free_2_add(self, cr, uid, ids, context=None):
        """
        Add all Free 2 in analytic_account_f2_ids field content
        """
        # Some verifications
        if not context:
            context = {}
        if isinstance(ids, (int, long)):
            ids = [ids]
        # Prepare some values
        obj = 'account.analytic.account'
        args = [('type', '!=', 'view'), ('category', '=', 'FREE2')]
        field = 'analytic_account_f2_ids'
        return self._button_add(cr, uid, ids, obj, field, args, context=context)

    def button_destination_clear(self, cr, uid, ids, context=None):
        """
        Delete analytic_account_dest_ids field content
        """
        # Some verifications
        if not context:
            context = {}
        if isinstance(ids, (int, long)):
            ids = [ids]
        # Return default behaviour with 'analytic_account_dest_ids' field
        return self.button_clear(cr, uid, ids, field='analytic_account_dest_ids', context=context)

    def button_destination_add(self, cr, uid, ids, context=None):
        """
        Add all Destination in analytic_account_dest_ids field content
        """
        # Some verifications
        if not context:
            context = {}
        if isinstance(ids, (int, long)):
            ids = [ids]
        # Prepare some values
        obj = 'account.analytic.account'
        args = [('type', '!=', 'view'), ('category', '=', 'DEST')]
        field = 'analytic_account_dest_ids'
        return self._button_add(cr, uid, ids, obj, field, args, context=context)

    def button_instance_clear(self, cr, uid, ids, context=None):
        """
        Delete instance_ids field content
        """
        # Some verifications
        if not context:
            context = {}
        if isinstance(ids, (int, long)):
            ids = [ids]
        # Return default behaviour with 'period_ids' field
        return self.button_clear(cr, uid, ids, field='instance_ids', context=context)

    def button_instance_add(self, cr, uid, ids, context=None):
        """
        Add all instances in instance_ids field content
        """
        # Some verifications
        if not context:
            context = {}
        if isinstance(ids, (int, long)):
            ids = [ids]
        # Prepare some values
        obj = 'msf.instance'
        args = []
        field = 'instance_ids'
        return self._button_add(cr, uid, ids, obj, field, args, context=context)

    def clean_up_search(self, cr, uid, ids, context=None):
        """
        Clean up objects that have no description.
        """
        if not context:
            context = {}
        to_clean = self.search(cr, uid, [('description', '=', False)])
        self.unlink(cr, uid, to_clean)
        return True

account_mcdb()
# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
