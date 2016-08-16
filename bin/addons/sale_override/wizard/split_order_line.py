# -*- coding: utf-8 -*-
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

from osv import osv, fields
from product._common import rounding

from tools.translate import _


class split_sale_order_line_wizard(osv.osv_memory):
    _name = 'split.sale.order.line.wizard'
    _description = 'Split sale order lines'

    _columns = {
        'sale_line_id': fields.many2one('sale.order.line', string='Line Id', readonly=True),
        'original_qty': fields.float(digits=(16,2), string='Original Quantity', readonly=True),
        'old_line_qty': fields.float(digits=(16,2), string='Old line quantity', readonly=True),
        'new_line_qty': fields.float(digits=(16,2), string='New line quantity', required=True),
    }

    _defaults = {
        'new_line_qty': lambda *a: 0.00,
    }

    def split_line(self, cr, uid, ids, context=None):
        '''
        Create a new order line and change the quantity of the old line
        '''
        line_obj = self.pool.get('sale.order.line')

        if not context:
            context = {}

        if isinstance(ids, (int, long)):
            ids = [ids]
        context['keepDateAndDistrib'] = True
        for split in self.browse(cr, uid, ids, context=context):
            # Check if the sum of new line and old line qty is equal to the original qty
            if split.new_line_qty > split.original_qty:
                raise osv.except_osv(_('Error'), _('You cannot have a new quantity greater than the original quantity !'))
            elif split.new_line_qty <= 0.00:
                raise osv.except_osv(_('Error'), _('The new quantity must be positive !'))
            elif split.new_line_qty == split.original_qty:
                raise osv.except_osv(_('Error'), _('The new quantity must be different than the original quantity !'))
            elif split.new_line_qty != rounding(split.new_line_qty, split.sale_line_id.product_uom.rounding):
                raise osv.except_osv(_('Error'), _('The new quantity must be a multiple of %s !') % split.sale_line_id.product_uom.rounding)
            else:
                # Change the qty of the old line
                line_obj.write(cr, uid, [split.sale_line_id.id], {'product_uom_qty': split.original_qty - split.new_line_qty}, context=context)
                # copy data
                so_copy_data = {'is_line_split': True, # UTP-972: Indicate that the line is split
                                'product_uom_qty': split.new_line_qty}
                # following new sequencing policy, we check if resequencing occur (behavior 1).
                # if not (behavior 2), the split line keeps the same line number as original line
                if not line_obj.allow_resequencing(cr, uid, [split.sale_line_id.id], context=context):
                    # set default value for line_number as the same as original line
                    so_copy_data.update({'line_number': split.sale_line_id.line_number})
                # Create the new line
                new_line_id = line_obj.copy(cr, uid, split.sale_line_id.id, so_copy_data, context=context)
                self.infolog(cr, uid, "The FO/IR line id:%s (%s) has been split" % (
                    split.sale_line_id.id,
                    split.sale_line_id.line_number,
                ))

        return {'type': 'ir.actions.act_window_close'}

    def line_qty_change(self, cr, uid, ids, original_qty, new_line_qty, context=None):
        '''
        Update the old line qty according to the new line qty
        '''
        result = {}

        if ids:
            line = self.browse(cr, uid, ids[0], context=context)
            uom_id = line.sale_line_id.product_uom.id
            result = self.pool.get('product.uom')._change_round_up_qty(cr, uid, uom_id, new_line_qty, 'new_line_qty', result=result)
            new_line_qty = result.get('value', {}).get('new_line_qty', new_line_qty)
        
        vals = {'old_line_qty': original_qty - new_line_qty}
        result.setdefault('value', {}).update(vals)

        return result

split_sale_order_line_wizard()

