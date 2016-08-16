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
from tools import drop_view_if_exists
from lxml import etree
from destination_tools import many2many_notlazy
from tools.translate import _

# here was destination_m2m, replaced by the generic many2many_notlazy

class account_destination_link(osv.osv):
    _name = 'account.destination.link'
    _description = 'Destination link between G/L and Analytic accounts'
    _order = 'name, id'

    def _get_tuple_name(self, cr, uid, ids, name=False, args=False, context=None):
        """
        Get account_id code for tuple name
        """
        # Some verifications
        if context is None:
            context = {}
        if isinstance(ids, (int, long)):
            ids = [ids]
        if not ids:
            return {}
        # Prepare some values
        res = {}
        # Browse given invoices
        for t in self.browse(cr, uid, ids):
            res[t.id] = ''
            # condition needed when a tuple is deleted from account.account
            if self.read(cr, uid, t.id, ['account_id']):
                res[t.id] = "%s %s"%(t.account_id and t.account_id.code or '', t.destination_id and t.destination_id.code or '')
        return res

    def _get_account_ids(self, cr, uid, ids, context=None):
        if isinstance(ids, (int, long)):
            ids = [ids]
        return self.pool.get('account.destination.link').search(cr, uid, [('account_id', 'in', ids)], limit=0)

    def _get_analytic_account_ids(self, cr, uid, ids, context=None):
        if isinstance(ids, (int, long)):
            ids = [ids]
        return self.pool.get('account.destination.link').search(cr, uid, [('destination_id', 'in', ids)], limit=0)

    def _get_used(self, cr, uid, ids, name=False, args=False, context=None):
        if context is None:
            context = {}

        used = []
        if context.get('dest_in_use') and isinstance(context['dest_in_use'], list):
            try:
                used = context['dest_in_use'][0][2]
            except ValueError:
                pass
        if isinstance(ids, (int, long)):
            ids = [ids]
        ret = {}
        for i in ids:
            ret[i] = i in used
        return ret

    _columns = {
        'account_id': fields.many2one('account.account', "G/L Account", required=True, domain="[('type', '!=', 'view'), ('is_analytic_addicted', '=', True)]", readonly=True),
        'destination_id': fields.many2one('account.analytic.account', "Analytical Destination Account", required=True, domain="[('type', '!=', 'view'), ('category', '=', 'DEST')]", readonly=True),
        'funding_pool_ids': fields.many2many('account.analytic.account', 'funding_pool_associated_destinations', 'tuple_id', 'funding_pool_id', "Funding Pools"),
        'name': fields.function(_get_tuple_name, method=True, type='char', size=254, string="Name", readonly=True,
            store={
                'account.destination.link': (lambda self, cr, uid, ids, c={}: ids, ['account_id', 'destination_id'], 20),
                'account.analytic.account': (_get_analytic_account_ids, ['code'], 10),
                'account.account': (_get_account_ids, ['code'], 10),
            }),
        'used': fields.function(_get_used, string='Used', method=True, type='boolean'),
    }

    _sql_constraints = [('unique_account_destination', 'unique(account_id, destination_id)', 'Couple account, destination must be unique!')]

account_destination_link()

class account_destination_summary(osv.osv):
    _name = 'account.destination.summary'
    _description = 'Destinations by accounts'
    _rec_name = 'account_id'
    _auto = False

    _columns = {
        'account_id': fields.many2one('account.account', "G/L Account"),
        'funding_pool_id': fields.many2one('account.analytic.account', 'Funding Pool'),
    }

    def fields_get(self, cr, uid, fields=None, context=None):
        fields = super(account_destination_summary, self).fields_get(cr, uid, fields, context)
        dest_obj = self.pool.get('account.analytic.account')
        destination_ids = dest_obj.search(cr, uid, [('type', '!=', 'view'), ('category', '=', 'DEST'), ('parent_id', '!=', False)])
        for dest in dest_obj.read(cr, uid, destination_ids, ['name']):
            fields['dest_%s'%(dest['id'])] = {'type': 'boolean', 'string': dest['name']}
        return fields

    def fields_view_get(self, cr, uid, view_id=None, view_type='form', context=None, toolbar=False, submenu=False):
        view = super(account_destination_summary, self).fields_view_get(cr, uid, view_id, view_type=view_type, context=context, toolbar=toolbar, submenu=submenu)
        if view_type == 'tree':
            fields_to_add = []
            form = etree.fromstring(view['arch'])
            tree = form.xpath('//tree')
            for field in view.get('fields', {}):
                if field.startswith('dest_'):
                    fields_to_add.append(int(field.split('_')[1]))

            if fields_to_add:
                for dest_order in self.pool.get('account.analytic.account').search(cr, uid, [('id', 'in', fields_to_add)], order='name'):
                    new_field = etree.Element('field', attrib={'name': 'dest_%d'%dest_order})
                    tree[0].append(new_field)
            view['arch'] = etree.tostring(form)
        return view

    def read(self, cr, uid, ids, fields_to_read=None, context=None, load='_classic_read'):
        first = False
        if isinstance(ids, (int, long)):
            ids = [ids]
            first = True
        if fields_to_read is None:
            fields_to_read = []
        ret = super(account_destination_summary, self).read(cr, uid, ids, fields_to_read, context, load)
        f_to_read = []
        for field in fields_to_read:
            if field.startswith('dest_'):
                f_to_read.append(field)

        if f_to_read:
            cr.execute('''
                SELECT
                    sum.id,
                    l.destination_id
                FROM
                    account_destination_link l,
                    account_destination_summary sum,
                    funding_pool_associated_destinations d
                WHERE
                    d.tuple_id = l.id and
                    sum.account_id = l.account_id and
                    sum.funding_pool_id = d.funding_pool_id and
                    sum.id in %s
                ''',(tuple(ids),)
                )
            tmp_result = {}
            for x in cr.fetchall():
                tmp_result.setdefault(x[0], []).append(x[1])

            for x in ret:
                for dest in tmp_result.get(x['id'], []):
                    x['dest_%s'%(dest,)] = True
                for false_value in f_to_read:
                    if false_value not in x:
                        x[false_value] = False

        if first:
            return ret[0]
        return ret



    def init(self, cr):
        # test if id exists in funding_pool_associated_destinations or create it
        cr.execute("SELECT attr.attname FROM pg_attribute attr, pg_class class WHERE attr.attrelid = class.oid AND class.relname = 'funding_pool_associated_destinations' AND attr.attname='id'")
        if not cr.fetchall():
            cr.execute("ALTER TABLE funding_pool_associated_destinations ADD COLUMN id SERIAL")

        drop_view_if_exists(cr, 'account_destination_summary')
        cr.execute("""
            CREATE OR REPLACE view account_destination_summary AS (
                SELECT
                    min(d.id) AS id,
                    l.account_id AS account_id,
                    d.funding_pool_id AS funding_pool_id
                FROM
                    account_destination_link l,
                    funding_pool_associated_destinations d
                WHERE
                    d.tuple_id = l.id
                GROUP BY
                    l.account_id,d.funding_pool_id
            )
        """)
    _order = 'account_id'
account_destination_summary()

class account_account(osv.osv):
    _name = 'account.account'
    _inherit = 'account.account'

    _columns = {
        'user_type_code': fields.related('user_type', 'code', type="char", string="User Type Code", store=False),
        'user_type_report_type': fields.related('user_type', 'report_type', type="char", string="User Type Report Type", store=False),
        'funding_pool_line_ids': fields.many2many('account.analytic.account', 'funding_pool_associated_accounts', 'account_id', 'funding_pool_id',
            string='Funding Pools'),
        'default_destination_id': fields.many2one('account.analytic.account', 'Default Destination', domain="[('type', '!=', 'view'), ('category', '=', 'DEST')]"),
        'destination_ids': many2many_notlazy('account.analytic.account', 'account_destination_link', 'account_id', 'destination_id', 'Destinations', readonly=True),
    }

    def create(self, cr, uid, vals, context=None):
        """
        Add default destination to the list of destination_ids
        """
        # Some checks
        if context is None:
            context = {}
        # Add default_destination_id in destination_ids if exists
        if not context.get('sync_update_execution') and 'default_destination_id' in vals and vals.get('default_destination_id', False):
            vals.update({'destination_ids': [(4, vals.get('default_destination_id'))]})
        return super(account_account, self).create(cr, uid, vals, context=context)

    def write(self, cr, uid, ids, vals, context=None):
        """
        Add default destination to the list of destination_ids
        """
        # Prepare some values
        if context is None:
            context = {}
        # Check default destination presence
        if not context.get('sync_update_execution') and 'default_destination_id' in vals and vals.get('default_destination_id'):
            # Fetch it
            dd_id = vals.get('default_destination_id')
            res = super(account_account, self).write(cr, uid, ids, vals, context=context)
            for a in self.browse(cr, uid, ids):
                if dd_id not in a.destination_ids:
                    all_ids = [x.id for x in a.destination_ids] or []
                    all_ids.append(dd_id)
                    super(account_account, self).write(cr, uid, [a.id], {'destination_ids': [(6, 0, all_ids)]})
            return res
        return super(account_account, self).write(cr, uid, ids, vals, context=context)

    def onchange_user_type(self, cr, uid, ids, user_type_id=False, code=False, context=None):
        """
        Update user_type_code with user_type_id code.
        Also update default_destination_id mandatory field
        """
        res = {}
        if not user_type_id:
            return res
        if context is None:
            context = {}
        data = self.pool.get('account.account.type').read(cr, uid, user_type_id, ['code', 'report_type'])
        if data:
            company_account_active = False
            company = self.pool.get('res.users').browse(cr, uid, uid).company_id
            if company and company.additional_allocation:
                company_account_active = company.additional_allocation
            company_account = 7 # User for accounts that begins by "7"
            is_analytic_addicted = self.is_analytic_addicted(cr, uid, data.get('code'), code, company_account, company_account_active)
            res.setdefault('value', {}).update({'user_type_code': data.get('code', False), 'user_type_report_type': data.get('report_type', False), 'is_analytic_addicted': is_analytic_addicted})
        return res

account_account()

class account_move(osv.osv):
    _name = 'account.move'
    _inherit = 'account.move'

    _columns = {
        'analytic_distribution_id': fields.many2one('analytic.distribution', 'Analytic Distribution', readonly=True),
    }

    def button_analytic_distribution(self, cr, uid, ids, context=None):
        """
        Launch analytic distribution wizard on a Journal Entry
        """
        # Some verifications
        if context is None:
            context = {}
        if isinstance(ids, (int, long)):
            ids = [ids]
        # Prepare some values
        move = self.browse(cr, uid, ids[0], context=context)
        amount = 0.0
        total_debit = 0.0
        total_credit = 0.0
        # Search elements for currency
        company_currency = self.pool.get('res.users').browse(cr, uid, uid, context=context).company_id.currency_id.id
        currency = move.currency_id and move.currency_id.id or company_currency
        # Search amount for this Journal Entry
        # We take the biggest amount (debit OR credit)
        # If debit > credit, then amount = debit
        # If credit > debit, them amount = credit
        # If debit = credit and debit != 0.0, then amount = debit = credit (here we take debit)
        # Else, amount is 0.0
        for ml in move.line_id:
            total_debit += ml.debit_currency
            total_credit += ml.credit_currency
        if total_debit > total_credit:
            amount = total_debit
        elif total_credit > total_debit:
            amount = total_credit
        elif total_credit == total_debit and total_debit <> 0.0:
            amount = total_debit
        # Get analytic_distribution_id
        distrib_id = move.analytic_distribution_id and move.analytic_distribution_id.id
        # Prepare values for wizard
        vals = {
            'total_amount': amount,
            'move_id': move.id,
            'currency_id': currency or False,
            'state': 'dispatch',
            'posting_date': move.date,
            'document_date': move.document_date,
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
                'name': _('Global analytic distribution'),
                'type': 'ir.actions.act_window',
                'res_model': 'analytic.distribution.wizard',
                'view_type': 'form',
                'view_mode': 'form',
                'target': 'new',
                'res_id': [wiz_id],
                'context': context,
        }

    def button_reset_distribution(self, cr, uid, ids, context=None):
        """
        Reset analytic distribution on all move lines.
        To do this, just delete the analytic_distribution id link on each move line.
        """
        if context is None:
            context = {}
        if isinstance(ids, (int, long)):
            ids = [ids]
        # Prepare some values
        move_obj = self.pool.get(self._name + '.line')
        # Search move lines
        to_reset = move_obj.search(cr, uid, [('move_id', 'in', ids)])
        move_obj.write(cr, uid, to_reset, {'analytic_distribution_id': False})
        return True

    def button_validate(self, cr, uid, ids, context=None):
        """
        Check that analytic distribution is ok for all lines
        """
        if context is None:
            context = {}
        for m in self.browse(cr, uid, ids):
            for ml in m.line_id:
                if ml.account_id and ml.account_id.is_analytic_addicted:
                    if ml.analytic_distribution_state != 'valid':
                        raise osv.except_osv(_('Error'), _('Analytic distribution is not valid for this line: %s') % (ml.name or '',))
                    # Copy analytic distribution from header
                    if not ml.analytic_distribution_id:
                        new_distrib_id = self.pool.get('analytic.distribution').copy(cr, uid, ml.move_id.analytic_distribution_id.id, {}, context=context)
                        # UF-2248: Improve the code by using a sql directly, and not a write -- make no impact on the validation, as it will be done in the call super.validate_button
                        #self.pool.get('account.move.line').write(cr, uid, [ml.id], {'analytic_distribution_id': new_distrib_id})
                        cr.execute('update account_move_line set analytic_distribution_id=%s where id=%s', (new_distrib_id, ml.id))

        return super(account_move, self).button_validate(cr, uid, ids, context=context)

    def validate(self, cr, uid, ids, context=None):
        """
        Check analytic distribution state for all lines that comes from a manual entry. If distribution is invalid, then line is also invalid! (draft state)
        """
        if context is None:
            context = {}
        res = super(account_move, self).validate(cr, uid, ids, context)
        for m in self.browse(cr, uid, ids):
            if m.status and m.status == 'manu':
                for ml in m.line_id:
                    if ml.analytic_distribution_state == 'invalid' or (ml.analytic_distribution_state == 'none' and ml.account_id.is_analytic_addicted):
                        self.pool.get('account.move.line').write(cr, uid, [x.id for x in m.line_id], {'state': 'draft'}, context, check=False, update_check=False)
                        break
        return res

account_move()
# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
