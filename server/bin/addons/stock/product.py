# -*- coding: utf-8 -*-
##############################################################################
#
#    OpenERP, Open Source Management Solution
#    Copyright (C) 2004-2010 Tiny SPRL (<http://tiny.be>).
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
from tools.translate import _
import decimal_precision as dp

class product_product(osv.osv):
    _inherit = "product.product"

    def get_product_accounts(self, cr, uid, product_id, context=None):
        """ To get the stock input account, stock output account and stock journal related to product.
        @param product_id: product id
        @return: dictionary which contains information regarding stock input account, stock output account and stock journal
        """
        if context is None:
            context = {}
        product_obj = self.pool.get('product.product').browse(cr, uid, product_id, context=context)

        stock_input_acc = product_obj.property_stock_account_input and product_obj.property_stock_account_input.id or False
        if not stock_input_acc:
            stock_input_acc = product_obj.categ_id.property_stock_account_input_categ and product_obj.categ_id.property_stock_account_input_categ.id or False

        stock_output_acc = product_obj.property_stock_account_output and product_obj.property_stock_account_output.id or False
        if not stock_output_acc:
            stock_output_acc = product_obj.categ_id.property_stock_account_output_categ and product_obj.categ_id.property_stock_account_output_categ.id or False

        journal_id = product_obj.categ_id.property_stock_journal and product_obj.categ_id.property_stock_journal.id or False
        account_variation = product_obj.categ_id.property_stock_variation and product_obj.categ_id.property_stock_variation.id or False

        return {
            'stock_account_input': stock_input_acc,
            'stock_account_output': stock_output_acc,
            'stock_journal': journal_id,
            'property_stock_variation': account_variation
        }

    def do_change_standard_price(self, cr, uid, ids, datas, context=None):
        """ Changes the Standard Price of Product and creates an account move accordingly.
        @param datas : dict. contain default datas like new_price, stock_output_account, stock_input_account, stock_journal
        @param context: A standard dictionary
        @return:

        """
        location_obj = self.pool.get('stock.location')
        move_obj = self.pool.get('account.move')
        move_line_obj = self.pool.get('account.move.line')
        if context is None:
            context = {}

        new_price = datas.get('new_price', 0.0)
        stock_output_acc = datas.get('stock_output_account', False)
        stock_input_acc = datas.get('stock_input_account', False)
        journal_id = datas.get('stock_journal', False)
        product_obj=self.browse(cr, uid, ids, context=context)[0]
        account_variation = product_obj.categ_id.property_stock_variation
        account_variation_id = account_variation and account_variation.id or False
        if not account_variation_id: raise osv.except_osv(_('Error!'), _('Variation Account is not specified for Product Category: %s') % (product_obj.categ_id.name))
        move_ids = []
        loc_ids = location_obj.search(cr, uid,[('usage','=','internal')])
        for rec_id in ids:
            for location in location_obj.browse(cr, uid, loc_ids, context=context):
                c = context.copy()
                c.update({
                    'location': location.id,
                    'compute_child': False
                })

                product = self.browse(cr, uid, rec_id, context=c)
                qty = product.qty_available
                diff = product.standard_price - new_price
                if not diff: raise osv.except_osv(_('Error!'), _("Could not find any difference between standard price and new price!"))
                if qty:
                    company_id = location.company_id and location.company_id.id or False
                    if not company_id: raise osv.except_osv(_('Error!'), _('Company is not specified in Location'))
                    #
                    # Accounting Entries
                    #
                    if not journal_id:
                        journal_id = product.categ_id.property_stock_journal and product.categ_id.property_stock_journal.id or False
                    if not journal_id:
                        raise osv.except_osv(_('Error!'),
                            _('There is no journal defined '\
                                'on the product category: "%s" (id: %d)') % \
                                (product.categ_id.name,
                                    product.categ_id.id,))
                    move_id = move_obj.create(cr, uid, {
                                'journal_id': journal_id,
                                'company_id': company_id
                                })

                    move_ids.append(move_id)


                    if diff > 0:
                        if not stock_input_acc:
                            stock_input_acc = product.product_tmpl_id.\
                                property_stock_account_input.id
                        if not stock_input_acc:
                            stock_input_acc = product.categ_id.\
                                    property_stock_account_input_categ.id
                        if not stock_input_acc:
                            raise osv.except_osv(_('Error!'),
                                    _('There is no stock input account defined ' \
                                            'for this product: "%s" (id: %d)') % \
                                            (product.name,
                                                product.id,))
                        amount_diff = qty * diff
                        move_line_obj.create(cr, uid, {
                                    'name': product.name,
                                    'account_id': stock_input_acc,
                                    'debit': amount_diff,
                                    'move_id': move_id,
                                    })
                        move_line_obj.create(cr, uid, {
                                    'name': product.categ_id.name,
                                    'account_id': account_variation_id,
                                    'credit': amount_diff,
                                    'move_id': move_id
                                    })
                    elif diff < 0:
                        if not stock_output_acc:
                            stock_output_acc = product.product_tmpl_id.\
                                property_stock_account_output.id
                        if not stock_output_acc:
                            stock_output_acc = product.categ_id.\
                                    property_stock_account_output_categ.id
                        if not stock_output_acc:
                            raise osv.except_osv(_('Error!'),
                                    _('There is no stock output account defined ' \
                                            'for this product: "%s" (id: %d)') % \
                                            (product.name,
                                                product.id,))
                        amount_diff = qty * -diff
                        move_line_obj.create(cr, uid, {
                                        'name': product.name,
                                        'account_id': stock_output_acc,
                                        'credit': amount_diff,
                                        'move_id': move_id
                                    })
                        move_line_obj.create(cr, uid, {
                                        'name': product.categ_id.name,
                                        'account_id': account_variation_id,
                                        'debit': amount_diff,
                                        'move_id': move_id
                                    })

            self.write(cr, uid, rec_id, {'standard_price': new_price})

        return move_ids

    def view_header_get(self, cr, user, view_id, view_type, context=None):
        if context is None:
            context = {}
        res = super(product_product, self).view_header_get(cr, user, view_id, view_type, context)
        if res: return res
        if (context.get('active_id', False)) and (context.get('active_model') == 'stock.location'):
            return _('Products: ')+self.pool.get('stock.location').browse(cr, user, context['active_id'], context).name
        return res

    def get_product_available(self, cr, uid, ids, context=None):
        """ Finds whether product is available or not in particular warehouse.
        @return: Dictionary of values
        """
        if context is None:
            context = {}
        states = context.get('states',[])
        what = context.get('what',())
        if not ids:
            ids = self.search(cr, uid, [], order='NO_ORDER')
        res = {}.fromkeys(ids, 0.0)
        if not ids:
            return res

        if not('in' in what or 'out' in what):
            return res

        stock_warehouse_obj = self.pool.get('stock.warehouse')
        stock_location_obj = self.pool.get('stock.location')
        if context.get('shop', False):
            sale_shop_obj = self.pool.get('sale.shop')
            warehouse_id = sale_shop_obj.read(cr, uid, int(context['shop']),
                    ['warehouse_id'], context=context)['warehouse_id']
            if warehouse_id:
                context['warehouse'] = warehouse_id[0]

        if context.get('warehouse', False):
            lot_stock_id = stock_warehouse_obj.read(cr, uid, int(context['warehouse']),
                    ['lot_stock_id'], context=context)['lot_stock_id']
            if lot_stock_id:
                context['location'] = lot_stock_id[0]

        if context.get('location', False):
            if type(context['location']) == type(1):
                location_ids = [context['location']]
            elif type(context['location']) in (type(''), type(u'')):
                location_ids = stock_location_obj.search(cr, uid,
                            [('name','ilike',context['location'])],
                            order='NO_ORDER', context=context)
            else:
                location_ids = context['location']
        else:
            location_ids = []
            wids = stock_warehouse_obj.search(cr, uid, [], order='NO_ORDER', context=context)
            for w in stock_warehouse_obj.read(cr, uid, wids, ['lot_stock_id'], context=context):
                location_ids.append(w['lot_stock_id'][0])

        # build the list of ids of children of the location given by id
        if context.get('compute_child',True):
            child_location_ids = stock_location_obj.search(cr, uid,
                    [('location_id', 'child_of', location_ids)],
                    order='NO_ORDER')
            location_ids = child_location_ids or location_ids

        results = []
        from_date = context.get('from_date',False)
        to_date = context.get('to_date',False)
        date_str = False
        date_values = False
        where = [tuple(location_ids),tuple(location_ids), tuple(location_ids),tuple(location_ids), tuple(ids), tuple(states)]
        if from_date and to_date:
            date_str = "date>=%s AND date<=%s"
            where.append(tuple([from_date]))
            where.append(tuple([to_date]))
        elif from_date:
            date_str = "date>=%s"
            date_values = [from_date]
            where.append(tuple(date_values))
        elif to_date:
            date_str = "date<=%s"
            date_values = [to_date]
            where.append(tuple(date_values))

        prodlot_id = context.get('prodlot_id', False)
        prodlot_id_str = (prodlot_id and (' AND prodlot_id = %s ' % str(prodlot_id)) or '')
        date_str = date_str and ' AND %s '% date_str or ''
        query = """SELECT SUM(product_qty), product_id, product_uom
           FROM stock_move
           WHERE ((location_id NOT IN %%s AND location_dest_id IN %%s) OR
                  (location_id IN %%s AND location_dest_id NOT IN %%s))
                  AND
                  product_id IN %%s
                  %s
                  AND
                  state in %%s
                  %s
           GROUP BY product_id, product_uom""" % (prodlot_id_str, date_str)

        cr.execute(query, tuple(where))
        results = cr.fetchall()
        if results:
            uoms_o = {}
            product2uom = {}
            uom_obj = self.pool.get('product.uom')
            for product in self.read(cr, uid, ids, ['uom_id'], context=context):
                product2uom[product['id']] = product['uom_id'][0]
                if product['uom_id'][0] not in uoms_o:
                    uoms_o[product['uom_id'][0]] = uom_obj.browse(cr, uid, product['uom_id'][0], context=context)
            uoms = map(lambda x: x[2], results)
            if context.get('uom', False):
                uoms += [context['uom']]

            uoms = filter(lambda x: x not in uoms_o.keys(), uoms)
            if uoms:
                uoms = uom_obj.browse(cr, uid, list(set(uoms)), context=context)
                for o in uoms:
                    uoms_o[o.id] = o
            #TOCHECK: before change uom of product, stock move line are in old uom.
            context.update({'raise-exception': False})
            for amount, prod_id, prod_uom in results:
                amount = uom_obj._compute_qty_obj(cr, uid, uoms_o[prod_uom], amount,
                         uoms_o[context.get('uom', False) or product2uom[prod_id]], context=context)
                res[prod_id] += amount
        return res

    def _product_available(self, cr, uid, ids, field_names=None, arg=False, context=None):
        """ Finds the incoming and outgoing quantity of product.
        @return: Dictionary of values
        """
        if not field_names:
            field_names = []
        if context is None:
            context = {}
        res = {}
        for id in ids:
            res[id] = {}.fromkeys(field_names, 0.0)
        for f in field_names:
            c = context.copy()
            if f == 'qty_available':
                c.update({ 'states': ('done',), 'what': ('in', 'out') })
            elif f == 'virtual_available':
                c.update({ 'states': ('confirmed','waiting','assigned','done'), 'what': ('in', 'out') })
            elif f == 'incoming_qty':
                c.update({ 'states': ('confirmed','waiting','assigned'), 'what': ('in',) })
            elif f == 'outgoing_qty':
                c.update({ 'states': ('confirmed','waiting','assigned'), 'what': ('out',) })
            stock = self.get_product_available(cr, uid, ids, context=c)
            if any(stock.values()):
                for id in ids:
                    res[id][f] = stock.get(id, 0.0)
        return res

    _columns = {
        'qty_available': fields.function(_product_available, method=True, type='float', string='Real Stock', help="Current quantities of products in selected locations or all internal if none have been selected.", multi='qty_available', digits_compute=dp.get_precision('Product UoM')),
        'virtual_available': fields.function(_product_available, method=True, type='float', string='Virtual Stock', help="Future stock for this product according to the selected locations or all internal if none have been selected. Computed as: Real Stock - Outgoing + Incoming.", multi='qty_available', digits_compute=dp.get_precision('Product UoM')),
        'incoming_qty': fields.function(_product_available, method=True, type='float', string='Incoming', help="Quantities of products that are planned to arrive in selected locations or all internal if none have been selected.", multi='qty_available', digits_compute=dp.get_precision('Product UoM')),
        'outgoing_qty': fields.function(_product_available, method=True, type='float', string='Outgoing', help="Quantities of products that are planned to leave in selected locations or all internal if none have been selected.", multi='qty_available', digits_compute=dp.get_precision('Product UoM')),
        'track_production': fields.boolean('Track Manufacturing Lots' , help="Forces to specify a Production Lot for all moves containing this product and generated by a Manufacturing Order"),
        'track_incoming': fields.boolean('Track Incoming Lots', help="Forces to specify a Production Lot for all moves containing this product and coming from a Supplier Location"),
        'track_outgoing': fields.boolean('Track Outgoing Lots', help="Forces to specify a Production Lot for all moves containing this product and going to a Customer Location"),
        'location_id': fields.dummy(string='Stock Location', relation='stock.location', type='many2one'),
        'valuation':fields.selection([('manual_periodic', 'Periodical (manual)'),
                                        ('real_time','Real Time (automated)'),], 'Inventory Valuation',
                                        help="If real-time valuation is enabled for a product, the system will automatically write journal entries corresponding to stock moves." \
                                             "The inventory variation account set on the product category will represent the current inventory value, and the stock input and stock output account will hold the counterpart moves for incoming and outgoing products."
                                        , required=True),
    }

    _defaults = {
        'valuation': lambda *a: 'manual_periodic',
    }

    def fields_view_get(self, cr, uid, view_id=None, view_type='form', context=None, toolbar=False, submenu=False):
        res = super(product_product,self).fields_view_get(cr, uid, view_id, view_type, context, toolbar=toolbar, submenu=submenu)
        if context is None:
            context = {}
        if ('location' in context) and context['location'] and type(context['location']) == type(1):
            location_info = self.pool.get('stock.location').read(cr, uid,
                    context['location'], ['usage'])
            fields=res.get('fields',{})
            if fields:
                if location_info['usage'] == 'supplier':
                    if fields.get('virtual_available'):
                        res['fields']['virtual_available']['string'] = _('Future Receptions')
                    if fields.get('qty_available'):
                        res['fields']['qty_available']['string'] = _('Received Qty')

                elif location_info['usage'] == 'internal':
                    if fields.get('virtual_available'):
                        res['fields']['virtual_available']['string'] = _('Future Stock')

                elif location_info['usage'] == 'customer':
                    if fields.get('virtual_available'):
                        res['fields']['virtual_available']['string'] = _('Future Deliveries')
                    if fields.get('qty_available'):
                        res['fields']['qty_available']['string'] = _('Delivered Qty')

                elif location_info['usage'] == 'inventory':
                    if fields.get('virtual_available'):
                        res['fields']['virtual_available']['string'] = _('Future P&L')
                    if fields.get('qty_available'):
                        res['fields']['qty_available']['string'] = _('P&L Qty')

                elif location_info['usage'] == 'procurement':
                    if fields.get('virtual_available'):
                        res['fields']['virtual_available']['string'] = _('Future Qty')
                    if fields.get('qty_available'):
                        res['fields']['qty_available']['string'] = _('Unplanned Qty')

                elif location_info['usage'] == 'production':
                    if fields.get('virtual_available'):
                        res['fields']['virtual_available']['string'] = _('Future Productions')
                    if fields.get('qty_available'):
                        res['fields']['qty_available']['string'] = _('Produced Qty')
        return res

product_product()

class product_template(osv.osv):
    _name = 'product.template'
    _inherit = 'product.template'
    _columns = {
        'property_stock_account_input': fields.many2one(
            'account.account',
            string='Stock Input Account',
            help='When doing real-time inventory valuation, counterpart Journal Items for all incoming stock moves will be posted in this account. If not set on the product, the one from the product category is used.'),
        'property_stock_account_output': fields.many2one(
            'account.account',
            string='Stock Output Account',
            help='When doing real-time inventory valuation, counterpart Journal Items for all outgoing stock moves will be posted in this account. If not set on the product, the one from the product category is used.'),
        'property_stock_procurement': fields.many2one('stock.location',
            string='Procurement Location',
            domain=[('usage','like','procurement')],
            required=True,
            help='For the current product, this stock location will be used, instead of the default on     e, \
as the source location for stock moves generated by procurements'),
        'property_stock_production': fields.many2one('stock.location',
            string='Production Location',
            domain=[('usage','like','production')],
            required=True,
            help='For the current product, this stock location will be used, instead of the default one     , \
as the source location for stock moves generated by production orders'),
        'property_stock_inventory': fields.many2one('stock.location',
            string='Inventory Location',
            domain=[('usage','like','inventory')],
            required=True,
            help='For the current product, this stock location will be used, instead of the default one,      \
as the source location for stock moves generated when you do an inventory'),
    }

    def _get_property_stock(self, cr, uid, location_xml_id, context=None):
        try:
            loc_ids = self.pool.get('ir.model.data').get_object_reference(cr, uid, 'stock', location_xml_id)
        except ValueError:
            return False

        if loc_ids:
            return loc_ids[1]

        return False

    _defaults = {
        'property_stock_procurement': lambda self, cr, uid, c={}: self._get_property_stock(cr, uid, 'location_procurement', context=c),
        'property_stock_production': lambda self, cr, uid, c={}: self._get_property_stock(cr, uid, 'location_production', context=c),
        'property_stock_inventory': lambda self, cr, uid, c={}: self._get_property_stock(cr, uid, 'location_inventory', context=c),
    }

product_template()

class product_category(osv.osv):

    _inherit = 'product.category'
    _columns = {
        'property_stock_journal': fields.property('account.journal',
            relation='account.journal', type='many2one',
            string='Stock journal', method=True, view_load=True,
            help="When doing real-time inventory valuation, this is the Accounting Journal in which entries will be automatically posted when stock moves are processed."),
        'property_stock_account_input_categ': fields.property('account.account',
            type='many2one', relation='account.account',
            string='Stock Input Account', method=True, view_load=True,
            help='When doing real-time inventory valuation, counterpart Journal Items for all incoming stock moves will be posted in this account. This is the default value for all products in this category, it can also directly be set on each product.'),
        'property_stock_account_output_categ': fields.property('account.account',
            type='many2one', relation='account.account',
            string='Stock Output Account', method=True, view_load=True,
            help='When doing real-time inventory valuation, counterpart Journal Items for all outgoing stock moves will be posted in this account. This is the default value for all products in this category, it can also directly be set on each product.'),
        'property_stock_variation': fields.property('account.account',
            type='many2one',
            relation='account.account',
            string="Stock Variation Account",
            method=True, view_load=True,
            help="When real-time inventory valuation is enabled on a product, this account will hold the current value of the products.",),
    }

product_category()

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
