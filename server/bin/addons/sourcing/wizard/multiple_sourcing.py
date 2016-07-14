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

from osv import fields
from osv import osv
from tools.translate import _

from ..sale_order_line import _SELECTION_PO_CFT

_SELECTION_TYPE = [
    ('make_to_stock', 'from stock'),
    ('make_to_order', 'on order'), ]


class multiple_sourcing_wizard(osv.osv_memory):
    _name = 'multiple.sourcing.wizard'

    _columns = {
        'line_ids': fields.many2many(
            'sale.order.line',
            'source_sourcing_line_rel',
            'line_id',
            'wizard_id',
            string='Sourcing lines',
        ),
        'run_scheduler': fields.boolean(
            string='Run scheduler ?',
            readonly="True",
        ),
        'type': fields.selection(
            _SELECTION_TYPE,
            string='Procurement Method',
            required=True,
        ),
        'po_cft': fields.selection(
            _SELECTION_PO_CFT,
            string='PO/CFT',
        ),
        'related_sourcing_id': fields.many2one(
            'related.sourcing',
            string='Group',
        ),
        'location_id': fields.many2one(
            'stock.location',
            string='Location',
        ),
        'supplier_id': fields.many2one(
            'res.partner',
            string='Supplier',
            help="If you have choose lines coming from Field Orders, only External/ESC suppliers will be available.",
        ),
        'company_id': fields.many2one(
            'res.company',
            string='Current company',
        ),
        'error_on_lines': fields.boolean(
            string='Error',
            help="If there is line without need sourcing on selected lines",
        ),
        'related_sourcing_ok': fields.boolean(
            string='Related sourcing OK',
        ),
    }

    def default_get(self, cr, uid, fields_list, context=None):
        """
        Set lines with the selected lines to source
        :param cr: Cursor to the database
        :param uid: ID of the res.users that calls the method
        :param fields_list: List of field names to fill with default value
        :param context: Context of the call
        :return: A dictionary that contains the field name as key and the default value for this field as value.
        """
        sol_obj = self.pool.get('sale.order.line')
        user_obj = self.pool.get('res.users')
        po_auto_cfg_obj = self.pool.get('po.automation.config')

        if context is None:
            context = {}

        active_ids = context.get('active_ids')
        if not active_ids or len(active_ids) < 2:
            raise osv.except_osv(_('Error'), _('You should select at least two lines to process.'))

        res = super(multiple_sourcing_wizard, self).default_get(cr, uid, fields_list, context=context)

        res.update({
            'line_ids': [],
            'error_on_lines': False,
            'run_scheduler': po_auto_cfg_obj.get_po_automation(cr, uid, context=context),
            'type': 'make_to_stock',
            'po_cft': False,
            'related_sourcing_ok': False,
        })

        # Check if all lines are with the same type, then set that type, otherwise set make_to_order
        # Ignore all lines which have already been sourced, if there are some already sourced lines, a message
        # will be displayed at the top of the wizard
        res['type'] = 'make_to_stock'
        res['po_cft'] = False
        loc = -1 # first location flag
        supplier = -1 # first location flag
        group = None
        for line in sol_obj.browse(cr, uid, active_ids, context=context):
            if line.state == 'draft' and line.sale_order_state == 'validated':
                res['line_ids'].append(line.id)
            else:
                res['error_on_lines'] = True

            if line.type == 'make_to_order':
                res['type'] = 'make_to_order'
                res['po_cft'] = 'po'

                loc = False  # always set False for location if source on order
                if not line.supplier:
                    supplier = False
                else:
                    temp = line.supplier.id
                    if supplier == -1:  # first location
                        supplier = temp
                    elif supplier != temp:
                        supplier = False

                if not line.related_sourcing_ok or not line.related_sourcing_id:
                    group = False
                else:
                    temp = line.related_sourcing_id.id
                    if group is None:
                        group = temp
                    elif group != temp:
                        group = False

            else:
                # UTP-1021: Calculate the location to set into the wizard view if all lines are sourced from the same location
                supplier = False # if source from stock, always set False to partner
                group = False
                temploc = line.location_id.id
                if loc == -1:  # first location
                    loc = temploc
                elif temploc != loc:
                    loc = False

        # UTP-1021: Set default values on opening the wizard
        if loc != -1:
            res['location_id'] = loc
        if supplier != -1:
            res['supplier_id'] = supplier
        if group is not None:
            res['related_sourcing_id'] = group

        res['related_sourcing_ok'] = sol_obj._check_related_sourcing_ok(cr, uid, supplier, res['type'], context=context)

        if not res['line_ids']:
            raise osv.except_osv(
                _('Error'),
                _('No non-sourced lines are selected. Please select non-sourced lines'),
            )

        res['company_id'] = user_obj.browse(cr, uid, uid, context=context).company_id.id

        return res

    def _get_related_sourcing_id(self, wiz):
        """
        Return the ID of a related.sourcing record or False
        :param wiz: browse_record of multiple.sourcing.wizard
        :return: ID of a related.sourcing record or False
        """
        if wiz.related_sourcing_id and wiz.supplier_id and wiz.supplier_id.partner_type == 'esc' \
           and wiz.supplier_id.split_po == 'yes':
            return wiz.related_sourcing_id.id

        return False

    def save_lines(self, cr, uid, ids, context=None):
        """
        Set values defined on the wizard to the lines of the wizard.
        :param cr: Cursor to the database
        :param uid: ID of the res.users that calls the method
        :param ids: List of ID of multiple.sourcing.wizard to save
        :param context: Context of the call
        :return: Close the wizard window
        """
        line_obj = self.pool.get('sale.order.line')

        if context is None:
            context = {}

        if isinstance(ids, (int, long)):
            ids = [ids]

        for wiz in self.browse(cr, uid, ids, context=context):
            if wiz.type == 'make_to_order':
                if not wiz.po_cft:
                    raise osv.except_osv(
                        _('Error'),
                        _('The Procurement method should be filled !'),
                    )
                elif wiz.po_cft != 'cft' and not wiz.supplier_id:
                    raise osv.except_osv(
                        _('Error'),
                        _('You should select a supplier !'),
                    )

            errors = {}
            for line in wiz.line_ids:
                if line.order_id.procurement_request and wiz.po_cft == 'dpo':
                    err_msg = 'You cannot choose Direct Purchase Order as method to source Internal Request lines.'
                    errors.setdefault(err_msg, [])
                    errors[err_msg].append((line.id, '%s of %s' % (line.line_number, line.order_id.name)))
                else:
                    try:
                        line_obj.write(cr, uid, [line.id], {
                            'type': wiz.type,
                            'po_cft': wiz.po_cft,
                            'supplier': wiz.supplier_id and wiz.supplier_id.id or False,
                            'related_sourcing_id': self._get_related_sourcing_id(wiz),
                            'location_id': wiz.location_id.id and wiz.location_id.id or False,
                        }, context=context)
                    except osv.except_osv, e:
                        errors.setdefault(e.value, [])
                        errors[e.value].append((line.id, '%s of %s' % (line.line_number, line.order_id.name)))

            if errors:
                error_msg = ''
                for e in errors:
                    if error_msg:
                        error_msg += ' // '
                    if len(errors[e]) > 1:
                        error_msg += 'Lines %s ' % ', '.join(str(x[1]) for x in errors[e])
                    else:
                        error_msg += 'Line %s ' % ', '.join(str(x[1]) for x in errors[e])
                    error_msg += ': %s' % e
                raise osv.except_osv(_('Errors'), _('There are some errors on sourcing lines : %s') % error_msg)

        # Commit the result to avoid problem confirmLine in thread with new cursor
        cr.commit()

        return {'type': 'ir.actions.act_window_close'}

    def source_lines(self, cr, uid, ids, context=None):
        """
        Confirm the sourcing of all the sale.order.line contained in the wizards.
        :param cr: Cursor to the database
        :param uid: ID of the res.users that calls the method
        :param ids: List of ID of multiple.sourcing.wizard that contain lines to confirm
        :param context: Context of the call
        :return: Close the wizard window
        """
        # Objects
        line_obj = self.pool.get('sale.order.line')
        po_auto_cfg_obj = self.pool.get('po.automation.config')

        if context is None:
            context = {}

        if isinstance(ids, (int, long)):
            ids = [ids]

        lines_to_confirm = []
        run_scheduler = True

        for wiz in self.browse(cr, uid, ids, context=context):
            if wiz.run_scheduler:
                run_scheduler = wiz.run_scheduler
            else:
                run_scheduler = po_auto_cfg_obj.get_po_automation(cr, uid, context=context)
            for line in wiz.line_ids:
                if line.order_id.procurement_request and wiz.po_cft == 'dpo':
                    raise osv.except_osv(_('Error'), _(
                        'You cannot choose Direct Purchase Order as method to source Internal Request lines.'))
                lines_to_confirm.append(line.id)

        line_obj.confirmLine(cr, uid, lines_to_confirm, run_scheduler=run_scheduler, context=context)

        return {'type': 'ir.actions.act_window_close'}

    def save_source_lines(self, cr, uid, ids, context=None):
        """
        Set values on sale.order.lines of the wizard and confirm them
        :param cr: Cursor to the database
        :param uid: ID of the res.users that calls the method
        :param ids: List of ID of multiple.sourcing.wizard that contain the lines to save and confirmed
        :param context: Context of the call
        :return: Close the wizard window
        """
        if context is None:
            context = {}

        self.save_lines(cr, uid, ids, context=context)
        self.source_lines(cr, uid, ids, context=context)

        return {'type': 'ir.actions.act_window_close'}

    def change_type(self, cr, uid, ids, l_type, supplier, context=None):
        """
        Unset the other fields if the type is 'from stock'
        :param cr: Cursor to the database
        :param uid: ID of the res.users that calls the method
        :param ids: List of ID of multiple.sourcing.wizard on which field values has to be changed
        :param l_type: Value of the field 'type'
        :param supplier: Value of the field 'supplier'
        :param context: Context of the call
        :return: A dictionary that contains the field names to change as keys and the value for these fields as values.
        """
        wh_obj = self.pool.get('stock.warehouse')
        sol_obj = self.pool.get('sale.order.line')

        if context is None:
            context = {}

        if l_type == 'make_to_order':
            return {
                'value': {
                    'location_id': False,
                    'related_sourcing_ok': sol_obj._check_related_sourcing_ok(cr, uid, supplier, l_type, context=context)
                },
            }

        res = {
            'value': {
                'po_cft': False,
                'supplier_id': False,
                'related_sourcing_ok': False,
                'related_sourcing_id': False,
            },
        }
        if not context or not context[0] or not context[0][2]:
            return res

        # UF-2508: Set by default Stock if all the lines had either no location or stock before
        active_ids = context[0][2]
        context = {}
        if not active_ids:
            return res

        # Get the default stock location of the default warehouse
        wh_ids = wh_obj.search(cr, uid, [], context=context)
        stock_loc = False
        if wh_ids:
            stock_loc = wh_obj.browse(cr, uid, wh_ids[0], context=context).lot_stock_id.id

        all_line_empty = True
        for line in sol_obj.browse(cr, uid, active_ids, context=context):
            if line.location_id and line.location_id.id != stock_loc:
                all_line_empty = False

        if all_line_empty:  # by default, and if all lines has no location, then set by default Stock
            return {
                'value': {
                    'po_cft': False,
                    'supplier_id': False,
                    'location_id': stock_loc,
                    'related_sourcing_ok': False,
                    'related_sourcing_id': False,
                },
            }

        return {
            'value': {
                'po_cft': False,
                'supplier_id': False,
                'related_sourcing_ok': False,
                'related_sourcing_id': False,
            },
        }

    def change_po_cft(self, cr, uid, ids, po_cft, context=None):
        """
        Unset the supplier if tender is choose
        :param cr: Cursor to the database
        :param uid: ID of the res.users that calls the method
        :param ids: List of ID of multiple.sourcing.wizard on which field values has to be changed
        :param po_cft: Value of the field 'po_cft'
        :param context: Context of the call
        :return: A dictionary that contains the field names to change as keys and the value for these fields as values.
        """
        if po_cft == 'cft':
            return {'value': {'supplier_id': False}}

        return {}

    def change_supplier(self, cr, uid, ids, supplier, l_type, context=None):
        """
        Check if the partner has an address.
        :param cr: Cursor to the database
        :param uid: ID of the res.users that calls the method
        :param ids: List of ID of multiple.sourcing.wizard on which field values has to be changed
        :param supplier: Value of the field 'supplier_id'
        :param l_type: Value of the field 'type'
        :param context: Context of the call
        :return: A dictionary that contains the field names to change as keys and the value for these fields as values.
        """
        partner_obj = self.pool.get('res.partner')
        sol_obj = self.pool.get('sale.order.line')

        if context is None:
            context = {}

        result = {}
        related_sourcing_ok = False
        if supplier:
            related_sourcing_ok = sol_obj._check_related_sourcing_ok(cr, uid, supplier, l_type, context=context)
            partner = partner_obj.browse(cr, uid, supplier, context)
            # Check if the partner has addresses
            if not partner.address:
                result['warning'] = {
                    'title': _('Warning'),
                    'message': _('The chosen partner has no address. Please define an address before continuing.'),
                }

        result['value'] = {
            'related_sourcing_ok': related_sourcing_ok,
        }

        if not related_sourcing_ok:
            result['value']['related_sourcing_id'] = False

        return result

    def change_location(self, cr, uid, ids, location_id, line_ids, context=None):
        """
        Update the stock value of lines according to given location.
        :param cr: Cursor to the database
        :param uid: ID of the user that calls this method
        :param ids: List of ID of multiple.sourcing.wizard that contain lines to change
        :param location_id: ID of stock.location selected in the wizard
        :param line_ids: List of ID of sale.order.line contained in the multiple.sourcing.wizard
        :param context: Context of the call
        :return: A dictionary that contains the field names to change as keys and the value for these fields as values.
        """
        line_obj = self.pool.get('sale.order.line')

        res = {}
        if not location_id or not line_ids or not line_ids[0] or not line_ids[0][2]:
            return res

        active_ids = line_ids[0][2]

        context = {
            'from_multiple_line_sourcing': False
        }
        for line in line_obj.browse(cr, uid, active_ids, context=context):
            line_obj.write(cr, uid, [line.id], {
                'type': 'make_to_stock',
                'po_cft': False,
                'supplier': False,
                'location_id': location_id,
            }, context=context)  # UTP-1021: Update loc and ask the view to refresh

        return {
            'value': {
                'line_ids': active_ids,
                'error_on_lines': False,
                'po_cft': False,
            },
        }

multiple_sourcing_wizard()

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
