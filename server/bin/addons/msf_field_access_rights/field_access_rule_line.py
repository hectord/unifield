#!/usr/bin/env python
# -*- encoding: utf-8 -*-
##############################################################################
#
#    OpenERP, Open Source Management Solution
#    Copyright (C) 2011 TeMPO Consulting, MSF. All Rights Reserved
#    Developer: Max Mumford
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

class field_access_rule_line(osv.osv):
    """
    Lets user create access and sync propagation rules for fields of models.
    This class specifies the fields and their access and sync propagation rules are implemented by the field_access_rule.
    """

    _name = "msf_field_access_rights.field_access_rule_line"
    _description = 'Field Access Rule Line'
    _rec_name = "field_name"
    
    _columns = {
        'field': fields.many2one('ir.model.fields', 'Field', help='The field of the model for which this rule applies', required=True),
        'field_name': fields.char('Field Name', size=256, help='The technical name for the field. This is used to make searching for Field Access Rule Lines easier.'),
        'write_access': fields.boolean('Write Access', help='If checked, the user has access to write on this field.'),
        'value_not_synchronized_on_create': fields.boolean('Value NOT Synchronised on Create', help='If checked, the value for this field given by a synchronisation or import is ignored when this record is created.'),
        'value_not_synchronized_on_write': fields.boolean('Value NOT Synchronised on Write', help='If checked, the value for this field given by a synchronisation or import is ignored when this record is editted.'),

        'field_access_rule': fields.many2one('msf_field_access_rights.field_access_rule', 'Field Access Rule', ondelete='cascade', required=True),
        'field_access_rule_model_id': fields.related('field_access_rule', 'model_id', type="integer", string='Field Model')
    }

    _defaults = {
        'write_access': True,
        'value_not_synchronized_on_write': False,
        'value_not_synchronized_on_create': False,
    }

    _sql_constraints = [
        ('rule_id_field_unique', 'unique (field_access_rule, field)', 'You cannot have two Field Access Rule Lines for the same Field in the same Rule')
    ]

    def _get_field_name_from_id(self, cr, uid, field, context={}):
        if field: 
            fields_pool = self.pool.get('ir.model.fields')
            fields = fields_pool.browse(cr, uid, field, context=context)
            return fields.name
        else:
            return ''

    def _add_field_name_to_values(self, cr, uid, values, context={}):
        if 'field' in values and ('field_name' not in values or not values['field_name']):
            values['field_name'] = self._get_field_name_from_id(cr, uid, values['field'], context=context)
        return values

    def create(self, cr, uid, values, context={}):
        values = self._add_field_name_to_values(cr, uid, values, context)
        return super(field_access_rule_line, self).create(cr, uid, values, context=context)

    def write(self, cr, uid, ids, values, context={}):
        values = self._add_field_name_to_values(cr, uid, values, context)
        return super(field_access_rule_line, self).write(cr, uid, ids, values, context=context)

    def onchange_field(self, cr, uid, ids, field, context={}):
        field_name = self._get_field_name_from_id(cr, uid, field, context=context)
        return {'value': {'field_name' : field_name}}
    
    def onchange_field_access_rule(self, cr, uid, ids, field_access_rule, context=None):
        if field_access_rule:
            model_id = self.pool.get('msf_field_access_rights.field_access_rule').browse(cr, uid, field_access_rule).model_id.id
            return {'value': {'field_access_rule_model_id': model_id, 'field': None}}
        else:
            return {'value': {'field_access_rule_model_id': None, 'field': None}}

field_access_rule_line()