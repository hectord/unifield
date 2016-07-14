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

from osv import osv, fields
from sync_common import xmlid_to_sdref
from lxml import etree

class so_po_common(osv.osv_memory):
    _name = "so.po.common"
    _description = "Common methods for SO - PO"

    # exact copy-pasted from @msf_outgoing/msf_outgoing.py, class stock_picking 
    CENTRAL_PLATFORM= "central_platform"
    REMOTE_WAREHOUSE="remote_warehouse"

    def rw_view_remove_buttons(self, cr, uid, res, view_type, instance_type):
        rw_type = self.pool.get('stock.picking')._get_usb_entity_type(cr, uid)
        if view_type in ['tree','form'] and rw_type == instance_type:
            root = etree.fromstring(res['arch'])
            root.set('hide_new_button', 'True')
            root.set('hide_delete_button', 'True')
            root.set('hide_duplicate_button', 'True')
            res['arch'] = etree.tostring(root)
        return res

    # UTP-952: get the partner type, for the case of intermission and section
    def get_partner_type(self, cr, uid, partner_name, context=None):
        if not context:
            context = {}
        context.update({'active_test': False})
        partner_obj = self.pool.get('res.partner')
        ids = partner_obj.search(cr, uid, [('name', '=', partner_name)], context=context)
        if not ids:
            raise Exception("The partner %s is not found in the system. The operation is thus interrupted." % partner_name)

        return partner_obj.read(cr, uid, ids, ['partner_type'], context=context)[0]['partner_type']

    def get_partner_id(self, cr, uid, partner_name, context=None):
        if not context:
            context = {}
        context.update({'active_test': False})
        ids = self.pool.get('res.partner').search(cr, uid, [('name', '=', partner_name)], context=context)
        if not ids:
            raise Exception("The partner %s is not found in the system. The operation is thus interrupted." % partner_name)
        return ids[0]

    def get_partner_address_id(self, cr, uid, partner_id, context=None):
        if not context:
            context = {}
        context.update({'active_test': False})
        partner = self.pool.get('res.partner').browse(cr, uid, partner_id, context=context)
        if not partner.address:
            raise Exception("The partner address is not found in the system. The operation is thus interrupted.")
        return partner.address[0].id

    def get_price_list_id(self, cr, uid, partner_id, context=None):
        if not context:
            context = {}
        context.update({'active_test': False})
        part = self.pool.get('res.partner').browse(cr, uid, partner_id, context=context)
        return part.property_product_pricelist and part.property_product_pricelist.id or False

    def get_full_original_fo_ref(self, source, original_fo_name):
        '''
        Get the full original name of the FO, prefixed by the source name --> Ex: COORDO_2.12/OC/BI101/PO00018
        In case FO is a split FO, then remove the suffix -x at the end
        '''
        if not original_fo_name:
            raise Exception, "The FO name of in the data is empty --> Cannot retrieve the original PO!"

        if original_fo_name[-2] == '-' and original_fo_name[-1] in ['1', '2', '3']:
            original_fo_name = original_fo_name[:-2] # remove the suffix (-2/-3 at the end)

        ref = source + '.' + original_fo_name
        if not ref:
            raise Exception, "PO reference format/value is invalid! (correct format: instance_name.po_name) " + ref
        return ref

    def get_original_po_id(self, cr, uid, source, so_info, context):
        if not context:
            context = {}
        context.update({'active_test': False})
        po_object = self.pool.get('purchase.order')

        # First, search the original PO via the client_order_ref stored in the FO
        ref = so_info.client_order_ref
        if ref:
            po_split = ref.split('.')
            if len(po_split) != 2:
                raise Exception, "PO reference format/value is invalid! (correct format: instance_name.po_name) " + ref
            po_ids = po_object.search(cr, uid, [('name', '=', po_split[1])], context=context)
        else: # if not found, then retrieve it via the FO Name as reference
            ref = self.get_full_original_fo_ref(source, so_info.name)
            po_ids = po_object.search(cr, uid, [('partner_ref', '=', ref)], context=context)

        if po_ids:
            return po_ids[0]
        return False

    def get_po_id_by_so_ref(self, cr, uid, so_ref, context):
        # Get the Id of the original PO to update these info back
        if not so_ref:
            return False
        if not context:
            context = {}
        context.update({'active_test': False})
        po_ids = self.pool.get('purchase.order').search(cr, uid, [('partner_ref', '=', so_ref)], context=context)
        if po_ids and po_ids[0]:
            return po_ids[0]
        return False

    def get_in_id_from_po_id(self, cr, uid, po_id, context):
        # Get the Id of the original PO to update these info back
        if not po_id:
            return False

        in_ids = self.pool.get('stock.picking').search(cr, uid, [('purchase_id', '=', po_id), ('state', '=', 'assigned')], 0, None, None, context)
        if in_ids:
            return in_ids[0]
        return False

    def get_in_id_by_state(self, cr, uid, po_id, po_ref, states, context):
        # Get the Id of the original PO to update these info back
        if not po_id:
            return False

        in_ids = self.pool.get('stock.picking').search(cr, uid, [('purchase_id', '=', po_id), ('state', 'in', states)], 0, None, 'id asc', context)
        return in_ids[0] if in_ids else False

    # Update the next line number for the FO, PO that have been created by the synchro
    def update_next_line_number_fo_po(self, cr, uid, order_id, fo_po_obj, order_line_object, context):
        sequence_id = fo_po_obj.read(cr, uid, [order_id], ['sequence_id'], context=context)[0]['sequence_id'][0]
        seq_tools = self.pool.get('sequence.tools')

        # Make sure that even if the FO/PO has no line, then the default value is 1
        cr.execute("select max(line_number) from " + order_line_object + " where order_id = " + str(order_id))
        for x in cr.fetchall():
            # For the FO without any line
            val = 1
            if x and x[0]:
                val = int(x[0]) + 1
            seq_tools.reset_next_number(cr, uid, sequence_id, val, context=context)
        return True

    def get_original_so_id(self, cr, uid, so_ref, context):
        # Get the Id of the original PO to update these info back
        if not so_ref:
            return False
        so_split = so_ref.split('.')
        if len(so_split) != 2:
            raise Exception, "The original sub-FO reference format/value is invalid! (correct format: instance_name.so_name) " + so_ref

        if not context:
            context = {}
        context.update({'active_test': False})
        so_ids = self.pool.get('sale.order').search(cr, uid, [('name', '=', so_split[1])], context=context)
        if not so_ids:
            if context.get('restore_flag'): # UF-1830
                return False # If it is a restore case, then just return False, and the system will search for the new replacement FO
            else:
                raise Exception, "The original sub-FO does not exist! " + so_split[1]

        return so_ids[0]

    def retrieve_po_header_data(self, cr, uid, source, header_result, header_info, context):
        if 'notes' in header_info:
            header_result['notes'] = header_info.get('notes')
            header_result['note'] = header_info.get('notes')
        elif 'note' in header_info:
            header_result['notes'] = header_info.get('note')
            header_result['note'] = header_info.get('note')

        if 'origin' in header_info:
            header_result['origin'] = header_info.get('origin')
        if 'order_type' in header_info:
            header_result['order_type'] = header_info.get('order_type')
        if 'priority' in header_info:
            header_result['priority'] = header_info.get('priority')
        if 'categ' in header_info:
            header_result['categ'] = header_info.get('categ')
        if 'loan_duration' in header_info:
            header_result['loan_duration'] = header_info.get('loan_duration')

        if 'details' in header_info:
            header_result['details'] = header_info.get('details')
        if 'delivery_confirmed_date' in header_info:
            header_result['delivery_confirmed_date'] = header_info.get('delivery_confirmed_date')
        if 'est_transport_lead_time' in header_info:
            header_result['est_transport_lead_time'] = header_info.get('est_transport_lead_time')
        if 'transport_type' in header_info:
            header_result['transport_type'] = header_info.get('transport_type')
        if 'ready_to_ship_date' in header_info:
            header_result['ready_to_ship_date'] = header_info.get('ready_to_ship_date')

        # US-830: If the PO is intermission/intersection, don't take the AD from the sync. message
        partner_type = self.get_partner_type(cr, uid, source, context)
        if 'analytic_distribution_id' in header_info and partner_type not in ['section', 'intermission']:
            header_result['analytic_distribution_id'] = self.get_analytic_distribution_id(cr, uid, header_info, context)

        if 'sync_date' in header_info:
            header_result['fo_sync_date'] = header_info.get('sync_date')

        # UF-2267: If the original FO provided, then retrieve the original PO that links to this FO
        if header_info.get('parent_order_name', False):
            # build the complete partner_ref value and search for the linked PO
            parent_order_name = source + "." + header_info.get('parent_order_name')
            po_obj = self.pool.get('purchase.order')

            # search only the original FO ref, not to the split one
            if parent_order_name[-2] == '-':
                parent_order_name = parent_order_name[:-2]
            # retrieve the original PO linked to the original FO
            po_ids = po_obj.search(cr, uid, [('partner_ref', '=', parent_order_name)], context=context)
            if po_ids and po_ids[0]:
                header_result['parent_order_name'] = po_ids[0] # and set the link into the newly created PO sourced

        partner_id = self.get_partner_id(cr, uid, source, context)
        address_id = self.get_partner_address_id(cr, uid, partner_id, context)
        location_id = self.get_location(cr, uid, partner_id, context)
        # just roll back what has been modified --- NO MODIF HERE!
        price_list = self.get_price_list_id(cr, uid, partner_id, context)

        header_result['partner_ref'] = source + "." + header_info.get('name')
        header_result['partner_id'] = partner_id
        header_result['partner_address_id'] = address_id
        header_result['pricelist_id'] = price_list
        header_result['location_id'] = location_id

        return header_result

    def get_xml_id_counterpart(self, cr, uid, object_name, context):
        identifier = context.get('identifier', False)
        if identifier:
            # for example: 'e45a954a-172a-11e4-af61-00259054f102/stock_picking/2_53'
            del context['identifier']
            object_name = object_name._name.replace('.', '_')
            if identifier.find(object_name) > 0:
                pos = identifier.rfind('_')
                return identifier[:pos] # return this: e45a954a-172a-11e4-af61-00259054f102/stock_picking/2
        return False

    def get_analytic_distribution_id(self, cr, uid, data_dict, context):
        # if it has been given in the sync message, then take into account if the value is False by intention,
        # --> be careful when modifying the statement below
        analytic_id = data_dict.get('analytic_distribution_id', False)
        if analytic_id:
            ana_id = self.pool.get('analytic.distribution').find_sd_ref(cr, uid, xmlid_to_sdref(analytic_id['id']), context=context)
            if ana_id:
                return ana_id
            # UTP-1177: If the AD is given but not valid, stop the process of the message and set the message not run 
            raise Exception, "Sorry the given analytic distribution " + analytic_id + " is not available. Cannot proceed this message!"
        return False

    def create_sync_order_label(self, cr, uid, data_dict, context=None):
        sourced_references = data_dict.get('sourced_references') and data_dict['sourced_references'].split(',') or []
        label_ids = []
        for sourced_order in sourced_references:
            label_ids.append((0,0,{'name': sourced_order}))

        return label_ids

    def retrieve_so_header_data(self, cr, uid, source, header_result, header_info, context):
        if 'notes' in header_info:
            header_result['notes'] = header_info.get('notes')
            header_result['note'] = header_info.get('notes')
        elif 'note' in header_info:
            header_result['notes'] = header_info.get('note')
            header_result['note'] = header_info.get('note')

        if 'order_type' in header_info:
            header_result['order_type'] = header_info.get('order_type')
        if 'priority' in header_info:
            header_result['priority'] = header_info.get('priority')
        if 'categ' in header_info:
            header_result['categ'] = header_info.get('categ')
        if 'loan_duration' in header_info:
            header_result['loan_duration'] = header_info.get('loan_duration')

        if 'details' in header_info:
            header_result['details'] = header_info.get('details')
        if 'delivery_requested_date' in header_info:
            header_result['delivery_requested_date'] = header_info.get('delivery_requested_date')
        if 'is_a_counterpart' in header_info:
            header_result['is_a_counterpart'] = header_info.get('is_a_counterpart')

        # UTP-952: only retrieve the AD from the source if the partner type is not intermission or section
        partner_type = self.get_partner_type(cr, uid, source, context)
        if partner_type not in ['section', 'intermission'] and header_info.get('analytic_distribution_id', False):
            header_result['analytic_distribution_id'] = self.get_analytic_distribution_id(cr, uid, header_info, context)

        if 'sourced_references' in header_info:
            header_result['sourced_references'] = self.create_sync_order_label(cr, uid, header_info, context)

        partner_id = self.get_partner_id(cr, uid, source, context)
        address_id = self.get_partner_address_id(cr, uid, partner_id, context)

        price_list = False
        # US-379: Fixed the price list retrieval 
        if 'pricelist_id' in header_info:
            price_list = header_info.get('pricelist_id')
            if price_list:
                price_list = self.pool.get('product.pricelist').find_sd_ref(cr, uid, xmlid_to_sdref(price_list['id']), context=context)

        # at the end, if there is no price list, just use the one from the partner
        if not price_list:
            price_list = self.get_price_list_id(cr, uid, partner_id, context)

        header_result['client_order_ref'] = source + "." + header_info.get('name')
        header_result['partner_id'] = partner_id
        header_result['partner_order_id'] = address_id
        header_result['partner_shipping_id'] = address_id
        header_result['partner_invoice_id'] = address_id
        header_result['pricelist_id'] = price_list

        return header_result

    def get_lines(self, cr, uid, source, line_values, po_id, so_id, for_update, so_called, context):
        line_result = []
        update_lines = []
        rw_type = self.pool.get('stock.picking')._get_usb_entity_type(cr, uid)

        split_cancel_line = {}
        split_bypass_lines = {}
        update_lines_sync_order_ids = []
        line_vals_dict = line_values.to_dict()
        if 'order_line' not in line_vals_dict:
            return []

        for line in line_values.order_line:
            values = {}
            line_dict = line.to_dict()

            if line_dict.get('product_uom'):
                values['product_uom'] = self.get_uom_id(cr, uid, line.product_uom, context=context)

            if line_dict.get('have_analytic_distribution_from_header'):
                values['have_analytic_distribution_from_header'] = line.have_analytic_distribution_from_header

            if line_dict.get('line_number'):
                values['line_number'] = line.line_number

            if line_dict.get('notes'):
                values['notes'] = line.notes

            if line_dict.get('comment'):
                values['comment'] = line.comment

            # UTP-972: send also the flat is line is a split line
            if line_dict.get('is_line_split'):
                values['is_line_split'] = line.is_line_split

            if line_dict.get('product_uom_qty'): # come from the SO
                values['product_qty'] = line.product_uom_qty
                values['product_uom_qty'] = line.product_uom_qty

            if line_dict.get('product_qty'): # come from the PO
                values['product_uom_qty'] = line.product_qty
                values['product_qty'] = line.product_qty

            if line_dict.get('date_planned'):
                values['date_planned'] = line.date_planned

            if line_dict.get('confirmed_delivery_date'):
                values['confirmed_delivery_date'] = line.confirmed_delivery_date

            if line_dict.get('nomenclature_description'):
                values['nomenclature_description'] = line.nomenclature_description

            if line_dict.get('price_unit'):
                values['price_unit'] = line.price_unit
            else:
                values['price_unit'] = 0 # This case is for the line that has price unit False (actually 0 but OpenERP converted to False)

            #US-172: Added the cost_price to IR, for FO line it's not required.
            if line_dict.get('cost_price'):
                values['cost_price'] = line.cost_price

            if line_dict.get('product_id'):
                rec_id = self.pool.get('product.product').find_sd_ref(cr, uid, xmlid_to_sdref(line.product_id.id), context=context)
                if rec_id:
                    values['product_id'] = rec_id
                    values['name'] = line.product_id.name

                    product_obj = self.pool.get('product.product')
                    product = product_obj.browse(cr, uid, [rec_id], context=context)[0]
                    procure_method = product.procure_method
                    # UF-1534: use the cost price of the product, not the one from PO line
                    # US-27: the request above is not applicable for RemoteWarehouse instance! so do not change the price!
                    if so_called and not so_id and rw_type != self.pool.get('stock.picking').REMOTE_WAREHOUSE:
                        values['price_unit'] = product.list_price

                    values['type'] = procure_method
                else:
                    values['name'] = line.comment
            else:
                values['name'] = line.comment

            if line_dict.get('procurement_id'): # replicating procurement for RW instance
                rec_id = self.pool.get('procurement.order').find_sd_ref(cr, uid, xmlid_to_sdref(line.procurement_id.id), context=context)
                if rec_id:
                    values['procurement_id'] = rec_id

            if line_dict.get('nomen_manda_0'):
                rec_id = self.pool.get('product.nomenclature').find_sd_ref(cr, uid, xmlid_to_sdref(line.nomen_manda_0.id), context=context)
                if rec_id:
                    values['nomen_manda_0'] = rec_id

            if line_dict.get('nomen_manda_1'):
                rec_id = self.pool.get('product.nomenclature').find_sd_ref(cr, uid, xmlid_to_sdref(line.nomen_manda_1.id), context=context)
                if rec_id:
                    values['nomen_manda_1'] = rec_id

            if line_dict.get('nomen_manda_2'):
                rec_id = self.pool.get('product.nomenclature').find_sd_ref(cr, uid, xmlid_to_sdref(line.nomen_manda_2.id), context=context)
                if rec_id:
                    values['nomen_manda_2'] = rec_id

            if line_dict.get('nomen_manda_3'):
                rec_id = self.pool.get('product.nomenclature').find_sd_ref(cr, uid, xmlid_to_sdref(line.nomen_manda_3.id), context=context)
                if rec_id:
                    values['nomen_manda_3'] = rec_id
    
            if line_dict.get('sync_sourced_origin'):
                values['origin'] = line_dict.get('sync_sourced_origin')
                so_ids = self.pool.get('sale.order').search(cr, uid, [('name', '=', values['origin']), ('state', 'in', ('sourced', 'progress', 'manual')), ('procurement_request', 'in', ('t', 'f'))], context=context)
                if so_ids:
                    values['link_so_id'] = so_ids[0]

            if line_dict.get('cancel_split_ok'):
                if line_dict.get('line_number'):
                    split_cancel_line.setdefault(line_dict.get('line_number'), [])
                    split_cancel_line[line_dict.get('line_number')].append(line_dict.get('cancel_split_ok'))

            if line_dict.get('id'): # Only used for Remote Warehouse when creating a new order line, this xmlid will be used and not the local one 
                values['rw_xmlid'] = line.id.replace('sd.','')

            # UTP-952: set empty AD for lines if the partner is intermission or section
            partner_type = self.get_partner_type(cr, uid, source, context)
            if partner_type not in ['section', 'intermission'] and line_dict.get('analytic_distribution_id'):
                values['analytic_distribution_id'] = self.get_analytic_distribution_id(cr, uid, line_dict, context)

            if line_dict.get('source_sync_line_id'):
                values['original_purchase_line_id'] = line_dict['source_sync_line_id']

            line_ids = False
            sync_order_line_db_id = False
            if line_dict.get('sync_order_line_db_id'):
                sync_order_line_db_id = line.sync_order_line_db_id
                values['sync_order_line_db_id'] = sync_order_line_db_id

                line_ids = self.pool.get('purchase.order.line').search(cr, uid, [('sync_order_line_db_id', '=', sync_order_line_db_id), ('order_id', '=', po_id)], context=context)
                lines_to_split = self.pool.get('purchase.order.line.to.split').search(cr, uid, [('new_sync_order_line_db_id', '=', sync_order_line_db_id), ('splitted', '=', False)], context=context)
                if lines_to_split and not line_ids:
#                if self.pool.get('purchase.order.line.to.split').search(cr, uid, [('new_sync_order_line_db_id', '=', sync_order_line_db_id)], context=context):
                    split_bypass_lines.setdefault(sync_order_line_db_id, [])
                    split_bypass_lines[sync_order_line_db_id].append((lines_to_split, values))
                    continue

            if (po_id or so_id) and not sync_order_line_db_id: # this updates the PO or SO -> the sync_order_line_db_id must exist
                raise Exception, "The field sync_order_line_db_id is missing - please check the relevant message rule!"
            if not po_id and line_dict.get('cancel_split_ok'):
                continue

            if po_id: # this case is for update the PO
                # look for the correct PO line for updating the value - corresponding to the SO line
                if not line_ids:
                    line_ids = self.pool.get('purchase.order.line').search(cr, uid, [('sync_order_line_db_id', '=', sync_order_line_db_id), ('order_id', '=', po_id)], context=context)

                """# Split PO lines that are canceled at other side
                if line_dict.get('cancel_split_ok') and line_ids:
                    pol = self.pool.get('purchase.order.line').read(cr, uid, line_ids[0], ['line_number', 'product_qty'], context=context)
                    pol_qty = pol['product_qty']

                    for sp in split_cancel_line.get(pol['line_number'], []):
                        if sp == pol_qty:
                            continue
                        split_obj = self.pool.get('split.purchase.order.line.wizard')
                        split_id = split_obj.create(cr, uid, {
                            'purchase_line_id': line_ids[0],
                            'original_qty': pol_qty,
                            'old_line_qty': pol_qty - sp,
                            'new_line_qty': sp,
                        }, context=context)
                        split_obj.split_line(cr, uid, [split_id], context=context)
                        pol_qty -= sp

                    if pol_qty == pol['product_qty']:
                        continue
                """

            elif so_id:
                # look for the correct PO line for updating the value - corresponding to the SO line
                line_ids = self.pool.get('sale.order.line').search(cr, uid, [('sync_order_line_db_id', '=', sync_order_line_db_id), ('order_id', '=', so_id)], context=context)
            
            if line_ids and line_ids[0]:
                if for_update: # add this value to the list of update, then remove
                    update_lines.append(line_ids[0])

                update_lines_sync_order_ids.append(values['sync_order_line_db_id'])
                line_result.append((1, line_ids[0], values))
            else:
                update_lines_sync_order_ids.append(values['sync_order_line_db_id'])
                line_result.append((0, 0, values))

        for sync_order_line_db_id, line_values in split_bypass_lines.iteritems():
            for line_vals in line_values:
                for polts in self.pool.get('purchase.order.line.to.split').browse(cr, uid, line_vals[0], context=context):
                    if polts.sync_order_line_db_id not in update_lines_sync_order_ids:
                        line_result.append((0, 0, line_vals[1]))

        # for update case, then check all updated lines, the other lines that are not presented in the sync message must be deleted at this destination instance!
        if for_update:
            existing_line_ids = False
            if po_id: # this case is for update the PO
                # look for the correct PO line for updating the value - corresponding to the SO line
                existing_line_ids = self.pool.get('purchase.order.line').search(cr, uid, [('order_id', '=', po_id),], context=context)
            elif so_id:
                # look for the correct PO line for updating the value - corresponding to the SO line
                existing_line_ids = self.pool.get('sale.order.line').search(cr, uid, [('order_id', '=', so_id)], context=context)

            if (existing_line_ids and update_lines) or (line_vals_dict.get('state', False) == 'done' and existing_line_ids):
                for existing_line in existing_line_ids:
                    if existing_line not in update_lines:
                        if po_id:
                            self.pool.get('purchase.order.line').fake_unlink(cr, uid, [existing_line], context=context)
                            #UFTP-242: Log if there is lines deleted for this PO
                            context.update({'deleted_line_po_id': po_id})
                        elif so_id:
                            self.pool.get('sale.order.line').ask_order_unlink(cr, uid, [existing_line], context=context)
                            #UFTP-242: Log if there is lines deleted for this SO
                            context.update({'deleted_line_so_id': so_id})
                        else:
                            line_result.append((2, existing_line))
        
        return line_result 


    def create_rw_xml_for_line(self, cr, uid, line_obj, line, context):
        '''
        UF-2377: This method is to add the xmlid of the order line from CP in RW with res_id at RW
        It is used for the OUT that linked to an IN when the IN got processed, stock moves will be transfered directly to OUT via
        procurement, retrieved from the order line
        '''
        line_id = line_obj.create(cr, uid, line, context=context)
        rw_xmlid = line.get('rw_xmlid', False)
        self.pool.get('ir.model.data').manual_create_sdref(cr, uid, line_obj, rw_xmlid, line_id, context=context)        

    def get_stock_move_lines(self, cr, uid, line_values, context):
        line_result = []
        update_lines = []

        line_vals_dict = line_values.to_dict()
        if 'move_lines' not in line_vals_dict:
            return []

        for line in line_values.move_lines:
            values = {}
            line_dict = line.to_dict()

            if line_dict.get('product_uom'):
                values['product_uom'] = self.get_uom_id(cr, uid, line.product_uom, context=context)

            if line_dict.get('line_number'):
                values['line_number'] = line.line_number

            if line_dict.get('product_qty'): # come from the PO
                values['product_qty'] = line.product_qty

            if line_dict.get('expired_date'):
                values['expired_date'] = line.expired_date

            if line_dict.get('asset_id'):
                values['asset_id'] = line.asset_id

            if line_dict.get('date_expected'):
                values['date_expected'] = line.date_expected

            if line_dict.get('product_id'):
                rec_id = self.pool.get('product.product').find_sd_ref(cr, uid, xmlid_to_sdref(line.product_id.id), context=context)
                if rec_id:
                    values['product_id'] = rec_id
                    values['name'] = line.product_id.name

            '''
            TO DO: The update or create of Stock moves for the IN must be discussed carefully, because the stock move lines in an IN at Project
            have no direct mapping with the OUT from Coordo, so the changes in OUT make it difficult to find the corresponding moves in IN at Project
            in order to update or create new moves (in case of split), but also in case of back orders!
            So the following block needs to be reviewed and checked for the case of update/create of the move lines.
            '''
#            line_ids = False
#            if line_ids and line_ids[0]:
#                if for_update: # add this value to the list of update, then remove
#                    update_lines.append(line_ids[0])
#
#                line_result.append((1, line_ids[0], values))
#            else:
#                line_result.append((0, 0, values))

        # for update case, then check all updated lines, the other lines that are not presented in the sync message must be deleted at this destination instance!
        return line_result

    def get_uom_id(self, cr, uid, uom_name, context=None):
        if not context:
            context = {}
        context.update({'active_test': False})
        ids = self.pool.get('product.uom').search(cr, uid, [('name', '=', uom_name)], context=context)
        if not ids:
            raise Exception("The Unit of Measure %s is not found in the system. The operation is thus interrupted." % uom_name)
        return ids[0]

    def get_location(self, cr, uid, partner_id, context=None):
        '''
        For instance, the location ID for the PO created will be by default the Input Location of the default warehouse
        Proper location should be taken when creating the PO from an SO

        The location is mandatory in PO, so, if there is no location, an exception will be raised to stop creating the PO
        '''
        warehouse_obj = self.pool.get('stock.warehouse')
        warehouse_ids = warehouse_obj.search(cr, uid, [], limit=1)
        if not warehouse_ids:
            raise Exception, "No valid warehouse location found for the PO! The PO cannot be created."
        return warehouse_obj.read(cr, uid, warehouse_ids, ['lot_input_id'])[0]['lot_input_id'][0]

    def create_message_with_object_and_partner(self, cr, uid, rule_sequence, object_id, partner_name,context,usb=False):

        ##############################################################################
        # This method creates a message and put into the sendbox, but the message is created for a given object, AND for a given partner
        # Meaning that for the same object, but for different internal partners, the object could be sent many times to these partner
        #
        ##############################################################################
        rule_obj = self.pool.get("sync.client.message_rule")
        rule = rule_obj.get_rule_by_sequence(cr, uid, rule_sequence, context)

        if not rule or not object_id:
            return

        model_obj = self.pool.get(rule.model)
        if usb:
            msg_to_send_obj = self.pool.get("sync_remote_warehouse.message_to_send")
        else:
            msg_to_send_obj = self.pool.get("sync.client.message_to_send")

        arguments = model_obj.get_message_arguments(cr, uid, object_id, rule, context=context)

        identifiers = msg_to_send_obj._generate_message_uuid(cr, uid, rule.model, [object_id], rule.server_id, context=context)
        
        if not identifiers:
            return

        xml_id = identifiers[object_id]
        existing_message_id = msg_to_send_obj.search(cr, uid, [('identifier',
            '=', xml_id), ('destination_name', '=', partner_name)],
            limit=1, order='NO_ORDER', context=context)
        if existing_message_id: # if similar message does not exist in the system, then do nothing
            return

        # if not then create a new one --- FOR THE GIVEN Batch number AND Destination
        data = {
                'identifier' : xml_id,
                'remote_call': rule.remote_call,
                'arguments': arguments,
                'destination_name': partner_name,
                'sent' : False,
                'generate_message' : True,
        }
        return msg_to_send_obj.create(cr, uid, data, context=context)

    def create_invalid_recovery_message(self, cr, uid, partner_name, name, context):
        rule_obj = self.pool.get("sync.client.message_rule")
        rule = rule_obj.get_rule_by_sequence(cr, uid, 1003, context)
        if not rule:
            return
        msg_to_send_obj = self.pool.get("sync.client.message_to_send")

        xml_id = cr.dbname + "_recovery_" + partner_name + "_object_" + name
        existing_message_id = msg_to_send_obj.search(cr, uid, [('identifier',
            '=', xml_id), ('destination_name', '=', partner_name)],
            limit=1, order='NO_ORDER', context=context)
        if existing_message_id: # if similar message does not exist in the system, then do nothing
            return

        # if not then create a new one --- FOR THE GIVEN Batch number AND Destination
        data = {
                'identifier' : xml_id,
                'remote_call': rule.remote_call,
                'arguments': [{'name': name}],
                'destination_name': partner_name,
                'sent' : False,
                'generate_message' : True,
        }
        return msg_to_send_obj.create(cr, uid, data, context=context)

so_po_common()

