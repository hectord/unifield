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
from time import strftime
from tools.misc import flatten

class account_move_line(osv.osv):
    _name = 'account.move.line'
    _inherit = 'account.move.line'

    def _is_corrigible(self, cr, uid, ids, name, args, context=None):
        """
        Return True for all element that correspond to some criteria:
         - The entry state is posted
         - The account is not payables, receivables or tax
         - Item have not been corrected
         - Item have not been reversed
         - Item come from a reconciliation that have set 'is_addendum_line' to True
         - The account is not the default credit/debit account of the attached statement (register)
         - The line isn't partially or totally reconciled
         - The line doesn't come from a write-off
         - The line is "corrected_upstream" that implies the line have been already corrected from a coordo or a hq to a level that is superior or equal to these instance.
        """
        # Some checks
        if context is None:
            context = {}
        # Prepare some values
        res = {}
        # Search all accounts that are used in bank, cheque and cash registers
        journal_ids = self.pool.get('account.journal').search(cr, uid, [('type', 'in', ['bank', 'cheque', 'cash'])])
        account_ids = []
        company = self.pool.get('res.users').browse(cr, uid, uid, context=context).company_id
        level = company and company.instance_id and company.instance_id.level or ''
        for j in self.pool.get('account.journal').read(cr, uid, journal_ids, ['default_debit_account_id', 'default_credit_account_id']):
            if j.get('default_debit_account_id', False) and j.get('default_debit_account_id')[0] not in account_ids:
                account_ids.append(j.get('default_debit_account_id')[0])
            if j.get('default_credit_account_id', False) and j.get('default_credit_account_id')[0] not in account_ids:
                account_ids.append(j.get('default_credit_account_id')[0])

        acc_corr = {}

        # Skip to next element if the line is set to False
        for ml in self.browse(cr, 1, ids, context=context):
            res[ml.id] = True
            acc_corr.setdefault(ml.account_id.id, ml.account_id.user_type.not_correctible)
            # False if account type is transfer
            if ml.account_id.type_for_register in ['transfer', 'transfer_same']:
                res[ml.id] = False
                continue
            # False if move is not posted
            if ml.move_id.state != 'posted':
                res[ml.id] = False
                continue
            # False if account type code (User type) is set as non correctible
            if acc_corr.get(ml.account_id.id):
                res[ml.id] = False
                continue
            # False if line have been corrected
            if ml.corrected:
                res[ml.id] = False
                continue
            # False if line is a reversal
            if ml.reversal:
                res[ml.id] = False
                continue
            # False if this line is an addendum line
            if ml.is_addendum_line:
                res[ml.id] = False
                continue
            # False if line account and statement default debit/credit account are similar
            if ml.statement_id:
                accounts = []
                accounts.append(ml.statement_id.journal_id.default_debit_account_id and ml.statement_id.journal_id.default_debit_account_id.id)
                accounts.append(ml.statement_id.journal_id.default_credit_account_id and ml.statement_id.journal_id.default_credit_account_id.id)
                if ml.account_id.id in accounts:
                    res[ml.id] = False
                    continue
            # False if this line come from a write-off
            if ml.is_write_off:
                res[ml.id] = False
                continue
            # False if this line come from an accrual
            if ml.accrual:
                res[ml.id] = False
                continue
            # False if the account is used in a cash/bank/cheque journal
            if ml.account_id.id in account_ids:
                res[ml.id] = False
                continue
            # False if "corrected_upstream" is True and that we come from project level
            if ml.corrected_upstream and level == 'project':
                res[ml.id] = False
                continue
            # False if this line is a revaluation or a system entry
            if ml.journal_id.type in ('revaluation', 'system', ):
                res[ml.id] = False
                continue
            # False if the move line is partially or totally reconciled
            if ml.reconcile_id or ml.reconcile_partial_id:
                res[ml.id] = False
                continue
        return res

    _columns = {
        'corrected': fields.boolean(string="Corrected?", readonly=True,
            help="If true, this line has been corrected by an accounting correction wizard"),
        'corrected_line_id': fields.many2one('account.move.line', string="Corrected Line", readonly=True,
            help="Line that have been corrected by this one."),
        'reversal': fields.boolean(string="Reversal?", readonly=True,
            help="If true, this line is a reversal of another (This was done via a correction wizard)."),
        'reversal_line_id': fields.many2one('account.move.line', string="Reversal Line", readonly=True,
            help="Line that have been reversed by this one."),
        'have_an_historic': fields.boolean(string="Display historic?", readonly=True,
            help="If true, this implies that this line have historical correction(s)."),
        'is_corrigible': fields.function(_is_corrigible, method=True, string="Is corrigible?", type='boolean',
            readonly=True, help="This informs system if this item is corrigible. Criteria: the entry state should be posted, account should not be payable or \
receivable, item have not been corrected, item have not been reversed and account is not the default one of the linked register (statement).",
            store=False),
        'corrected_st_line_id': fields.many2one('account.bank.statement.line', string="Corrected register line", readonly=True,
            help="This register line is those which have been corrected last."),
        'last_cor_was_only_analytic': fields.boolean(string="AD Corrected?",
            invisible=True,
            help="If true, this line has been corrected by an accounting correction wizard but with only an AD correction (no G/L correction)"),
    }

    _defaults = {
        'corrected': lambda *a: False,
        'reversal': lambda *a: False,
        'have_an_historic': lambda *a: False,
        'is_corrigible': lambda *a: True,
        'last_cor_was_only_analytic': lambda *a: False,
    }

    def copy(self, cr, uid, aml_id, default=None, context=None):
        """
        Copy a move line with draft state. Do not create a new analytic_distribution from line if we come from a correction.
        """
        if default is None:
            default = {}
        if 'omit_analytic_distribution' in context and context.get('omit_analytic_distribution') is True:
            default.update({
                'analytic_distribution_id': False,
            })
        default.update({
            'state': 'draft',
            'have_an_historic': False,
            'corrected': False,
            'reversal': False,
            'last_cor_was_only_analytic': False,
        })
        # Add default date if no one given
        if not 'date' in default:
            default.update({'date': strftime('%Y-%m-%d')})
        return super(account_move_line, self).copy(cr, uid, aml_id, default, context=context)

    def get_corrections_history(self, cr, uid, ids, context=None):
        """
        Give for each line their history by using "corrected_line_id" field to browse lines
        Return something like that:
            {id1: [line_id, another_line_id], id2: [a_line_id, other_line_id]}
        """
        # Verifications
        if not context:
            context = {}
        if isinstance(ids, (int, long)):
            ids = [ids]
        # Prepare some values
        res = {}
        # Browse all given lines
        for ml in self.browse(cr, uid, ids, context=context):
            upstream_line_ids = []
            downstream_line_ids = []
            # Get upstream move lines
            line = ml
            while line != None:
                if line:
                    # Add line to result
                    upstream_line_ids.append(line.id)
                    # Add reversal line to result
                    reversal_ids = self.search(cr, uid, [('move_id', '=', line.move_id.id), ('reversal', '=', True)], context=context)
                    if reversal_ids:
                        upstream_line_ids.append(reversal_ids)
                if line.corrected_line_id:
                    line = line.corrected_line_id
                else:
                    line = None
            # Get downstream move lines
            sline_ids = [ml.id]
            while sline_ids != None:
                operator = 'in'
                if len(sline_ids) == 1:
                    operator = '='
                search_ids = self.search(cr, uid, [('corrected_line_id', operator, sline_ids)], context=context)
                if search_ids:
                    # Add line to result
                    downstream_line_ids.append(search_ids)
                    # Add reversal line to result
                    for dl in self.browse(cr, uid, search_ids, context=context):
                        reversal_ids = self.search(cr, uid, [('move_id', '=', dl.move_id.id), ('reversal', '=', True)], context=context)
                        downstream_line_ids.append(reversal_ids)
                    sline_ids = search_ids
                else:
                    sline_ids = None
            # Add search result to res
            res[str(ml.id)] = list(set(flatten(upstream_line_ids) + flatten(downstream_line_ids))) # downstream_line_ids needs to be simplify with flatten
        return res

    def get_first_corrected_line(self, cr, uid, ids, context=None):
        """
        For each move line, give the first line from which all corrections have been done.
        Example:
         - line 1 exists.
         - line 1 was corrected by line 3.
         - line 5 correct line 3.
         - line 8 correct line 5.
         - get_first_corrected_line of line 8 should give line 1.
        """
        # Some verifications
        if not context:
            context = {}
        if isinstance(ids, (int, long)):
            ids = [ids]
        # Prepare some values
        res = {}
        for ml in self.browse(cr, uid, ids, context=context):
            # Get upstream move lines
            line = ml
            corrected_line_id = ml.corrected_line_id and ml.corrected_line_id
            while corrected_line_id != False:
                line = line.corrected_line_id or False
                if not line:
                    corrected_line_id = False
                    continue
                corrected_line_id = line.corrected_line_id and line.corrected_line_id.id or False
            res[str(ml.id)] = False
            if line:
                res[str(ml.id)] = line.id
        return res

    def button_do_accounting_corrections(self, cr, uid, ids, context=None):
        """
        Launch accounting correction wizard to do reverse or correction on selected move line.
        """
        # Verification
        if not context:
            context={}
        if isinstance(ids, (int, long)):
            ids = [ids]
        # Retrieve some values
        wiz_obj = self.pool.get('wizard.journal.items.corrections')
        ml = self.browse(cr, uid, ids[0])
        # Create wizard
        wizard = wiz_obj.create(cr, uid, {'move_line_id': ids[0]}, context=context)
        # Change wizard state in order to change date requirement on wizard
        wiz_obj.write(cr, uid, [wizard], {'state': 'open'}, context=context)
        # Update context
        # UFTP-354: Delete "from_web_menu" to avoid conflict with UFTP-262
        if 'from_web_menu' in context:
            del(context['from_web_menu'])
        context.update({
            'active_id': ids[0],
            'active_ids': ids,
        })
        # Change context if account special type is "donation"
        if ml.account_id and ml.account_id.type_for_register and ml.account_id.type_for_register == 'donation':
            wiz_obj.write(cr, uid, [wizard], {'from_donation': True}, context=context)
        # Update context to inform wizard we come from a correction wizard
        context.update({'from_correction': True,})
        return {
            'name': _("Accounting Corrections Wizard (from Journal Items)"),
            'type': 'ir.actions.act_window',
            'res_model': 'wizard.journal.items.corrections',
            'target': 'new',
            'view_mode': 'form,tree',
            'view_type': 'form',
            'res_id': [wizard],
            'context': context,
        }

    def button_open_corrections(self, cr, uid, ids, context=None):
        """
        Open all corrections linked to the given one
        """
        # Verification
        if not context:
            context={}
        if isinstance(ids, (int, long)):
            ids = [ids]
        # Prepare some values
        domain_ids = []
        # Search ids to be open
        res_ids = self.get_corrections_history(cr, uid, ids, context=context)
        # For each ids, add elements to the domain
        for el in res_ids:
            domain_ids.append(res_ids[el])
        # If no result, just display selected ids
        if not domain_ids:
            domain_ids = ids
        # Create domain
        domain = [('id', 'in', flatten(domain_ids))]#, ('reversal', '=', False)]
        # Update context
        context.update({
            'active_id': ids[0],
            'active_ids': ids,
        })
        # Display the result
        return {
            'name': "History Move Line",
            'type': 'ir.actions.act_window',
            'res_model': 'account.move.line',
            'target': 'new',
            'view_type': 'form',
            'view_mode': 'tree',
            'context': context,
            'domain': domain,
        }
        return True

# Method abandonned because no "reverse" button on Correction Wizard
#    def reverse(self, cr, uid, ids, date=None, context=None):
#        """
#        Reverse given lines by creating a new Journal Entry (account_move) and write in the reversal line.
#        Reversal lines have some information:
#         - name begin with REV
#         - debit and credit are reversed
#         - amount_currency is the opposite
#         - date is those from given date or current date by default
#         - period is those that correspond to the given date
#         - line is written in the first 'correction' type journal found
#        NB : return the succeeded move lines
#        """
#        # Verifications
#        if not context:
#            context = {}
#        if isinstance(ids, (int, long)):
#            ids = [ids]
#        if not date:
#            date = strftime('%Y-%m-%d')
#        # Prepare some values
#        success_move_line_ids = []
#        move_obj = self.pool.get('account.move')
#        aal_obj = self.pool.get('account.analytic.line')
#        j_obj = self.pool.get('account.journal')
#        j_ids = j_obj.search(cr, uid, [('type', '=', 'correction'),
#                                       ('is_current_instance', '=', True)], context=context)
#        # Search correction journal
#        j_corr_ids = j_obj.search(cr, uid, [('type', '=', 'correction'),
#                                            ('is_current_instance', '=', True)], context=context)
#        j_corr_id = j_corr_ids and j_corr_ids[0] or False
#        # Search extra accounting journal
#        ej_ids = j_obj.search(cr, uid, [('type', '=', 'extra'),
#                                        ('is_current_instance', '=', True)])
#        j_extra_id = ej_ids and ej_ids[0] or False
#        # Search attached period
#        period_ids = self.pool.get('account.period').search(cr, uid, [('date_start', '<=', date), ('date_stop', '>=', date)], context=context,
#            limit=1, order='date_start, name')
#        # Browse move line
#        for ml in self.browse(cr, uid, ids, context=context):
#            # Abort process if this move line was corrected before
#            if ml.corrected:
#                continue
#            # Retrieve right journal. Extra-accounting journal for donation, else correction journal
#            journal_id = j_corr_id
#            if ml.account_id and ml.account_id.type_for_register == 'donation':
#                journal_id = j_extra_id
#                if not journal_id:
#                    raise osv.except_osv(_('Error'), _('No OD-Extra Accounting Journal found!'))
#            elif not journal_id:
#                raise osv.except_osv(_('Error'), _('No Correction Journal found!'))
#            # Create a new move
#            move_id = move_obj.create(cr, uid,{'journal_id': journal_id, 'period_id': period_ids[0], 'date': date}, context=context)
#            # Prepare default value for new line
#            vals = {
#                'move_id': move_id,
#                'date': date,
#                'document_date': date,
#                'journal_id': journal_id,
#                'period_id': period_ids[0],
#            }
#            # Copy the line
#            rev_line_id = self.copy(cr, uid, ml.id, vals, context=context)
#            # Do the reverse
#            name = self.join_without_redundancy(ml.name, 'REV')
#            amt = -1 * ml.amount_currency
#            vals.update({
#                'debit': ml.credit,
#                'credit': ml.debit,
#                'amount_currency': amt,
#                'journal_id': journal_id,
#                'name': name,
#                'reversal_line_id': ml.id,
#                'account_id': ml.account_id.id,
#                'source_date': ml.date,
#                'reversal': True,
#                'reference': ml.move_id and ml.move_id.name or '',
#                'ref': ml.move_id and ml.move_id.name or '',
#            })
#            self.write(cr, uid, [rev_line_id], vals, context=context)
#            # Inform old line that it have been corrected
#            self.write(cr, uid, [ml.id], {'corrected': True, 'have_an_historic': True,}, context=context)
#            # Search analytic lines from first move line
#            aal_ids = aal_obj.search(cr, uid, [('move_id', '=', ml.id)])
#            aal_obj.write(cr, uid, aal_ids, {'is_reallocated': True})
#            # Search analytic lines from reversed line and flag them as "is_reversal"
#            new_aal_ids = aal_obj.search(cr, uid, [('move_id', '=', rev_line_id)])
#            aal_obj.write(cr, uid, new_aal_ids, {'is_reversal': True,})
#            # Add this line to succeded lines
#            success_move_line_ids.append(ml.id)
#        return success_move_line_ids

    def make_reversal_link(self, cr, uid, old_id, new_id, context=None):
        """
        Make new_id the reverse for the old_id in analytic items
        """
        # Checks
        if context is None:
            context = {}
        # Prepare some values
        ana_obj = self.pool.get('account.analytic.line')
        old_ana_ids = ana_obj.search(cr, uid, [('move_id', '=', old_id)])
        new_ana_ids = ana_obj.search(cr, uid, [('move_id', '=', new_id)])
        if not old_ana_ids or not new_ana_ids:
            raise osv.except_osv(_('Warning'), _('No analytic journal items found for the given journal items.'))
        # Process: we search all linked Analytic Journal Items linked to the given one and write the link.
        # Criteria:
        # - cost center
        # - destination
        # - amount
        # - analytic account (account_id)
        for aal in ana_obj.browse(cr, uid, new_ana_ids, context=context):
            amount = -1 * aal.amount
            old_ids = ana_obj.search(cr, uid, [('id', 'in', old_ana_ids), ('cost_center_id', '=', aal.cost_center_id.id), ('destination_id', '=', aal.destination_id.id), ('amount', '=', amount), ('account_id', '=', aal.account_id.id)])
            if not old_ids:
                raise osv.except_osv(_('Error'), _('No corresponding analytic journal items with this one: %s') % (aal.name or ''))
            if len(old_ids) > 1:
                raise osv.except_osv(_('Error'), _('More than one corresponding line from this one: %s') % (aal.name or ''))
            ana_obj.write(cr, uid, aal.id, {'reversal_origin': old_ids[0]}, context=context)
        return True

    def reverse_move(self, cr, uid, ids, date=None, context=None):
        """
        Reverse the move from lines
        Return succeeded move lines (not complementary move lines)
        """
        # Verifications
        if not context:
            context = {}
        if isinstance(ids, (int, long)):
            ids = [ids]
        if not date:
            date = strftime('%Y-%m-%d')
        # Prepare some values
        success_move_line_ids = []
        move_obj = self.pool.get('account.move')
        j_obj = self.pool.get('account.journal')
        ana_j_obj = self.pool.get('account.analytic.journal')
        aal_obj = self.pool.get('account.analytic.line')
        # Search correction journal
        j_corr_ids = j_obj.search(cr, uid, [('type', '=', 'correction'),
                                            ('is_current_instance', '=', True)], context=context)
        j_corr_id = j_corr_ids and j_corr_ids[0] or False
        j_ana_corr_ids = ana_j_obj.search(cr, uid, [('type', '=', 'correction'), ('is_current_instance', '=', True)], context=context)
        j_ana_corr_id = j_ana_corr_ids and j_ana_corr_ids[0] or False
        # Search extra-accounting journal
        j_extra_ids = j_obj.search(cr, uid, [('type', '=', 'extra'),
                                             ('is_current_instance', '=', True)])
        j_extra_id = j_extra_ids and j_extra_ids[0] or False
        # Search attached period
        period_ids = self.pool.get('account.period').search(cr, uid, [('date_start', '<=', date), ('date_stop', '>=', date)], context=context,
            limit=1, order='date_start, name')
        # Sort ids
        move_lines = self.browse(cr, uid, ids, context=context)
        tmp_move_ids = [x.move_id.id for x in move_lines if x.move_id]
        # Delete double and sort it
        move_ids = sorted(list(set(tmp_move_ids)))
        # Browse moves
        success_move_ids = []
        for m in move_obj.browse(cr, uid, move_ids, context=context):
            # Verify this move could be reversed
            corrigible = True
            is_inkind = False
            for ml in m.line_id:
                if ml.corrected:
                    corrigible = False
                if ml.account_id and ml.account_id.type_for_register == 'donation':
                    is_inkind = True
            if not corrigible:
                continue

            # FIXME: verify that no lines come from a statement_id => should be corrected if necessary

            # Retrieve right journal. Extra-accounting journal for donation account, otherwise correction journal.
            journal_id = j_corr_id
            if is_inkind:
                journal_id = j_extra_id
            if not journal_id and is_inkind:
                raise osv.except_osv(_('Error'), _('No OD-Extra Accounting Journal found!'))
            elif not journal_id:
                raise osv.except_osv(_('Error'), _('No correction journal found!'))

            # Create a new move
            new_move_id = move_obj.create(cr, uid,{'journal_id': journal_id, 'period_id': period_ids[0], 'date': date, 'document_date': m.document_date}, context=context)
            # Search move line that have to be corrected.
            # NB: this is useful when you correct a move line twice and do a reverse on it. It should be reverse the complementary move line of the first move line
            # and reverse the last correction line.
            # This is just a little bit more complicated than reverse a move.
            to_reverse = []
            # 1/ add move line from this move that have not been reversed to the "to_reverse"
            # 2/ search first move line of each move lines
            # 3/ add complementary line of first move_line to the "to_reverse"
            valid = []
            # Search valid lines into current move
            for line in m.line_id:
                if not line.reversal:
                    valid.append(line)
            # Search first line for each valid lines
            for line in valid:
                first_line_id = self.get_first_corrected_line(cr, uid, line.id, context=context).get(str(line.id), False)
                # add line_id to line to be reversed
                to_reverse.append(line.id)
                if first_line_id:
                    # Get first line move
                    first_line = self.browse(cr, uid, [first_line_id], context=context)[0]
                    for ml in first_line.move_id.line_id:
                        # Add lines that come not from valid lines
                        if ml.id != first_line_id:
                            to_reverse.append(ml.id)
            # Browse all move lines and change information
            new_ml_ids = []
            tuple_old_new = []
            for ml in self.browse(cr, uid, to_reverse, context=context):
                amt = -1 * ml.amount_currency
                name = self.join_without_redundancy(ml.name, 'REV')
                vals = {}
                # omit analytic_distribution if exists on first move line
                context.update({'omit_analytic_distribution': False})
                new_distrib_id = False
                if ml.analytic_distribution_id:
                    context.update({'omit_analytic_distribution': True})
                    ana_obj = self.pool.get('analytic.distribution')
                    # create a new distribution
                    new_distrib_id = ana_obj.copy(cr, uid, ml.analytic_distribution_id.id, {}, context=context)
                    # update amount on new distribution
                    ana_obj.update_distribution_line_amount(cr, uid, new_distrib_id, (-1 * (ml.debit - ml.credit)), context=context)
                new_line_id = self.copy(cr, uid, ml.id, {'move_id': new_move_id, 'date': date, 'document_date': ml.document_date, 'period_id': period_ids[0]}, context=context)
                vals.update({
                    'name': name,
                    'debit': ml.credit,
                    'credit': ml.debit,
                    'amount_currency': amt,
                    'reversal_line_id': ml.id,
                    'source_date': ml.source_date or ml.date,
                    'reversal': True,
                    'reference': ml.move_id and ml.move_id.name or '',
                    'ref': ml.move_id and ml.move_id.name or '',
                })
                # Add distribution if new one
                if new_distrib_id:
                    vals.update({'analytic_distribution_id': new_distrib_id})
                self.write(cr, uid, [new_line_id], vals, context=context)
                # Flag this line as corrected
                self.write(cr, uid, [ml.id], {'corrected': True, 'have_an_historic': True,}, context=context)
                # Only add line ID that appear in IDS (success move lines)
                if ml.id in ids:
                    success_move_line_ids.append(ml.id)
                new_ml_ids.append(new_line_id)
                # If this line is an expense one, add it to the tuple old/new for making a reversal link between them
                if ml.account_id.user_type_code == 'expense':
                    tuple_old_new.append((ml.id, new_line_id))
            # Hard post the move
            move_obj.post(cr, uid, [new_move_id], context=context)
            # Update analytic lines data (reversal: True)
            ana_ids = aal_obj.search(cr, uid, [('move_id', 'in', new_ml_ids)])
            aal_obj.write(cr, uid, ana_ids, {'is_reversal': True, 'journal_id': j_ana_corr_id, 'last_corrected_id': False,})
            # Update old analytic lines as "is_reallocated" to True
            old_ana_ids = aal_obj.search(cr, uid, [('move_id', 'in', success_move_line_ids)])
            aal_obj.write(cr, uid, old_ana_ids, {'is_reallocated': True,})
            # Add reversal link between old move line and new ones
            for pair in tuple_old_new:
                self.make_reversal_link(cr, uid, pair[0], pair[1], context=context)
            # Save successful new move_id post
            success_move_ids.append(new_move_id)
        return success_move_line_ids, success_move_ids

    def update_account_on_st_line(self, cr, uid, ids, account_id=None, context=None):
        """
        Update the account from the statement line attached if different
        """
        # Some verifications
        if not context:
            context = {}
        if isinstance(ids, (int, long)):
            ids = [ids]
        if not account_id:
            raise osv.except_osv(_('Warning'), _('No account_id given. No update on account will be done.'))
        # Prepare some values
        absl_obj = self.pool.get('account.bank.statement.line')
        # Update lines
        for ml in self.browse(cr, uid, ids, context=context):
            # in order to update hard posted line (that's forbidden!), we use a tip: add from_correction in context
            context.update({'from_correction': True})
            # Search lines that are correction of this one (in order to add some fields)
            corrected_line_ids = self.search(cr, uid, [('corrected_line_id', '=', ml.id)], context=context)
            # Case where this move line have a link to some statement lines
            if ml.statement_id and ml.move_id.statement_line_ids:
                for st_line in ml.move_id.statement_line_ids:
                    # US-303: only update the statement line that links to this move line
                    if st_line.cash_return_move_line_id:
                        if st_line.cash_return_move_line_id.id == ml.id:
                            absl_obj.write(cr, uid, [st_line.id], {'account_id': account_id}, context=context)
                            # we informs new move line that it have correct a statement line
                            self.write(cr, uid, corrected_line_ids, {'corrected_st_line_id': st_line.id}, context=context)
                            break
                    elif not st_line.from_cash_return: #US-1044: only update the account on line if the regline is not cash return!
                        #US-303: If not the case, then we inform the new move line that it has corrected a statement line
                        absl_obj.write(cr, uid, [st_line.id], {'account_id': account_id}, context=context)
                        self.write(cr, uid, corrected_line_ids, {'corrected_st_line_id': st_line.id}, context=context)
            # if not, this move line should have a direct link to a register line
            elif ml.statement_id and ml.corrected_st_line_id:
                absl_obj.write(cr, uid, [ml.corrected_st_line_id.id], {'account_id': account_id}, context=context)
        return True

    def correct_account(self, cr, uid, ids, date=None, new_account_id=None, distrib_id=False, context=None):
        """
        Correct given account_move_line by only changing account
        """
        # Verification
        if not context:
            context = {}
        if isinstance(ids, (int, long)):
            ids = [ids]
        if not date:
            date = strftime('%Y-%m-%d')
        if not new_account_id:
            raise osv.except_osv(_('Error'), _('No new account_id given!'))

        # Prepare some values
        move_obj = self.pool.get('account.move')
        j_obj = self.pool.get('account.journal')
        al_obj = self.pool.get('account.analytic.line')
        success_move_line_ids = []

        # New account
        new_account = self.pool.get('account.account').browse(cr, uid,
            new_account_id, context=context)

        # Search correction journal
        j_corr_ids = j_obj.search(cr, uid, [('type', '=', 'correction'),
                                            ('is_current_instance', '=', True)], context=context)
        j_corr_id = j_corr_ids and j_corr_ids[0] or False

        # Search extra-accounting journal
        j_extra_ids = j_obj.search(cr, uid, [('type', '=', 'extra'),
                                             ('is_current_instance', '=', True)])
        j_extra_id = j_extra_ids and j_extra_ids[0] or False

        # Search attached period
        period_obj = self.pool.get('account.period')
        period_ids = period_obj.search(cr, uid, [('date_start', '<=', date), ('date_stop', '>=', date)],
                                                                context=context, limit=1, order='date_start, name')
        period_number = period_ids and period_obj.browse(cr, uid, period_ids, context)[0].number or False

        # Browse all given move line for correct them
        for ml in self.browse(cr, uid, ids, context=context):
            # Abort process if this move line was corrected before
            if ml.corrected:
                continue

            # UTP-1187 check corrected line has an AD if need one
            # + BKLG-19/3: search only for fp ones as 'free' are not synced to
            # HQ and initial_al_ids[0] is used to set reversal_origin
            initial_al_ids = al_obj.search(cr, uid,
                [('move_id', '=', ml.id), ('account_id.category', '=', 'FUNDING')],
                context=context)
            # Note: this search result will be used near end of this function
            # (see # Change analytic lines that come from)
            if not distrib_id and \
                not initial_al_ids and new_account and \
                new_account.is_analytic_addicted:
                # we check only if no distrib_id arg passed to function
                msg = _("The line '%s' with new account '%s - %s' need an" \
                    " analytic distribution (you may have changed account from" \
                    " one with no AD required to a new one with AD required).")
                raise osv.except_osv(_('Error'), msg % (ml.move_id.name,
                    new_account.code, new_account.name, ))

            # If this line was already been corrected, check the first analytic line ID (but not the first first analytic line)
            first_analytic_line_id = False
            first_ana_ids = self.pool.get('account.analytic.line').search(cr, uid, [('move_id', '=', ml.id)])
            if first_ana_ids:
                first_ana = self.pool.get('account.analytic.line').browse(cr, uid, first_ana_ids)[0]
                if first_ana.last_corrected_id:
                    first_analytic_line_id = first_ana.last_corrected_id.id
            # Retrieve right journal
            journal_id = j_corr_id

            # Abort process if the move line is a donation account (type for specific treatment) and that new account is not a donation account
            if ml.account_id.type_for_register == 'donation':
                journal_id = j_extra_id
                if not journal_id:
                    raise osv.except_osv(_('Error'), _('No OD-Extra Accounting Journal found!'))
                if new_account.type_for_register != 'donation':
                    raise osv.except_osv(_('Error'), _('You come from a donation account. And new one is not a Donation account. You should give a Donation account!'))
            if not journal_id:
                raise osv.except_osv(_('Error'), _('No correction journal found!'))

            # Abort process if the move line have some analytic line that have one line with a FP used in a soft/hard closed contract
            aal_ids = self.pool.get('account.analytic.line').search(cr, uid, [('move_id', '=', ml.id)])
            for aal in self.pool.get('account.analytic.line').browse(cr, uid, aal_ids):
                check_accounts = self.pool.get('account.analytic.account').is_blocked_by_a_contract(cr, uid, [aal.account_id.id])
                if check_accounts and aal.account_id.id in check_accounts:
                    raise osv.except_osv(_('Warning'), _('You cannot change the G/L account since it is used in a closed financing contract.'))
            # (US-815) use the right period for December HQ Entries
            period_id_dec_hq_entry = False
            if period_number == 12 and context.get('period_id_for_dec_hq_entries', False):
                period_id_dec_hq_entry = context['period_id_for_dec_hq_entries']
            # Create a new move
            move_id = move_obj.create(cr, uid,{'journal_id': journal_id, 'period_id': period_id_dec_hq_entry or period_ids[0], 'date': date, 'document_date': ml.document_date}, context=context)
            # Prepare default value for new line
            vals = {
                'move_id': move_id,
                'date': date,
                'document_date': ml.document_date,
                'journal_id': journal_id,
                'period_id': period_id_dec_hq_entry or period_ids[0],
            }
            # Copy the line
            context.update({'omit_analytic_distribution': False})
            rev_line_id = self.copy(cr, uid, ml.id, vals, context=context)
            correction_line_id = self.copy(cr, uid, ml.id, vals, context=context)
            # Do the reverse
            name = self.join_without_redundancy(ml.name, 'REV')
            amt = -1 * ml.amount_currency
            vals.update({
                'debit': ml.credit,
                'credit': ml.debit,
                'amount_currency': amt,
                'journal_id': journal_id,
                'name': name,
                'reversal_line_id': ml.id,
                'account_id': ml.account_id.id,
                'source_date': ml.source_date or ml.date,
                'reversal': True,
                'document_date': ml.document_date,
                'reference': ml.move_id and ml.move_id.name or '',
                'ref': ml.move_id and ml.move_id.name or '',
            })
            self.write(cr, uid, [rev_line_id], vals, context=context, check=False, update_check=False)
            # Do the correction line
            name = self.join_without_redundancy(ml.name, 'COR')
            cor_vals = {
                'name': name,
                'journal_id': journal_id,
                'corrected_line_id': ml.id,
                'account_id': new_account_id,
                'source_date': ml.source_date or ml.date,
                'have_an_historic': True,
                'document_date': ml.document_date,
                'reference': ml.move_id and ml.move_id.name or '',
                'ref': ml.move_id and ml.move_id.name or '',
            }
            if distrib_id:
                cor_vals['analytic_distribution_id'] = distrib_id
            elif ml.analytic_distribution_id:
                cor_vals['analytic_distribution_id'] = self.pool.get('analytic.distribution').copy(cr, uid, ml.analytic_distribution_id.id, {}, context=context)
            self.write(cr, uid, [correction_line_id], cor_vals, context=context, check=False, update_check=False)
            # UF-2231: Remove the update to the statement line
            # Update register line if exists

            # UFTP-119: Reverted a code that has been commented out in UF-2231 without explanation, and which caused the problem of updating back the Reg line
            if ml.statement_id:
                self.update_account_on_st_line(cr, uid, [ml.id], new_account_id, context=context)
            # Inform old line that it have been corrected
            self.write(cr, uid, [ml.id], {'corrected': True, 'have_an_historic': True,}, context=context, check=False, update_check=False)
            # Post the move
            move_obj.post(cr, uid, [move_id], context=context)
            # Change analytic lines that come from:
            #- initial move line: is_reallocated is True
            #- reversal move line: is_reversal is True + initial analytic line
            #- correction line: change is_reallocated and is_reversal to False
            #- old reversal line: reset is_reversal to True (lost previously in validate())
            if initial_al_ids:  # as initial AD
                search_datas = [(ml.id, {'is_reallocated': True}),
                                (rev_line_id, {'is_reversal': True, 'reversal_origin': initial_al_ids[0]}),
                                (correction_line_id, {'is_reallocated': False, 'is_reversal': False, 'last_corrected_id': initial_al_ids[0]})]
                # If line is already a correction, take the previous reversal move line id
                # (UF_1234: otherwise, the reversal is not set correctly)
                if ml.corrected_line_id:
                    old_reverse_ids = self.search(cr, uid, [('reversal_line_id', '=', ml.corrected_line_id.id)])
                    if len(old_reverse_ids) > 0:
                        search_datas += [(old_reverse_ids[0], {'is_reversal': True, 'reversal_origin': first_analytic_line_id})]
                for search_data in search_datas:
                    # keep initial analytic line as corrected line if it the 2nd or more correction on this line
                    if ml.corrected_line_id and search_data[0] == ml.id and first_analytic_line_id:
                        search_data[1].update({'last_corrected_id': first_analytic_line_id, 'have_an_historic': True,})
                    search_ids = al_obj.search(cr, uid, [('move_id', '=', search_data[0]), ('reversal_origin', '=', False), ('last_corrected_id', '=', False)])
                    if search_ids:
                        al_obj.write(cr, uid, search_ids, search_data[1])
            # Add this line to succeded lines
            success_move_line_ids.append(ml.id)
            # Mark it as "corrected_upstream" if needed
            self.corrected_upstream_marker(cr, uid, [ml.id], context=context)
        return success_move_line_ids

    def correct_partner_id(self, cr, uid, ids, date=None, partner_id=None, context=None):
        """
        Correct given entries in order to change its partner_id:
         - do a reverse line for partner line
         - do a correction line for new partner
        """
        # Verifications
        if not context:
            context = {}
        if isinstance(ids, (int, long)):
            ids = [ids]
        if not date:
            date = strftime('%Y-%m-%d')
        if not partner_id:
            raise osv.except_osv(_('Error'), _('No new partner_id given!'))
        # Prepare some values
        j_obj = self.pool.get('account.journal')
        move_obj = self.pool.get('account.move')
        success_move_line_ids = []
        # Search correction journal
        j_corr_ids = j_obj.search(cr, uid, [('type', '=', 'correction'),
                                            ('is_current_instance', '=', True)], context=context)
        j_corr_id = j_corr_ids and j_corr_ids[0] or False
        # Search extra-accounting journal
        j_extra_ids = j_obj.search(cr, uid, [('type', '=', 'extra'),
                                             ('is_current_instance', '=', True)])
        j_extra_id = j_extra_ids and j_extra_ids[0] or False
        # Search attached period
        period_ids = self.pool.get('account.period').search(cr, uid, [('date_start', '<=', date), ('date_stop', '>=', date)],
            context=context, limit=1, order='date_start, name')
        # Correct all given move lines
        for ml in self.browse(cr, uid, ids, context=context):
            # Search the move line (in the move) to be changed (account that have a payable OR a receivable account)
            move_line = None
            for line in ml.move_id.line_id:
                if line.account_id.type == 'payable' or line.account_id.type == 'receivable':
                    move_line = line
                    break
            # If no move line found or move line has been corrected, continue process
            if not move_line or move_line.corrected:
                continue
            # Retrieve journal. If account is inkind, so use extra-accounting journal, otherwise use correction journal
            journal_id = j_corr_id
            if ml.account_id.type_for_register == 'donation':
                journal_id = j_extra_id
                if not journal_id:
                    raise osv.except_osv(_('Error'), _('No OD-Extra Accounting Journal found!'))
            if not journal_id:
                raise osv.except_osv(_('Error'), _('No correction journal found!'))
            # Create a new move
            move_id = move_obj.create(cr, uid,{'journal_id': journal_id, 'period_id': period_ids[0], 'date': date}, context=context)
            # Search the new attached account_id
            partner_type = 'res.partner,%s' % partner_id
            account_vals = self.pool.get('account.bank.statement.line').onchange_partner_type(cr, uid, [], partner_type, move_line.credit,
                move_line.debit, context=context)
            if not 'value' in account_vals and not account_vals.get('value').get('account_id', False):
                raise osv.except_osv(_('Error'), _('No account found for this partner!'))
            account_id = account_vals.get('value').get('account_id')
            # Prepare default value for new line
            vals = {
                'move_id': move_id,
                'date': date,
                'journal_id': journal_id,
                'period_id': period_ids[0],
                'source_date': ml.date,
            }
            # Copy the line
            rev_line_id = self.copy(cr, uid, move_line.id, vals, context=context)
            correction_line_id = self.copy(cr, uid, move_line.id, vals, context=context)
            # Do the reverse
            name = self.join_without_redundancy(move_line.name, 'REV')
            amt = -1 * move_line.amount_currency
            vals.update({
                'debit': move_line.credit,
                'credit': move_line.debit,
                'amount_currency': amt,
                'journal_id': journal_id,
                'name': name,
                'reversal_line_id': move_line.id,
                'account_id': move_line.account_id.id,
            })
            self.write(cr, uid, [rev_line_id], vals, context=context)
            # Do the correction line
            name = self.join_without_redundancy(move_line.name, 'COR')
            self.write(cr, uid, [correction_line_id], {'name': name, 'journal_id': journal_id, 'corrected_line_id': move_line.id,
                'account_id': account_id, 'partner_id': partner_id, 'have_an_historic': True,}, context=context)
            # Inform old line that it have been corrected
            self.write(cr, uid, [move_line.id], {'corrected': True, 'have_an_historic': True,}, context=context)
            # Post the move
            move_obj.post(cr, uid, [move_id], context=context)
            # Reconcile the line with its reversal
            self.reconcile_partial(cr, uid, [line.id, rev_line_id], context=context)
            # Add this line to succeded lines
            success_move_line_ids.append(move_line.id)
        return success_move_line_ids

    def corrected_upstream_marker(self, cr, uid, ids, context=None):
        """
        Check if we are in a COORDO / HQ instance. If yes, set move line(s) as corrected upstream.
        """
        # Some check
        if context is None:
            context = {}
        if isinstance(ids, (int, long)):
            ids = [ids]
        # Prepare some values
        company = self.pool.get('res.users').browse(cr, uid, uid, context=context).company_id
        # Check if we come from COORDO/HQ instance
        if company and company.instance_id and company.instance_id.level in ['section', 'coordo']:
            # UF-1746: Set also all other move lines as corrected upstream to disallow projet user to correct any move line of this move.
            move_ids = [x and x.get('move_id', False) and x.get('move_id')[0] for x in self.read(cr, uid, ids, ['move_id'], context=context)]
            ml_ids = self.search(cr, uid, [('move_id', 'in', move_ids), ('corrected_upstream', '!=', True)])
            self.write(cr, uid, ml_ids, {'corrected_upstream': True}, check=False, update_check=False, context=context)
        return True

account_move_line()

class account_move(osv.osv):
    _name = 'account.move'
    _inherit = 'account.move'

    def reverse(self, cr, uid, ids, date=False, context=None):
        """
        Reverse move
        """
        if not context:
            context = {}
        if isinstance(ids, (int, long)):
            ids = [ids]
        reversed_move = []
        for m in self.browse(cr, uid, ids):
            res_ml_ids = self.pool.get('account.move.line').reverse_move(cr, uid, [x.id for x in m.line_id], date=date, context=context)
            if res_ml_ids:
                reversed_move.append(m.id)
        return reversed_move

account_move()
# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
