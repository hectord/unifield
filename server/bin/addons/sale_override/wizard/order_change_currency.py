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
from msf_partner import PARTNER_TYPE
from tools.translate import _


class sale_order_change_currency(osv.osv_memory):
    _name = 'sale.order.change.currency'
    
    _columns = {
        'order_id': fields.many2one('sale.order', string='Order', required=True),
        'partner_id': fields.many2one('res.partner', string='Partner', required=True),
        'partner_type': fields.selection(string='Partner Type', selection=PARTNER_TYPE),
        'old_pricelist_id': fields.many2one('product.pricelist', string='Old currency', required=True, readonly=True),
        'new_pricelist_id': fields.many2one('product.pricelist', string='New currency', required=True),
        'currency_rate': fields.float(digits=(16,6), string='Currency rate', readonly=True),
    }
    
    def compute_pricelist_rate(self, cr, uid, from_pricelist, to_pricelist, context=None):
        '''
        Compute the currency rate between two products pricelists
        '''
        if not from_pricelist and not to_pricelist:
            raise osv.except_osv(_('Error'), _('Please give two pricelists'))
        
        pricelist_obj = self.pool.get('product.pricelist')
        from_currency = pricelist_obj.browse(cr, uid, from_pricelist).currency_id.id
        to_currency = pricelist_obj.browse(cr, uid, to_pricelist).currency_id.id
        
        rate = self.pool.get('res.currency').compute(cr, uid, from_currency, to_currency, 1.00)
        
        return rate
    
    def currency_change(self, cr, uid, ids, old_pricelist_id, new_pricelist_id):
        '''
        Compute the rate between the two currencies
        '''
        res = {'currency_rate': 0.00}
        if old_pricelist_id and new_pricelist_id:
            rate = self.compute_pricelist_rate(cr, uid, old_pricelist_id, new_pricelist_id)
            res = {'currency_rate': rate}
            
        return {'value': res}
    
    def apply_to_lines(self, cr, uid, ids, context=None):
        '''
        Apply the conversion on lines
        '''
        if not context:
            context = {}
            
        if isinstance(ids, (int, long)):
            ids = [ids]
            
        c = context.copy()
        c.update({'update_merge': True})
            
        currency_obj = self.pool.get('res.currency')
        line_obj = self.pool.get('sale.order.line')
        order_obj = self.pool.get('sale.order')
            
        for wiz in self.browse(cr, uid, ids, context=context):            
            for line in wiz.order_id.order_line:
                new_price = currency_obj.compute(cr, uid, wiz.old_pricelist_id.currency_id.id, wiz.new_pricelist_id.currency_id.id, line.price_unit, round=False, context=context)
                line_obj.write(cr, uid, line.id, {'price_unit': new_price}, context=c)
                
            order_data = {'pricelist_id': wiz.new_pricelist_id.id,}
            
            order_obj.write(cr, uid, wiz.order_id.id, order_data, context=context)
            self.infolog(cr, uid, "The currency of the FO id:%s (%s) has been changed from id:%s (%s) to id:%s (%s)" % (
                wiz.order_id.id, wiz.order_id.name,
                wiz.old_pricelist_id.currency_id.id, wiz.old_pricelist_id.currency_id.name,
                wiz.new_pricelist_id.currency_id.id, wiz.new_pricelist_id.currency_id.name,
            ))
            
        return {'type': 'ir.actions.act_window_close'}
    
sale_order_change_currency()

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
