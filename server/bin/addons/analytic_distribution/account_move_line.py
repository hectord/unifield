# -*- coding: utf-8 -*-
##############################################################################
#
#    OpenERP, Open Source Management Solution
#    Copyright (C) 2011 MSF, TeMPO consulting
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

from osv import fields, osv
from tools.translate import _

class account_move_line(osv.osv):
    _inherit = 'account.move.line'

    def _display_analytic_button(self, cr, uid, ids, name, args, context=None):
        """
        Return True for all element that correspond to some criteria:
         - The journal entry state is draft (unposted)
         - The account is analytic-a-holic
        """
        res = {}
        for ml in self.browse(cr, uid, ids, context=context):
            res[ml.id] = True
            # False if account not anlaytic-a-holic
            if not ml.account_id.is_analytic_addicted:
                res[ml.id] = False
        return res

    def _get_distribution_state(self, cr, uid, ids, name, args, context=None):
        """
        Get state of distribution:
         - if compatible with the move line, then "valid"
         - if no distribution, take a tour of move distribution, if compatible, then "valid"
         - if no distribution on move line and move, then "none"
         - all other case are "invalid"
        """
        # Some verifications
        if context is None:
            context = {}
        if isinstance(ids, (int, long)):
            ids = [ids]
        # Prepare some values
        res = {}
        distrib_obj = self.pool.get('analytic.distribution')
        sql = """
            SELECT aml.id, aml.analytic_distribution_id AS distrib_id, m.analytic_distribution_id AS move_distrib_id, aml.account_id
            FROM account_move_line AS aml, account_move AS m
            WHERE aml.move_id = m.id
            AND aml.id IN %s
            ORDER BY aml.id;"""
        cr.execute(sql, (tuple(ids),))
        for line in cr.fetchall():
            res[line[0]] = distrib_obj._get_distribution_state(cr, uid, line[1], line[2], line[3])
        return res

    def _have_analytic_distribution_from_header(self, cr, uid, ids, name, arg, context=None):
        """
        If move have an analytic distribution, return False, else return True
        """
        # Some verifications
        if context is None:
            context = {}
        if isinstance(ids, (int, long)):
            ids = [ids]
        res = {}
        for ml in self.browse(cr, uid, ids, context=context):
            res[ml.id] = True
            if ml.analytic_distribution_id:
                res[ml.id] = False
        return res

    def _get_distribution_state_recap(self, cr, uid, ids, name, arg, context=None):
        """
        Get a recap from analytic distribution state and if it come from header or not.
        """
        if isinstance(ids, (int, long)):
            ids = [ids]
        res = {}
        get_sel = self.pool.get('ir.model.fields').get_browse_selection
        for ml in self.browse(cr, uid, ids):
            res[ml.id] = ''
            from_header = ''
            if ml.have_analytic_distribution_from_header:
                from_header = _(' (from header)')
            d_state = get_sel(cr, uid, ml, 'analytic_distribution_state', context)
            res[ml.id] = "%s%s" % (d_state, from_header)
            # Do not show any recap for non analytic-a-holic accounts
            if ml.account_id and not ml.account_id.is_analytic_addicted:
                res[ml.id] = ''
        return res

    _columns = {
        'analytic_distribution_id': fields.many2one('analytic.distribution', 'Analytic Distribution'),
        'display_analytic_button': fields.function(_display_analytic_button, method=True, string='Display analytic button?', type='boolean', readonly=True,
            help="This informs system that we can display or not an analytic button", store=False),
        'analytic_distribution_state': fields.function(_get_distribution_state, method=True, type='selection',
            selection=[('none', 'None'), ('valid', 'Valid'), ('invalid', 'Invalid')],
            string="Distribution state", help="Informs from distribution state among 'none', 'valid', 'invalid."),
         'have_analytic_distribution_from_header': fields.function(_have_analytic_distribution_from_header, method=True, type='boolean',
            string='Header Distrib.?'),
        'analytic_distribution_state_recap': fields.function(_get_distribution_state_recap, method=True, type='char', size=30,
            string="Distribution",
            help="Informs you about analaytic distribution state among 'none', 'valid', 'invalid', from header or not, or no analytic distribution"),
  }

    def create_analytic_lines(self, cr, uid, ids, context=None):
        """
        Create analytic lines on analytic-a-holic accounts that have an analytical distribution.
        """
        if context is None:
            context = {}
        acc_ana_line_obj = self.pool.get('account.analytic.line')
        company_currency = self.pool.get('res.users').browse(cr, uid, uid, context=context).company_id.currency_id.id
        ft_obj = self.pool.get('finance.tools')

        obj_fields = [
            'debit_currency',
            'credit_currency',
            'analytic_distribution_id',
            'move_id',
            'state',
            'journal_id',
            'source_date',
            'date',
            'document_date',
            'name',
            'ref',
            'currency_id',
            'corrected_line_id',
            'is_write_off',
            'account_id',
        ]

        for obj_line in self.read(cr, uid, ids, obj_fields, context=context):
            # Prepare some values
            amount = obj_line.get('debit_currency', 0.0) - obj_line.get('credit_currency', 0.0)
            journal = self.pool.get('account.journal').read(cr, uid, obj_line.get('journal_id', [False])[0], ['analytic_journal_id', 'name'], context=context)
            move = self.pool.get('account.move').read(cr, uid, obj_line.get('move_id', [False])[0], ['analytic_distribution_id', 'status', 'line_id'], context=context)
            account = self.pool.get('account.account').read(cr, uid, obj_line.get('account_id', [False])[0], ['is_analytic_addicted'], context=context)
            aal_obj = self.pool.get('account.analytic.line')
            line_distrib_id = (obj_line.get('analytic_distribution_id', False) and obj_line.get('analytic_distribution_id')[0]) or (move.get('analytic_distribution_id', False) and move.get('analytic_distribution_id')[0]) or False
            # When you create a journal entry manually, we should not have analytic lines if ONE line is invalid!
            other_lines_are_ok = True
            result = self.search(cr, uid, [('move_id', '=', move.get('id', False)), ('move_id.status', '=', 'manu'), ('state', '!=', 'valid')], count=1)
            if result and result > 0 and move.get('status', False) == 'manu':
                other_lines_are_ok = False
            # Check that line have analytic-a-holic account and have a distribution
            if line_distrib_id and account.get('is_analytic_addicted', False) and other_lines_are_ok:
                ana_state = self.pool.get('analytic.distribution')._get_distribution_state(cr, uid, line_distrib_id, {}, account.get('id'))
                # For manual journal entries, do not raise an error. But delete all analytic distribution linked to other_lines because if one line is invalid, all lines should not create analytic lines
                if ana_state == 'invalid' and move.get('status', '') == 'manu':
                    ana_line_ids = acc_ana_line_obj.search(cr, uid, [('move_id', 'in', move.get('line_id', []))])
                    acc_ana_line_obj.unlink(cr, uid, ana_line_ids)
                    continue
                elif ana_state == 'invalid':
                    raise osv.except_osv(_('Warning'), _('Invalid analytic distribution.'))
                if not journal.get('analytic_journal_id', False):
                    raise osv.except_osv(_('Warning'),_("No Analytic Journal! You have to define an analytic journal on the '%s' journal!") % (journal.get('name', ''), ))
                distrib_obj = self.pool.get('analytic.distribution').browse(cr, uid, line_distrib_id, context=context)
                # create lines
                for distrib_lines in [distrib_obj.funding_pool_lines, distrib_obj.free_1_lines, distrib_obj.free_2_lines]:
                    aji_greater_amount = {
                        'amount': 0.,
                        'is': False,
                        'id': False,
                        'iso': 0.,
                    }

                    # US-1463/2: are all lines eguals by amount ?
                    if distrib_lines:
                        amounts = list(set([ dl.percentage*amount/100 for dl in distrib_lines ]))
                        if len(amounts) == 1:
                            aji_greater_amount['iso'] = round(amounts[0], 2)

                    dl_total_amount_rounded = 0.
                    for distrib_line in distrib_lines:
                        context.update({'date': obj_line.get('source_date', False) or obj_line.get('date', False)})
                        anal_amount = distrib_line.percentage*amount/100
                        anal_amount_rounded = round(anal_amount, 2)
                        dl_total_amount_rounded += anal_amount_rounded
                        if anal_amount_rounded > aji_greater_amount['amount']:
                            # US-119: breakdown by fp line or free 1, free2
                            # register the aji that will have the greatest amount
                            aji_greater_amount['amount'] = anal_amount_rounded
                            aji_greater_amount['is'] = True
                        else:
                            aji_greater_amount['is'] = False
                        line_vals = {
                                     'name': obj_line.get('name', ''),
                                     'date': obj_line.get('date', False),
                                     'ref': obj_line.get('ref', False),
                                     'journal_id': journal.get('analytic_journal_id', [False])[0],
                                     'amount': -1 * self.pool.get('res.currency').compute(cr, uid, obj_line.get('currency_id', [False])[0], company_currency,
                                        anal_amount, round=False, context=context),
                                     'amount_currency': -1 * anal_amount_rounded,
                                     'account_id': distrib_line.analytic_id.id,
                                     'general_account_id': account.get('id'),
                                     'move_id': obj_line.get('id'),
                                     'distribution_id': distrib_obj.id,
                                     'user_id': uid,
                                     'currency_id': obj_line.get('currency_id', [False])[0],
                                     'distrib_line_id': '%s,%s'%(distrib_line._name, distrib_line.id),
                                     'document_date': obj_line.get('document_date', False),
                                     'source_date': obj_line.get('source_date', False) or obj_line.get('date', False),  # UFTP-361 source_date from date if not any (posting date)
                        }
                        # Update values if we come from a funding pool
                        if distrib_line._name == 'funding.pool.distribution.line':
                            destination_id = distrib_line.destination_id and distrib_line.destination_id.id or False
                            line_vals.update({'cost_center_id': distrib_line.cost_center_id and distrib_line.cost_center_id.id or False,
                                'destination_id': destination_id,})
                        # Update value if we come from a write-off
                        if obj_line.get('is_write_off', False):
                            line_vals.update({'from_write_off': True,})
                        # Add source_date value for account_move_line that are a correction of another account_move_line
                        if obj_line.get('corrected_line_id', False) and obj_line.get('source_date', False):
                            line_vals.update({'source_date': obj_line.get('source_date', False)})
                        aji_id = aal_obj.create(cr, uid, line_vals, context=context)
                        if aji_greater_amount['is']:
                            aji_greater_amount['id'] = aji_id

                    if amount > 0. and dl_total_amount_rounded > 0.:
                        if abs(dl_total_amount_rounded - amount) > 0.001 and \
                            aji_greater_amount['id']:
                            # US-119 deduce the rounding gap and apply it
                            # to the AJI of greater amount
                            # http://jira.unifield.org/browse/US-119?focusedCommentId=38217&page=com.atlassian.jira.plugin.system.issuetabpanels:comment-tabpanel#comment-38217
                            # and US-1463
                            fixed_amount = aji_greater_amount['amount'] - (round(dl_total_amount_rounded, 2) - amount)
                            func_amount = None

                            if aji_greater_amount['iso'] > 0:
                                # US-1463/2
                                # AD lines with same ratio/amount
                                # and 50/50 breakdown
                                if len(distrib_lines) == 2:
                                    diff = round(dl_total_amount_rounded - amount, 2)
                                    #print 'difff', diff, 'rounded', dl_total_amount_rounded, 'amount', amount
                                    if (abs(diff)) < 0.001:
                                        diff = 0.  # non significative gap
                                    fixed_amount = round(aji_greater_amount['iso'] - diff, 2)
                                    #print 'fixed_amount', fixed_amount, 'aji_greater_amount', aji_greater_amount['iso']
                            else:
                                # US-1463/1
                                func_amount = -1 * self.pool.get('res.currency').compute(cr, uid, obj_line.get('currency_id', [False])[0], company_currency, fixed_amount, round=False, context=context)
                                func_amount = round(func_amount, 2)
                            fixed_amount_vals = {
                                'amount_currency': -1 * fixed_amount,
                            }
                            if func_amount is not None:
                                fixed_amount_vals['amount'] = func_amount
                            aal_obj.write(cr, uid, [aji_greater_amount['id']],
                                fixed_amount_vals, context=context)

        return True

    def unlink(self, cr, uid, ids, context=None, check=True):
        """
        Delete analytic lines before unlink move lines.
        Update Manual Journal Entries.
        """
        if context is None:
            context = {}
        if context.get('sync_update_execution'):
            # US-836: no need to cascade actions in sync context
            # AJI deletion and JE validation are sync'ed
            return super(account_move_line, self).unlink(cr, uid, ids, context=context, check=False)
        move_ids = []
        if ids:
            # Search manual moves to revalidate
            sql = """
                SELECT m.id
                FROM account_move_line AS ml, account_move AS m
                WHERE ml.move_id = m.id
                AND m.status = 'manu'
                AND ml.id IN %s
                GROUP BY m.id
                ORDER BY m.id;"""
            cr.execute(sql, (tuple(ids),))
            move_ids += [x and x[0] for x in cr.fetchall()]
        # Search analytic lines
        ana_ids = self.pool.get('account.analytic.line').search(cr, uid, [('move_id', 'in', ids)], context=context)
        self.pool.get('account.analytic.line').unlink(cr, uid, ana_ids, context=context)
        res = super(account_move_line, self).unlink(cr, uid, ids, context=context, check=check) #ITWG-84: Pass also the check flag to the super!
        # Revalidate move
        self.pool.get('account.move').validate(cr, uid, move_ids, context=context)
        return res

    def button_analytic_distribution(self, cr, uid, ids, context=None):
        """
        Launch analytic distribution wizard on an move line
        """
        # Some verifications
        if context is None:
            context = {}
        if isinstance(ids, (int, long)):
            ids = [ids]
        if not ids:
            raise osv.except_osv(_('Error'), _('No journal item given. Please save your line before.'))
        # Prepare some values
        ml = self.browse(cr, uid, ids[0], context=context)
        amount = ml.debit_currency - ml.credit_currency
        # Search elements for currency
        company_currency = self.pool.get('res.users').browse(cr, uid, uid, context=context).company_id.currency_id.id
        currency = ml.currency_id and ml.currency_id.id or company_currency
        # Get analytic distribution id from this line
        distrib_id = ml and ml.analytic_distribution_id and ml.analytic_distribution_id.id or False
        # Prepare values for wizard
        vals = {
            'total_amount': amount,
            'move_line_id': ml.id,
            'currency_id': currency or False,
            'state': 'dispatch',
            'account_id': ml.account_id and ml.account_id.id or False,
            'posting_date': ml.date,
            'document_date': ml.document_date,
        }
        if distrib_id:
            vals.update({'distribution_id': distrib_id,})
        # Create the wizard
        wiz_obj = self.pool.get('analytic.distribution.wizard')
        wiz_id = wiz_obj.create(cr, uid, vals, context=context)
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

    def _check_employee_analytic_distribution(self, cr, uid, ids, context=None):
        """
        Check that analytic distribution could be retrieved from given employee.
        If not employee, return True.
        """
        if context is None:
            context = {}
        if isinstance(ids, (int, long)):
            ids = [ids]
        for l in self.browse(cr, uid, ids):
            # Next line if this one comes from a non-manual move (journal entry)
            if l.move_id.status != 'manu':
                continue
            # Do not continue if no employee or no cost center (could not be invented)
            if not l.employee_id or not l.employee_id.cost_center_id:
                continue
            if l.account_id and l.account_id.is_analytic_addicted:
                vals = {'cost_center_id': l.employee_id.cost_center_id.id}
                if l.employee_id.destination_id:
                    if l.employee_id.destination_id.id in [x and x.id for x in l.account_id.destination_ids]:
                        vals.update({'destination_id': l.employee_id.destination_id.id})
                    else:
                        vals.update({'destination_id': l.account_id.default_destination_id.id})
                if l.employee_id.funding_pool_id:
                    vals.update({'analytic_id': l.employee_id.funding_pool_id.id})
                    if vals.get('cost_center_id') not in l.employee_id.funding_pool_id.cost_center_ids:
                        # Fetch default funding pool: MSF Private Fund
                        try:
                            msf_fp_id = self.pool.get('ir.model.data').get_object_reference(cr, uid, 'analytic_distribution', 'analytic_account_msf_private_funds')[1]
                        except ValueError:
                            msf_fp_id = 0
                        vals.update({'analytic_id': msf_fp_id})
                # Create analytic distribution
                if 'cost_center_id' in vals and 'analytic_id' in vals and 'destination_id' in vals:
                    distrib_id = self.pool.get('analytic.distribution').create(cr, uid, {'name': 'check_employee_analytic_distribution'})
                    vals.update({'distribution_id': distrib_id, 'percentage': 100.0, 'currency_id': l.currency_id.id})
                    # Create funding pool lines
                    self.pool.get('funding.pool.distribution.line').create(cr, uid, vals)
                    # Then cost center lines
                    vals.update({'analytic_id': vals.get('cost_center_id'),})
                    self.pool.get('cost.center.distribution.line').create(cr, uid, vals)
                    # finally free1 and free2
                    if l.employee_id.free1_id:
                        self.pool.get('free.1.distribution.line').create(cr, uid, {'distribution_id': distrib_id, 'percentage': 100.0, 'currency_id': l.currency_id.id, 'analytic_id': l.employee_id.free1_id.id})
                    if l.employee_id.free2_id:
                        self.pool.get('free.2.distribution.line').create(cr, uid, {'distribution_id': distrib_id, 'percentage': 100.0, 'currency_id': l.currency_id.id, 'analytic_id': l.employee_id.free2_id.id})
                    if context.get('from_write', False):
                        return {'analytic_distribution_id': distrib_id,}
                    # Write analytic distribution on the move line
                    self.pool.get('account.move.line').write(cr, uid, [l.id], {'analytic_distribution_id': distrib_id}, check=False, update_check=False)
                else:
                    return False
        return True

    def create(self, cr, uid, vals, context=None, check=True):
        """
        Check analytic distribution for employee (if given)
        """
        res = super(account_move_line, self).create(cr, uid, vals, context, check)
        self._check_employee_analytic_distribution(cr, uid, res, context)
        return res

    def write(self, cr, uid, ids, vals, context=None, check=True, update_check=True):
        """
        Check line if we come from web (from_web_menu)
        """
        if context is None:
            context = {}
        if isinstance(ids, (int, long)):
            ids = [ids]
        if context.get('from_web_menu', False):
            res = []
            for ml in self.browse(cr, uid, ids):
                distrib_state = self.pool.get('analytic.distribution')._get_distribution_state(cr, uid, ml.analytic_distribution_id.id, ml.move_id and ml.move_id.analytic_distribution_id and ml.move_id.analytic_distribution_id.id or False, vals.get('account_id') or ml.account_id.id)
                if distrib_state in ['invalid', 'none']:
                    vals.update({'state': 'draft'})
                # Add account_id because of an error with account_activable module for checking date
                if not 'account_id' in vals and 'date' in vals:
                    vals.update({'account_id': ml.account_id and ml.account_id.id or False})
                check = self._check_employee_analytic_distribution(cr, uid, [ml.id], context={'from_write': True})
                if check and isinstance(check, dict):
                    vals.update(check)
                tmp_res = super(account_move_line, self).write(cr, uid, [ml.id], vals, context, False, False)
                res.append(tmp_res)
            return res
        res = super(account_move_line, self).write(cr, uid, ids, vals, context, check, update_check)
        return res

    def copy(self, cr, uid, aml_id, default=None, context=None):
        """
        Copy analytic_distribution
        """
        # Some verifications
        if context is None:
            context = {}
        if default is None:
            default = {}
        # Default method
        res = super(account_move_line, self).copy(cr, uid, aml_id, default, context)
        # Update analytic distribution
        if res:
            c = self.browse(cr, uid, res, context=context)
        if res and c.analytic_distribution_id:
            new_distrib_id = self.pool.get('analytic.distribution').copy(cr, uid, c.analytic_distribution_id.id, {}, context=context)
            if new_distrib_id:
                self.write(cr, uid, [res], {'analytic_distribution_id': new_distrib_id}, context=context)
        return res

    def get_analytic_move_lines(self, cr, uid, ids, context=None):
        """
        Return FP analytic lines attached to move lines
        """
        # Some verifications
        if context is None:
            context = {}
        if 'active_ids' in context:
            ids = context.get('active_ids')
        if isinstance(ids, (int, long)):
            ids = [ids]
        # Search valid ids
        domain = [('move_id', 'in', ids), ('account_id.category', '=', 'FUNDING')]
        context.update({'display_fp': True})
        return {
            'name': _('Analytic lines (FP) from Journal Items'),
            'type': 'ir.actions.act_window',
            'res_model': 'account.analytic.line',
            'view_type': 'form',
            'view_mode': 'tree,form',
            'context': context,
            'domain': domain,
            'target': 'current',
        }

    def get_analytic_move_free1_lines(self, cr, uid, ids, context=None):
        """
        Return FREE1 analytic lines attached to move lines
        """
        # Some verifications
        if context is None:
            context = {}
        if 'active_ids' in context:
            ids = context.get('active_ids')
        if isinstance(ids, (int, long)):
            ids = [ids]
        # Search valid ids
        domain = [('move_id', 'in', ids), ('account_id.category', '=', 'FREE1')]
        context.update({'display_fp': False, 'categ': 'FREE1'})
        return {
            'name': _('Analytic Lines (Free 1) from Journal Items'),
            'type': 'ir.actions.act_window',
            'res_model': 'account.analytic.line',
            'view_type': 'form',
            'view_mode': 'tree,form',
            'context': context,
            'domain': domain,
            'target': 'current',
        }

    def get_analytic_move_free2_lines(self, cr, uid, ids, context=None):
        """
        Return FREE2 analytic lines attached to move lines
        """
        # Some verifications
        if context is None:
            context = {}
        if 'active_ids' in context:
            ids = context.get('active_ids')
        if isinstance(ids, (int, long)):
            ids = [ids]
        # Search valid ids
        domain = [('move_id', 'in', ids), ('account_id.category', '=', 'FREE2')]
        context.update({'display_fp': False, 'categ': 'FREE2'})
        return {
            'name': _('Analytic Lines (Free 2) from Journal Items'),
            'type': 'ir.actions.act_window',
            'res_model': 'account.analytic.line',
            'view_type': 'form',
            'view_mode': 'tree,form',
            'context': context,
            'domain': domain,
            'target': 'current',
        }

account_move_line()
# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
