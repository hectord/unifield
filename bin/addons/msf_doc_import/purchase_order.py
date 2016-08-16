# -*- coding: utf-8 -*-
##############################################################################
#
#    OpenERP, Open Source Management Solution
#    Copyright (C) 2012 TeMPO Consulting, MSF. All Rights Reserved
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
import logging
import tools
import time
from mx.DateTime import *
from os import path
from tools.translate import _
import base64
from spreadsheet_xml.spreadsheet_xml_write import SpreadsheetCreator
from msf_doc_import.wizard import PO_COLUMNS_HEADER_FOR_IMPORT as columns_header_for_po_line_import
from msf_doc_import.wizard import PO_LINE_COLUMNS_FOR_IMPORT as columns_for_po_line_import
from msf_doc_import import GENERIC_MESSAGE
from check_line import *
from msf_doc_import import MAX_LINES_NB
from msf_doc_import.wizard import PO_COLUMNS_FOR_INTEGRATION as columns_for_po_integration, PO_COLUMNS_HEADER_FOR_INTEGRATION, NEW_COLUMNS_HEADER

from lxml import etree
import datetime


class purchase_order(osv.osv):
    _inherit = 'purchase.order'

    def init(self, cr):
        """
        Load data (product_data.xml) before self
        """
        if hasattr(super(purchase_order, self), 'init'):
            super(purchase_order, self).init(cr)

        logging.getLogger('init').info('HOOK: module product: loading product_data.xml')
        pathname = path.join('product', 'product_data.xml')
        file = tools.file_open(pathname)
        tools.convert_xml_import(cr, 'product', file, {}, mode='init', noupdate=False)

        logging.getLogger('init').info('HOOK: module product_attributes: loading data/sale_data.yml')
        pathname = path.join('product_attributes', 'data', 'sale_data.yml')
        file = tools.file_open(pathname)
        tools.convert_yaml_import(cr, 'product_attributes', file, {}, mode='init', noupdate=False)

    def hook_rfq_sent_check_lines(self, cr, uid, ids, context=None):
        '''
        Please copy this to your module's method also.
        This hook belongs to the rfq_sent method from tender_flow>tender_flow.py
        - check lines after import
        '''
        res = super(purchase_order, self).hook_rfq_sent_check_lines(cr, uid, ids, context)
        if self.check_lines_to_fix(cr, uid, ids, context):
            res = False
        return res

    def _get_import_progress(self, cr, uid, ids, field_name, args, context=None):
        """
        Check if there are import wizard associated to POs
        """
        wiz_obj = self.pool.get('wizard.import.po.line')

        if context is None:
            context = {}

        if isinstance(ids, (int, long)):
            ids = [ids]

        res = {}

        for po_id in ids:
            res[po_id] = wiz_obj.search(cr, 1, [
                ('po_id', '=', po_id),
                ('state', '=', 'in_progress'),
            ], limit=1, context=context) and True or False

        return res

    _columns = {
        'import_in_progress': fields.function(
            _get_import_progress,
            method=True,
            type='boolean',
            string='Import in progress',
            store=False,
        ),
        'import_filenames': fields.one2many('purchase.order.simu.import.file', 'order_id', string='Imported files', readonly=True),
    }

    _defaults = {
        'import_in_progress': lambda *a: False,
    }

    def copy(self, cr, uid, id, defaults=None, context=None):
        '''
        Remove the import_in_progress flag
        '''
        if not defaults:
            defaults = {}

        if 'import_in_progress' not in defaults:
            defaults.update({'import_in_progress': False})

        return super(purchase_order, self).copy(cr, uid, id, defaults, context=context)

    def _check_active_product(self, cr, uid, ids, context=None):
        '''
        Check if the Purchase order contains a line with an inactive products
        '''
        inactive_lines = self.pool.get('purchase.order.line').search(cr, uid, [('product_id.active', '=', False),
                                                                               ('order_id', 'in', ids),
                                                                               ('order_id.state', 'not in', ['draft', 'cancel', 'done'])], context=context)

        if inactive_lines:
            plural = len(inactive_lines) == 1 and _('A product has') or _('Some products have')
            l_plural = len(inactive_lines) == 1 and _('line') or _('lines')
            raise osv.except_osv(_('Error'), _('%s been inactivated. If you want to validate this document you have to remove/correct the line containing those inactive products (see red %s of the document)') % (plural, l_plural))
            return False
        return True

    _constraints = [
        (_check_active_product, "You cannot validate this purchase order because it contains a line with an inactive product", ['order_line', 'state'])
    ]

    def wizard_import_file(self, cr, uid, ids, context=None):
        '''
        Launches the wizard to import lines from a file
        '''
        export_obj = self.pool.get('wizard.import.po.simulation.screen')
        export_line_obj = self.pool.get('wizard.import.po.simulation.screen.line')

        if context is None:
            context = {}

        context.update({'active_id': ids[0]})
        columns_header = NEW_COLUMNS_HEADER
        default_template = SpreadsheetCreator('Template of import', columns_header, [])
        export_ids = export_obj.search(cr, uid, [('order_id', '=', ids[0])], context=context)
        export_obj.unlink(cr, uid, export_ids, context=context)
        export_id = export_obj.create(cr, uid, {
                                                'order_id': ids[0]}, context)

        for l in self.pool.get('purchase.order').browse(cr, uid, ids[0], context=context).order_line:
            export_line_obj.create(cr, uid, {'po_line_id': l.id,
                                             'in_line_number': l.line_number,
                                             'simu_id': export_id}, context=context)

        return {'type': 'ir.actions.act_window',
                'res_model': 'wizard.import.po.simulation.screen',
                'res_id': export_id,
                'view_type': 'form',
                'view_mode': 'form',
                'target': 'same',
                'context': context,
                }

    def export_po_integration(self, cr, uid, ids, context=None):
        '''
        Call the wizard to choose the export file format
        '''
        wiz_obj = self.pool.get('wizard.export.po.validated')

        if isinstance(ids, (int, long)):
            ids = [ids]

        wiz_id = wiz_obj.create(cr, uid, {'order_id': ids[0]}, context=context)

        return {'type': 'ir.actions.act_window',
                'res_model': wiz_obj._name,
                'res_id': wiz_id,
                'view_type': 'form',
                'view_mode': 'form',
                'target': 'new',
                'context': context}

    def export_get_file_name(self, cr, uid, ids, prefix='PO', context=None):
        """
        UFTP-56: get export file name
        :param prefix: prefix of the file (POV for PO Validated, etc)
        :return POV_14_OC_MW101_PO00060_YYYY_MM_DD.xls or POV_14_OC_MW101_PO00060_YYYY_MM_DD.xml
        """
        if isinstance(ids, (int, long)):
            ids = [ids]
        if len(ids) != 1:
            return False
        po_r = self.read(cr, uid, ids[0], ['name'], context=context)
        if not po_r or not po_r['name']:
            return False
        dt_now = datetime.datetime.now()
        po_name = "%s_%s_%d_%02d_%02d" % (prefix,
            po_r['name'].replace('/', '_'),
            dt_now.year, dt_now.month, dt_now.day)
        return po_name

    def export_xml_po_integration(self, cr, uid, ids, context=None):
        '''
        Call the Pure XML report of validated PO
        '''
        if context is None:
            context = {}

        if isinstance(ids, (int, long)):
            ids = [ids]

        datas = {}
        datas['ids'] = ids
        file_name = self.export_get_file_name(cr, uid, ids, prefix='POV',
            context=context)
        if file_name:
            datas['target_filename'] = file_name
        report_name = 'validated.purchase.order_xml'

        return {
                'type': 'ir.actions.report.xml',
                'report_name': report_name,
                'datas': datas,
                'context': context,
               }

    def export_excel_po_integration(self, cr, uid, ids, context=None):
        '''
        Call the Excel report of validated PO
        '''
        if context is None:
            context = {}

        if isinstance(ids, (int, long)):
            ids = [ids]

        datas = {}
        datas['ids'] = ids
        file_name = self.export_get_file_name(cr, uid, ids, prefix='POV',
            context=context)
        if file_name:
            datas['target_filename'] = file_name
        report_name = 'validated.purchase.order_xls'

        return {
                'type': 'ir.actions.report.xml',
                'report_name': report_name,
                'datas': datas,
                'context': context,
               }

    def wizard_import_po_line(self, cr, uid, ids, context=None):
        '''
        Launches the wizard to import lines from a file
        '''
        if context is None:
            context = {}
        if isinstance(ids, (int, long)):
            ids = [ids]
        context.update({'active_id': ids[0]})
        columns_header = [(_(f[0]), f[1]) for f in columns_header_for_po_line_import]
        default_template = SpreadsheetCreator('Template of import', columns_header, [])
        file = base64.encodestring(default_template.get_xml(default_filters=['decode.utf8']))
        export_id = self.pool.get('wizard.import.po.line').create(cr, uid, {'file': file,
                                                                            'filename_template': 'template.xls',
                                                                            'filename': 'Lines_Not_Imported.xls',
                                                                            'po_id': ids[0],
                                                                            'message': """%s %s""" % (_(GENERIC_MESSAGE), ', '.join([_(f) for f in columns_for_po_line_import]),),
                                                                            'state': 'draft', },
                                                                   context)
        return {'type': 'ir.actions.act_window',
                'res_model': 'wizard.import.po.line',
                'res_id': export_id,
                'view_type': 'form',
                'view_mode': 'form',
                'target': 'same',
                'context': context,
                }

    def check_lines_to_fix(self, cr, uid, ids, context=None):
        """
        Check both the lines that need to be corrected and also that the supplier or the address is not 'To be defined'
        """
        if isinstance(ids, (int, long)):
            ids = [ids]
        message = ''
        plural = ''
        obj_data = self.pool.get('ir.model.data')

        for var in self.browse(cr, uid, ids, context=context):
            # we check the supplier and the address
            if var.partner_id.id == obj_data.get_object_reference(cr, uid, 'msf_doc_import', 'supplier_tbd')[1] \
            or var.partner_address_id.id == obj_data.get_object_reference(cr, uid, 'msf_doc_import', 'address_tbd')[1]:
                raise osv.except_osv(_('Warning !'), _("\n You can't have a supplier or an address 'To Be Defined', please select a consistent supplier."))
            # we check the lines that need to be fixed
            if var.order_line:
                for var in var.order_line:
                    if var.to_correct_ok:
                        line_num = var.line_number
                        if message:
                            message += ', '
                        message += str(line_num)
                        if len(message.split(',')) > 1:
                            plural = 's'
        if message:
            raise osv.except_osv(_('Warning !'), _('You need to correct the following line%s: %s') % (plural, message))
        return True

    def check_condition(self, cr, uid, ids, context=None):
        if isinstance(ids, (int, long)):
            ids = [ids]
        for var in self.browse(cr, uid, ids, context=context):
            if not var.from_sync and var.partner_type not in ('external', 'esc'):
                raise osv.except_osv(_('Warning !'), _("""You can\'t cancel the PO because it may have already been synchronized,
                the cancellation should then come from the supplier instance (and synchronize down to the requestor instance)."""))
        return True

purchase_order()


class purchase_order_line(osv.osv):
    '''
    override of purchase_order_line class
    '''
    _inherit = 'purchase.order.line'
    _description = 'Purchase Order Line'


    def _get_inactive_product(self, cr, uid, ids, field_name, args, context=None):
        '''
        Fill the error message if the product of the line is inactive
        '''
        res = {}
        for line in self.browse(cr, uid, ids, context=context):
            res[line.id] = {'inactive_product': False,
                            'inactive_error': ''}
            if line.text_error:
                res[line.id] = {'inactive_error': line.comment}
            if line.order_id and line.order_id.state not in ('cancel', 'done') and line.product_id and not line.product_id.active:
                res[line.id] = {'inactive_product': True,
                                'inactive_error': _('The product in line is inactive !')}

        return res

    _columns = {
        'to_correct_ok': fields.boolean('To correct'),
        'show_msg_ok': fields.boolean('Info on importation of lines'),
        'text_error': fields.text('Errors when trying to import file'),
        'inactive_product': fields.function(_get_inactive_product, method=True, type='boolean', string='Product is inactive', store=False, multi='inactive'),
        'inactive_error': fields.function(_get_inactive_product, method=True, type='char', string='Comment', store=False, multi='inactive'),
    }

    _defaults = {
        'inactive_product': False,
        'inactive_error': lambda *a: '',
    }

    def check_line_consistency(self, cr, uid, ids, *args, **kwargs):
        """
        After having taken the value in the to_write variable we are going to check them.
        This function routes the value to check in dedicated methods (one for checking UoM, an other for Price Unit...).
        """
        context = kwargs['context']
        if context is None:
            context = {}
        obj_data = self.pool.get('ir.model.data')
        to_write = kwargs['to_write']
        order_id = to_write.get('order_id', False)
        if order_id:
            text_error = to_write['text_error']
            price_unit_defined = to_write['price_unit_defined']
            po_obj = self.pool.get('purchase.order')
            po = po_obj.browse(cr, uid, order_id, context=context)
            # on_change functions to call for updating values
            pricelist = po.pricelist_id.id or False
            partner_id = po.partner_id.id or False
            date_order = po.date_order or False
            fiscal_position = po.fiscal_position or False
            state = po.state or False
            product = to_write.get('product_id', False)
            if product:
                qty = to_write.get('product_qty')
                price_unit = to_write.get('price_unit')
                uom = to_write.get('product_uom')
                if product and qty and not price_unit_defined:
                    try:
                        res = self.product_id_on_change(cr, uid, False, pricelist, product, qty, uom,
                                                    partner_id, date_order, fiscal_position, date_planned=False,
                                                    name=False, price_unit=price_unit, notes=False, state=state, old_price_unit=False,
                                                    nomen_manda_0=False, comment=False, context=context)
                        if not context.get('po_integration'):
                            price_unit = res.get('value', {}).get('price_unit', False)
                            text_error += _('\n We use the price mechanism to compute the Price Unit.')
                        uom = res.get('value', {}).get('product_uom', False)
                        warning_msg = res.get('warning', {}).get('message', '')
                        text_error += '\n %s' % warning_msg
                    except osv.except_osv as osv_error:
                        if not context.get('po_integration'):
                            osv_value = osv_error.value
                            osv_name = osv_error.name
                            text_error += '%s. %s\n' % (osv_value, osv_name)
                    to_write.update({'price_unit': price_unit, 'product_uom': uom, 'text_error': text_error})
                if uom:
                    self.check_data_for_uom(cr, uid, False, to_write=to_write, context=context)
                else:
                    if not context.get('po_integration'):
                        uom = obj_data.get_object_reference(cr, uid, 'msf_doc_import', 'uom_tbd')[1]
                        text_error += _('\n It wasn\'t possible to update the UoM with the product\'s one because the former wasn\'t either defined.')
                        to_write.update({'product_uom': uom, 'text_error': text_error})

                # Check product line restrictions
                if product and po.partner_id:
                    self.pool.get('product.product')._get_restriction_error(cr, uid, [product], {'partner_id': po.partner_id.id}, context=dict(context, noraise=False))

        return to_write

    def check_data_for_uom(self, cr, uid, ids, *args, **kwargs):
        context = kwargs['context']
        if context is None:
            context = {}
        obj_data = self.pool.get('ir.model.data')
        # we take the values that we are going to write in PO line in "to_write"
        to_write = kwargs['to_write']
        text_error = to_write['text_error']
        product_id = to_write['product_id']
        uom_id = to_write['product_uom']
        if uom_id and product_id:
            if not self.pool.get('uom.tools').check_uom(cr, uid, product_id, uom_id, context):
                text_error += _("""\n You have to select a product UOM in the same category than the UOM of the product.""")
                return to_write.update({'text_error': text_error,
                                        'to_correct_ok': True})
        elif (not uom_id or uom_id == obj_data.get_object_reference(cr, uid, 'msf_doc_import', 'uom_tbd')[1]) and product_id:
            # we take the default uom of the product
            product = self.pool.get('product.product').browse(cr, uid, product_id)
            product_uom = product.uom_id.id
            return to_write.update({'product_uom': product_uom})
        elif not uom_id or uom_id == obj_data.get_object_reference(cr, uid, 'msf_doc_import', 'uom_tbd')[1]:
            # this is inspired by the on_change in purchase>purchase.py: product_uom_change
            text_error += _("\n The UoM was not defined so we set the price unit to 0.0.")
            return to_write.update({'text_error': text_error,
                                    'to_correct_ok': True,
                                    'price_unit': 0.0, })

    def write(self, cr, uid, ids, vals, context=None):
        if isinstance(ids, (int, long)):
            ids = [ids]
        if context is None:
            context = {}
        obj_data = self.pool.get('ir.model.data')
        tbd_uom = obj_data.get_object_reference(cr, uid, 'msf_doc_import', 'uom_tbd')[1]
        message = ''
        if not context.get('import_in_progress') and not context.get('button'):
            if vals.get('product_uom') or vals.get('nomen_manda_0') or vals.get('nomen_manda_1') or vals.get('nomen_manda_2'):
                if vals.get('product_uom'):
                    if vals.get('product_uom') == tbd_uom:
                        message += _('You have to define a valid UOM, i.e. not "To be defined".')
                if vals.get('nomen_manda_0'):
                    if vals.get('nomen_manda_0') == obj_data.get_object_reference(cr, uid, 'msf_doc_import', 'nomen_tbd0')[1]:
                        message += _('You have to define a valid Main Type (in tab "Nomenclature Selection"), i.e. not "To be defined".')
                if vals.get('nomen_manda_1'):
                    if vals.get('nomen_manda_1') == obj_data.get_object_reference(cr, uid, 'msf_doc_import', 'nomen_tbd1')[1]:
                        message += _('You have to define a valid Group (in tab "Nomenclature Selection"), i.e. not "To be defined".')
                if vals.get('nomen_manda_2'):
                    if vals.get('nomen_manda_2') == obj_data.get_object_reference(cr, uid, 'msf_doc_import', 'nomen_tbd2')[1]:
                        message += _('You have to define a valid Family (in tab "Nomenclature Selection"), i.e. not "To be defined".')
                # the 3rd level is not mandatory
                if message:
                    raise osv.except_osv(_('Warning !'), _(message))
                else:
                    vals['show_msg_ok'] = False
                    vals['to_correct_ok'] = False
                    vals['text_error'] = False

        return super(purchase_order_line, self).write(cr, uid, ids, vals, context=context)

purchase_order_line()


class wizard_export_po_validated(osv.osv_memory):
    _name = 'wizard.export.po.validated'

    _columns = {
        'order_id': fields.many2one('purchase.order', string='Purchase Order', required=True),
        'file_type': fields.selection([('excel', 'Excel file'),
                                       ('xml', 'XML file')], string='File type', required=True),
    }

    def export_file(self, cr, uid, ids, context=None):
        '''
        Launch the good method to download the good file
        '''
        order_obj = self.pool.get('purchase.order')

        if isinstance(ids, (int, long)):
            ids = [ids]

        wiz = self.browse(cr, uid, ids[0], context=context)

        if wiz.file_type == 'xml':
            return order_obj.export_xml_po_integration(cr, uid, wiz.order_id.id, context=context)
        else:
            return order_obj.export_excel_po_integration(cr, uid, wiz.order_id.id, context=context)

wizard_export_po_validated()


class purchase_order_simu_import_file(osv.osv):
    _name = 'purchase.order.simu.import.file'
    _order = 'timestamp'
    _rec_name = 'order_id'

    _columns = {
        'order_id': fields.many2one('purchase.order', string='Order', required=True),
        'filename': fields.char(size=256, string='Filename', required=True),
        'timestamp': fields.datetime(string='Date', required=True),
    }

    _defaults = {
        'timestamp': lambda *a: time.strftime('%Y-%m-%d %H:%M:%S'),
    }

purchase_order_simu_import_file()
