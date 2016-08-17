#!/usr/bin/env python
# -*- encoding: utf-8 -*-
##############################################################################
#
#    OpenERP, Open Source Management Solution
#    Copyright (C) 2011 TeMPO Consulting, MSF
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

import wizard
import pooler

class wizard_request_to_order(wizard.interface):

    def _get_order(self, cr, uid, data, context=None):
        '''
        Returns the Purchase Orders generated by the current
        Procurement List
        '''
        pool_obj = pooler.get_pool(cr.dbname)
        list_obj = pool_obj.get('sale.order')

        order_ids = []

        for l in list_obj.browse(cr, uid, data['ids'], context=context):
            for o in l.order_ids:
                order_ids.append(o.id)

        return {'type': 'ir.actions.act_window',
                'res_model': 'purchase.order',
                'view_type': 'form',
                'view_mode': 'tree,form',
                'domain': [('state', '!=', 'draft'), ('id', 'in', order_ids)],
               }

    states = {
        'init': {
            'actions': [],
            'result': {
                'type': 'action',
                'action': _get_order,
                'state': 'end',
            },
        },
    }

wizard_request_to_order('wizard_request_to_order')

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
