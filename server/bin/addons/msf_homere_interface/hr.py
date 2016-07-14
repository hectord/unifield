#!/usr/bin/env python
# -*- coding: utf-8 -*-
##############################################################################
#
#    OpenERP, Open Source Management Solution
#    Copyright (C) 2012 TeMPO Consulting, MSF. All Rights Reserved
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
from lxml import etree
from tools.translate import _

class hr_employee(osv.osv):
    _name = 'hr.employee'
    _inherit = 'hr.employee'
    _rec_name = 'name_resource'

    _order = 'name_resource'

    def _get_allow_edition(self, cr, uid, ids, field_name=None, arg=None, context=None):
        """
        For given ids get True or False regarding payroll system configuration (activated or not).
        If payroll_ok is True, so don't permit Local employee edition.
        Otherwise permit user to edit them.
        """
        if not context:
            context = {}
        res = {}
        allowed = False
        setup = self.pool.get('unifield.setup.configuration').get_config(cr, uid)
        if setup and not setup.payroll_ok:
            allowed = True
        for e in ids:
            res[e] = allowed
        return res

    def _get_ex_allow_edition(self, cr, uid, ids, field_name=None, arg=None,
        context=None):
        """
        US-94 do not allow to modify an already set identification id for expat
        """
        res = {}
        if not ids:
            return res

        if not context:
            context = {}
        if isinstance(ids, (int, long)):
            ids = [ids]
        for self_br in self.browse(cr, uid, ids, context=context):
            can_edit = True
            if self_br.employee_type == 'ex' and self_br.identification_id:
                can_edit = False
            res[self_br.id] = can_edit
        return res

    def onchange_type(self, cr, uid, ids, e_type=None, context=None):
        """
        Update allow_edition field when changing employee_type
        """
        res = {}
        if not context:
            context = {}
        if not e_type:
            return res
        elif e_type == 'local':
            if not 'value' in res:
                res['value'] = {}
            allowed = False
            setup = self.pool.get('unifield.setup.configuration').get_config(cr, uid)
            if setup and not setup.payroll_ok:
                allowed = True
            res['value'].update({'allow_edition': allowed,})
        return res

    _columns = {
        'employee_type': fields.selection([('', ''), ('local', 'Local Staff'), ('ex', 'Expatriate employee')], string="Type", required=True),
        'cost_center_id': fields.many2one('account.analytic.account', string="Cost Center", required=False, domain="[('category','=','OC'), ('type', '!=', 'view'), ('state', '=', 'open')]"),
        'funding_pool_id': fields.many2one('account.analytic.account', string="Funding Pool", domain="[('category', '=', 'FUNDING'), ('type', '!=', 'view'), ('state', '=', 'open')]"),
        'free1_id': fields.many2one('account.analytic.account', string="Free 1", domain="[('category', '=', 'FREE1'), ('type', '!=', 'view'), ('state', '=', 'open')]"),
        'free2_id': fields.many2one('account.analytic.account', string="Free 2", domain="[('category', '=', 'FREE2'), ('type', '!=', 'view'), ('state', '=', 'open')]"),
        'homere_codeterrain': fields.char(string='Homere field: codeterrain', size=20, readonly=True, required=False),
        'homere_id_staff': fields.integer(string='Homere field: id_staff', size=10, readonly=True, required=False),
        'homere_id_unique': fields.char(string='Homere field: id_unique', size=42, readonly=True, required=False),
        'gender': fields.selection([('male', 'Male'),('female', 'Female'), ('unknown', 'Unknown')], 'Gender'),
        'private_phone': fields.char(string='Private Phone', size=32),
        'name_resource': fields.related('resource_id', 'name', string="Name", type='char', size=128, store=True),
        'destination_id': fields.many2one('account.analytic.account', string="Destination", domain="[('category', '=', 'DEST'), ('type', '!=', 'view'), ('state', '=', 'open')]"),
        'allow_edition': fields.function(_get_allow_edition, method=True, type='boolean', store=False, string="Allow local employee edition?", readonly=True),
        'photo': fields.binary('Photo', readonly=True),
        'ex_allow_edition': fields.function(_get_ex_allow_edition, method=True, type='boolean', store=False, string="Allow expat employee edition?", readonly=True),
    }

    _defaults = {
        'employee_type': lambda *a: 'ex',
        'homere_codeterrain': lambda *a: '',
        'homere_id_staff': lambda *a: 0.0,
        'homere_id_unique': lambda *a: '',
        'gender': lambda *a: 'unknown',
        'ex_allow_edition': lambda *a: True,
    }

    def _check_unicity(self, cr, uid, ids, context=None):
        """
        Check that identification_id is not used yet.
        """
        # Some verifications
        if not context:
            context = {}
        # Search if no one use this identification_id
        for e in self.browse(cr, uid, ids):
            if e.identification_id:
                same = self.search(cr, uid, [('identification_id', '=', e.identification_id)])
                if same and len(same) > 1:
                    same_data = self.read(cr, uid, same, ['name'])
                    names = [e.name]
                    for employee in same_data:
                        employee_name = employee.get('name', False)
                        if employee_name and employee_name not in names:
                            names.append(employee_name)
                    raise osv.except_osv(_('Error'), _('Some employees have the same unique code: %s') % (';'.join(names)))
                    return False
        return True

    _constraints = [
        (_check_unicity, "Another employee has the same unique code.", ['identification_id']),
    ]

    def create(self, cr, uid, vals, context=None):
        """
        Block creation for local staff if no 'from' in context
        """
        # Some verifications
        if not context:
            context = {}
        allow_edition = False
        if 'employee_type' in vals and vals.get('employee_type') == 'local':
            # Search Payroll functionnality preference (activated or not)
            # If payroll_ok is False, then we permit user to create local employees
            setup = self.pool.get('unifield.setup.configuration').get_config(cr, uid)
            if setup and not setup.payroll_ok:
                allow_edition = True
            # Raise an error if employee is created manually
            if (not context.get('from', False) or context.get('from') not in ['yaml', 'import']) and not context.get('sync_update_execution', False) and not allow_edition:
                raise osv.except_osv(_('Error'), _('You are not allowed to create a local staff! Please use Import to create local staff.'))
#            # Raise an error if no cost_center
#            if not vals.get('cost_center_id', False):
#                raise osv.except_osv(_('Warning'), _('You have to complete Cost Center field before employee creation!'))
            # Add Nat. staff by default if not in vals
            if not vals.get('destination_id', False):
                try:
                    ns_id = self.pool.get('ir.model.data').get_object_reference(cr, uid, 'analytic_distribution', 'analytic_account_destination_national_staff')[1]
                except ValueError:
                    ns_id = False
                vals.update({'destination_id': ns_id})

        return super(hr_employee, self).create(cr, uid, vals, context)

    def write(self, cr, uid, ids, vals, context=None):
        """
        Block write for local staff if no 'from' in context.
        Allow only analytic distribution changes (cost center, funding pool, free 1 and free 2)
        """
        # Some verifications
        if not context:
            context = {}
        # Prepare some values
        local = False
        ex = False
        allowed = False
        res = []
        setup = self.pool.get('unifield.setup.configuration').get_config(cr, uid)
        if setup and not setup.payroll_ok:
            allowed = True
        # Prepare some variable for process
        if vals.get('employee_type', False):
            if vals.get('employee_type') == 'local':
                local = True
            elif vals.get('employee_type') == 'ex':
                ex = True
        if (context.get('from', False) and context.get('from') in ['yaml', 'import']) or context.get('sync_update_execution', False):
            allowed = True
        # Browse all employees
        for emp in self.browse(cr, uid, ids):
            new_vals = dict(vals)
            # Raise an error if attempt to change local into expat and expat into local
            if emp.employee_type == 'ex' and local and not allowed:
                raise osv.except_osv(_('Error'), _('You are not allowed to change an expatriate to local staff!'))
            if emp.employee_type == 'local' and ex and not allowed:
                raise osv.except_osv(_('Error'), _('You are not allowed to change a local staff to expatriate!'))
            # Do some modifications for local employees
            if local or emp.employee_type == 'local':
                # Do not change any field except analytic distribution (if not allowed)
                for el in vals:
                    if el in ['cost_center_id', 'funding_pool_id', 'free1_id', 'free2_id']:
                        new_vals.update({el: vals[el]})
            # Write changes
            employee_id = super(hr_employee, self).write(cr, uid, emp.id, new_vals, context)
            if employee_id:
                res.append(employee_id)
        return res

    def unlink(self, cr, uid, ids, context=None):
        """
        Delete local staff is not allowed except if:
        - 'unlink' is in context and its value is 'auto'
        - Payroll functionnality have been DESactivated
        """
        # Some verification
        if not context:
            context = {}
        delete_local_staff = False
        allowed = False
        setup = self.pool.get('unifield.setup.configuration').get_config(cr, uid)
        if setup and not setup.payroll_ok:
            allowed = True
        if (context.get('unlink', False) and context.get('unlink') == 'auto') or allowed:
            delete_local_staff = True
        setup_id = self.pool.get('unifield.setup.configuration').get_config(cr, uid)
        if not setup_id.payroll_ok:
            delete_local_staff = True
        # Browse all employee
        for emp in self.browse(cr, uid, ids):
            if emp.employee_type == 'local' and (not delete_local_staff or not allowed):
                raise osv.except_osv(_('Warning'), _('You are not allowed to delete local staff manually!'))
        return super(hr_employee, self).unlink(cr, uid, ids, context)

    def fields_view_get(self, cr, uid, view_id=None, view_type='form', context=None, toolbar=False, submenu=False):
        """
        Change funding pool domain in order to include MSF Private fund
        """
        if not context:
            context = {}
        view = super(hr_employee, self).fields_view_get(cr, uid, view_id, view_type, context, toolbar, submenu)
        if view_type in ['form', 'tree']:
            form = etree.fromstring(view['arch'])
            data_obj = self.pool.get('ir.model.data')
            try:
                oc_id = data_obj.get_object_reference(cr, uid, 'analytic_distribution', 'analytic_account_project')[1]
            except ValueError:
                oc_id = 0
            # Change OC field
            fields = form.xpath('/' + view_type + '//field[@name="cost_center_id"]')
            for field in fields:
                field.set('domain', "[('type', '!=', 'view'), ('state', '=', 'open'), ('id', 'child_of', [%s])]" % oc_id)
            # Change FP field
            try:
                fp_id = data_obj.get_object_reference(cr, uid, 'analytic_distribution', 'analytic_account_msf_private_funds')[1]
            except ValueError:
                fp_id = 0
            fp_fields = form.xpath('/'  + view_type + '//field[@name="funding_pool_id"]')
            for field in fp_fields:
                field.set('domain', "[('category', '=', 'FUNDING'), ('type', '!=', 'view'), ('state', '=', 'open'), '|', ('cost_center_ids', '=', cost_center_id), ('id', '=', %s)]" % fp_id)
            view['arch'] = etree.tostring(form)
        return view

    def onchange_cc(self, cr, uid, ids, cost_center_id=False, funding_pool_id=False):
        """
        Update FP or CC regarding both.
        """
        # Prepare some values
        vals = {}
        if not cost_center_id or not funding_pool_id:
            return {}
        if cost_center_id and funding_pool_id:
            fp = self.pool.get('account.analytic.account').browse(cr, uid, funding_pool_id)
            try:
                fp_id = self.pool.get('ir.model.data').get_object_reference(cr, uid, 'analytic_distribution', 'analytic_account_msf_private_funds')[1]
            except ValueError:
                fp_id = 0
            # Exception for MSF Private Fund
            if funding_pool_id == fp_id:
                return {}
            if cost_center_id not in [x.id for x in fp.cost_center_ids]:
                vals.update({'funding_pool_id': False})
        return {'value': vals}

    def search(self, cr, uid, args, offset=0, limit=None, order=None, context=None, count=False):

        if not args:
            args = []
        if context is None:
            context = {}
        # US_262: add disrupt in search
        # If disrupt is not define don't block inactive
        disrupt = False
        if context.get('disrupt_inactive', True):
            disrupt = True

        if not disrupt:
            if ('active', '=', False) not in args \
               and ('active', '=', True) not in args:
                args += [('active', '=', True)]
        return super(hr_employee, self).search(cr, uid, args, offset=offset,
                                               limit=limit, order=order,
                                               context=context, count=count)

    def name_search(self, cr, uid, name, args=None, operator='ilike', context=None, limit=100):
        if not args:
            args=[]
        if context is None:
            context={}
        # UTP-441: only see active employee execept if args also contains a search on 'active' field
        disrupt = False
        if context.get('disrupt_inactive', False) and context.get('disrupt_inactive') == True:
            disrupt = True
        if not disrupt:
            if not ('active', '=', False) or not ('active', '=', True) in args:
                args += [('active', '=', True)]

        return super(hr_employee, self).name_search(cr, uid, name, args, operator, context, limit)

    def auto_import(self, cr, uid, file_to_import):
        import base64
        import os
        processed = []
        rejected = []
        headers = []

        import_obj = self.pool.get('hr.expat.employee.import')
        import_id = import_obj.create(cr, uid, {
            'file': base64.encodestring(open(file_to_import, 'r').read()),
            'filename': os.path.split(file_to_import)[1],
        })
        processed, rejected, headers = import_obj.button_validate(cr, uid, [import_id], auto_import=True)
        return processed, rejected, headers

hr_employee()
# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
