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

from osv import osv
from osv import fields

from tools.translate import _

import time


class product_supplierinfo(osv.osv):
    _name = 'product.supplierinfo'
    _inherit = 'product.supplierinfo'
    
    def unlink(self, cr, uid, info_ids, context=None):
        '''
        Disallow the possibility to remove a supplier info if 
        it's linked to a catalogue
        If 'product_change' is set to True in context, allows the deletion
        because it says that the unlink method is called by the write method
        of supplier.catalogue.line and that the product of the line has changed.
        '''
        if context is None:
            context = {}
        if isinstance(info_ids, (int, long)):
            info_ids = [info_ids]
            
        for info in self.browse(cr, uid, info_ids, context=context):
            if info.catalogue_id and not context.get('product_change', False):
                raise osv.except_osv(_('Error'), _('You cannot remove a supplier information which is linked ' \
                                                   'to a supplier catalogue line ! Please remove the corresponding ' \
                                                   'supplier catalogue line to remove this supplier information.'))
        
        return super(product_supplierinfo, self).unlink(cr, uid, info_ids, context=context)
    
    def search(self, cr, uid, args, offset=0, limit=None, order=None, context=None, count=False):
        if not context:
            context = {}
        
        new_res = [] 
        res = super(product_supplierinfo, self).search(cr, uid, args, offset, limit,
                order, context=context, count=count)
        if count:
            return res
        
        if isinstance(res, (int, long)):
            res = [res]
        
        for r in self.browse(cr, uid, res, context=context):
            if not r.catalogue_id or r.catalogue_id.active:
                new_res.append(r.id)
        
        return new_res
    
    def _get_editable(self, cr, uid, ids, field_name, args, context=None):
        '''
        Return True if no catalogue associated
        '''
        res = {}
        
        for x in self.browse(cr, uid, ids, context=context):
            res[x.id] = True
            if x.catalogue_id:
                res[x.id] = False
        
        return res

    def _get_seller_delay(self, cr, uid, ids, field_name, args, context=None):
        '''
        Returns the supplier lt
        '''
        res = {}
        for price in self.browse(cr, uid, ids, context=context):
            product_id = self.pool.get('product.product').search(cr, uid, [('product_tmpl_id', '=', price.id)])
            product = self.pool.get('product.product').browse(cr, uid, product_id)
            res[price.id] = (price.name and price.name.supplier_lt) or (product_id and int(product[0].procure_delay)) or 1

        return res
    
    _columns = {
        'catalogue_id': fields.many2one('supplier.catalogue', string='Associated catalogue', ondelete='cascade'),
        'editable': fields.function(_get_editable, method=True, string='Editable', store=False, type='boolean'),
        'min_qty': fields.float('Minimal Quantity', required=False, help="The minimal quantity to purchase to this supplier, expressed in the supplier Product UoM if not empty, in the default unit of measure of the product otherwise."),
        'product_uom': fields.related('product_id', 'uom_id', string="Supplier UoM", type='many2one', relation='product.uom',  
                                      help="Choose here the Unit of Measure in which the prices and quantities are expressed below."),
        'delay': fields.function(_get_seller_delay, method=True, type='integer', string='Indicative Delivery LT', help='Lead time in days between the confirmation of the purchase order and the reception of the products in your warehouse. Used by the scheduler for automatic computation of the purchase order planning.'),

    }

    _defaults = {
        'product_uom': lambda *a: False,
    }

    def onchange_supplier(self, cr, uid, ids, supplier_id):
        '''
        Set the Indicative delivery LT
        '''
        v = {}

        if supplier_id:
            supplier = self.pool.get('res.partner').browse(cr, uid, supplier_id)
            v.update({'delay': supplier.supplier_lt})

        return {'value': v}

    
    # Override the original method
    def price_get(self, cr, uid, supplier_ids, product_id, product_qty=1, context=None):
        """
        Calculate price from supplier pricelist.
        @param supplier_ids: Ids of res.partner object.
        @param product_id: Id of product.
        @param product_qty: specify quantity to purchase.
        """
        if type(supplier_ids) in (int,long,):
            supplier_ids = [supplier_ids]
        res = {}
        product_pool = self.pool.get('product.product')
        partner_pool = self.pool.get('res.partner')
        currency_id = context.get('currency_id', False) or self.pool.get('res.users').browse(cr, uid, uid, context=context).company_id.currency_id.id
        date = context.get('date', False) or time.strftime('%Y-%m-%d')
        uom_id = context.get('uom', False) or product_pool.browse(cr, uid, product_id, context=context).uom_id.id
        for supplier in partner_pool.browse(cr, uid, supplier_ids, context=context):
            res[supplier.id] = product_pool._get_partner_price(cr, uid, product_id, supplier.id, product_qty,
                                                                        currency_id, date, uom_id, context=context)
        return res
    
product_supplierinfo()


class pricelist_partnerinfo(osv.osv):
    _name = 'pricelist.partnerinfo'
    _inherit = 'pricelist.partnerinfo'
    
    def default_get(self, cr, uid, fields, context=None):
        '''
        Set automatically the currency of the line with the default
        purchase currency of the supplier, and the uom with the uom of the product.supplierinfo.
        '''
        if not context:
            context = {}
        
        res = super(pricelist_partnerinfo, self).default_get(cr, uid, fields, context=context)
        
        if context.get('partner_id', False) and isinstance(context['partner_id'], (int, long)):
            partner = self.pool.get('res.partner').browse(cr, uid, context.get('partner_id'), context=context)
            res['currency_id'] = partner.property_product_pricelist_purchase.currency_id.id
            res['partner_id'] = partner.id
        if context.get('active_model', False) == 'product.supplierinfo' and context.get('active_id', False) and isinstance(context['active_id'], (int, long)):
            read_partnerinfo = self.pool.get('product.supplierinfo').read(cr, uid, context['active_id'])
            res['uom_id'] = read_partnerinfo['product_uom'][0]
        
        return res
    
    def unlink(self, cr, uid, info_id, context=None):
        '''
        Disallow the possibility to remove a supplier pricelist 
        if it's linked to a catalogue line.
        If 'product_change' is set to True in context, allows the deletion
        because the product on catalogue line has changed and the current line
        should be removed.
        '''
        if context is None:
            context = {}
            
        if isinstance(info_id, (int, long)):
            info_id = [info_id]

        for info in self.browse(cr, uid, info_id, context=context):
            if info.suppinfo_id.catalogue_id and not context.get('product_change', False):
                raise osv.except_osv(_('Error'), _('You cannot remove a supplier pricelist line which is linked ' \
                                                   'to a supplier catalogue line ! Please remove the corresponding ' \
                                                   'supplier catalogue line to remove this supplier information.'))
        
        return super(pricelist_partnerinfo, self).unlink(cr, uid, info_id, context=context)
    
    def search(self, cr, uid, args, offset=0, limit=None, order=None, context=None, count=False):
        if not context:
            context = {}
            
        res = super(pricelist_partnerinfo, self).search(cr, uid, args, offset, limit,
                order, context=context, count=count)

        if count:
            return res
        
        new_res = []
        
        for r in self.browse(cr, uid, res, context=context):
            if not r.suppinfo_id or not r.suppinfo_id.catalogue_id or r.suppinfo_id.catalogue_id.active:
                new_res.append(r.id)
        
        return new_res
    
    def _check_min_quantity(self, cr, uid, ids, context=None):
        '''
        Check if the min_qty field is set
        '''
        if isinstance(ids, (int, long)):
            ids = [ids]

        if context is None:
            context = {}

        if not context.get('noraise'):
            for line in self.browse(cr, uid, ids, context=context):
                if line.min_quantity <= 0.00:
                    raise osv.except_osv(_('Error'), _('The line of product %s has a negative or zero min. quantity !') %line.suppinfo_id.product_id.name)
                    return False
            
        return True

    def _get_supplierinfo(self, cr, uid, ids, context=None):
        if isinstance(ids, (int, long)):
            ids = [ids]
        result = self.pool.get('pricelist.partnerinfo').search(cr, uid, [('suppinfo_id', 'in', ids)], context=context)
        return result

    def _get_sequence(self, cr, uid, ids, field_name, args, context=None):
        res = {}
        for line in self.browse(cr, uid, ids, context=context):
            res[line.id] = False
            if line.suppinfo_id:
                res[line.id] = line.suppinfo_id.sequence
        return res

    _columns = {
        'uom_id': fields.many2one('product.uom', string='UoM', required=True),
        'rounding': fields.float(digits=(16,2), string='SoQ Rounding',
                                 help='The ordered quantity must be a multiple of this rounding value.'),
        'min_order_qty': fields.float(digits=(16, 2), string='Min. Order Qty'),
        'valid_from': fields.date(string='Valid from'),
        'partner_id': fields.related('suppinfo_id', 'name', string='Partner', type='many2one', relation='res.partner'),
        'product_id': fields.related('suppinfo_id', 'product_id', string='Product', type='many2one', relation='product.template'),
        'sequence': fields.function(_get_sequence, method=True, string='Sequence', type='integer',
                                    store={'pricelist.partnerinfo': (lambda self, cr, uid, ids, c={}: ids, [], 20),
                                           'product.supplierinfo': (_get_supplierinfo, ['sequence'], 20),
                                        })
    }

    def create(self, cr, uid, vals, context=None):
        '''
        Check the constraint
        '''
        res = super(pricelist_partnerinfo, self).create(cr, uid, vals, context=context)

        self._check_min_quantity(cr, uid, res, context=context)

        return res

    def write(self, cr, uid, ids, vals, context=None):
        '''
        Check the constraint
        '''
        res = super(pricelist_partnerinfo, self).write(cr, uid, ids, vals, context=context)

        self._check_min_quantity(cr, uid, ids, context=context)

        return res

pricelist_partnerinfo()


class product_product(osv.osv):
    _name = 'product.product'
    _inherit = 'product.product'
    
    def _get_partner_info_price(self, cr, uid, product, partner_id, product_qty, currency_id,
                                          order_date, product_uom_id, context=None):
        '''
        Returns the pricelist_information from product form
        '''
        if not context:
            context = {}
            
        partner_price = self.pool.get('pricelist.partnerinfo')
        info_prices = []
        suppinfo_ids = self.pool.get('product.supplierinfo').search(cr, uid, [('name', '=', partner_id), ('product_id', '=', product.product_tmpl_id.id)], context=context)
        domain = [('min_quantity', '<=', product_qty),
                  ('uom_id', '=', product_uom_id),
                  ('suppinfo_id', 'in', suppinfo_ids),
                  '|', ('valid_from', '<=', order_date),
                  ('valid_from', '=', False),
                  '|', ('valid_till', '>=', order_date),
                  ('valid_till', '=', False)]
        
        domain_cur = [('currency_id', '=', currency_id)]
        domain_cur.extend(domain)
        
        info_prices = partner_price.search(cr, uid, domain_cur, order='sequence asc, min_quantity desc, id desc', limit=1, context=context)
        if not info_prices:
            info_prices = partner_price.search(cr, uid, domain, order='sequence asc, min_quantity desc, id desc', limit=1, context=context)
        
        return info_prices
    
    def _get_partner_price(self, cr, uid, product_ids, partner_id, product_qty, currency_id,
                                          order_date, product_uom_id, context=None):
        '''
        Search the good partner price line for products
        '''
        res = {}
        one_product = False
        cur_obj = self.pool.get('res.currency')
        partner_price = self.pool.get('pricelist.partnerinfo')
        suppinfo_obj = self.pool.get('product.supplierinfo')
        prod_obj = self.pool.get('product.product')
        catalogue_obj = self.pool.get('supplier.catalogue')
        
        if not context:
            context = {}
            
        if isinstance(product_ids, (int, long)):
            one_product = product_ids
            product_ids = [product_ids]
            
        for product in prod_obj.browse(cr, uid, product_ids, context=context):
            info_prices = self._get_partner_info_price(cr, uid, product, partner_id, product_qty, currency_id,
                                                       order_date, product_uom_id, context=context)
                
            if info_prices:
    #            info = partner_price.browse(cr, uid, info_price, context=context)[0]
                info = partner_price.browse(cr, uid, info_prices[0], context=context)
                price = cur_obj.compute(cr, uid, info.currency_id.id, currency_id, info.price, round=False, context=context)
                res[product.id] = (price, info.rounding or 1.00, info.suppinfo_id.min_qty or 0.00) 
            else:
                res[product.id] = (False, 1.0, 1.0)
                        
        return not one_product and res or res[one_product]

    def _get_catalogue_ids(self, cr, uid, ids, field_name, arg, context=None):
        '''
        Returns all catalogues where the product is in
        '''
        # Objects
        line_obj = self.pool.get('supplier.catalogue.line')

        context = context is None and {} or context

        if isinstance(ids, (long, int)):
            ids = [ids]

        res = {}

        for product in self.browse(cr, uid, ids, context=context):
            catalogue_ids = set()
            catalogue_line_ids = line_obj.search(cr, uid, [('product_id', '=', product.id)], context=context)
            for line in line_obj.read(cr, uid, catalogue_line_ids, ['catalogue_id'], context=context):
                catalogue_ids.add(line['catalogue_id'][0])

            res[product.id] = list(catalogue_ids)

        return res
                            
    def _search_catalogue_ids(self, cr, uid, obj, name, args, context=None):
        '''
        Filter the search according to the args parameter
        '''
        # Objects
        catalogue_obj = self.pool.get('supplier.catalogue')

        context = context is None and {} or context
        ids = set()

        for arg in args:
            if arg[0] == 'catalogue_ids' and arg[1] == '=' and arg[2]:
                catalogue = catalogue_obj.browse(cr, uid, int(arg[2]), context=context)
                for line in catalogue.line_ids:
                    ids.add(line.product_id.id)
            elif arg[0] == 'catalogue_ids' and arg[1] == 'in' and arg[2]:
                for catalogue in catalogue_obj.browse(cr, uid, arg[2], context=context):
                    for line in catalogue.line_ids:
                        ids.add(line.product_id.id)
            else:
                return []

        return [('id', 'in', list(ids))]

    _columns = {
        'catalogue_ids': fields.function(_get_catalogue_ids, fnct_search=_search_catalogue_ids,
                                            type='many2many', relation='supplier.catalogue', method=True, string='Catalogues'),
    }
    
product_product()


class product_pricelist(osv.osv):
    _name = 'product.pricelist'
    _inherit = 'product.pricelist'
    
    def _get_in_search(self, cr, uid, ids, field_name, args, context=None):
        res = {}
        
        for id in ids:
            res[id] = True
        
        return res
    
    def _search_in_search(self, cr, uid, obj, name, args, context=None):
        '''
        Returns pricelists according to partner type
        '''
        user_obj = self.pool.get('res.users')
        cur_obj = self.pool.get('res.currency')
        dom = []
        
        for arg in args:
            if arg[0] == 'in_search':
                if arg[1] != '=':
                    raise osv.except_osv(_('Error !'), _('Bad operator !'))
                else:
                    if arg[2] in ('internal', 'intermission'):
                        func_currency_id = user_obj.browse(cr, uid, uid, context=context).company_id.currency_id.id
                        dom.append(('currency_id', '=', func_currency_id))
                    elif arg[2] == 'section':
                        currency_ids = cur_obj.search(cr, uid, [('is_section_currency', '=', True)])
                        dom.append(('currency_id', 'in', currency_ids))
                    elif arg[2] == 'esc':
                        currency_ids = cur_obj.search(cr, uid, [('is_esc_currency', '=', True)])
                        dom.append(('currency_id', 'in', currency_ids))
                        
        return dom
    
    def _get_currency_name(self, cr, uid, ids, field_name, args, context=None):
        '''
        Return the name of the related currency
        '''  
        res = {}
        
        for p_list in self.browse(cr, uid, ids, context=context):
            res[p_list.id] = False
            if p_list.currency_id:
                res[p_list.id] = p_list.currency_id.currency_name
        
        return res
    
    def _search_currency_name(self, cr, uid, obj, name, args, context=None):
        '''
        Return the list corresponding to the currency name
        '''
        dom = []
        
        for arg in args:
            if arg[0] == 'currency_name':
                currency_ids = self.pool.get('res.currency').search(cr, uid, [('currency_name', arg[1], arg[2])], context=context)
                dom.append(('currency_id', 'in', currency_ids))
                
        return dom
        
    
    _columns = {
        'in_search': fields.function(_get_in_search, fnct_search=_search_in_search, method=True,
                                     type='boolean', string='In search'),
        'currency_name': fields.function(_get_currency_name, fnct_search=_search_currency_name, type='char', method=True, string='Currency name'),
    }
    
    def _hook_product_partner_price(self, cr, uid, *args, **kwargs):
        '''
        Rework the computation of price from partner section in product form
        '''
        product_id = kwargs['product_id']
        partner = kwargs['partner']
        qty = kwargs['qty']
        currency_id = kwargs['currency_id']
        date = kwargs['date']
        uom = kwargs['uom']
        context = kwargs['context']
        if not uom and product_id:
            uom = self.pool.get('product.product').browse(cr, uid, product_id, context=context).uom_id.id
        if not partner and 'partner_id' in context:
            partner = context.get('partner_id', False)
        uom_price_already_computed = kwargs['uom_price_already_computed']
        
        price, rounding, min_qty = self.pool.get('product.product')._get_partner_price(cr, uid, product_id, partner, qty, currency_id,
                                                                                       date, uom, context=context)
        uom_price_already_computed = 1
        
        return price, uom_price_already_computed
    
    def name_get(self, cr, user, ids, context=None):
        '''
        Display the currency name instead of the pricelist name
        '''
        result = self.browse(cr, user, ids, context=context)
        res = []
        for pp in result:
            txt = pp.currency_id.name
            res += [(pp.id, txt)]
        return res
    
    def name_search(self, cr, uid, name='', args=None, operator='ilike', context=None, limit=80):
        '''
        Search pricelist by currency name instead of pricelist name
        '''
        ids = []
        if name:
            currency_ids = self.pool.get('res.currency').search(cr, uid,
                    [('name', operator, name)], order='NO_ORDER', context=context)
            ids = self.search(cr, uid, [('currency_id', 'in', currency_ids)] + (args or []))
            
        return self.name_get(cr, uid, ids)          
        
    
product_pricelist()

class res_currency(osv.osv):
    _name = 'res.currency'
    _inherit = 'res.currency'

    def _get_in_search(self, cr, uid, ids, field_name, args, context=None):
        res = {}
        for id in ids:
            res[id] = True
        return res

    def _search_in_search(self, cr, uid, obj, name, args, context=None):
        '''
        Returns currency according to partner type
        '''
        user_obj = self.pool.get('res.users')
        price_obj = self.pool.get('product.pricelist')
        dom = []

        for arg in args:
            if arg[0] == 'is_po_functional':
                if arg[1] != '=':
                    raise osv.except_osv(_('Error !'), _('Bad operator !'))
                else:
                    func_currency_id = user_obj.browse(cr, uid, uid, context=context).company_id.currency_id.id
                    po_currency_id = price_obj.browse(cr, uid, arg[2]).currency_id.id
                    dom.append(('id', 'in', [func_currency_id, po_currency_id]))
        return dom
    
    def _get_partner_currency(self, cr, uid, ids, field_name, args, context=None):
        res = {}
        for id in ids:
            res[id] = True
            
        return res
    
    def _src_partner_currency(self, cr, uid, obj, name, args, context=None):
        '''
        Returns currencies according to partner type
        '''
        user_obj = self.pool.get('res.users')
        dom = []
        
        for arg in args:
            if arg[0] == 'partner_currency':
                if arg[1] != '=':
                    raise osv.except_osv(_('Error !'), _('Bad operator !'))
                elif arg[2]:
                    partner = self.pool.get('res.partner').browse(cr, uid, arg[2], context=context)
                    if partner.partner_type in ('internal', 'intermission'):
                        func_currency_id = user_obj.browse(cr, uid, uid, context=context).company_id.currency_id.id
                        dom.append(('id', '=', func_currency_id))
                    elif partner.partner_type == 'section':
                        dom.append(('is_section_currency', '=', True))
                    elif partner.partner_type == 'esc':
                        dom.append(('is_esc_currency', '=', True))
                        
        return dom

    _columns = {
        'is_section_currency': fields.boolean(string='Functional currency', 
                                        help='If this box is checked, this currency is used as a functional currency for at least one section in MSF.'),
        'is_esc_currency': fields.boolean(string='ESC currency', 
                                        help='If this box is checked, this currency is used as a currency for at least one ESC.'),
        'is_po_functional': fields.function(_get_in_search, fnct_search=_search_in_search, method=True,
                                            type='boolean', string='transport PO currencies'),
        'partner_currency': fields.function(_get_partner_currency, fnct_search=_src_partner_currency, type='boolean', method=True,
                                            string='Partner currency', store=False, help='Only technically to filter currencies according to partner type'),
    }

    def write(self, cr, uid, ids, values, context=None):
        '''
        Disallow the uncheck of section/esc checkbox if a section/esc partner use this currency
        '''
        property_obj = self.pool.get('ir.property')
        partner_obj = self.pool.get('res.partner')
        pricelist_obj = self.pool.get('product.pricelist')

        # Check if Inter-section partners used one of these currencies
        if 'is_section_currency' in values and not values['is_section_currency']:
            pricelist_ids = pricelist_obj.search(cr, uid, [('currency_id',
                'in', ids)], order='NO_ORDER', context=context)
            partner_ids = partner_obj.search(cr, uid, [('partner_type', '=',
                'section')], order='NO_ORDER', context=context)
            value_reference = ['product.pricelist,%s' % x for x in pricelist_ids]
            res_reference = ['res.partner,%s' % x for x in partner_ids]
            property_ids = []
            if value_reference and res_reference:
                property_ids = property_obj.search(cr, uid, [('res_id', 'in', res_reference),
                                                             ('value_reference', 'in', value_reference),
                                                             '|', ('name', '=', 'property_product_pricelist'),
                                                                  ('name', '=', 'property_product_pricelist_purchase'),], context=context)
            if property_ids:
                properties = property_obj.browse(cr, uid, property_ids, context=context)
                partner_list = ' / '.join(x.res_id.name for x in properties)
                raise osv.except_osv(_('Error !'),
                                     _('You cannot uncheck the Section checkbox because this currency is used on these \'Inter-section\' partners : \
                                      %s') % (partner_list,))

        # Check if ESC partners used one of these currencies
        if 'is_esc_currency' in values and not values['is_esc_currency']:
            pricelist_ids = pricelist_obj.search(cr, uid, [('currency_id',
                'in', ids)], order='NO_ORDER', context=context)
            partner_ids = partner_obj.search(cr, uid, [('partner_type', '=',
                'esc')], order='NO_ORDER', context=context)
            value_reference = ['product.pricelist,%s' % x for x in pricelist_ids]
            res_reference = ['res.partner,%s' % x for x in partner_ids]
            property_ids = []
            if value_reference and res_reference:
                property_ids = property_obj.search(cr, uid, [('res_id', 'in', res_reference),
                                                             ('value_reference', 'in', value_reference),
                                                             '|', ('name', '=', 'property_product_pricelist'),
                                                                  ('name', '=', 'property_product_pricelist_purchase'),], context=context)
            if property_ids:
                properties = property_obj.browse(cr, uid, property_ids, context=context)
                partner_list = ' / '.join(x.res_id.name for x in properties)
                raise osv.except_osv(_('Error !'), 
                                     _('You cannot uncheck the ESC checkbox because this currency is used on these \'ESC\' partners : \
                                      %s' % partner_list))

        return super(res_currency, self).write(cr, uid, ids, values, context=context)

res_currency()

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
