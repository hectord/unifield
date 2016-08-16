#!/usr/bin/env python
# -*- coding: utf-8 -*-
##############################################################################
#
#    OpenERP, Open Source Management Solution
#    Copyright (C) 2013 TeMPO Consulting, MSF. All Rights Reserved
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
from lxml import etree

class hq_entries_split_lines(osv.osv_memory):
    _name = 'hq.entries.split.lines'
    _description = 'HQ entries split lines'

    def _get_distribution_state(self, cr, uid, ids, name, args, context=None):
        """
        Get state of distribution and some info if needed.
        By default the distribution is "none". But valid is all is OK and invalid if ONE point is not OK.
        """
        # Checks
        if context is None:
            context = {}
        # Prepare some values
        res = {}
        # Process
        for line in self.browse(cr, uid, ids, context=context):
            res[line.id] = {'state_info': False, 'state': 'none'}
            state, info = self.pool.get('analytic.distribution').analytic_state_from_info(cr, uid, line.account_id.id, line.destination_id.id, line.cost_center_id.id, line.analytic_id.id, context=context)
            res[line.id].update({'state_info': info, 'state': state,})
        return res

    _columns = {
        'wizard_id': fields.many2one('hq.entries.split', "Wizard", required=True),
        'name': fields.char("Description", size=255, required=True),
        'ref': fields.char("Reference", size=255),
        'account_id': fields.many2one("account.account", "Account", domain=[('type', '!=', 'view')], required=True),
        'account_hq_correctible': fields.boolean("Is HQ correctible?"),
        'amount': fields.float('Amount', required=True),
        'destination_id': fields.many2one('account.analytic.account', "Destination", domain=[('category', '=', 'DEST'), ('type', '!=', 'view')], required=True),
        'cost_center_id': fields.many2one('account.analytic.account', "Cost Center", domain=[('category', '=', 'OC'), ('type', '!=', 'view')], required=True),
        'analytic_id': fields.many2one('account.analytic.account', "Funding Pool", domain=[('category', '=', 'FUNDING'), ('type', '!=', 'view')], required=True),
        'state': fields.function(_get_distribution_state, method=True, type='selection', selection=[('none', 'None'), ('valid', 'Valid'), ('invalid', 'Invalid')], string="State", help="Informs from distribution state among 'none', 'valid', 'invalid.", multi="hq_split_line_distrib_state"),
        'state_info': fields.function(_get_distribution_state, method=True, type='char', string="Info", help="Informs about distribution state.", multi='hq_split_line_distrib_state'),
    }

    def _get_original_line(self, cr, uid, context=None, wizard_id=False):

        """
        Fetch original line from context. If not, return False.
        """
        if not wizard_id:
            wizard_id = context and context.get('parent_id', False) or False
        if not wizard_id:
            return False
        wiz = self.pool.get('hq.entries.split').browse(cr, uid, wizard_id)
        return wiz and wiz.original_id or False

    def _get_field(self, cr, uid, field_name, field_type=False, context=None):
        """
        Get original line specific info given by "field_name" parameter
        """
        res = False
        if not context or not field_name:
            return res
        original_line = self._get_original_line(cr, uid, context=context)
        res = original_line and getattr(original_line, field_name, False) or False
        if res and field_type and field_type == 'm2o':
            res = getattr(res, 'id', False)
        return res

    def _get_amount(self, cr, uid, context=None):
        """
        Get original line amount substracted of all other lines amount
        """
        res = 0.0
        if not context:
            return res
        original_line = self._get_original_line(cr, uid, context=context)
        if original_line:
            res = original_line.amount
            line_ids = self.search(cr, uid, [('wizard_id', '=', context.get('parent_id', False))])
            for line in self.browse(cr, uid, line_ids) or []:
                res -= line.amount
        # Do not allow negative amounts if the original amount is positive and vice versa
        if (original_line.amount >= 0 and res < 0.0) or (original_line.amount < 0 and res > 0.0):
            res = 0.0
        return res

    def _get_hq_correctible(self, cr, uid, context=None):
        res = False
        if not context:
            return res
        original_line = self._get_original_line(cr, uid, context=context)
        account = original_line and getattr(original_line, 'account_id', False) or False
        if account:
            res = getattr(account, 'is_not_hq_correctible', False)
        return res

    _defaults = {
        'name': lambda obj, cr, uid, c: obj._get_field(cr, uid, 'name', context=c),
        'ref': lambda obj, cr, uid, c: obj._get_field(cr, uid, 'ref', context=c),
        'account_id': lambda obj, cr, uid, c: obj._get_field(cr, uid, 'account_id', field_type='m2o', context=c),
        'amount': _get_amount,
        'destination_id': lambda obj, cr, uid, c: obj._get_field(cr, uid, 'destination_id', field_type='m2o', context=c),
        'cost_center_id': lambda obj, cr, uid, c: obj._get_field(cr, uid, 'cost_center_id', field_type='m2o', context=c),
        'analytic_id': lambda obj, cr, uid, c: obj._get_field(cr, uid, 'analytic_id', field_type='m2o', context=c),
        'account_hq_correctible': lambda obj, cr, uid, c: obj._get_hq_correctible(cr, uid, context=c)
    }

    def create(self, cr, uid, vals, context=None):
        """
        Check that:
        - no negative value is given for amount
        - amount and all other line's amount is not superior to original line
        - amount is not null
        """
        if not context:
            context = {}
        # UFTP-36 name readonly so not passed here into vals, get it
        wiz = self.pool.get('hq.entries.split').browse(cr, uid, context.get('active_id'))
        if wiz and wiz.original_id and wiz.original_id.name:
            vals['name'] = wiz.original_id.name
        if vals.get('amount', 0.0):
            # Check that amount is not negative if the original amount is positive and vice versa
            if wiz.original_amount >= 0 and vals.get('amount') < 0.0:
                raise osv.except_osv(_('Error'), _('Negative value is not allowed!'))
            elif wiz.original_amount < 0 and vals.get('amount') > 0.0:
                raise osv.except_osv(_('Error'), _('Positive value is not allowed!'))
        # In case we come from an account that is "Not HQ correctible", the account_id field is readonly and so not retrieved from the wizard. So we take the original line account as account_id value in vals dictionnary.
        if not 'account_id' in vals or not vals.get('account_id', False):
            if not vals.get('wizard_id'):
                raise osv.except_osv(_('Error'), _('No link from this line to a specific wizard. Do you come from web client?'))
            wiz = self.pool.get('hq.entries.split').browse(cr, uid, vals.get('wizard_id', False))
            account = wiz and wiz.original_id and wiz.original_id.account_id or False
            if not account:
                raise osv.except_osv(_('Error'), _('Account is required!'))
            vals['account_id'] = account.id
        # US-672/2
        hq_entry = self._get_original_line(cr, uid, context=context,
            wizard_id=vals.get('wizard_id', False))
        if hq_entry and hq_entry.partner_txt:
            self.pool.get('account.account').is_allowed_for_thirdparty(cr, uid,
                [vals['account_id']], partner_txt=hq_entry.partner_txt,
                raise_it=True, context=context)
        res = super(hq_entries_split_lines, self).create(cr, uid, vals, context=context)
        # Check that amount is not superior to what expected
        if res:
            line = self.browse(cr, uid, res)
            expected_max_amount = line.wizard_id.original_amount
            for line in line.wizard_id.line_ids:
                # Check line amount
                if line.amount == 0.0:
                    # WARNING: On osv.memory, no rollback. That's why we should unlink the previous line before raising this error
                    self.unlink(cr, uid, [res], context=context)
                    raise osv.except_osv(_('Error'), _('Null amount is not allowed!'))
                expected_max_amount -= line.amount
            expected_max_amount += line.amount
            # Case where amount is superior to expected
            if abs(line.amount) > abs(expected_max_amount):
                # Allow those where difference is inferior to 10^-2
                if (abs(line.amount) - abs(expected_max_amount)) > 10 ** -2:
                    # WARNING: On osv.memory, no rollback. That's why we should unlink the previous line before raising this error
                    self.unlink(cr, uid, [res], context=context)
                    raise osv.except_osv(_('Error'), _('Expected max amount: %.2f') % (expected_max_amount or 0.0,))
        return res

    def write(self, cr, uid, ids, vals, context=None):
        """
        Check that amount is not Null.
        """
        # Checks
        if context is None:
            context = {}

        original_amount = self.pool.get('hq.entries.split').browse(cr, uid, context.get('active_id')).original_amount
        if vals.get('amount', 0.0):
            # Check that amount is not negative if the original amount is positive and vice versa
            if original_amount >= 0 and vals.get('amount') < 0.0:
                raise osv.except_osv(_('Error'), _('Negative value is not allowed!'))
            elif original_amount < 0 and vals.get('amount') > 0.0:
                raise osv.except_osv(_('Error'), _('Positive value is not allowed!'))
        # Prepare some values

        # US-672/2
        for line in self.browse(cr, uid, ids, context=context):
            hq_entry = line.wizard_id and line.wizard_id.original_id or False
            if hq_entry and hq_entry.partner_txt:
                self.pool.get('account.account').is_allowed_for_thirdparty(cr, uid,
                    [vals['account_id']], partner_txt=hq_entry.partner_txt,
                    raise_it=True, context=context)

        res = super(hq_entries_split_lines, self).write(cr, uid, ids, vals, context=context)
        for line in self.browse(cr, uid, ids, context=context):
            # Check line amount
            if line.amount == 0.0:
                raise osv.except_osv(_('Error'), _('Null amount is not allowed!'))
        return res

hq_entries_split_lines()

class hq_entries_split(osv.osv_memory):
    _name = 'hq.entries.split'
    _description = 'HQ entry split'

    _columns = {
        'original_id': fields.many2one('hq.entries', "Original HQ Entry", readonly=True, required=True),
        'original_amount': fields.float('Original Amount', readonly=True, required=True),
        'line_ids': fields.one2many('hq.entries.split.lines', 'wizard_id', "Split lines"),
        'running': fields.boolean('Is running'),
    }

    _defaults = {
        'running': False,
    }

    def create(self, cr, uid, vals, context=None):
        # BKLG-77: check transation at wiz creation (done by hq.entries model)
        line_ids = context and context.get('active_ids', []) or []
        if isinstance(line_ids, (int, long)):
            line_ids = [line_ids]
        self.pool.get('hq.entries').check_hq_entry_transaction(cr, uid,
            line_ids, self._name, context=context)
        return super(hq_entries_split, self).create(cr, uid, vals,
            context=context)

    # UFTP-200: Add the correct funding pool domain to the split line based on the account_id and cost_center
    def fields_view_get(self, cr, uid, view_id=None, view_type='form', context=None, toolbar=False, submenu=False):
        """
        Change funding pool domain in order to include MSF Private fund
        """
        if context is None:
            context = {}
        view = super(hq_entries_split, self).fields_view_get(cr, uid, view_id, view_type, context, toolbar, submenu)
        fields = view['fields']
        if view_type=='form' and fields:
            if fields.get('line_ids') and fields.get('line_ids')['views']:
                # get the default PF and include into the domain for analytic_id
                try:
                    fp_id = self.pool.get('ir.model.data').get_object_reference(cr, uid, 'analytic_distribution', 'analytic_account_msf_private_funds')[1]
                except ValueError:
                    fp_id = 0

                viewtemp = fields.get('line_ids')['views']
                arch = etree.fromstring(viewtemp['tree']['arch']) # the analytic_id is found in the line_ids, one level down
                fields = arch.xpath('field[@name="analytic_id"]')
                if fields:
                    fields[0].set('domain', "[('type', '!=', 'view'), ('state', '=', 'open'), ('category', '=', 'FUNDING'), '|', '&', ('cost_center_ids', '=', cost_center_id), ('tuple_destination', '=', (account_id, destination_id)), ('id', '=', %s)]" % fp_id)

                # Change Destination field
                dest_fields = arch.xpath('field[@name="destination_id"]')
                for field in dest_fields:
                    field.set('domain', "[('type', '!=', 'view'), ('state', '=', 'open'), ('category', '=', 'DEST'), ('destination_ids', '=', account_id)]")
                    viewtemp['tree']['arch'] = etree.tostring(arch)
        return view

    def button_validate(self, cr, uid, ids, context=None):
        """
        Validate wizard lines and create new split HQ lines.
        Do not allow line that have a null amount!
        """
        # Some checks
        if not context:
            context = {}
        # Prepare some values
        hq_obj = self.pool.get('hq.entries')
        for wiz in self.browse(cr, uid, ids, context=context):
            if wiz.running:
                return {}
            # Check that wizard have 2 lines at least
            if len(wiz.line_ids) < 2:
                raise osv.except_osv(_('Warning'), _('Make 2 lines at least.'))
            # Check total amount for this wizard
            total = 0.00
            for line in wiz.line_ids:
                total += line.amount
            if abs(abs(wiz.original_amount) - abs(total)) > 0.000000000001:
                # US-1361 tolerate minimal python rounding gap
                raise osv.except_osv(_('Error'), _('Wrong total: %f, instead of: %.2f') % (total or 0.00, wiz.original_amount or 0.00,))

            self.write(cr, uid, [wiz.id], {'running': True})
            # If all is OK, do process of lines
            # Mark original line as it is: an original one :-)
            hq_obj.write(cr, uid, wiz.original_id.id, {'is_original': True,})
            # Create new lines
            for line in wiz.line_ids:
                # Check line amount
                if line.amount == 0.0:
                    raise osv.except_osv(_('Error'), _('Null amount is not allowed!'))
                # Prepare line values
                line_vals = {
                    'original_id': wiz.original_id.id,
                    'is_split': True,
                    'account_id': line.account_id.id,
                    'destination_id': line.destination_id.id,
                    'cost_center_id': line.cost_center_id.id,
                    'analytic_id': line.analytic_id.id,
                    'date': wiz.original_id.date,
                    'partner_txt': wiz.original_id.partner_txt or '',
                    'period_id': wiz.original_id.period_id and wiz.original_id.period_id.id or False,
                    'name': line.name,
                    'ref': line.ref,
                    'document_date': wiz.original_id.document_date,
                    'currency_id': wiz.original_id.currency_id and wiz.original_id.currency_id.id or False,
                    'amount': line.amount,
                    'account_id_first_value': line.account_id.id,
                    'cost_center_id_first_value': line.cost_center_id.id,
                    'analytic_id_first_value': line.analytic_id.id,
                    'destination_id_first_value': line.destination_id.id,
                }
                hq_line_id = hq_obj.create(cr, uid, line_vals, context=context)
                hq_line = hq_obj.browse(cr, uid, hq_line_id, context=context)
                if hq_line.analytic_state != 'valid':
                    self.write(cr, uid, [wiz.id], {'running': False})
                    raise osv.except_osv(_('Warning'), _('Analytic distribution is invalid for the line "%s" with %.2f amount.') % (line.name, line.amount))
        return {'type' : 'ir.actions.act_window_close',}

hq_entries_split()
# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
