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
from lxml import etree
import netsvc

class hq_entries(osv.osv):
    _name = 'hq.entries'
    _description = 'HQ Entries'

    def _get_analytic_state(self, cr, uid, ids, name, args, context=None):
        """
        Get state of distribution:
         - if compatible with the line, then "valid"
         - all other case are "invalid"
        """
        if isinstance(ids, (int, long)):
            ids = [ids]
        # Prepare some values
        res = {}
        logger = netsvc.Logger()
        # Search MSF Private Fund element, because it's valid with all accounts
        try:
            fp_id = self.pool.get('ir.model.data').get_object_reference(cr, uid, 'analytic_distribution', 
            'analytic_account_msf_private_funds')[1]
        except ValueError:
            fp_id = 0
        # Browse all given lines to check analytic distribution validity
        ## TO CHECK:
        # A/ if no CC
        # B/ if FP = MSF Private FUND
        # C/ (account/DEST) in FP except B
        # D/ CC in FP except when B
        # E/ DEST in list of available DEST in ACCOUNT
        # F/ Check posting date with cost center and destination if exists
        # G/ Check document date with funding pool
        ## CASES where FP is filled in (or not) and/or DEST is filled in (or not).
        ## CC is mandatory, so always available:
        # 1/ no FP, no DEST => Distro = valid
        # 2/ FP, no DEST => Check D except B
        # 3/ no FP, DEST => Check E
        # 4/ FP, DEST => Check C, D except B, E
        ## 
        for line in self.browse(cr, uid, ids, context=context):
            res[line.id] = 'valid' # by default
            #### SOME CASE WHERE DISTRO IS OK
            # if account is not expense, so it's valid
            if line.account_id and line.account_id.user_type_code and line.account_id.user_type_code != 'expense':
                continue
            # Date checks
            # F Check
            if line.cost_center_id:
                cc = self.pool.get('account.analytic.account').browse(cr, uid, line.cost_center_id.id, context={'date': line.date})
                if cc and cc.filter_active is False:
                    res[line.id] = 'invalid'
                    logger.notifyChannel('account_hq_entries', netsvc.LOG_WARNING, _('%s: inactive CC (%s)') % (line.id or '', cc.code or ''))
                    continue
            if line.destination_id:
                dest = self.pool.get('account.analytic.account').browse(cr, uid, line.destination_id.id, context={'date': line.date})
                if dest and dest.filter_active is False:
                    res[line.id] = 'invalid'
                    logger.notifyChannel('account_hq_entries', netsvc.LOG_WARNING, _('%s: inactive DEST (%s)') % (line.id or '', dest.code or ''))
                    continue
            # G Check
            if line.analytic_id:
                fp = self.pool.get('account.analytic.account').browse(cr, uid, line.analytic_id.id, context={'date': line.document_date})
                if fp and fp.filter_active is False:
                    res[line.id] = 'invalid'
                    logger.notifyChannel('account_hq_entries', netsvc.LOG_WARNING, _('%s: inactive FP (%s)') % (line.id or '', fp.code or ''))
                    continue
            # if just a cost center, it's also valid! (CASE 1/)
            if not line.analytic_id and not line.destination_id:
                continue
            # if FP is MSF Private Fund and no destination_id, then all is OK.
            if line.analytic_id and line.analytic_id.id == fp_id and not line.destination_id:
                continue
            #### END OF CASES
            if not line.cost_center_id:
                res[line.id] = 'invalid'
                logger.notifyChannel('account_hq_entries', netsvc.LOG_WARNING, _('%s: No CC') % (line.id or ''))
                continue
            if line.analytic_id and not line.destination_id: # CASE 2/
                # D Check, except B check
                if line.cost_center_id.id not in [x.id for x in line.analytic_id.cost_center_ids] and line.analytic_id.id != fp_id:
                    res[line.id] = 'invalid'
                    logger.notifyChannel('account_hq_entries', netsvc.LOG_WARNING, _('%s: CC (%s) not found in FP (%s)') % (line.id or '', line.cost_center_id.code or '', line.analytic_id.code or ''))
                    continue
            elif not line.analytic_id and line.destination_id: # CASE 3/
                # E Check
                account = self.pool.get('account.account').browse(cr, uid, line.account_id.id)
                if line.destination_id.id not in [x.id for x in account.destination_ids]:
                    res[line.id] = 'invalid'
                    logger.notifyChannel('account_hq_entries', netsvc.LOG_WARNING, _('%s: DEST (%s) not compatible with account (%s)') % (line.id or '', line.destination_id.code or '', account.code or ''))
                    continue
            else: # CASE 4/
                # C Check, except B
                if (line.account_id.id, line.destination_id.id) not in [x.account_id and x.destination_id and (x.account_id.id, x.destination_id.id) for x in line.analytic_id.tuple_destination_account_ids] and line.analytic_id.id != fp_id:
                    res[line.id] = 'invalid'
                    logger.notifyChannel('account_hq_entries', netsvc.LOG_WARNING, _('%s: Tuple Account/DEST (%s/%s) not found in FP (%s)') % (line.id or '', line.account_id.code or '', line.destination_id.code or '', line.analytic_id.code or ''))
                    continue
                # D Check, except B check
                if line.cost_center_id.id not in [x.id for x in line.analytic_id.cost_center_ids] and line.analytic_id.id != fp_id:
                    res[line.id] = 'invalid'
                    logger.notifyChannel('account_hq_entries', netsvc.LOG_WARNING, _('%s: CC (%s) not found in FP (%s)') % (line.id or '', line.cost_center_id.code or '', line.analytic_id.code or ''))
                    continue
                # E Check
                account = self.pool.get('account.account').browse(cr, uid, line.account_id.id)
                if line.destination_id.id not in [x.id for x in account.destination_ids]:
                    res[line.id] = 'invalid'
                    logger.notifyChannel('account_hq_entries', netsvc.LOG_WARNING, _('%s: DEST (%s) not compatible with account (%s)') % (line.id or '', line.destination_id.code or '', account.code or ''))
                    continue
        return res

    def _get_cc_changed(self, cr, uid, ids, field_name, arg, context=None):
        """
        Return True if the CC value is different from the original one or if this line is a split from an original entry that have a different cost center value
        """
        # Checks
        if context is None:
            context = {}
        # Prepare some values
        res = {}
        for e in self.browse(cr, uid, ids):
            res[e.id] = False
            if e.cost_center_id.id != e.cost_center_id_first_value.id:
                res[e.id] = True
            elif e.original_id and e.original_id.cost_center_id.id != e.cost_center_id.id:
                res[e.id] = True
        return res

    def _get_account_changed(self, cr, uid, ids, field_name, arg, context=None):
        """
        Return True if the account is different from the original one or if this line is a split from an original entry that have a different account value
        """
        # Checks
        if context is None:
            context = {}
        # Prepare some values
        res = {}
        for e in self.browse(cr, uid, ids):
            res[e.id] = False
            if e.account_id.id != e.account_id_first_value.id:
                res[e.id] = True
            elif e.original_id and e.original_id.account_id.id != e.account_id.id:
                res[e.id] = True
        return res

    def _get_is_account_partner_compatible(self, cr, uid, ids, field_name, arg,
        context=None):
        if context is None:
            context = {}
        res = {}
        account_obj = self.pool.get('account.account')

        for r in self.browse(cr, uid, ids, context=context):
            res[r.id] = True
            if r.account_id and r.partner_txt:
                res[r.id] = account_obj.is_allowed_for_thirdparty(cr, uid,
                    r.account_id.id, partner_txt=r.partner_txt,
                    context=context)[r.account_id.id]
        return res

    _columns = {
        'account_id': fields.many2one('account.account', "Account", required=True),
        'destination_id': fields.many2one('account.analytic.account', string="Destination", required=True, domain="[('category', '=', 'DEST'), ('type', '!=', 'view'), ('state', '=', 'open')]"),
        'cost_center_id': fields.many2one('account.analytic.account', "Cost Center", required=False, domain="[('category','=','OC'), ('type', '!=', 'view'), ('state', '=', 'open')]"),
        'analytic_id': fields.many2one('account.analytic.account', "Funding Pool", required=True, domain="[('category', '=', 'FUNDING'), ('type', '!=', 'view'), ('state', '=', 'open')]"),
        'free_1_id': fields.many2one('account.analytic.account', "Free 1", domain="[('category', '=', 'FREE1'), ('type', '!=', 'view'), ('state', '=', 'open')]"),
        'free_2_id': fields.many2one('account.analytic.account', "Free 2", domain="[('category', '=', 'FREE2'), ('type', '!=', 'view'), ('state', '=', 'open')]"),
        'user_validated': fields.boolean("User validated?", help="Is this line validated by a user in a OpenERP field instance?", readonly=True),
        'date': fields.date("Posting Date", readonly=True),
        'partner_txt': fields.char("Third Party", size=255, readonly=True),
        'period_id': fields.many2one("account.period", "Period", readonly=True),
        'name': fields.char('Description', size=255, required=True, readonly=True),
        'ref': fields.char('Reference', size=255),
        'document_date': fields.date("Document Date", readonly=True),
        'currency_id': fields.many2one('res.currency', "Book. Currency", required=True, readonly=True),
        'amount': fields.float('Amount', readonly=True),
        'account_id_first_value': fields.many2one('account.account', "Account @import", required=True, readonly=True),
        'cost_center_id_first_value': fields.many2one('account.analytic.account', "Cost Center @import", required=False, readonly=False),
        'analytic_id_first_value': fields.many2one('account.analytic.account', "Funding Pool @import", required=True, readonly=True),
        'destination_id_first_value': fields.many2one('account.analytic.account', "Destination @import", required=True, readonly=True),
        'analytic_state': fields.function(_get_analytic_state, type='selection', method=True, readonly=True, string="Distribution State",
            selection=[('none', 'None'), ('valid', 'Valid'), ('invalid', 'Invalid')], help="Give analytic distribution state"),
        'is_original': fields.boolean("Is Original HQ Entry?", help="This line was split into other one.", readonly=True),
        'is_split': fields.boolean("Is split?", help="This line comes from a split.", readonly=True),
        'original_id': fields.many2one("hq.entries", "Original HQ Entry", readonly=True, help="The Original HQ Entry from which this line comes from."),
        'split_ids': fields.one2many('hq.entries', 'original_id', "Split lines", help="All lines linked to this original HQ Entry."),
        'cc_changed': fields.function(_get_cc_changed, method=True, type='boolean', string='Have Cost Center changed?', help="When you change the cost center from the initial value (from a HQ Entry or a Split line), so the Cost Center changed is True."),
        'account_changed': fields.function(_get_account_changed, method=True, type='boolean', string='Have account changed?', help="When your entry have a different account from the initial one or from the original one."),
        'is_account_partner_compatible': fields.function(_get_is_account_partner_compatible, method=True, type='boolean', string='Account and partner compatible ?'),
    }

    _defaults = {
        'user_validated': lambda *a: False,
        'amount': lambda *a: 0.0,
        'is_original': lambda *a: False,
        'is_split': lambda *a: False,
        'is_account_partner_compatible': lambda *a: True,
    }

    def split_forbidden(self, cr, uid, ids, context=None):
        """
        Split is forbidden for these lines:
         - original one
         - split one
         - validated lines
        """
        # Checks
        if context is None:
            context = {}
        # Prepare some values
        res = False
        for line in self.browse(cr, uid, ids, context=context):
            if line.is_original:
                res = True
                break
            if line.is_split:
                res = True
                break
            if line.user_validated == True:
                res = True
                break
        return res

    def get_linked_lines(self, cr, uid, ids, context=None):
        """
        Give all lines (split/original) linked to the given ones
        """
        res = set()
        if context is None:
            context = {}

        def add_split(original_browse):
            for split in original_browse.split_ids:
                res.add(split.id)

        for line in self.browse(cr, uid, ids, context=context):
            res.add(line.id)
            if line.is_original:
                add_split(line)
            if line.is_split:
                # add original one
                res.add(line.original_id.id)
                # then other split lines
                add_split(line.original_id)
        return list(res)

    def unsplit_allowed_lines(self, cr, uid, ids, context=None):
        """
        You can unsplit a line if these one have the following criteria:
         - line is a draft one
         - line is original OR a split one
        This method return so the lines that can be unsplit
        """
        # Checks
        if context is None:
            context = {}
        # Prepare some values
        res = set()
        for line in self.browse(cr, uid, ids, context=context):
            if line.user_validated == False and (line.is_original or line.is_split):
                # First add original and split linked lines
                for el in self.get_linked_lines(cr, uid, [line.id]):
                    res.add(el)
                # Then add the line
                res.add(line.id)
        return list(res)

    def get_split_wizard(self, cr, uid, ids, context=None):
        """
        Launch HQ Entry Split Wizard
        """
        # Some checks
        if not context or not context.get('active_ids', False):
            raise osv.except_osv(_('Error'), _('No line found!'))
        # Prepare some values
        vals = {}
        ids = context.get('active_ids')
        if isinstance(ids, (int, long)):
            ids = [ids]
        if len(ids) > 1:
            raise osv.except_osv(_('Warning'), _('You can only split HQ Entries one by one!'))
        original_id = ids[0]
        original = self.browse(cr, uid, original_id, context=context)
        # some lines are forbidden to be split:
        if self.split_forbidden(cr, uid, ids, context=context):
            raise osv.except_osv(_('Error'), _('This line cannot be split.'))
        # Check if Original HQ Entry is valid (distribution state)
        if original.analytic_state != 'valid':
            raise osv.except_osv(_('Error'), _('You cannot split a HQ Entry which analytic distribution state is not valid!'))
        original_amount = original.amount
        vals.update({'original_id': original_id, 'original_amount': original_amount,})
        wiz_id = self.pool.get('hq.entries.split').create(cr, uid, vals, context=context)
        # Return view with register_line id
        context.update({
            'active_id': wiz_id,
            'active_ids': [wiz_id],
        })
        return {
            'name': _("HQ Entry Split"),
            'type': 'ir.actions.act_window',
            'res_model': 'hq.entries.split',
            'target': 'new',
            'res_id': [wiz_id],
            'view_mode': 'form',
            'view_type': 'form',
            'context': context,
        }

    def get_unsplit_wizard(self, cr, uid, ids, context=None):
        """
        Open Unsplit wizard
        """
        # Some checks
        if not context or not context.get('active_ids', False):
            raise osv.except_osv(_('Error'), _('No selected line(s)!'))
        # Prepare some values
        vals = {}
        if context is None:
            context = {}
        ids = context.get('active_ids')
        if isinstance(ids, (int, long)):
            ids = [ids]
        # Update vals
        vals.update({'line_ids': [(6, 0, ids)], 'process_ids': [(6, 0, self.unsplit_allowed_lines(cr, uid, ids, context=context))]})
        wiz_id = self.pool.get('hq.entries.unsplit').create(cr, uid, vals, context=context)
        # Return view with register_line id
        context.update({
            'active_id': wiz_id,
            'active_ids': [wiz_id],
        })
        return {
            'name': _("HQ Entry Unsplit"),
            'type': 'ir.actions.act_window',
            'res_model': 'hq.entries.unsplit',
            'target': 'new',
            'res_id': [wiz_id],
            'view_mode': 'form',
            'view_type': 'form',
            'context': context,
        }

    def get_validation_wizard(self, cr, uid, ids, context=None):
        """
        Open Validation wizard
        """
        # Some checks
        if not context or not context.get('active_ids', False):
            raise osv.except_osv(_('Error'), _('No selected line(s)!'))
        # Prepare some values
        vals = {}
        if context is None:
            context = {}
        ids = context.get('active_ids')
        if isinstance(ids, (int, long)):
            ids = [ids]
        # Search lines that should be processed
        # - exclude validated lines (user_validated = False)
        # - search for original lines (get_linked_lines)
        # - search for split linked lines (get_linked_lines)
        process_ids = self.search(cr, uid, [('id', 'in', self.get_linked_lines(cr, uid, ids, context=context)), ('user_validated', '=', False)])
        txt = _('Are you sure you want to post %d HQ entries ?') % (len(process_ids) or 0,)
        # Update vals
        vals.update({'line_ids': [(6, 0, ids)], 'process_ids': [(6, 0, process_ids)], 'txt': txt,})
        wiz_id = self.pool.get('hq.entries.validation').create(cr, uid, vals, context=context)
        # Return view with register_line id
        context.update({
            'active_id': wiz_id,
            'active_ids': [wiz_id],
        })
        return {
            'name': _("HQ Entries Validation"),
            'type': 'ir.actions.act_window',
            'res_model': 'hq.entries.validation',
            'target': 'new',
            'res_id': [wiz_id],
            'view_mode': 'form',
            'view_type': 'form',
            'context': context,
        }

    def fields_view_get(self, cr, uid, view_id=None, view_type='form', context=None, toolbar=False, submenu=False):
        """
        Change funding pool domain in order to include MSF Private fund
        """
        if context is None:
            context = {}
        view = super(hq_entries, self).fields_view_get(cr, uid, view_id, view_type, context, toolbar, submenu)
        arch = etree.fromstring(view['arch'])
        fields = arch.xpath('field[@name="analytic_id"]')
        if fields:
            try:
                fp_id = self.pool.get('ir.model.data').get_object_reference(cr, uid, 'analytic_distribution', 'analytic_account_msf_private_funds')[1]
            except ValueError:
                fp_id = 0
            fields[0].set('domain', "[('type', '!=', 'view'), ('state', '=', 'open'), ('category', '=', 'FUNDING'), '|', '&', ('cost_center_ids', '=', cost_center_id), ('tuple_destination', '=', (account_id, destination_id)), ('id', '=', %s)]" % fp_id)
        # Change Destination field
        dest_fields = arch.xpath('field[@name="destination_id"]')
        for field in dest_fields:
            field.set('domain', "[('type', '!=', 'view'), ('state', '=', 'open'), ('category', '=', 'DEST'), ('destination_ids', '=', account_id)]")
            view['arch'] = etree.tostring(arch)
        return view

    def onchange_destination(self, cr, uid, ids, destination_id=False, funding_pool_id=False, account_id=False):
        """
        Check given funding pool with destination
        """
        # Prepare some values
        res = {}
        # If all elements given, then search FP compatibility
        if destination_id and funding_pool_id and account_id:
            fp_line = self.pool.get('account.analytic.account').browse(cr, uid, funding_pool_id)
            # Search MSF Private Fund element, because it's valid with all accounts
            try:
                fp_id = self.pool.get('ir.model.data').get_object_reference(cr, uid, 'analytic_distribution', 
                'analytic_account_msf_private_funds')[1]
            except ValueError:
                fp_id = 0
            # Delete funding_pool_id if not valid with tuple "account_id/destination_id".
            # but do an exception for MSF Private FUND analytic account
            if (account_id, destination_id) not in [x.account_id and x.destination_id and (x.account_id.id, x.destination_id.id) for x in fp_line.tuple_destination_account_ids] and funding_pool_id != fp_id:
                res = {'value': {'analytic_id': False}}
        # If no destination, do nothing
        elif not destination_id:
            res = {}
        # Otherway: delete FP
        else:
            res = {'value': {'analytic_id': False}}
        # If destination given, search if given 
        return res

    def write(self, cr, uid, ids, vals, context=None):
        """
        Change Expat salary account is not allowed
        """
        if context is None:
            context={}

        #US-921: Only save the user_validated value if the update comes from sync!
        if context.get('sync_update_execution', False):
            if 'user_validated' in  vals:
                return super(hq_entries, self).write(cr, uid, ids, {'user_validated': vals['user_validated']}, context)
            return True

        if 'account_id' in vals:
            account = self.pool.get('account.account').browse(cr, uid, [vals.get('account_id')])[0]
            for line in self.browse(cr, uid, ids):
                if line.account_id_first_value and line.account_id_first_value.is_not_hq_correctible and not account.is_not_hq_correctible:
                    raise osv.except_osv(_('Warning'), _('Change Expat salary account is not allowed!'))
        return super(hq_entries, self).write(cr, uid, ids, vals, context)

    def unlink(self, cr, uid, ids, context=None):
        """
        Do not permit user to delete:
         - validated HQ entries
         - split entries
         - original entries
        """
        if isinstance(ids, (int, long)):
            ids = [ids]
        if not context.get('from', False) or context.get('from') != 'code' and ids:
            if self.search(cr, uid, [('id', 'in', ids), ('user_validated', '=', True)]):
                raise osv.except_osv(_('Error'), _('You cannot delete validated HQ Entries lines!'))
            if self.search(cr, uid, [('id', 'in', ids), ('is_split', '=', True)]):
                raise osv.except_osv(_('Error'), _('You cannot delete split entries!'))
            if self.search(cr, uid, [('id', 'in', ids), ('is_original', '=', True)]):
                raise osv.except_osv(_('Error'), _('You cannot delete original entries!'))
        return super(hq_entries, self).unlink(cr, uid, ids, context)

    def check_hq_entry_transaction(self, cr, uid, ids, wizard_model,
        context=None):
        if not ids:
            raise osv.except_osv(_("Warning"),
                _("No HQ Entry selected for transaction"))

        # BKLG-77
        domain = [
            ('id', 'in', ids),
            ('user_validated', '=', True),
        ]
        if self.search(cr, uid, domain, context=context, count=True):
            raise osv.except_osv(_("Warning"),
                _("You can not perform this action on a validated HQ Entry" \
                    " (please use the 'To Validate' filter in the HQ Entries list)"))

        # US-306: forbid to validate mission closed or + entries
        # => at coordo level you can not validate entries since field closed
        # period; but they can come from HQ mission opened via SYNC)
        period_ids = list(set([ he.period_id.id \
            for he in self.browse(cr, uid, ids, context=context) ]))
        if period_ids:
            domain = [
                ('id', 'in', period_ids),
                ('state', 'in', ['mission-closed', 'done', ]),
            ]
            if self.pool.get('account.period').search(cr, uid, domain,
                context=context, count=True):
                raise osv.except_osv(_("Warning"),
                    _("You can not validate HQ Entry in a mission-closed" \
                      " period"))

hq_entries()
# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
