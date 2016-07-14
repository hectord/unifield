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
import time
from os import path

KIT_CREATION_STATE = [('draft', 'Draft'),
                      ('in_production', 'In Production'),
                      ('done', 'Closed'),
                      ('cancel', 'Cancelled'),
                      ]

KIT_TO_CONSUME_AVAILABILITY = [('empty', ''),
                               ('not_available', 'Not Available'),
                               ('partially_available', 'Partially Available'),
                               ('available', 'Available')]

class kit_creation(osv.osv):
    '''
    kit composition class, representing both theoretical composition and actual ones
    '''
    _name = 'kit.creation'
    
    def create_sequence(self, cr, uid, vals, context=None):
        """
        create a new sequence
        """
        seq_pool = self.pool.get('ir.sequence')
        seq_typ_pool = self.pool.get('ir.sequence.type')

        name = 'Kit Creation'
        code = 'kit.creation'

        types = {'name': name,
                 'code': code,
                 }
        seq_typ_pool.create(cr, uid, types)

        seq = {'name': name,
               'code': code,
               'prefix': '',
               'padding': 0,
               }
        return seq_pool.create(cr, uid, seq)
    
    def create(self, cr, uid, vals, context=None):
        '''
        create a new sequence for to consume lines
        '''
        vals.update({'to_consume_sequence_id': self.create_sequence(cr, uid, vals, context=context)})
        return super(kit_creation, self).create(cr, uid, vals, context=context)
    
    def copy(self, cr, uid, id, defaults=None, context=None):
        '''
        avoid copy
        '''
        raise osv.except_osv(_('Warning !'), _('Copy is deactivated for Kitting Order.'))
    
    def action_cancel(self, cr, uid, ids, context=None):
        '''
        cancel the kit_creation
        - cancel the related kit in production
        - cancel the related internal picking (stock moves are canceled at the same time)
        '''
        # Some verifications
        if context is None:
            context = {}
        if isinstance(ids, (int, long)):
            ids = [ids]
        # objects
        wf_service = netsvc.LocalService("workflow")
        move_obj = self.pool.get('stock.move')
        kit_obj = self.pool.get('composition.kit')
        fields_tool_obj = self.pool.get('fields.tools')
        
        for kit in self.browse(cr, uid, ids, context=context):
            # cancel related kits in production
            kit_ids = fields_tool_obj.get_ids_from_browse_list(cr, uid, browse_list=kit.kit_ids_kit_creation, context=context)
            if kit_ids:
                kit_obj.action_cancel(cr, uid, kit_ids, context=dict(context, flag_force_cancel_composition_kit=True))
            # cancel the picking - stock moves are canceled at the same time
            if kit.internal_picking_id_kit_creation:
                picking_id = kit.internal_picking_id_kit_creation.id
                wf_service.trg_validate(uid, 'stock.picking', picking_id, 'button_cancel', cr)

            if kit.consumed_ids_kit_creation:
                 move_ids = [x.id for x in kit.consumed_ids_kit_creation]
                 # we set original_from_process_stock_move to False, so lines can be deleted when canceled
                 move_obj.write(cr, uid, move_ids, {'original_from_process_stock_move': False}, context=context)

        # cancel the kit creation
        self.write(cr, uid, ids, {'state': 'cancel'}, context=context)
        return True
    
    def reset_to_version(self, cr, uid, ids, context=None):
        '''
        open confirmation wizard
        '''
        # data
        name = _("Reset Components to Consume to Version Reference. Are you sure?")
        model = 'confirm'
        step = 'default'
        question = 'The list of items to consume will be reset to reference list from the selected Version. Are you sure ?'
        clazz = 'kit.creation'
        func = 'do_reset_to_version'
        args = [ids]
        kwargs = {}
        # to reset to version
        for obj in self.browse(cr, uid, ids, context=context):
            # state
            if obj.state != 'draft':
                raise osv.except_osv(_('Warning !'), _('Kitting Order must be Draft.'))
            # a version must have been selected
            if not obj.version_id_kit_creation:
                raise osv.except_osv(_('Warning !'), _('The Kitting order is not linked to any version.'))
        
        wiz_obj = self.pool.get('wizard')
        # open the selected wizard
        res = wiz_obj.open_wizard(cr, uid, ids, name=name, model=model, step=step, context=dict(context, question=question,
                                                                                                callback={'clazz': clazz,
                                                                                                          'func': func,
                                                                                                          'args': args,
                                                                                                          'kwargs': kwargs}))
        return res
    
    def do_reset_to_version(self, cr, uid, ids, context=None):
        '''
        remove all items and create one item for each item from the referenced version
        '''
        # objects
        to_consume_obj = self.pool.get('kit.creation.to.consume')
        seq_tools = self.pool.get('sequence.tools')
        # unlink all to consume items corresponding to selected kits
        to_consume_ids = to_consume_obj.search(cr, uid, [('kit_creation_id_to_consume', 'in', ids)], context=context)
        to_consume_obj.unlink(cr, uid, to_consume_ids, context=context)
        for obj in self.browse(cr, uid, ids, context=context):
            # reset the to_consume list sequence
            seq_tools.reset_next_number(cr, uid, obj.to_consume_sequence_id.id, context=context)
            # state
            if obj.state != 'draft':
                raise osv.except_osv(_('Warning !'), _('Kitting Order must be Draft.'))
            # a version must have been selected
            if not obj.version_id_kit_creation:
                raise osv.except_osv(_('Warning !'), _('The Kitting order is not linked to any version.'))
            # copy all items from the version
            for item_v in obj.version_id_kit_creation.composition_item_ids:
                values = {'kit_creation_id_to_consume': obj.id,
                          'module_to_consume': item_v.item_module,
                          'product_id_to_consume': item_v.item_product_id.id,
                          'qty_to_consume': item_v.item_qty,
                          'uom_id_to_consume': item_v.item_uom_id.id,
                          'location_src_id_to_consume': obj.default_location_src_id_kit_creation.id,
                          }
                to_consume_obj.create(cr, uid, values, context=context)
        return True
    
    def dummy_function(self, cr, uid, ids, context=None):
        '''
        dummy function to refresh the screen
        '''
        return True
    
    def _confirm_internal_picking(self, cr, uid, ids, pick_id, context=None):
        '''
        confirm the internal picking
        '''
        # objects
        pick_obj = self.pool.get('stock.picking')
        wf_service = netsvc.LocalService("workflow")
        wf_service.trg_validate(uid, 'stock.picking', pick_id, 'button_confirm', cr)
        return True
    
    def _validate_internal_picking(self, cr, uid, ids, pick_id, context=None):
        '''
        confirm and validate the internal picking
        '''
        # objects
        pick_obj = self.pool.get('stock.picking')
        wf_service = netsvc.LocalService("workflow")
        wf_service.trg_validate(uid, 'stock.picking', pick_id, 'button_confirm', cr)
        # simulate check assign button, as stock move must be available
        pick_obj.force_assign(cr, uid, [pick_id])
        # trigger standard workflow
        pick_obj.action_move(cr, uid, [pick_id])
        wf_service.trg_validate(uid, 'stock.picking', pick_id, 'button_done', cr)
        return True
    
    def _create_picking(self, cr, uid, ids, context=None):
        '''
        create internal picking object
        '''
        # objects
        kit_obj = self.pool.get('composition.kit')
        pick_obj = self.pool.get('stock.picking')
        # we create the internal picking object
        data = self.read(cr, uid, ids, ['name'], context=context)[0]
        kitting_order_name = data['name']
        name = self.pool.get('ir.sequence').get(cr, uid, 'stock.picking.internal')
        data = name.split('/')
        name = data[0] + '/' + 'KIT' + data[1]
        pick_values = {'name': name,
                       'origin': kitting_order_name,
                       'type': 'internal',
                       'state': 'draft',
                       'sale_id': False,
                       'address_id': False,
                       'note': 'Internal Picking corresponding to Kitting Order %s.'%kitting_order_name,
                       'date': context['common']['date'],
                       'company_id': context['common']['company_id'],
                       'reason_type_id': context['common']['reason_type_id'],
                       }
        pick_id = pick_obj.create(cr, uid, pick_values, context=context)
        # log picking creation
        pick_obj.log(cr, uid, pick_id, _('The new internal Picking %s has been created.')%name)
        return pick_id
    
    def _create_kit(self, cr, uid, ids, obj, context=None):
        '''
        create a kit
        - if the product is batch management, we create a new lot
        '''
        # objects
        lot_obj = self.pool.get('stock.production.lot')
        kit_obj = self.pool.get('composition.kit')
        
        batch_management = obj.product_id_kit_creation.batch_management
        lot_ref_name = self.pool.get('ir.sequence').get(cr, uid, 'kit.lot')
        default_date = kit_obj.get_default_expiry_date(cr, uid, ids, context=context)
        if batch_management:
            # we create a new lot
            vals = {'product_id': obj.product_id_kit_creation.id,
                    'name': lot_ref_name,
                    'life_date': default_date, # default value, the kit does not exist yet
                    }
            new_lot_id = lot_obj.create(cr, uid, vals, context=context)
            lot_obj.log(cr, uid, new_lot_id, _('Batch Number %s has been created.')%lot_ref_name)
        
        values = {'composition_type': 'real',
                  'composition_product_id': obj.product_id_kit_creation.id,
                  'composition_version_id': obj.version_id_kit_creation and obj.version_id_kit_creation.id or False,
                  #'composition_creation_date': lambda *a: time.strftime('%Y-%m-%d'),
                  'composition_reference': not batch_management and lot_ref_name or False,
                  'composition_lot_id': batch_management and new_lot_id or False,
                  'composition_ref_exp': not batch_management and default_date or False,
                  'composition_kit_creation_id': obj.id,
                  'state': 'in_production',
                  }
        new_kit_id = kit_obj.create(cr, uid, values, context=context)
        # log kit creation
        kit_obj.log(cr, uid, new_kit_id, _('The new empty Kit Composition List %s has been created.')%lot_ref_name)
        return new_kit_id
    
    def start_production(self, cr, uid, ids, context=None):
        '''
        start production - change the state and create internal picking and corresponding kits
        '''
        # objects
        pick_obj = self.pool.get('stock.picking')
        kit_obj = self.pool.get('composition.kit')
        data_tools_obj = self.pool.get('data.tools')
        # load data into the context
        data_tools_obj.load_common_data(cr, uid, ids, context=context)
        # load the consume lines
        self.do_reset_to_version(cr, uid, ids, context=context)
        for obj in self.browse(cr, uid, ids, context=context):
            # create the internal picking - confirmation of internal picking cannot be performed as long as no stock move exist
            pick_id = self._create_picking(cr, uid, ids, context=context)
            # update the link to picking object and the state
            # change the state
            self.write(cr, uid, ids, {'state': 'in_production',
                                      'internal_picking_id_kit_creation': pick_id}, context=context)
            # create kit in production
            for i in range(obj.qty_kit_creation):
                kit_id = self._create_kit(cr, uid, ids, obj, context=context)
        
        return True
    
    def assert_confirm_kitting(self, cr, uid, ids, context=None):
        '''
        if the returned value evaluates to True (True or text), the confirm kitting cannot be processed
        '''
        # objects
        move_obj = self.pool.get('stock.move')
        
        for obj in self.browse(cr, uid, ids, context=context):
            # all products to consume must have been consumed
            for to_consume in obj.to_consume_ids_kit_creation:
                if not to_consume.consumed_to_consume:
                    return 'All products have not been consumed.'
            # all moves must be done
            move_ids = move_obj.search(cr, uid, [('kit_creation_id_stock_move', '=', obj.id),('state', '!=', 'done')], context=context)
            if move_ids:
                return 'All products consumed are not done.'
            # all moves with perishable/batch management products must have been assigned totally
            for move in obj.consumed_ids_kit_creation:
                if move.product_id.perishable and move.assigned_qty_stock_move != move.product_qty:
                    return 'All Products with Batch Number must be assigned manually to Kits.'
        
        return False
    
    def confirm_kitting(self, cr, uid, ids, context=None):
        '''
        confirm the kitting, assign the production to kits
        '''
        # objects
        item_obj = self.pool.get('composition.item')
        move_obj = self.pool.get('stock.move')
        kit_obj = self.pool.get('composition.kit')
        data_tools_obj = self.pool.get('data.tools')
        # load data into the context
        data_tools_obj.load_common_data(cr, uid, ids, context=context)
        # validation of kitting order
        assertion = self.assert_confirm_kitting(cr, uid, ids, context=context)
        if assertion:
            raise osv.except_osv(_(assertion), _(assertion))
        
        for obj in self.browse(cr, uid, ids, context=context):
            # we copy the notes from kitting order to each kit
            notes = obj.notes_kit_creation
            # assign products to kits TODO modify to many2many to keep stock move traceability?? needed?
            for kit in obj.kit_ids_kit_creation:
                for item in obj.version_id_kit_creation.composition_item_ids:
                    if not item.hidden_perishable_mandatory:
                        item_values = {'item_module': item.item_module,
                                       'item_product_id': item.item_product_id.id,
                                       'item_qty': item.item_qty,
                                       'item_uom_id': item.item_uom_id.id,
                                       'item_lot': False,
                                       'item_exp': False,
                                       'item_kit_id': kit.id,
                                       'item_description': 'Kitting Order',
                                       }
                        item_obj.create(cr, uid, item_values, context=context)
                # create a stock move for the kit, from kitting to location_dest_id_kit_creation
                move_values = {'kit_creation_id_stock_move': False,
                               'to_consume_id_stock_move': False,
                               'name': kit.composition_product_id.name,
                               'picking_id': obj.internal_picking_id_kit_creation.id,
                               'product_id': kit.composition_product_id.id,
                               'date': context['common']['date'],
                               'date_expected': context['common']['date'],
                               'product_qty': 1.0,
                               'product_uom': obj.uom_id_kit_creation.id,
                               'product_uos_qty': 1.0,
                               'product_uos': obj.uom_id_kit_creation.id,
                               'product_packaging': False,
                               'address_id': False,
                               'location_id': context['common']['kitting_id'],
                               'location_dest_id': obj.location_dest_id_kit_creation.id,
                               'sale_line_id': False,
                               'tracking_id': False,
                               'state': 'done',
                               'note': 'Kitting Order - New Kit',
                               'company_id': context['common']['company_id'],
                               'reason_type_id': context['common']['reason_type_id'],
                               'prodlot_id': kit.composition_lot_id.id,
                               }
                new_move_id = move_obj.create(cr, uid, move_values, context=context)
                # for all kit, we compute the expiry date if batch management will update corresponding lot, otherwise corresponding field
                # we need to compute it for each kit, as the distribution of lots across kits is not homogeneous
                expiry_date = kit_obj._compute_expiry_date(cr, uid, [kit.id], context=context)
                kit_values = {'composition_exp': expiry_date}
                # notes depend if notes exist already
                if notes:
                    if kit.composition_description:
                        new_notes = notes + '\n' + kit.composition_description
                    else:
                        new_notes = notes
                    kit_values.update({'composition_description': new_notes})
                # update the kit
                kit_obj.write(cr, uid, [kit.id], kit_values, context=context)
                # all kits are completed
                kit_obj.mark_as_completed(cr, uid, [kit.id], context=context)
            # state of kitting order is Done
            self.write(cr, uid, [obj.id], {'state': 'done'}, context=context)
            self.log(cr, uid, obj.id, _('The Kitting Order %s has been confirmed.')%obj.name)
            # validate the internal picking ticket
            self._validate_internal_picking(cr, uid, ids, obj.internal_picking_id_kit_creation.id, context=context)
        return True
    
    def force_assign2(self, cr, uid, ids, context=None):
        '''
        force assign moves in 'confirmed' (Not Available) state
        
        renamed because two buttons cannot have the same name in the view - force_assign already exist in stock moves
        '''
        # objects
        pick_obj = self.pool.get('stock.picking')
        
        for obj in self.browse(cr, uid, ids, context=context):
            if obj.state != 'in_production':
                raise osv.except_osv(_('Warning !'), _('Kitting Order must be In Production.'))
            return pick_obj.force_assign(cr, uid, [obj.internal_picking_id_kit_creation.id]) #original function does not support context
        
    def cancel_availability_all_lines(self, cr, uid, ids, context=None):
        '''
        cancel availability for moves in 'assigned' (Available) state
        '''
        # objects
        pick_obj = self.pool.get('stock.picking')
        move_obj = self.pool.get('stock.move')
        
        for obj in self.browse(cr, uid, ids, context=context):
            if obj.state != 'in_production':
                raise osv.except_osv(_('Warning !'), _('Kitting Order must be In Production.'))
            # concerned moves
            move_ids = move_obj.search(cr, uid, [('state', '=', 'assigned'), ('kit_creation_id_stock_move', '=', obj.id)], context=context)
            move_obj.write(cr, uid, move_ids, {'state': 'confirmed'}, context=context)
        
        return True
        
    def validate_assign_all_lines(self, cr, uid, ids, context=None):
        '''
        validate all lines in 'assigned' state
        '''
        # objects
        pick_obj = self.pool.get('stock.picking')
        move_obj = self.pool.get('stock.move')
        
        for obj in self.browse(cr, uid, ids, context=context):
            if obj.state != 'in_production':
                raise osv.except_osv(_('Warning !'), _('Kitting Order must be In Production.'))
            for line in obj.consumed_ids_kit_creation:
                move_obj.validate_assign(cr, uid, [line.id], context=context)
        return True
    
    def cancel_all_lines(self, cr, uid, ids, context=None):
        '''
        cancel corresponding stock move which are in state 'confirmed' and 'assigned'
        '''
        # objects
        move_obj = self.pool.get('stock.move')
        # states to take into account
        states = ['confirmed', 'assigned']
        move_ids = move_obj.search(cr, uid, [('state', 'in', states),('kit_creation_id_stock_move', 'in', ids)], context=context)
        move_obj.write(cr, uid, move_ids, {'state': 'cancel'}, context=context)
        return True
    
    def _consolidate_data(self, cr, uid, id, context=None):
        '''
        consolidate data from stock moves which are confirmed
        '''
        obj = self.browse(cr, uid, id, context=context)
        if obj.state != 'in_production':
            raise osv.except_osv(_('Warning !'), _('Kitting Order must be In Production.'))
        # data
        data = {}
        # moves consolidated
        move_list = []
        move_manual = []
        
        for move in obj.consumed_ids_kit_creation:
            # the stock move should not be canceled, but... we recycle them in case.
            if move.state in ['confirmed', 'cancel'] and not move.kol_lot_manual:
                move_list.append(move.id)
                # consolidate the moves qty
                qty = data.setdefault(move.product_id.id, {}).setdefault('uoms', {}).setdefault(move.product_uom.id, {}).setdefault('qty', 0.0)
                # if we get an original move among the consolidated ones, we keep a flag to remember that
                if not data.setdefault(move.product_id.id, {}).setdefault('uoms', {}).setdefault(move.product_uom.id, {}).get('original', False):
                    data.setdefault(move.product_id.id, {}).setdefault('uoms', {}).setdefault(move.product_uom.id, {})['original'] = move.original_from_process_stock_move
                # save the link to to_consume line - well if we get multiple times the same product in the to consume list, we'll get 1 move for both when consolidated
                data.setdefault(move.product_id.id, {}).setdefault('uoms', {}).setdefault(move.product_uom.id, {})['to_consume_id'] = move.to_consume_id_stock_move.id
                qty += move.product_qty
                data.setdefault(move.product_id.id, {}).setdefault('uoms', {})[move.product_uom.id]['qty'] = qty
                # save object for efficiency
                data.setdefault(move.product_id.id, {}).setdefault('object', move.product_id)
            elif move.kol_lot_manual:
                move_manual.append(move.id)
        
        return data, move_list, move_manual
    
    def consolidate_lines(self, cr, uid, ids, context=None):
        '''
        consolidate lines which are 'confirmed' (Not Available) considering product and uom
        '''
        # Some verifications
        if context is None:
            context = {}
        if isinstance(ids, (int, long)):
            ids = [ids]
            
        # objects
        move_obj = self.pool.get('stock.move')
        data_tools_obj = self.pool.get('data.tools')
        # load data into the context
        data_tools_obj.load_common_data(cr, uid, ids, context=context)
        
        for obj in self.browse(cr, uid, ids, context=context):
            # consolidate data
            data, move_list, move_manual = self._consolidate_data(cr, uid, obj.id, context=context)
            # delete stock moves
            move_obj.unlink(cr, uid, move_list, context=dict(context, call_unlink=True))
            # default location
            default_location_id = obj.default_location_src_id_kit_creation.id
            # create consolidated stock moves
            for product_id in data.keys():
                for uom_id in data[product_id]['uoms'].keys():
                    # total qty needed for this product/uom
                    needed_qty = data[product_id]['uoms'][uom_id]['qty']
                    # the consolidated data contains a move which was original
                    original_flag = data[product_id]['uoms'][uom_id].get('original', False)
                    # true for both batch management and not batch management products
                    values = {'kit_creation_id_stock_move': obj.id,
                              'name': data[product_id]['object'].name,
                              'picking_id': obj.internal_picking_id_kit_creation.id,
                              'product_uom': uom_id,
                              'product_id': product_id,
                              'date_expected': context['common']['date'],
                              'date': context['common']['date'],
                              'product_qty': needed_qty,
                              'prodlot_id': False, # the qty is not available
                              'location_id': default_location_id,
                              'location_dest_id': context['common']['kitting_id'],
                              'state': 'confirmed', # not available
                              'reason_type_id': context['common']['reason_type_id'],
                              'to_consume_id_stock_move': data[product_id]['uoms'][uom_id]['to_consume_id'],
                              'original_from_process_stock_move': original_flag,
                              }
                    move_obj.create(cr, uid, values, context=context)
                    # we reset original move flag
                    original_flag = False
        return True
    
    def check_availability(self, cr, uid, ids, context=None):
        '''
        auto selection of location and lots for stock moves
        
        we treat ('confirmed', 'Not Available') moves
        '''
        # Some verifications
        if context is None:
            context = {}
        if isinstance(ids, (int, long)):
            ids = [ids]
            
        # objects
        move_obj = self.pool.get('stock.move')
        loc_obj = self.pool.get('stock.location')
        prodlot_obj = self.pool.get('stock.production.lot')
        data_tools_obj = self.pool.get('data.tools')
        uom_obj = self.pool.get('product.uom')
        # load data into the context
        data_tools_obj.load_common_data(cr, uid, ids, context=context)
        
        for obj in self.browse(cr, uid, ids, context=context):
            # consolidate data
            data, move_list, move_manual = self._consolidate_data(cr, uid, obj.id, context=context)
            # default location
            default_location_id = obj.default_location_src_id_kit_creation.id

            # Check availability of manual moves
            for move in move_obj.browse(cr, uid, move_manual, context=context):
                if move.state != 'confirmed' or not move.prodlot_id:
                    continue

                location_ids = loc_obj.search(cr, uid, [('location_id', 'child_of', move.location_id.id)], context=context)
                needed_qty = move.product_qty
                for loc in location_ids:
                    available_qty = prodlot_obj.browse(cr, uid, move.prodlot_id.id, context=dict(context, location_id=loc)).stock_virtual
                    diff_qty = available_qty - uom_obj._compute_qty(cr, uid, move.product_uom.id, needed_qty, move.product_id.uom_id.id)
                    if diff_qty >= 0:
                        move_obj.write(cr, uid, [move.id], {'state': 'assigned'}, context=context)
                        break
                    else:
                        if available_qty:
                            move_obj.copy(cr, uid, move.id, {'product_qty': available_qty, 'state': 'assigned'}, context=context)
                        needed_qty -= available_qty
                        move_obj.write(cr, uid, [move.id], {'product_qty': needed_qty}, context=context)
                else:
                    move_obj.write(cr, uid, [move.id], {'prodlot_id': False, 'kol_lot_manual': False}, context=context)

            data, move_list, move_manual = self._consolidate_data(cr, uid, obj.id, context=context)
            # delete stock moves
            move_obj.unlink(cr, uid, move_list, context=dict(context, call_unlink=True))

            # create consolidated stock moves
            for product_id in data.keys():
                for uom_id in data[product_id]['uoms'].keys():
                    # we check the availability - we use default location from kitting order object
                    res = loc_obj.compute_availability(cr, uid, [default_location_id], obj.consider_child_locations_kit_creation, product_id, uom_id, context=context)
                    # total qty needed for this product/uom
                    needed_qty = data[product_id]['uoms'][uom_id]['qty']
                    # the consolidated data contains a move which was original
                    original_flag = data[product_id]['uoms'][uom_id].get('original', False)
                    if res['total'] < needed_qty:
                        if res['total'] <= 0:
                            diff_qty = needed_qty
                        else:
                            diff_qty = needed_qty - res['total']
                        needed_qty -= diff_qty
                        # we don't have enough availability, a first move 'confirmed' is created with missing qty
                        # true for both batch management and not batch management products
                        values = {'kit_creation_id_stock_move': obj.id,
                                  'name': data[product_id]['object'].name,
                                  'picking_id': obj.internal_picking_id_kit_creation.id,
                                  'product_uom': uom_id,
                                  'product_id': product_id,
                                  'date_expected': context['common']['date'],
                                  'date': context['common']['date'],
                                  'product_qty': diff_qty,
                                  'prodlot_id': False, # the qty is not available
                                  'location_id': default_location_id,
                                  'location_dest_id': context['common']['kitting_id'],
                                  'state': 'confirmed', # not available
                                  'reason_type_id': context['common']['reason_type_id'],
                                  'to_consume_id_stock_move': data[product_id]['uoms'][uom_id]['to_consume_id'],
                                  'original_from_process_stock_move': original_flag,
                                  }
                        move_obj.create(cr, uid, values, context=context)
                        # we reset original move flag
                        original_flag = False
                                
                    if data[product_id]['object'].perishable: # perishable for perishable or batch management
                        # the product is batch management we use the FEFO list
                        for loc in res['fefo']:
                            # we ignore the batch that are outdated
                            expired_date = prodlot_obj.read(cr, uid, loc['prodlot_id'], ['life_date'], context)['life_date']
                            if datetime.strptime(expired_date, "%Y-%m-%d") < datetime.today():
                                continue
                            # as long all needed are not fulfilled
                            if needed_qty > 0.0:
                                # we treat the available qty from FEFO list corresponding to needed quantity
                                if loc['qty'] > needed_qty:
                                    # we have everything !
                                    selected_qty = needed_qty
                                    needed_qty = 0.0
                                else:
                                    # we take all available
                                    selected_qty = loc['qty']
                                    needed_qty -= selected_qty
                                # stock move values
                                values = {'kit_creation_id_stock_move': obj.id,
                                          'name': data[product_id]['object'].name,
                                          'picking_id': obj.internal_picking_id_kit_creation.id,
                                          'product_uom': uom_id,
                                          'product_id': product_id,
                                          'date_expected': context['common']['date'],
                                          'date': context['common']['date'],
                                          'product_qty': selected_qty,
                                          'prodlot_id': loc['prodlot_id'],
                                          'location_id': loc['location_id'],
                                          'location_dest_id': context['common']['kitting_id'],
                                          'state': 'assigned', # available
                                          'reason_type_id': context['common']['reason_type_id'],
                                          'to_consume_id_stock_move': data[product_id]['uoms'][uom_id]['to_consume_id'],
                                          'original_from_process_stock_move': original_flag,
                                          }
                                move_obj.create(cr, uid, values, context=context)
                                # we reset original move flag
                                original_flag = False
                        if needed_qty:
                            values = {'kit_creation_id_stock_move': obj.id,
                                      'name': data[product_id]['object'].name,
                                      'picking_id': obj.internal_picking_id_kit_creation.id,
                                      'product_uom': uom_id,
                                      'product_id': product_id,
                                      'date_expected': context['common']['date'],
                                      'date': context['common']['date'],
                                      'product_qty': needed_qty,
                                      'prodlot_id': False,
                                      'location_id': loc['location_id'],
                                      'location_dest_id': context['common']['kitting_id'],
                                      'state': 'confirmed', # not available
                                      'reason_type_id': context['common']['reason_type_id'],
                                      'to_consume_id_stock_move': data[product_id]['uoms'][uom_id]['to_consume_id'],
                                      'original_from_process_stock_move': original_flag,
                                      }
                            move_obj.create(cr, uid, values, context=context)
                            # we reset original move flag
                            original_flag = False

                    else:
                        # the product is not batch management, we use locations in id order
                        for loc in sorted(res.keys()):
                            if isinstance(loc, int) and res[loc]['total'] > 0.0:
                                # as long all needed are not fulfilled
                                if needed_qty > 0.0:
                                    # we treat the available qty from locations corresponding to needed quantity
                                    if res[loc]['total'] > needed_qty:
                                        # we have everything !
                                        selected_qty = needed_qty
                                        needed_qty = 0.0
                                    else:
                                        # we take all available
                                        selected_qty = res[loc]['total']
                                        needed_qty -= selected_qty
                                    # stock move values
                                    values = {'kit_creation_id_stock_move': obj.id,
                                              'name': data[product_id]['object'].name,
                                              'picking_id': obj.internal_picking_id_kit_creation.id,
                                              'product_uom': uom_id,
                                              'product_id': product_id,
                                              'date_expected': context['common']['date'],
                                              'date': context['common']['date'],
                                              'product_qty': selected_qty,
                                              'prodlot_id': False, # not batch management
                                              'location_id': loc,
                                              'location_dest_id': context['common']['kitting_id'],
                                              'state': 'assigned',
                                              'reason_type_id': context['common']['reason_type_id'],
                                              'to_consume_id_stock_move': data[product_id]['uoms'][uom_id]['to_consume_id'],
                                              'original_from_process_stock_move': original_flag,
                                              }
                                    move_obj.create(cr, uid, values, context=context)
                                    # we reset original move flag
                                    original_flag = False
        
        return True
        
    def process_to_consume_partial(self, cr, uid, ids, context=None):
        '''
        open wizard for to consume processing
        
        # this must go under refactoring - the wizard also
        - we select a number of kit to be produced
        - the number selected must be present in the to_consume object / not the case now
        - integrity on quantities
        '''
        # Some verifications
        if context is None:
            context = {}
        if isinstance(ids, (int, long)):
            ids = [ids]
        # data
        name = _("Process Components to Consume")
        model = 'process.to.consume'
        step = 'default'
        wiz_obj = self.pool.get('wizard')
        # this purchase order line replacement function can only be used when the po is in state ('confirmed', 'Validated'),
        for obj in self.browse(cr, uid, ids, context=context):
            if obj.state != 'in_production':
                raise osv.except_osv(_('Warning !'), _('Kitting Order must be In Production.'))
            if not len(obj.to_consume_ids_kit_creation):
                raise osv.except_osv(_('Warning !'), _('Components to Consume list is empty.'))
        # open the selected wizard
        res = wiz_obj.open_wizard(cr, uid, ids, name=name, model=model, step=step, context=dict(context))
        return res
    
    def do_process_to_consume2(self, cr, uid, ids, context=None):
        '''
        - update components to consume
        - create a stock move for each line
        
        renamed with do_process_to_consume2 because two button cannot have the same name in the view
        and we have also a do_process_to_consume method at lines to consume level
        '''
        # objects
        to_consume_obj = self.pool.get('kit.creation.to.consume')
        move_obj = self.pool.get('stock.move')
        data_tools_obj = self.pool.get('data.tools')
        # load data into the context
        data_tools_obj.load_common_data(cr, uid, ids, context=context)
        
        for obj in self.browse(cr, uid, ids, context=context):
            # only if in production
            if obj.state != 'in_production':
                raise osv.except_osv(_('Warning !'), _('Kitting Order must be In Production.'))
            if context.get('to_consume_line_id', False):
                # only one line has been selected
                to_consume_list = [to_consume_obj.browse(cr, uid, context.get('to_consume_line_id'), context=context)]
            else:
                # all lines are processed not consumed
                to_consume_list = obj.to_consume_ids_kit_creation
                
            for to_consume in to_consume_list:
                if not to_consume.consumed_to_consume:
                    # create a corresponding stock move
                    move_values = {'kit_creation_id_stock_move': obj.id,
                                   'to_consume_id_stock_move': to_consume.id,
                                   'name': to_consume.product_id_to_consume.name,
                                   'picking_id': obj.internal_picking_id_kit_creation.id,
                                   'product_id': to_consume.product_id_to_consume.id,
                                   'date': context['common']['date'],
                                   'date_expected': context['common']['date'],
                                   'product_qty': to_consume.total_qty_to_consume,
                                   'product_uom': to_consume.uom_id_to_consume.id,
                                   'product_uos_qty': to_consume.total_qty_to_consume,
                                   'product_uos': to_consume.uom_id_to_consume.id,
                                   'product_packaging': False,
                                   'address_id': False,
                                   'location_id': to_consume.location_src_id_to_consume.id,
                                   'location_dest_id': context['common']['kitting_id'],
                                   'sale_line_id': False,
                                   'tracking_id': False,
                                   'state': 'confirmed',
                                   'note': 'Kitting Order - Consume Move',
                                   'company_id': context['common']['company_id'],
                                   'reason_type_id': context['common']['reason_type_id'],
                                   'prodlot_id': False,
                                   'original_from_process_stock_move': True,
                                   }
                    move_id = move_obj.create(cr, uid, move_values, context=context)
                    
            # to_consume lines are consumed
            to_consume_obj.write(cr, uid, [x.id for x in to_consume_list], {'consumed_to_consume': True}, context=context)
            
            # update the view so the new move is displayed in the one2many
            return {'name':_("Kitting Order"),
                    'view_mode': 'form,tree',
                    'view_type': 'form',
                    'res_model': 'kit.creation',
                    'res_id': obj.id,
                    'type': 'ir.actions.act_window',
                    'target': 'crush',
                    }
    
    def on_change_product_id(self, cr, uid, ids, product_id, context=None):
        '''
        on change function
        
        version - qty - uom are set to False
        '''
        result = {'value': {'batch_check_kit_creation': False,
                            'expiry_check_kit_creation': False,
                            'version_id_kit_creation': False,
                            'qty_kit_creation': 1,
                            'uom_id_kit_creation': False}}
        if not product_id:
            # no product, reset values
            result['value'].update({})
        else:
            # we have a product
            product = self.pool.get('product.product').browse(cr, uid, product_id, context=context)
            # set the default uom
            uom_id = product.uom_id.id
            # product, fill default UoM
            result['value'].update({'uom_id_kit_creation': uom_id,
                                    'batch_check_kit_creation': product.batch_management,
                                    'expiry_check_kit_creation': product.perishable})
        
        return result
    
    def _vals_get_kit_creation(self, cr, uid, ids, fields, arg, context=None):
        '''
        multi fields function method
        '''
        # Some verifications
        if context is None:
            context = {}
        if isinstance(ids, (int, long)):
            ids = [ids]
        # objects
        loc_obj = self.pool.get('stock.location')
        
        result = {}
        for obj in self.browse(cr, uid, ids, context=context):
            # batch management
            completed = not self.assert_confirm_kitting(cr, uid, [obj.id], context=context)
            result.setdefault(obj.id, {}).update({'completed_kit_creation': completed})
        return result
    
    _columns = {'name': fields.char(string='Reference', size=1024, required=True),
                'to_consume_sequence_id': fields.many2one('ir.sequence', 'To Consume Sequence', required=True, ondelete='cascade'),
                'creation_date_kit_creation': fields.date(string='Creation Date', required=True),
                'product_id_kit_creation': fields.many2one('product.product', string='Product', required=True, domain=[('type', '=', 'product'), ('subtype', '=', 'kit'), ('has_active_completed_theo_kit_kit', '=', True)]),
                'version_id_kit_creation': fields.many2one('composition.kit', string='Version', domain=[('composition_type', '=', 'theoretical'), ('state', '=', 'completed')], required=True),
                'qty_kit_creation': fields.integer(string='Qty', required=True),
                'uom_id_kit_creation': fields.many2one('product.uom', string='UoM', required=True),
                'notes_kit_creation': fields.text(string='Notes'),
                'default_location_src_id_kit_creation': fields.many2one('stock.location', string='Default Source Location', required=True, domain=[('usage', '=', 'internal')], help='The Kitting Order needs to be saved in order this option to be taken into account.'),
                'consider_child_locations_kit_creation': fields.boolean(string='Consider Child Locations', help='Consider or not child locations for availability check. The Kitting Order needs to be saved in order this option to be taken into account.'),
                'internal_picking_id_kit_creation': fields.many2one('stock.picking', string='Internal Picking', readonly=True),
                'state': fields.selection(KIT_CREATION_STATE, string='State', readonly=True, required=True),
                'to_consume_ids_kit_creation': fields.one2many('kit.creation.to.consume', 'kit_creation_id_to_consume', string='To Consume'),
                'consumed_ids_kit_creation': fields.one2many('stock.move', 'kit_creation_id_stock_move', string='Stock Moves'),
                'kit_ids_kit_creation': fields.one2many('composition.kit', 'composition_kit_creation_id', string='Stock Moves'),
                'location_dest_id_kit_creation': fields.many2one('stock.location', string='Destination Location', required=True, domain=[('usage', '=', 'internal')], help='The Kitting Order needs to be saved in order this option to be taken into account.'),
                # related
                'batch_check_kit_creation': fields.related('product_id_kit_creation', 'batch_management', type='boolean', string='Batch Number Mandatory', readonly=True, store=False),
                # expiry is always true if batch_check is true. we therefore use expry_check for now in the code
                'expiry_check_kit_creation': fields.related('product_id_kit_creation', 'perishable', type='boolean', string='Expiry Date Mandatory', readonly=True, store=False),
                # function
                'completed_kit_creation': fields.function(_vals_get_kit_creation, method=True, type='boolean', string='Kitting Order completed', multi='get_vals_kit_creation', store=False),
                }
    
    _defaults = {'state': 'draft',
                 'name': lambda obj, cr, uid, context: obj.pool.get('ir.sequence').get(cr, uid, 'kit.creation'),
                 'creation_date_kit_creation': lambda *a: time.strftime('%Y-%m-%d'),
#                 'default_location_src_id_kit_creation': lambda obj, cr, uid, c: obj.pool.get('ir.model.data').get_object_reference(cr, uid, 'stock', 'stock_location_stock') and obj.pool.get('ir.model.data').get_object_reference(cr, uid, 'stock', 'stock_location_stock')[1] or False,
#                 'location_dest_id_kit_creation': lambda obj, cr, uid, c: obj.pool.get('ir.model.data').get_object_reference(cr, uid, 'stock', 'stock_location_stock') and obj.pool.get('ir.model.data').get_object_reference(cr, uid, 'stock', 'stock_location_stock')[1] or False,
                 'consider_child_locations_kit_creation': True,
                 'qty_kit_creation': 1,
                 }
    
    _order = 'name desc'
    
    def _kit_creation_constraint(self, cr, uid, ids, context=None):
        '''
        constraint on item composition 
        '''
        # Some verifications
        if context is None:
            context = {}
        if isinstance(ids, (int, long)):
            ids = [ids]
            
        for obj in self.browse(cr, uid, ids, context=context):
            if obj.qty_kit_creation <= 0.0:
                # qty to consume cannot be empty
                raise osv.except_osv(_('Warning !'), _('Number of Kit to produce must be greater than 0.'))
                
        return True
    
    def _uom_constraint(self, cr, uid, ids, context=None):
        for obj in self.browse(cr, uid, ids, context=context):
            if not self.pool.get('uom.tools').check_uom(cr, uid, obj.product_id_kit_creation.id, obj.uom_id_kit_creation.id, context):
                raise osv.except_osv(_('Error'), _('You have to select a product UOM in the same category than the purchase UOM of the product !'))
        return True
    
    _constraints = [(_kit_creation_constraint, 'Constraint error on Kit Creation.', []),
                    (_uom_constraint, 'Constraint error on Uom', [])]

kit_creation()


class composition_kit(osv.osv):
    '''
    kit composition class, representing both theoretical composition and actual ones
    '''
    _inherit = 'composition.kit'
    
    _columns = {'composition_kit_creation_id': fields.many2one('kit.creation', string='Kitting Order', readonly=True)}
    
composition_kit()


class kit_creation_to_consume(osv.osv):
    '''
    common ancestor
    '''
    _name = 'kit.creation.to.consume'
    _rec_name = 'product_id_to_consume'
    
    def create(self, cr, uid, vals, context=None):
        '''
        add the corresponding line number
        '''
        # gather the line number from the sequence
        kit_creation = self.pool.get('kit.creation').browse(cr, uid, vals['kit_creation_id_to_consume'], context)
        sequence = kit_creation.to_consume_sequence_id
        line = sequence.get_id(code_or_id='id', context=context)
        vals.update({'line_number_to_consume': line})
        result = super(kit_creation_to_consume, self).create(cr, uid, vals, context=context)
        return result
    
    def process_to_consume_partial(self, cr, uid, ids, context=None):
        '''
        open wizard for to consume processing
        '''
        # Some verifications
        if context is None:
            context = {}
        if isinstance(ids, (int, long)):
            ids = [ids]
        # objects
        kit_creation_obj = self.pool.get('kit.creation')
        
        for obj in self.browse(cr, uid, ids, context=context):
            if obj.state != 'in_production':
                raise osv.except_osv(_('Warning !'), _('Kitting Order must be In Production.'))
            # inform the wizard we only want one line in it
            context.update({'to_consume_line_id': obj.id})
            # call the kit order method
            return kit_creation_obj.process_to_consume(cr, uid, [obj.kit_creation_id_to_consume.id], context=context)
        
    def do_process_to_consume(self, cr, uid, ids, context=None):
        '''
        process to consume
        '''
        # Some verifications
        if context is None:
            context = {}
        if isinstance(ids, (int, long)):
            ids = [ids]
        # objects
        kit_creation_obj = self.pool.get('kit.creation')
        
        for obj in self.browse(cr, uid, ids, context=context):
            if obj.state != 'in_production':
                raise osv.except_osv(_('Warning !'), _('Kitting Order must be In Production.'))
            # we only want one line in it
            context.update({'to_consume_line_id': obj.id})
            # call the kit order method
            return kit_creation_obj.do_process_to_consume2(cr, uid, [obj.kit_creation_id_to_consume.id], context=context)
    
    def _vals_get(self, cr, uid, ids, fields, arg, context=None):
        '''
        multi fields function method
        '''
        # Some verifications
        if context is None:
            context = {}
        if isinstance(ids, (int, long)):
            ids = [ids]
        # objects
        loc_obj = self.pool.get('stock.location')
        
        result = {}
        for obj in self.browse(cr, uid, ids, context=context):
            # batch management
            result.setdefault(obj.id, {}).update({'batch_check_kit_creation_to_consume': obj.product_id_to_consume.batch_management})
            # perishable
            result.setdefault(obj.id, {}).update({'expiry_check_kit_creation_to_consume': obj.product_id_to_consume.perishable})
            # total_qty
            total_qty = obj.kit_creation_id_to_consume.qty_kit_creation * obj.qty_to_consume
            result.setdefault(obj.id, {}).update({'total_qty_to_consume': total_qty})
            # state
            state = obj.kit_creation_id_to_consume.state
            result.setdefault(obj.id, {}).update({'state': state})
            # fill the fake state attribute - because of openERP bug in attrs, the one2many state field was considered by kitting order attrs, instead of kitting order state
            result.setdefault(obj.id, {}).update({'fake_state': state})
            # qty_available_to_consume
            # corresponding product object
            product = obj.product_id_to_consume
            # uom from product is taken by default if needed
            uom_id = obj.uom_id_to_consume.id
            # compute child
            compute_child = obj.kit_creation_id_to_consume.consider_child_locations_kit_creation
            # we check for the available qty (in:done, out: assigned, done)
            res = loc_obj.compute_availability(cr, uid, [obj.location_src_id_to_consume.id], compute_child, product.id, uom_id, context=context)
            result.setdefault(obj.id, {}).update({'qty_available_to_consume': res['total']})
        return result
    
    def on_change_product_id(self, cr, uid, ids, product_id, default_location_src_id, consider_child_locations, context=None):
        '''
        on change function
        
        version - qty - uom are set to False
        '''
        # Some verifications
        if context is None:
            context = {}
        if isinstance(ids, (int, long)):
            ids = [ids]
        # objects
        loc_obj = self.pool.get('stock.location')
        prod_obj = self.pool.get('product.product')
        
        result = {'value': {'batch_check_kit_creation_to_consume': False,
                            'expiry_check_kit_creation_to_consume': False,
                            'qty_to_consume': 0.0,
                            'total_qty_to_consume': 0.0,
                            'uom_id_to_consume': False,
                            'location_src_id_to_consume': default_location_src_id,
                            }}
        
        if product_id:
            # we have a product
            product = self.pool.get('product.product').browse(cr, uid, product_id, context=context)
            # set the default uom
            uom_id = product.uom_id.id
            # product, fill default UoM
            result['value'].update({'uom_id_to_consume': uom_id,
                                    'batch_check_kit_creation': product.batch_management,
                                    'expiry_check_kit_creation': product.perishable})
        
            if default_location_src_id:
                # we check for the available qty (in:done, out: assigned, done)
                res = loc_obj.compute_availability(cr, uid, [default_location_src_id], consider_child_locations, product_id, uom_id, context=context)
                result.setdefault('value', {}).update({'qty_available_to_consume': res['total']})
        
        return result
    
    def on_change_qty(self, cr, uid, ids, qty, creation_qty, context=None):
        '''
        on change function
        '''
        # Some verifications
        if context is None:
            context = {}
        if isinstance(ids, (int, long)):
            ids = [ids]
            
        result = {}
        result.setdefault('value', {}).update({'total_qty_to_consume': qty * creation_qty})
        
        return result
    
    def on_change_uom_id(self, cr, uid, ids, product_id, default_location_src_id, consider_child_locations, uom_id, location_src_id, context=None):
        '''
        on change function
        '''
        # Some verifications
        if context is None:
            context = {}
        if isinstance(ids, (int, long)):
            ids = [ids]
        # objects
        loc_obj = self.pool.get('stock.location')
        prod_obj = self.pool.get('product.product')
        
        result = {}
        # priority to line location
        location_id = location_src_id or default_location_src_id
        if product_id and location_id:
            # availability flag
            # corresponding product object
            product = prod_obj.browse(cr, uid, product_id, context=context)
            # uom from product is taken by default if needed - priority to selected uom
            uom_id = uom_id or product.uom_id.id
            # we check for the available qty (in:done, out: assigned, done)
            res = loc_obj.compute_availability(cr, uid, [location_id], consider_child_locations, product_id, uom_id, context=context)
            result.setdefault('value', {}).update({'qty_available_to_consume': res['total']})
        
        return result
    
    def _get_to_consume_ids(self, cr, uid, ids, context=None):
        '''
        ids represents the ids of composition.kit objects for which values have changed
        
        return the list of ids of composition.item objects which need to get their fields updated
        
        self is an composition.kit object
        '''
        # Some verifications
        if context is None:
            context = {}
        if isinstance(ids, (int, long)):
            ids = [ids]
            
        to_consume_obj = self.pool.get('kit.creation.to.consume')
        result = to_consume_obj.search(cr, uid, [('kit_creation_id_to_consume', 'in', ids)], context=context)
        return result
    
    _columns = {'kit_creation_id_to_consume': fields.many2one('kit.creation', string="Kitting Order", readonly=True, required=True, on_delete='cascade'),
                'module_to_consume': fields.char(string='Module', size=1024, readonly=True),
                'product_id_to_consume': fields.many2one('product.product', string='Product', readonly=True),
                'qty_to_consume': fields.float(string='Qty per Kit', digits_compute=dp.get_precision('Product UoM'), readonly=True),
                'uom_id_to_consume': fields.many2one('product.uom', string='UoM', readonly=True),
                'location_src_id_to_consume': fields.many2one('stock.location', string='Source Location', required=True, domain=[('usage', '=', 'internal')]),
                'line_number_to_consume': fields.integer(string='Line', required=True, readonly=True),
                'availability_to_consume': fields.selection(KIT_TO_CONSUME_AVAILABILITY, string='Availability', readonly=True, required=True),
                'consumed_to_consume': fields.boolean(string='Consumed', readonly=True),
                'qty_consumed_to_consume': fields.float(string='Consumed Qty', digits_compute=dp.get_precision('Product UoM'), readonly=True),
                # functions
                # state is defined in children classes as the dynamic store does not seem to work properly with _name + _inherit
                'total_qty_to_consume': fields.function(_vals_get, method=True, type='float', string='Qty', multi='get_vals', store=False),
                'qty_available_to_consume': fields.function(_vals_get, method=True, type='float', string='Available Qty', multi='get_vals', store=False),
                'state': fields.function(_vals_get, method=True, type='selection', selection=KIT_CREATION_STATE, string='State', readonly=True, multi='get_vals',
                                         store= {'kit.creation.to.consume': (lambda self, cr, uid, ids, c=None: ids, ['kit_creation_id_to_consume'], 10),
                                                 'kit.creation': (_get_to_consume_ids, ['state'], 10)}),
                'fake_state': fields.function(_vals_get, method=True, type='selection', selection=KIT_CREATION_STATE, string='Fake State', readonly=True, multi='get_vals',
                                         store= {'kit.creation.to.consume': (lambda self, cr, uid, ids, c=None: ids, ['kit_creation_id_to_consume'], 10),
                                                 'kit.creation': (_get_to_consume_ids, ['state'], 10)}),
                'batch_check_kit_creation_to_consume': fields.function(_vals_get, method=True, type='boolean', string='B.Num', multi='get_vals', store=False, readonly=True),
                'expiry_check_kit_creation_to_consume': fields.function(_vals_get, method=True, type='boolean', string='Exp', multi='get_vals', store=False, readonly=True),
                }
    
    _defaults = {'location_src_id_to_consume': lambda obj, cr, uid, c: c.get('location_src_id_to_consume', False),
                 'availability_to_consume': 'empty',
                 'consumed_to_consume': False,
                 'qty_consumed_to_consume': 0.0,
                 }
    _order = 'line_number_to_consume'
    
    def _kit_creation_to_consume_constraint(self, cr, uid, ids, context=None):
        '''
        constraint on item composition 
        '''
        # Some verifications
        if context is None:
            context = {}
        if isinstance(ids, (int, long)):
            ids = [ids]
            
        for obj in self.browse(cr, uid, ids, context=context):
            if obj.qty_to_consume <= 0.0:
                # qty to consume cannot be empty
                raise osv.except_osv(_('Warning !'), _('Quantity to consume must be greater than 0.0.'))
                
        return True
    
    _constraints = [(_kit_creation_to_consume_constraint, 'Constraint error on Kit Creation to Consume.', []),]
    
kit_creation_to_consume()


class stock_move(osv.osv):
    '''
    add link to kit creation
    '''
    _inherit = 'stock.move'
    
    SELECTION = [('draft', 'Draft'),
                 ('waiting', 'Waiting'),
                 ('confirmed', 'Not Available'),
                 ('assigned', 'Available'),
                 ('done', 'Closed'),
                 ('cancel', 'Cancelled'),
                 ]
    
    def _vals_get_kit_creation(self, cr, uid, ids, fields, arg, context=None):
        '''
        multi fields function method
        '''
        # Some verifications
        if context is None:
            context = {}
        if isinstance(ids, (int, long)):
            ids = [ids]
        # objects
        item_obj = self.pool.get('composition.item')
        
        result = {}
        for obj in self.browse(cr, uid, ids, context=context):
            result[obj.id] = {}
            # assigned qty
            assigned_qty = 0.0
            # if the product is perishable (or batch management), we gather assigned qty from kit items

            if obj.product_id.perishable:
                item_ids = item_obj.search(cr, uid, [('item_stock_move_id', '=', obj.id)], context=context)
                if item_ids:
                    data = item_obj.read(cr, uid, item_ids, ['item_qty'], context=context)
                    for value in data:
                        assigned_qty += value['item_qty']
            
            # when the state is assigned or done, the assigned qty is set to product_qty
            elif obj.state in ['assigned', 'done']:
                assigned_qty = obj.product_qty
            result[obj.id].update({'assigned_qty_stock_move': assigned_qty})
            # hidden_state
            result[obj.id].update({'hidden_state': obj.state})
            # hidden_prodlot_id
            result[obj.id].update({'hidden_prodlot_id': obj.lot_check})
            # hidden_exp_check
            result[obj.id].update({'hidden_exp_check': obj.exp_check})
            # hidden_asset_check
            hidden_asset_check = False
            if obj.product_id.type == 'product' and obj.product_id.subtype == 'asset':
                hidden_asset_check = True
            result[obj.id].update({'hidden_asset_check': hidden_asset_check})
            
            hidden_creation_state = False
            hidden_creation_qty_stock_move = 0
            if obj.kit_creation_id_stock_move:
                hidden_creation_state = obj.kit_creation_id_stock_move.state
                hidden_creation_qty_stock_move = obj.kit_creation_id_stock_move.qty_kit_creation
            # hidden_creation_state
            result[obj.id].update({'hidden_creation_state': hidden_creation_state})
            # hidden_creation_qty_stock_move
            result[obj.id].update({'hidden_creation_qty_stock_move': hidden_creation_qty_stock_move})
        return result
    
    _columns = {'kit_creation_id_stock_move': fields.many2one('kit.creation', string='Kit Creation', readonly=True),
                'to_consume_id_stock_move': fields.many2one('kit.creation.to.consume', string='To Consume Line', readonly=True),# link to to consume line - is not deleted anymore ! but colored
                'original_from_process_stock_move': fields.boolean(string='Original', readonly=True),
                # functions
                'hidden_state': fields.function(_vals_get_kit_creation, method=True, type='selection', selection=SELECTION, string='Hidden State', multi='get_vals_kit_creation', store=False, readonly=True),
                'hidden_prodlot_id': fields.function(_vals_get_kit_creation, method=True, type='boolean', string='Hidden Prodlot', multi='get_vals_kit_creation', store=False, readonly=True),
                'hidden_exp_check': fields.function(_vals_get_kit_creation, method=True, type='boolean', string='Hidden Expiry Check', multi='get_vals_kit_creation', store=False, readonly=True),
                'hidden_asset_check': fields.function(_vals_get_kit_creation, method=True, type='boolean', string='Hidden Asset Check', multi='get_vals_kit_creation', store=False, readonly=True),
                'hidden_creation_state': fields.function(_vals_get_kit_creation, method=True, type='selection', selection=KIT_CREATION_STATE, string='Hidden Creation State', multi='get_vals_kit_creation', store=False, readonly=True),
                'assigned_qty_stock_move': fields.function(_vals_get_kit_creation, method=True, type='float', string='Assigned Qty', multi='get_vals_kit_creation', store=False, readonly=True),
                'hidden_creation_qty_stock_move': fields.function(_vals_get_kit_creation, method=True, type='float', string='Hidden Creation Qty', multi='get_vals_kit_creation', store=False, readonly=True),
                'kol_lot_manual': fields.boolean(string='The batch is set manually'),
                }
    
    _defaults = {'to_consume_id_stock_move': False,
                 'original_from_process_stock_move': False,
                 }
    
    def assign_to_kit(self, cr, uid, ids, context=None):
        '''
        open the assign to kit wizard
        '''
        if context is None:
            context = {}
        # data
        name = _("Assign to Kit")
        model = 'assign.to.kit'
        step = 'default'
        wiz_obj = self.pool.get('wizard')
        # open the selected wizard
        res = wiz_obj.open_wizard(cr, uid, ids, name=name, model=model, step=step, context=dict(context))
        return res

    def kol_prodlot_change(self, cr, uid, ids, prodlot_id, context=None):
        '''
        Set a new attribute on stock move if the prodolt is change manually in the Kit order creation
        '''
        if prodlot_id:
            return {'value': {'kol_lot_manual': True}}

        return {'value': {'kol_lot_manual': False}}
    
    def automatic_assignment(self, cr, uid, ids, context=None):
        '''
        automatic assignment of products to generated kits
        
        + a_sum = compute sum of assigned qty
        + left = compute available qty not assigned (available - a_sum)
        + for each line we update assigned qty if needed
          + assigned < required
            + needed = required - assigned
            + needed <= left:
              + assigned = assigned + needed
              + left = left - needed
            + needed > left:
              + assigned = assigned + left
              + left = 0.0
        '''
        # Some verifications
        if context is None:
            context = {}
        if isinstance(ids, (int, long)):
            ids = [ids]
        
        # create corresponding wizard object (containing processing logic)
        res = self.assign_to_kit(cr, uid, ids, context=context)
        # objects
        wiz_obj = self.pool.get(res['res_model'])
        # perform auto assignment
        wiz_obj.automatic_assignment(cr, uid, [res['res_id']], context=res['context'])
        # process the wizard
        return wiz_obj.do_assign_to_kit(cr, uid, [res['res_id']], context=res['context'])
    
    def validate_assign(self, cr, uid, ids, context=None):
        '''
        set the state to done, so the move can be assigned to a kit
        '''
        # Some verifications
        if context is None:
            context = {}
        if isinstance(ids, (int, long)):
            ids = [ids]
        
        kit_creation_id = False
        for move in self.browse(cr, uid, ids, context=context):
            kit_creation_id = move.kit_creation_id_stock_move.id
            if move.state == 'assigned':
                self.write(cr, uid, [move.id], {'state': 'done'}, context=context)
            
            # we assign automatically the lot to the kit only for products perishable at least (perishable and batch management)
            if move.product_id.perishable:
                # openERP bug -> fields.function integer returns a string
                self.automatic_assignment(cr, uid, [move.id], context=context)
                #if move.hidden_creation_qty_stock_move in [1, '1']:
                    # if only one kit, automatic assignement
                #    self.automatic_assignment(cr, uid, [move.id], context=context)
                #else:
                    # multiple kit, we open the assignation wizard
                #    return self.assign_to_kit(cr, uid, ids, context=context)
        
        # refresh the vue so the completed flag is updated and Confirm Kitting button possibly appears
        data_obj = self.pool.get('ir.model.data')
        view_id = False
        try:
            view_id = data_obj.get_object_reference(cr, uid, 'kit', 'view_kit_creation_form')
        except:
            pass
        view_id = view_id and view_id[1] or False
        return {'view_mode': 'form,tree',
                'view_id': [view_id],
                'view_type': 'form',
                'res_model': 'kit.creation',
                'res_id': kit_creation_id,
                'type': 'ir.actions.act_window',
                'target': 'crush',
                }
    
    def check_assign_lot(self, cr, uid, ids, context=None):
        """
        check the assignation of stock move taking into account lot and FEFO rule
        """
        # treated move ids
        done = []
        count = 0
        pickings = {}
        if context is None:
            context = {}
        for move in self.browse(cr, uid, ids, context=context):
            if self._hook_check_assign(cr, uid, move=move):
#            if move.product_id.type == 'consu' or move.location_id.usage == 'supplier':
                if move.state in ('confirmed', 'waiting'):
                    done.append(move.id)
                pickings[move.picking_id.id] = 1
                continue
            if move.state in ('confirmed', 'waiting'):
                # Important: we must pass lock=True to _product_reserve() to avoid race conditions and double reservations
                res = self.pool.get('stock.location')._product_reserve(cr, uid, [move.location_id.id], move.product_id.id, move.product_qty, {'uom': move.product_uom.id}, lock=True)
                if res:
                    #_product_available_test depends on the next status for correct functioning
                    #the test does not work correctly if the same product occurs multiple times
                    #in the same order. This is e.g. the case when using the button 'split in two' of
                    #the stock outgoing form
                    self.write(cr, uid, [move.id], {'state':'assigned'})
                    done.append(move.id)
                    pickings[move.picking_id.id] = 1
                    r = res.pop(0)
                    cr.execute('update stock_move set location_id=%s, product_qty=%s, product_uos_qty=%s where id=%s', (r[1], r[0], r[0] * move.product_id.uos_coeff, move.id))

                    while res:
                        r = res.pop(0)
                        move_id = self.copy(cr, uid, move.id, {'product_qty': r[0],'product_uos_qty': r[0] * move.product_id.uos_coeff,'location_id': r[1]})
                        done.append(move_id)
        if done:
            count += len(done)
            self.write(cr, uid, done, {'state': 'assigned'})

        if count:
            for pick_id in pickings:
                wf_service = netsvc.LocalService("workflow")
                wf_service.trg_write(uid, 'stock.picking', pick_id, cr)
        return count
    
    def unlink(self, cr, uid, ids, context=None):
        '''
        override the function so we prevent deletion of original_from_process_stock_move stock.moves
        '''
        # Some verifications
        if context is None:
            context = {}
        if isinstance(ids, (int, long)):
            ids = [ids]
        
        for move in self.browse(cr, uid, ids, context=context):
            if move.original_from_process_stock_move and not context.get('call_unlink', False):
                raise osv.except_osv(_('Warning !'), _('Original Stock Move cannot be deleted.'))
        
        return super(stock_move, self).unlink(cr, uid, ids, context=context)
    
    def copy_data(self, cr, uid, id, default=None, context=None):
        '''
        reset original_from_process_stock_move
        '''
        if not default:
            default = {}
        default.update({'original_from_process_stock_move': False})
        return super(stock_move, self).copy_data(cr, uid, id, default, context=context)
    
    def split_stock_move(self, cr, uid, ids, context=None):
        '''
        open the wizard to split stock move
        '''
        # we need the context for the wizard switch
        if context is None:
            context = {}
        
        wiz_obj = self.pool.get('wizard')
        # data
        name = _("Split move")
        model = 'split.move'
        step = 'create'
        # open the selected wizard
        return wiz_obj.open_wizard(cr, uid, ids, name=name, model=model, step=step, context=context)
    
stock_move()

