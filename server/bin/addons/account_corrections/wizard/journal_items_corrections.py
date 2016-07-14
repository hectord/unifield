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
from lxml import etree

class journal_items_corrections_lines(osv.osv_memory):
    _name = 'wizard.journal.items.corrections.lines'
    _description = 'Journal items corrections lines'

    def _get_distribution_state(self, cr, uid, ids, name, args, context=None):
        """
        Get state of distribution:
         - if compatible with the line, then "valid"
         - if no distribution on line, then "none"
         - all other case are "invalid"
        """
        # Some verifications
        if not context:
            context = {}
        if isinstance(ids, (int, long)):
            ids = [ids]
        # Prepare some values
        res = {}
        # Browse all given lines
        for line in self.browse(cr, uid, ids, context=context):
            res[line.id] = 'none'
            if line.analytic_distribution_id:
                res[line.id] = self.pool.get('analytic.distribution')._get_distribution_state(cr, uid, line.analytic_distribution_id.id, False, line.account_id.id)
        return res

    def _get_is_analytic_target(self, cr, uid, ids, name, args,  context=None):
        res = {}
        if not ids:
            return res
        if isinstance(ids, (int, long)):
            ids = [ids]
        for line_br in self.browse(cr, uid, ids, context=context):
            res[line_br.id] = line_br.account_id and line_br.account_id.is_analytic_addicted or False
        return res

    def _get_is_account_correctible(self, cr, uid, ids, name, args,  context=None):
        res = {}
        if not ids:
            return res
        if isinstance(ids, (int, long)):
            ids = [ids]
        for line_br in self.browse(cr, uid, ids, context=context):
            res[line_br.id] = True
            if line_br.move_line_id \
                and line_br.move_line_id.last_cor_was_only_analytic:
                res[line_br.id] = False
            elif line_br.account_id and line_br.account_id.is_not_hq_correctible:
                res[line_br.id] = False
        return res

    _columns = {
        'move_line_id': fields.many2one('account.move.line', string="Account move line", readonly=True, required=True),
        'wizard_id': fields.many2one('wizard.journal.items.corrections', string="wizard"),
        'account_id': fields.many2one('account.account', string="Account", required=True),
        'move_id': fields.many2one('account.move', string="Entry sequence", readonly=True),
        'ref': fields.char(string="Reference", size=254, readonly=True),
        'journal_id': fields.many2one('account.journal', string="Journal Code", readonly=True),
        'period_id': fields.many2one('account.period', string="Period", readonly=True),
        'date': fields.date('Posting date', readonly=True),
        'partner_id': fields.many2one('res.partner', 'Partner'),
        'transfer_journal_id': fields.many2one("account.journal", "Journal"),
        'employee_id': fields.many2one("hr.employee", "Employee"),
        'debit_currency': fields.float('Book. Debit', readonly=True),
        'credit_currency': fields.float('Book. Credit', readonly=True),
        'currency_id': fields.many2one('res.currency', string="Book. Curr.", readonly=True),
        'analytic_distribution_id': fields.many2one('analytic.distribution', string="Analytic Distribution", readonly=True),
        'analytic_distribution_state': fields.function(_get_distribution_state, method=True, type='selection',
            selection=[('none', 'None'), ('valid', 'Valid'), ('invalid', 'Invalid')],
            string="Distribution state", help="Informs from distribution state among 'none', 'valid', 'invalid."),
        'is_analytic_target': fields.function(_get_is_analytic_target, type='boolean', string='Is analytic target', method=True, invisible=True),
        'is_account_correctible': fields.function(_get_is_account_correctible,
            type='boolean', string='Is account correctible',
            method=True, invisible=True),
    }

    _defaults = {
        'from_donation': lambda *a: False,
        'is_analytic_target': lambda *a: False,
        'is_account_correctible': lambda *a: True,
    }

    def fields_view_get(self, cr, uid, view_id=None, view_type='form', context=None, toolbar=False, submenu=False):
        """
        Change account_id domain if account is donation
        """
        if not context:
            context = {}
        view = super(journal_items_corrections_lines, self).fields_view_get(cr, uid, view_id, view_type, context, toolbar, submenu)
        if context and context.get('from_donation_account', False):
            tree = etree.fromstring(view['arch'])
            fields = tree.xpath('//field[@name="account_id"]')
            for field in fields:
                field.set('domain', "[('type', '!=', 'view'), ('type_for_register', '=', 'donation'), ('user_type.code', '=', 'expense'), ('user_type.report_type', '=', 'none')]")
            view['arch'] = etree.tostring(tree)
        return view

    def button_analytic_distribution(self, cr, uid, ids, context=None):
        """
        Open an analytic distribution wizard
        """
        # Some verifications
        if not context:
            context = {}
        if isinstance(ids, (int, long)):
            ids = [ids]
        # Add context in order to know we come from a correction wizard
        this_line = self.browse(cr, uid, ids[0], context=context)
        wiz = this_line.wizard_id
        context.update({'from': 'wizard.journal.items.corrections', 'wiz_id': wiz.id or False})
        # Get distribution
        distrib_id = False
        if wiz and wiz.move_line_id and wiz.move_line_id.analytic_distribution_id:
            distrib_id = wiz.move_line_id.analytic_distribution_id.id or False
        if not distrib_id:
            distrib_id = self.pool.get('analytic.distribution').create(cr, uid, {})
            self.pool.get('account.move.line').write(cr, uid, wiz.move_line_id.id, {'analytic_distribution_id': distrib_id})
        # Prepare values
        company_currency = self.pool.get('res.users').browse(cr, uid, uid, context=context).company_id.currency_id.id
        currency = wiz.move_line_id.currency_id and wiz.move_line_id.currency_id.id or company_currency
        amount = wiz.move_line_id.amount_currency and wiz.move_line_id.amount_currency or 0.0
        vals = {
            'total_amount': amount,
            'move_line_id': wiz.move_line_id and wiz.move_line_id.id,
            'currency_id': currency or False,
            'old_account_id': wiz.move_line_id and wiz.move_line_id.account_id and wiz.move_line_id.account_id.id or False,
            'distribution_id': distrib_id,
            'state': 'dispatch', # Be very careful, if this state is not applied when creating wizard => no lines displayed
            'date': wiz.date or strftime('%Y-%m-%d'),
            'account_id': this_line.account_id and this_line.account_id.id or False,
            'document_date': wiz.move_line_id.document_date,
            'posting_date': wiz.date or wiz.move_line_id.date,
        }
        # Create the wizard
        wiz_obj = self.pool.get('analytic.distribution.wizard')
        wiz_id = wiz_obj.create(cr, uid, vals, context=context)
        # Change wizard state to 'correction' in order to display mandatory fields
        wiz_obj.write(cr, uid, [wiz_id], {'state': 'correction'}, context=context)
        # Update some context values
        context.update({
            'active_id': ids[0],
            'active_ids': ids,
        })
        # Open it!
        return {
                'name': _('Analytic distribution'),
                'type': 'ir.actions.act_window',
                'res_model': 'analytic.distribution.wizard',
                'view_type': 'form',
                'view_mode': 'form',
                'target': 'new',
                'res_id': [wiz_id],
                'context': context,
        }

journal_items_corrections_lines()

class journal_items_corrections(osv.osv_memory):
    _name = 'wizard.journal.items.corrections'
    _description = 'Journal items corrections wizard'

    def _get_from_register(self, cr, uid, ids, field_name, arg, context):
        """
        Return true if the line comes from a journal entry that have links to a register line
        """
        res = {}
        for wiz in self.browse(cr, uid, ids, context):
            res[wiz.id] = False
            if wiz.move_line_id.move_id and wiz.move_line_id.move_id.line_id:
                for ml_line in wiz.move_line_id.move_id.line_id:
                    if ml_line.statement_id:
                        res[wiz.id] = True
                        break
        return res

    _columns = {
        'date': fields.date(string="Correction date", states={'open':[('required', True)]}),
        'move_line_id': fields.many2one('account.move.line', string="Move Line", required=True, readonly=True),
        'to_be_corrected_ids': fields.one2many('wizard.journal.items.corrections.lines', 'wizard_id', string='', help='Line to be corrected'),
        'state': fields.selection([('draft', 'Draft'), ('open', 'Open')], string="state"),
        'from_donation': fields.boolean('From Donation account?'),
        'from_register': fields.function(_get_from_register, type='boolean', string='From register?', method=True, store=False),
    }

    _defaults = {
        'state': lambda *a: 'draft',
    }

    def onchange_date(self, cr, uid, ids, date, context=None):
        """
        Write date on this wizard.
        NB: this is essentially for analytic distribution correction wizard
        """
        # Some verifications
        if not context:
            context = {}
        if isinstance(ids, (int, long)):
            ids = [ids]
        if not date:
            return False
        return self.write(cr, uid, ids, {'date': date}, context=context)

    def create(self, cr, uid, vals, context=None):
        """
        Fill in all elements in our wizard with given move_line_id field
        """
        # Verifications
        if not context:
            context = {}
        # Normal mechanism
        res = super(journal_items_corrections, self).create(cr, uid, vals, context=context)
        # Process given move line to complete wizard
        if 'move_line_id' in vals:
            move_line_id = vals.get('move_line_id')
            move_line = self.pool.get('account.move.line').browse(cr, uid, [move_line_id])[0]
            corrected_line_vals = {
                'wizard_id': res,
                'move_line_id': move_line.id,
                'account_id': move_line.account_id.id,
                'move_id': move_line.move_id.id,
                'ref': move_line.ref,
                'journal_id': move_line.journal_id.id,
                'date': move_line.date,
                'debit_currency': move_line.debit_currency,
                'credit_currency': move_line.credit_currency,
                'period_id': move_line.period_id.id,
                'currency_id': move_line.currency_id.id,
                'partner_id': move_line.partner_id and move_line.partner_id.id or None,
                'employee_id': move_line.employee_id and move_line.employee_id.id or None,
                'transfer_journal_id': move_line.transfer_journal_id and move_line.transfer_journal_id.id or None,
#                'partner_type_mandatory': move_line.partner_type_mandatory or None,
                'analytic_distribution_id': move_line.analytic_distribution_id and move_line.analytic_distribution_id.id or None,
            }
            self.pool.get('wizard.journal.items.corrections.lines').create(cr, uid, corrected_line_vals, context=context)
        return res

    def compare_lines(self, cr, uid, old_line_id=None, new_line_id=None, context=None):
        """
        Compare an account move line to a wizard journal items corrections lines regarding 3 fields:
         - account_id (1)
         - partner_type (partner_id, employee_id or transfer_journal_id) (2)
         - analytic_distribution_id (4)
        Then return the sum.
        """
        # Verifications
        if not context:
            context = {}
        if not old_line_id or not new_line_id:
            raise osv.except_osv(_('Error'), _('An ID is missing!'))
        # Prepare some values
        res = 0
        # Lines
        old_line = self.pool.get('account.move.line').browse(cr, uid, [old_line_id], context=context)[0]
        new_line = self.pool.get('wizard.journal.items.corrections.lines').browse(cr, uid, [new_line_id], context=context)[0]
        # Fields
        old_account = old_line.account_id and old_line.account_id.id or False
        new_account = new_line.account_id and new_line.account_id.id or False
        old_partner = old_line.partner_id and old_line.partner_id.id or False
        new_partner = new_line.partner_id and new_line.partner_id.id or False
        old_distrib = old_line.analytic_distribution_id and old_line.analytic_distribution_id.id or False
        new_distrib = new_line.analytic_distribution_id and new_line.analytic_distribution_id.id or False
        if cmp(old_account, new_account):
            res += 1
        if cmp(old_partner, new_partner): # FIXME !!!!! or cmp(old_line.employee_id, new_line.employee_id) or
            # cmp(old_line.register_id, new_line.register_id):
            res += 2
        if cmp(old_distrib, new_distrib):
            # UFTP-1187
            if old_line.account_id.is_analytic_addicted and \
                new_account.account_id.is_analytic_addicted:
                # tolerate this diff (no +4)
                # if we correct an account with no AD required to a new account
                # with AD required or from AD required to no AD
                res += 4
        return res

    # UF-2056: Delete reverse button
#    def action_reverse(self, cr, uid, ids, context=None):
#        """
#        Do a reverse from the lines attached to this wizard
#        NB: The reverse is done on the first correction journal found (type = 'correction')
#        """
#        # Verifications
#        if not context:
#            context = {}
#        if isinstance(ids, (int, long)):
#            ids = [ids]
#        # Verify that date is superior to line's date
#        for wiz in self.browse(cr, uid, ids, context=context):
#            if wiz.move_line_id and wiz.move_line_id.date:
#                if not wiz.date >= wiz.move_line_id.date:
#                    raise osv.except_osv(_('Warning'), _('Please insert a correction date from the entry date onwards.'))
#        # Retrieve values
#        wizard = self.browse(cr, uid, ids[0], context=context)
#        aml_obj = self.pool.get('account.move.line')
#        # Do reverse
#        res, move_ids = aml_obj.reverse_move(cr, uid, [wizard.move_line_id.id], wizard.date, context=context)
#        return {'type': 'ir.actions.act_window_close', 'success_move_line_ids': res}

    def action_confirm(self, cr, uid, ids, context=None, distrib_id=False):
        """
        Do a correction from the given line
        """
        # Verification
        if not context:
            context = {}
        if isinstance(ids, (int, long)):
            ids = [ids]
        # Verify that date is superior to line's date
        for wiz in self.browse(cr, uid, ids, context=context):
            if wiz.move_line_id and wiz.move_line_id.date:
                if not wiz.date >= wiz.move_line_id.date:
                    raise osv.except_osv(_('Warning'), _('Please insert a correction date from the entry date onwards.'))
        # Retrieve values
        wizard = self.browse(cr, uid, ids[0], context=context)

        # UFTP-388: Check if the given period is valid: period open, or not close, if not just block the correction
        correction_period_ids = self.pool.get('account.period').get_period_from_date(cr, uid, wizard.date)
        if not correction_period_ids:
                raise osv.except_osv(_('Error'), _('No period found for the given date: %s') % (wizard.date,))
        for cp in self.pool.get('account.period').browse(cr, uid, correction_period_ids):
            if cp.state != 'draft':
                raise osv.except_osv(_('Error'), _('Period (%s) is not open.') % (cp.name,))

        aml_obj = self.pool.get('account.move.line')
        # Fetch old line
        old_line = wizard.move_line_id
        # Verify what have changed between old line and new one
        new_lines = wizard.to_be_corrected_ids
        # compare lines
        comparison = self.compare_lines(cr, uid, old_line.id, new_lines[0].id, context=context)
        # Result
        res = [] # no result yet
        # Correct account
        if comparison == 1:
            res = aml_obj.correct_account(cr, uid, [old_line.id], wizard.date, new_lines[0].account_id.id, distrib_id, context=context)
            if not res:
                raise osv.except_osv(_('Error'), _('No account changed!'))
        # Correct third parties
        elif comparison == 2:
            if not old_line.statement_id:
                res = aml_obj.correct_partner_id(cr, uid, [old_line.id], wizard.date, new_lines[0].partner_id.id, context=context)
                if not res:
                    raise osv.except_osv(_('Error'),
                        _('No partner changed! Verify that the Journal Entries attached to this line was not modify previously.'))
        elif comparison == 4:
            raise osv.except_osv('Warning', 'Do analytic distribution reallocation here!')
        elif comparison in [3, 5, 7]:
            raise osv.except_osv(_('Error'), _("You're just allowed to change ONE field amongst Account, Third Party or Analytical Distribution"))
        else:
            raise osv.except_osv(_('Warning'), _('No modifications seen!'))
        return {'type': 'ir.actions.act_window_close', 'success_move_line_ids': res}

journal_items_corrections()
# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
