# -*- coding: utf-8 -*-
##############################################################################
#
#    OpenERP, Open Source Management Solution
#    Copyright (C) 2011 MSF, TeMPO Consulting
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

from osv import osv, fields
from tools.translate import _
import netsvc
from datetime import datetime, timedelta
from dateutil.relativedelta import relativedelta
import decimal_precision as dp
import logging
import tools
from os import path

class stock_picking(osv.osv):
    '''
    add a check boolean for confirmation of delivery
    '''
    _inherit = 'stock.picking'
    
    PICKING_STATE = [
        ('draft', 'Draft'),
        ('auto', 'Waiting'),
        ('confirmed', 'Confirmed'),
        ('assigned', 'Available'),
        ('shipped', 'Available Shipped'),
        ('done', 'Closed'),
        ('cancel', 'Cancelled'),
        ('import', 'Import in progress'),
        ('delivered', 'Delivered'),
    ]

    def _vals_get_out_step(self, cr, uid, ids, fields, arg, context=None):
        '''
        get function values
        '''
        result = {}
        for obj in self.browse(cr, uid, ids, context=context):
            result[obj.id] = {}
            for f in fields:
                result[obj.id].update({f:False,})
                
            # delivered_hidden
            result[obj.id]['delivered_hidden'] = obj.delivered
            # state_hidden
            result[obj.id]['state_hidden'] = obj.state
            if obj.state == 'done' and obj.delivered:
                result[obj.id]['state_hidden'] = 'delivered'
            
        return result

    _columns = {
        'delivered': fields.boolean(string='Delivered', readonly=True,),
        'delivered_hidden': fields.function(_vals_get_out_step, method=True, type='boolean', string='Delivered Hidden', multi='get_vals_out_step',),
        'state_hidden': fields.function(_vals_get_out_step, method=True, type='selection', selection=PICKING_STATE, string='State', multi='get_vals_out_step',),
    }
    
    _defaults = {
        'delivered': False,
    }
    
    def copy_data(self, cr, uid, id, default=None, context=None):
        '''
        set delivered to False
        '''
        if default is None:
            default = {}
        if context is None:
            context = {}
        default.update(delivered=False)
        res = super(stock_picking, self).copy_data(cr, uid, id, default=default, context=context)
        return res
    
    def set_delivered(self, cr, uid, ids, context=None):
        '''
        set the delivered flag
        '''
        self.write(cr, uid, ids, {'delivered': True,}, context=context)
        return True
     
stock_picking()
