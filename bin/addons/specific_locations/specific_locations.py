# -*- coding: utf-8 -*-
##############################################################################
#
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

class stock_warehouse(osv.osv):
    '''
    add a new field quarantine which is not mandatory
    '''
    _inherit = 'stock.warehouse'
    _columns = {'lot_quarantine_id': fields.many2one('stock.location', 'Location Quarantine', domain=[('usage','<>','view'), ('quarantine_location', '=', True),]),
                }
    
stock_warehouse()


class stock_location(osv.osv):
    '''
    override stock location to add:
    - quarantine location (checkbox - boolean)
    - destruction location (checkbox - boolean)
    - location category (selection)
    '''
    _inherit = 'stock.location'
    
    def remove_flag(self, flag, list):
        '''
        if we do not remove the flag, we fall into an infinite loop
        '''
        i = 0
        to_del = []
        for arg in list:
            if arg[0] == flag:
                to_del.append(i)
            i+=1
        for i in to_del:
            list.pop(i)
        
        return True
    
    def search_check_quarantine(self, cr, uid, obj, name, args, context=None):
        '''
        modify the query to take the type of stock move into account
        
        if type is 'out', quarantine_location must be False
        '''
        move_obj = self.pool.get('stock.move')
        move_id = context.get('move_id', False)
        
        # remove flag avoid infinite loop
        self.remove_flag('check_quarantine', args)
            
        if not move_id:
            return args
        
        # check the move
        move = move_obj.browse(cr, uid, move_id, context=context)

        if move.type == 'out':
            # out -> not from quarantine
            args.append(('quarantine_location', '=', False))
            
        return args
    
    def _get_false(self, cr, uid, ids, field_name, arg, context=None):
        '''
        return false for each id
        '''
        if isinstance(ids,(long, int)):
           ids = [ids]
        
        result = {}
        for id in ids:
          result[id] = False
        return result
    
    def _check_parent(self, cr, uid, ids, context=None):
        """ 
        Quarantine Location can only have Quarantine Location or Views as parent location.
        """
        for obj in self.browse(cr, uid, ids, context=context):
            if obj.quarantine_location and obj.location_id:
                if obj.location_id.usage not in ('view',) and not obj.location_id.quarantine_location:
                    return False
        return True
    
    def _check_chained(self, cr, uid, ids, context=None):
        """ Checks if location is quarantine and chained loc
        @return: True or False
        """
        for obj in self.browse(cr, uid, ids, context=context):
            if obj.quarantine_location:
                if obj.chained_location_type != 'none':
                    if obj.chained_location_type == 'fixed' and obj.chained_location_id.usage == 'internal':
                        return True
                    else:
                        return False
        return True

    
    _columns = {'quarantine_location': fields.boolean(string='Quarantine Location'),
                'destruction_location': fields.boolean(string='Destruction Location'),
                'location_category': fields.selection([('stock', 'Stock'),
                                                       ('consumption_unit', 'Consumption Unit'),
                                                       ('transition', 'Transition'),
                                                       ('eprep', 'EPrep'),
                                                       ('other', 'Other'),], string='Location Category', required=True),
                # could be used after discussion with Magali
                #'check_quarantine': fields.function(_get_false, fnct_search=search_check_quarantine, string='Check Quarantine', type="boolean", readonly=True, method=True),
                }
    _defaults = { 
       'location_category': 'stock',
    }
    
    _constraints = [(_check_parent,
                     'Quarantine Location can only have Quarantine Location or Views as parent location.',
                     ['location_id'],),
                    (_check_chained,
                     'You cannot define a quarantine location as chained location.',
                     ['quarantine_location', 'chained_location_type'],),
                    ]

stock_location()


class purchase_order(osv.osv):
    '''
    override purchase order
    - add hook _hook_action_picking_create_modify_out_source_loc_check
    '''
    _inherit = 'purchase.order'
    
    def _hook_action_picking_create_modify_out_source_loc_check(self, cr, uid, ids, context=None, *args, **kwargs):
        '''
        Please copy this to your module's method also.
        This hook belongs to the action_picking_create method from purchase>purchase.py>purchase_order class
        
        - allow to choose whether or not the source location of the corresponding outgoing stock move should
        match the destination location of incoming stock move
        '''
        # we do not want the corresponding out stock move to be updated
        return False
    
purchase_order()


class stock_move(osv.osv):
    '''
    add _hook_action_done_update_out_move_check
    '''
    _inherit = 'stock.move'
    
    def _hook_action_done_update_out_move_check(self, cr, uid, ids, context=None, *args, **kwargs):
        '''
        choose if the corresponding out stock move must be updated
        '''
        result = super(stock_move, self)._hook_action_done_update_out_move_check(cr, uid, ids, context=context, *args, **kwargs)
        # we never update the corresponding out stock move
        return False

stock_move()
