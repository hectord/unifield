# -*- coding: utf-8 -*-
##############################################################################
#
#    OpenERP, Open Source Management Solution
#    Copyright (C) Copyright (C) 2011 MSF, TeMPO Consulting.
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

from osv import fields
from osv import osv
from tools.translate import _

from msf_outgoing import INTEGRITY_STATUS_SELECTION

import threading


class stock_incoming_processor(osv.osv):
    """
    Incoming shipment processing wizard
    """
    _name = 'stock.incoming.processor'
    _inherit = 'stock.picking.processor'
    _description = 'Wizard to process an incoming shipment'

    _columns = {
        'move_ids': fields.one2many(
            'stock.move.in.processor',
            'wizard_id',
            string='Moves',
        ),
        'dest_type': fields.selection([
            ('to_cross_docking', 'To Cross Docking'),
            ('to_stock', 'To Stock'),
            ('default', 'Other Types'),
            ],
            string='Destination Type',
            readonly=False,
            required=True,
            help="The default value is the one set on each stock move line.",
        ),
        'source_type': fields.selection([
            ('from_cross_docking', 'From Cross Docking'),
            ('from_stock', 'From stock'),
            ('default', 'Default'),
            ],
            string='Source Type',
            readonly=False,
        ),
        'direct_incoming': fields.boolean(
            string='Direct to Requesting Location',
        ),
        'draft': fields.boolean('Draft'),
        'already_processed': fields.boolean('Already processed'),
    }

    _defaults = {
        'dest_type': 'default',
        'direct_incoming': True,
        'draft': lambda *a: False,
        'already_processed': lambda *a: False,
    }


    # Models methods
    def create(self, cr, uid, vals, context=None):
        """
        Update the dest_type value according to picking
        """
        # Objects
        picking_obj = self.pool.get('stock.picking')
        move_obj = self.pool.get('stock.move')

        if not vals.get('picking_id', False):
            raise osv.except_osv(
                _('Error'),
                _('No picking defined !'),
            )

        picking = picking_obj.browse(cr, uid, vals.get('picking_id'), context=context)

        if not vals.get('dest_type', False):
            cd_move = move_obj.search(cr, uid, [
                ('picking_id', '=', picking.id),
                ('location_dest_id.cross_docking_location_ok', '=', True),
            ], count=True, context=context)
            in_move = move_obj.search(cr, uid, [
                ('picking_id', '=', picking.id),
                ('location_dest_id.input_ok', '=', True),
            ], count=True, context=context)

            if cd_move and in_move:
                vals['dest_type'] = 'default'
            elif not picking.backorder_id:
                if picking.purchase_id and picking.purchase_id.cross_docking_ok:
                    vals['dest_type'] = 'to_cross_docking'
                elif picking.purchase_id:
                    vals['dest_type'] = 'to_stock'
            elif picking.cd_from_bo or (cd_move and not in_move):
                vals['dest_type'] = 'to_cross_docking'
            elif not picking.cd_from_bo or (in_move and not cd_move):
                vals['dest_type'] = 'to_stock'

        if not vals.get('source_type', False):
            vals['source_type'] = 'default'

        return super(stock_incoming_processor, self).create(cr, uid, vals, context=context)

    def do_incoming_shipment(self, cr, uid, ids, context=None):
        """
        Made some integrity check on lines and run the do_incoming_shipment of stock.picking
        """
        # Objects
        in_proc_obj = self.pool.get('stock.move.in.processor')
        picking_obj = self.pool.get('stock.picking')
        data_obj = self.pool.get('ir.model.data')
        wizard_obj = self.pool.get('stock.incoming.processor')

        if context is None:
            context = {}

        if not ids:
            raise osv.except_osv(
                _('Error'),
                _('No wizard found !'),
            )

        # Delete drafts
        wizard_obj.write(cr, uid, ids, {'draft': False}, context=context)

        to_unlink = []

        picking_id = None
        for proc in self.browse(cr, uid, ids, context=context):
            picking_id = proc.picking_id.id
            total_qty = 0.00

            if proc.already_processed:
                raise osv.except_osv(
                    _('Error'),
                    _('You cannot process two times the same IN. Please '\
'return to IN form view and re-try.'),
                )

            self.write(cr, uid, [proc.id], {
                'already_processed': True,
            }, context=context)

            for line in proc.move_ids:
                # If one line as an error, return to wizard
                if line.integrity_status != 'empty':
                    return {
                        'type': 'ir.actions.act_window',
                        'res_model': proc._name,
                        'view_mode': 'form',
                        'view_type': 'form',
                        'res_id': line.wizard_id.id,
                        'target': 'new',
                        'context': context,
                    }

            for line in proc.move_ids:
                # if no quantity, don't process the move
                if not line.quantity:
                    to_unlink.append(line.id)
                    continue

                total_qty += line.quantity

                if line.exp_check \
                   and not line.lot_check \
                   and not line.prodlot_id \
                   and line.expiry_date:
                    if line.type_check == 'in':
                        # US-838: The method has been moved to addons/stock_batch_recall/product_expiry.py
                        prodlot_id = self.pool.get('stock.production.lot')._get_prodlot_from_expiry_date(cr, uid, line.expiry_date, line.product_id.id, context=context)
                        in_proc_obj.write(cr, uid, [line.id], {'prodlot_id': prodlot_id}, context=context)
                    else:
                        # Should not be reached thanks to UI checks
                        raise osv.except_osv(
                            _('Error !'),
                            _('No Batch Number with Expiry Date for Expiry Date Mandatory and not Incoming Shipment should not happen. Please hold...')
                        )

            if not total_qty:
                raise osv.except_osv(
                    _('Processing Error'),
                    _("You have to enter the quantities you want to process before processing the move")
                )

        if to_unlink:
            in_proc_obj.unlink(cr, uid, to_unlink, context=context)

        cr.commit()
        new_thread = threading.Thread(target=picking_obj.do_incoming_shipment_new_cr, args=(cr, uid, ids, context))
        new_thread.start()
        new_thread.join(30.0)

        if new_thread.isAlive():
            view_id = data_obj.get_object_reference(cr, uid, 'delivery_mechanism', 'stock_picking_processing_info_form_view')[1]
            prog_id = picking_obj.update_processing_info(cr, uid, picking_id, prog_id=False, values={}, context=context)

            return {
                'type': 'ir.actions.act_window',
                'res_model': 'stock.picking.processing.info',
                'view_type': 'form',
                'view_mode': 'form',
                'res_id': prog_id,
                'view_id': [view_id],
                'context': context,
                'target': 'new',
            }

        if context.get('from_simu_screen'):
            view_id = data_obj.get_object_reference(cr, uid, 'stock', 'view_picking_in_form')[1]
            return {
                'type': 'ir.actions.act_window',
                'res_model': 'stock.picking',
                'res_id': picking_id,
                'view_id': [view_id],
                'view_mode': 'form, tree',
                'view_type': 'form',
                'target': 'crush',
                'context': context,
            }

        return {'type': 'ir.actions.act_window_close'}

    """
    Controller methods
    """
    def onchange_dest_type(self, cr, uid, ids, dest_type, picking_id=False, context=None):
        """
        Raise a message if the user change a default dest type (cross docking or IN stock).
        @param dest_type: Changed value of dest_type.
        @return: Dictionary of values.
        """
        # Objects
        pick_obj = self.pool.get('stock.picking')
        setup = self.pool.get('unifield.setup.configuration').get_config(cr, uid)

        if context is None:
            context = {}

        if not picking_id:
            return {}

        result = {}

        picking = pick_obj.browse(cr, uid, picking_id, context=context)
        if picking.purchase_id and dest_type != 'to_cross_docking'and picking.purchase_id.cross_docking_ok:
            # display warning
            result['warning'] = {
                'title': _('Error'),
                'message': _('You want to receive the IN into a location which is NOT Cross Docking but "Cross docking" was originally checked. As you are re-routing these products to a different destination, please ensure you cancel any transport document(OUT/PICK etc) if it is no longer needed for the original requesting location.')
            }
        elif picking.purchase_id and dest_type == 'to_cross_docking' and not picking.purchase_id.cross_docking_ok:
            # display warning
            result['warning'] = {
                'title': _('Error'),
                'message': _('You want to receive the IN on Cross Docking but "Cross docking" was not checked.')
            }

        if dest_type == 'to_cross_docking' and setup.allocation_setup == 'unallocated':
            result['value'].update({
                'dest_type': 'default'
            })

            result['warning'] = {'title': _('Error'),
                                 'message': _('The Allocated stocks setup is set to Unallocated.' \
'In this configuration, you cannot made moves from/to Cross-docking locations.')
            }

        return result

    def do_reset(self, cr, uid, ids, context=None):
        incoming_obj = self.pool.get('stock.incoming.processor')
        stock_p_obj = self.pool.get('stock.picking')

        if context is None:
            context = {}
        if isinstance(ids, (int, long)):
            ids = [ids]
        if not ids:
            raise osv.except_osv(
                _('Processing Error'),
                _('No data to process !'),
            )
        incoming_ids = incoming_obj.browse(cr, uid, ids, context=context)
        res_id = []
        for incoming in incoming_ids:
            res_id = incoming['picking_id']['id']
        incoming_obj.write(cr, uid, ids, {'draft': False}, context=context)
        return stock_p_obj.action_process(cr, uid, res_id, context=context)

    def do_save_draft(self, cr, uid, ids, context=None):
        incoming_obj = self.pool.get('stock.incoming.processor')

        if context is None:
            context = {}
        if isinstance(ids, (int, long)):
            ids = [ids]
        if not ids:
            raise osv.except_osv(
             _('Processing Error'),
             _('No data to process !'),
            )
        incoming_obj.write(cr, uid, ids, {'draft': True}, context=context)
        return {}

    def force_process(self, cr, uid, ids, context=None):
        '''
        Go to the processing wizard
        '''
        if context is None:
            context = {}

        if isinstance(ids, (int, long)):
            ids = [ids]

        return {
            'type': 'ir.actions.act_window',
            'res_model': self._name,
            'res_id': ids[0],
            'view_type': 'form',
            'view_mode': 'form',
            'target': 'new',
            'context': context,
        }

    def launch_simulation(self, cr, uid, ids, context=None):
        '''
        Launch the simulation screen
        '''
        if context is None:
            context = {}

        if isinstance(ids, (int, long)):
            ids = [ids]

        if not ids:
            raise osv.except_osv(
                _('Error'),
                _('No picking defined.')
            )

        pick_obj = self.pool.get('stock.picking')
        simu_obj = self.pool.get('wizard.import.in.simulation.screen')
        line_obj = self.pool.get('wizard.import.in.line.simulation.screen')

        for wizard in self.browse(cr, uid, ids, context=context):
            picking_id = wizard.picking_id.id

            simu_id = simu_obj.create(cr, uid, {'picking_id': picking_id, }, context=context)
            for move in pick_obj.browse(cr, uid, picking_id, context=context).move_lines:
                if move.state not in ('draft', 'cancel', 'done'):
                    line_obj.create(cr, uid, {'move_id': move.id,
                                              'simu_id': simu_id,
                                              'move_product_id': move.product_id and move.product_id.id or False,
                                              'move_product_qty': move.product_qty or 0.00,
                                              'move_uom_id': move.product_uom and move.product_uom.id or False,
                                              'move_price_unit': move.price_unit or move.product_id.standard_price,
                                              'move_currency_id': move.price_currency_id and move.price_currency_id.id or False,
                                              'line_number': move.line_number, }, context=context)

        return {'type': 'ir.actions.act_window',
                'res_model': 'wizard.import.in.simulation.screen',
                'view_mode': 'form',
                'view_type': 'form',
                'target': 'same',
                'res_id': simu_id,
                'context': context}

stock_incoming_processor()


class stock_move_in_processor(osv.osv):
    """
    Incoming moves processing wizard
    """
    _name = 'stock.move.in.processor'
    _inherit = 'stock.move.processor'
    _description = 'Wizard lines for incoming shipment processing'

    def _get_move_info(self, cr, uid, ids, field_name, args, context=None):
        return super(stock_move_in_processor, self)._get_move_info(cr, uid, ids, field_name, args, context=context)

    def _get_product_info(self, cr, uid, ids, field_name, args, context=None):
        return super(stock_move_in_processor, self)._get_product_info(cr, uid, ids, field_name, args, context=context)

    def _get_integrity_status(self, cr, uid, ids, field_name, args, context=None):
        return super(stock_move_in_processor, self)._get_integrity_status(cr, uid, ids, field_name, args, context=context)

    def _get_batch_location_ids(self, cr, uid, ids, field_name, args, context=None):
        """
        UFTP-53: specific get stock locations ids for incoming shipment
        in batch numbers:
            - From FO:     CD + Main Stock & children (For example LOG/MED)
            - From non-FO: Main Stock & children (For example LOG/MED)
        """
        res = {}
        if not ids:
            return res
        if isinstance(ids, (int, long)):
            ids = [ids]

        main_stock_id = self.pool.get('ir.model.data').get_object_reference(cr,
            uid, 'stock', 'stock_location_stock')[1]
        cd_id = False

        # get related move ids and map them to ids
        moves_to_ids = {}
        for r in self.read(cr, uid, ids, ['move_id'], context=context,
                name_get=False):
            if r['move_id']:
                moves_to_ids[r['move_id'][0]] = r['id']

        # scan moves' purchase line and check if associated with a SO/FO
        po_obj = self.pool.get('purchase.order')
        sol_obj = self.pool.get('sale.order.line')
        # store the result as most of the time lines have same order_id
        move_purchase_line = self.pool.get('stock.move').read(cr,
                uid,moves_to_ids.keys(), ['purchase_line_id'],
                context=context, name_get=False)
        purchaine_line_list = [x['purchase_line_id'][0] for x in
                move_purchase_line]

        purchase_line_order_id = self.pool.get('purchase.order.line').read(cr,
                uid, purchaine_line_list, ['order_id'], context=context,
                name_get=False)
        purchase_line_order_dict = dict([(x['id'], x['order_id'][0]) for x in
            purchase_line_order_id])

        order_id_set = [x['order_id'][0] for x in purchase_line_order_id]
        order_id_set = list(set(order_id_set))

        order_id_location_dict = {}
        for order_id in order_id_set:
            is_from_fo = False
            location_ids = [main_stock_id] if main_stock_id else []
            sol_ids = po_obj.get_sol_ids_from_po_ids(cr, uid,
                    [order_id], context=context)
            if sol_ids:
                # move associated with a SO, check not with an IR (so is FO)
                is_from_fo = True
                for sol in sol_obj.browse(cr, uid, sol_ids,
                    context=context):
                    if sol.order_id and sol.order_id.procurement_request and sol.order_id.location_requestor_id.usage != 'customer':
                        # from an IR then not from FO
                        is_from_fo = False
                        break

            if is_from_fo:
                if not cd_id:
                    cd_id = self.pool.get('ir.model.data').get_object_reference(
                        cr, uid, 'msf_cross_docking',
                        'stock_location_cross_docking')[1]
                location_ids.append(cd_id)
            order_id_location_dict[order_id] = location_ids

        for elem in move_purchase_line:
            move_id = elem['id']
            purchase_line_id = elem['purchase_line_id'][0]
            order_id = purchase_line_order_dict[purchase_line_id]
            location_ids = order_id_location_dict[order_id]
            res[moves_to_ids[move_id]] = ','.join(map(lambda id: str(id), location_ids))

        # set ids default value for ids with no specific location
        for id in ids:
            if id not in res:
                res[id] = False
        return res

    _columns = {
        # Parent wizard
        'wizard_id': fields.many2one(
            'stock.incoming.processor',
            string='Wizard',
            required=True,
            readonly=True,
            select=True,
            ondelete='cascade',
        ),
        'state': fields.char(size=32, string='State', readonly=True),
        'ordered_product_id': fields.function(
            _get_move_info,
            method=True,
            string='Ordered product',
            type='many2one',
            relation='product.product',
            store={
                'stock.move.in.processor': (lambda self, cr, uid, ids, c=None: ids, ['move_id'], 20),
            },
            readonly=True,
            help="Expected product to receive",
            multi='move_info',
        ),
        'ordered_uom_id': fields.function(
            _get_move_info,
            method=True,
            string='Ordered UoM',
            type='many2one',
            relation='product.uom',
            store={
                'stock.move.in.processor': (lambda self, cr, uid, ids, c=None: ids, ['move_id'], 20),
            },
            readonly=True,
            help="Expected UoM to receive",
            multi='move_info',
        ),
        'ordered_uom_category': fields.function(
            _get_move_info,
            method=True,
            string='Ordered UoM category',
            type='many2one',
            relation='product.uom.categ',
            store={
                'stock.move.in.processor': (lambda self, cr, uid, ids, c=None: ids, ['move_id'], 20),
            },
            readonly=True,
            help="Category of the expected UoM to receive",
            multi='move_info'
        ),
        'location_id': fields.function(
            _get_move_info,
            method=True,
            string='Location',
            type='many2one',
            relation='stock.location',
            store={
                'stock.move.in.processor': (lambda self, cr, uid, ids, c=None: ids, ['move_id'], 20),
            },
            readonly=True,
            help="Source location of the move",
            multi='move_info'
        ),
        'batch_location_ids': fields.function(
            _get_batch_location_ids,
            method=True,
            string='Locations',
            type='char',
            help="Specific locations with batch number",
            invisible=True,
        ),
        'location_supplier_customer_mem_out': fields.function(
            _get_move_info,
            method=True,
            string='Location Supplier Customer',
            type='boolean',
            store={
                'stock.move.in.processor': (lambda self, cr, uid, ids, c=None: ids, ['move_id'], 20),
            },
            readonly=True,
            multi='move_info',
            help="",
        ),
        'integrity_status': fields.function(
            _get_integrity_status,
            method=True,
            string='',
            type='selection',
            selection=INTEGRITY_STATUS_SELECTION,
            store={
                'stock.move.in.processor': (
                    lambda self, cr, uid, ids, c=None: ids,
                    ['product_id', 'wizard_id', 'quantity', 'asset_id', 'prodlot_id', 'expiry_date'],
                    20
                ),
            },
            readonly=True,
            help="Integrity status (e.g: check if a batch is set for a line with a batch mandatory product...)",
        ),
        'type_check': fields.function(
            _get_move_info,
            method=True,
            string='Picking Type Check',
            type='char',
            size=32,
            store={
                'stock.move.in.processor': (lambda self, cr, uid, ids, c=None: ids, ['move_id'], 20),
            },
            readonly=True,
            help="Return the type of the picking",
            multi='move_info',
        ),
        'lot_check': fields.function(
            _get_product_info,
            method=True,
            string='B.Num',
            type='boolean',
            store={
                'stock.move.in.processor': (lambda self, cr, uid, ids, c=None: ids, ['product_id'], 20),
            },
            readonly=True,
            multi='product_info',
            help="A batch number is required on this line",
        ),
        'exp_check': fields.function(
            _get_product_info,
            method=True,
            string='Exp.',
            type='boolean',
            store={
                'stock.move.in.processor': (lambda self, cr, uid, ids, c=None: ids, ['product_id'], 20),
            },
            readonly=True,
            multi='product_info',
            help="An expiry date is required on this line",
        ),
        'asset_check': fields.function(
            _get_product_info,
            method=True,
            string='Asset',
            type='boolean',
            store={
                'stock.move.in.processor': (lambda self, cr, uid, ids, c=None: ids, ['product_id'], 20),
            },
            readonly=True,
            multi='product_info',
            help="An asset is required on this line",
        ),
        'kit_check': fields.function(
            _get_product_info,
            method=True,
            string='Kit',
            type='boolean',
            store={
                'stock.move.in.processor': (lambda self, cr, uid, ids, c=None: ids, ['product_id'], 20),
            },
            readonly=True,
            multi='product_info',
            help="A kit is required on this line",
        ),
        'kc_check': fields.function(
            _get_product_info,
            method=True,
            string='KC',
            type='char',
            size=8,
            store={
                'stock.move.in.processor': (lambda self, cr, uid, ids, c=None: ids, ['product_id'], 20),
            },
            readonly=True,
            multi='product_info',
            help="Ticked if the product is a Heat Sensitive Item",
        ),
        'ssl_check': fields.function(
            _get_product_info,
            method=True,
            string='SSL',
            type='char',
            size=8,
            store={
                'stock.move.in.processor': (lambda self, cr, uid, ids, c=None: ids, ['product_id'], 20),
            },
            readonly=True,
            multi='product_info',
            help="Ticked if the product is a Short Shelf Life product",
        ),
        'dg_check': fields.function(
            _get_product_info,
            method=True,
            string='DG',
            type='char',
            size=8,
            store={
                'stock.move.in.processor': (lambda self, cr, uid, ids, c=None: ids, ['product_id'], 20),
            },
            readonly=True,
            multi='product_info',
            help="Ticked if the product is a Dangerous Good",
        ),
        'np_check': fields.function(
            _get_product_info,
            method=True,
            string='CS',
            type='char',
            size=8,
            store={
                'stock.move.in.processor': (lambda self, cr, uid, ids, c=None: ids, ['product_id'], 20),
            },
            readonly=True,
            multi='product_info',
            help="Ticked if the product is a Controlled Substance",
        ),
    }

    """
    Model methods
    """
    def create(self, cr, uid, vals, context=None):
        """
        Add default values for cost and currency if not set in vals
        """
        # Objects
        product_obj = self.pool.get('product.product')
        user_obj = self.pool.get('res.users')

        if context is None:
            context = {}

        if vals.get('product_id', False):
            if not vals.get('cost', False):
                price = product_obj.browse(cr, uid, vals['product_id'], context=context).standard_price
                vals['cost'] = price
            if not vals.get('currency', False):
                vals['currency'] = user_obj.browse(cr, uid, uid, context=context).company_id.currency_id.id

        return super(stock_move_in_processor, self).create(cr, uid, vals, context=context)

    def _get_line_data(self, cr, uid, wizard=False, move=False, context=None):
        """
        Update the unit price and the currency of the move line wizard if the
        move is attached to a purchase order line
        """
        line_data = super(stock_move_in_processor, self)._get_line_data(cr, uid, wizard, move, context=context)
        if wizard.picking_id.purchase_id and move.purchase_line_id and move.product_id.cost_method == 'average':
            line_data.update({
                'cost': move.purchase_line_id.price_unit,
                'currency': wizard.picking_id.purchase_id.pricelist_id.currency_id.id,
            })

        return line_data

    def open_change_product_wizard(self, cr, uid, ids, context=None):
        """
        Change the locations on which product quantities are computed
        """
        # Objects
        wiz_obj = self.pool.get('change.product.move.processor')

        if isinstance(ids, (int, long)):
            ids = [ids]

        res = super(stock_move_in_processor, self).\
            open_change_product_wizard(cr, uid, ids, context=context)

        wiz_id = res.get('res_id', False)
        if wiz_id:
            in_move = self.browse(cr, uid, ids[0], context=context)
            if in_move.batch_location_ids:
                wiz_obj.write(cr, uid, [wiz_id], {
                    'move_location_ids': in_move.batch_location_ids,
                }, context=context)

        return res

stock_move_in_processor()

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
