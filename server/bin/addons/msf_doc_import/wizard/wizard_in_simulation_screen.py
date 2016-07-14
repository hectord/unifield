# -*- coding: utf-8 -*-
##############################################################################
#
#    OpenERP, Open Source Management Solution
#    Copyright (C) 2011 MSF, TeMPO Consulting.
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

# Module imports
import base64
from mx import DateTime
import threading
import time

from osv import fields
from osv import osv
import pooler
from tools.translate import _

from msf_order_date import TRANSPORT_TYPE
from msf_outgoing import INTEGRITY_STATUS_SELECTION
from spreadsheet_xml.spreadsheet_xml import SpreadsheetXML
import xml.etree.ElementTree as ET


# Server imports
# Addons imports
NB_OF_HEADER_LINES = 7
NB_LINES_COLUMNS = 12


PRODUCT_CODE_ID = {}
UOM_NAME_ID = {}
CURRENCY_NAME_ID = {}
PRODLOT_NAME_ID = {}

SIMU_LINES = {}


LINES_COLUMNS = [(0, _('Line number'), 'optionnal'),
                 (1, _('Product Code'), 'mandatory'),
                 (2, _('Product Description'), 'optionnal'),
                 (3, _('Product Qty'), 'mandatory'),
                 (4, _('Product UoM'), 'mandatory'),
                 (5, _('Price Unit'), 'mandatory'),
                 (6, _('Currency'), 'mandatory'),
                 (7, _('Batch'), 'optionnal'),
                 (8, _('Expiry Date'), 'optionnal'),
                 (9, _('Packing List'), 'optionnal'),
                 (10, _('ESC message 1'), 'optionnal'),
                 (11, _('ESC message 2'), 'optionnal'),
                 ]

HEADER_COLUMNS = [(1, _('Freight'), 'optionnal'),
                  (2, _('Picking Reference'), 'optionnal'),
                  (3, _('Origin'), 'optionnal'),
                  (4, _('Supplier'), 'optionnal'),
                  (5, _('Transport mode'), 'optionnal'),
                  (6, _('Notes'), 'optionnal'),
                  (7, _('Message ESC'), 'optionnal'),
                  ]


class wizard_import_in_simulation_screen(osv.osv):
    _name = 'wizard.import.in.simulation.screen'
    _rec_name = 'picking_id'

    def _get_related_values(self, cr, uid, ids, field_name, args, context=None):
        '''
        Get the values related to the picking
        '''
        if context is None:
            context = {}

        if isinstance(ids, (int, long)):
            ids = [ids]

        res = {}
        for simu in self.browse(cr, uid, ids, context=context):
            res[simu.id] = {'origin': simu.picking_id.origin,
                            'creation_date': simu.picking_id.date,
                            'purchase_id': simu.picking_id.purchase_id and simu.picking_id.purchase_id.id or False,
                            'backorder_id': simu.picking_id.backorder_id and simu.picking_id.backorder_id.id or False,
                            'header_notes': simu.picking_id.note,
                            'freight_number': simu.picking_id.shipment_ref,
                            'transport_mode': simu.picking_id and simu.picking_id.purchase_id and simu.picking_id.purchase_id.transport_type or False}

        return res

    _columns = {
        'picking_id': fields.many2one('stock.picking', string='Incoming shipment', required=True, readonly=True),
        'message': fields.text(string='Import message',
                               readonly=True),
        'state': fields.selection([('draft', 'Draft'),
                                   ('simu_progress', 'Simulation in progress'),
                                   ('simu_done', 'Simulation done'),
                                   ('import_progress', 'Import in progress'),
                                   ('error', 'Error'),
                                   ('done', 'Done')],
                                  string='State',
                                  readonly=True),
        # File information
        'file_to_import': fields.binary(string='File to import'),
        'filename': fields.char(size=64, string='Filename'),
        'filetype': fields.selection([('excel', 'Excel file'),
                                      ('xml', 'XML file')], string='Type of file',
                                     required=True),
        'error_file': fields.binary(string='File with errors'),
        'error_filename': fields.char(size=64, string='Lines with errors'),
        'nb_file_lines': fields.integer(string='Total of file lines',
                                        readonly=True),
        'nb_treated_lines': fields.integer(string='Nb treated lines',
                                           readonly=True),
        'percent_completed': fields.float(string='Percent completed',
                                          readonly=True),
        'import_error_ok': fields.boolean(string='Error at import'),
        # Related fields
        'origin': fields.function(_get_related_values, method=True, string='Origin',
                                  readonly=True, type='char', size=512, multi='related'),
        'creation_date': fields.function(_get_related_values, method=True, string='Creation date',
                                         readonly=True, type='datetime', multi='related'),
        'purchase_id': fields.function(_get_related_values, method=True, string='Purchase Order',
                                       readonly=True, type='many2one', relation='purchase.order', multi='related'),
        'backorder_id': fields.function(_get_related_values, method=True, string='Back Order Of',
                                        readonly=True, type='many2one', relation='stock.picking', multi='related'),
        'header_notes': fields.function(_get_related_values, method=True, string='Header notes',
                                        readonly=True, type='text', multi='related'),
        'freight_number': fields.function(_get_related_values, method=True, string='Freight number',
                                          readonly=True, type='char', size=128, multi='related'),
        'transport_mode': fields.function(_get_related_values, method=True, string='Transport mode',
                                          readonly=True, type='selection', selection=TRANSPORT_TYPE, multi='related'),
        # Import fields
        'imp_notes': fields.text(string='Notes', readonly=True),
        'message_esc': fields.text(string='Message ESC', readonly=True),
        'imp_origin': fields.char(size=128, string='Origin', readonly=True),
        'imp_freight_number': fields.char(size=128, string='Freight number', readonly=True),
        'imp_transport_mode': fields.char(string='Transport mode', size=128, readonly=True),
        # Lines
        'line_ids': fields.one2many('wizard.import.in.line.simulation.screen', 'simu_id', string='Stock moves'),

    }

    _defaults = {
        'state': 'draft',
        'filetype': 'excel',
    }

    def write(self, cr, uid, ids, vals, context=None):
        '''
        Remove the concurrency access warning
        '''
        if context is None:
            context = {}

        buttons = ['return_to_in',
                   'go_to_simulation',
                   'print_simulation_report',
                   'launch_import',
                   'simulate']
        if context.get('button') in buttons:
            return True

        return super(wizard_import_in_simulation_screen, self).write(cr, uid, ids, vals, context=context)

    def return_to_in(self, cr, uid, ids, context=None):
        '''
        '''
        if context is None:
            context = {}

        if isinstance(ids, (int, long)):
            ids = [ids]

        picking_id = self.browse(cr, uid, ids[0], context=context).picking_id.id
        context['pick_type'] = 'incoming'

        view_id = self.pool.get('ir.model.data').get_object_reference(cr, uid, 'stock', 'view_picking_in_form')[1]

        return {'type': 'ir.actions.act_window',
                'res_model': 'stock.picking',
                'res_id': picking_id,
                'view_type': 'form',
                'view_mode': 'form,tree',
                'view_id': [view_id],
                'target': 'crush',
                'context': context}

    def go_to_simulation(self, cr, uid, ids, context=None):
        '''
        Reload the simulation screen
        '''
        if context is None:
            context = {}

        if isinstance(ids, (int, long)):
            ids = [ids]

        return {'type': 'ir.actions.act_window',
                'res_model': self._name,
                'res_id': ids[0],
                'view_type': 'form',
                'view_mode': 'form',
                'target': 'same'}

    def print_simulation_report(self, cr, uid, ids, context=None):
        '''
        Print the Excel report of the simulation
        '''
        if context is None:
            context = {}

        if isinstance(ids, (int, long)):
            ids = [ids]

        datas = {}
        datas['ids'] = ids
        report_name = 'in.simulation.screen.xls'

        return {
            'type': 'ir.actions.report.xml',
            'report_name': report_name,
            'datas': datas,
            'context': context,
        }

    def launch_import(self, cr, uid, ids, context=None):
        '''
        '''
        if context is None:
            context = {}

        if isinstance(ids, (int, long)):
            ids = [ids]

        return self._import(cr, uid, ids, context=context)

    def launch_simulate(self, cr, uid, ids, context=None):
        '''
        Launch the simulation routine in background
        '''
        if context is None:
            context = {}

        if isinstance(ids, (int, long)):
            ids = [ids]

        for wiz in self.browse(cr, uid, ids, context=context):
            if not wiz.file_to_import:
                raise osv.except_osv(
                    _('Error'),
                    _('Please select a file to import !'),
                )
            if wiz.filetype == 'excel':
                xml_file = base64.decodestring(wiz.file_to_import)
                excel_file = SpreadsheetXML(xmlstring=xml_file)
                if not excel_file.getWorksheets():
                    raise osv.except_osv(_('Error'), _('The given file is not a valid Excel 2003 Spreadsheet file !'))
            else:
                xml_file = base64.decodestring(wiz.file_to_import)
                root = ET.fromstring(xml_file)
                if root.tag != 'data':
                    raise osv.except_osv(_('Error'), _('The given file is not a valid XML file !'))

            self.write(cr, uid, ids, {'state': 'simu_progress'}, context=context)
            cr.commit()
            new_thread = threading.Thread(target=self.simulate, args=(cr.dbname, uid, ids, context))
            new_thread.start()
            new_thread.join(10.0)

            return self.go_to_simulation(cr, uid, ids, context=context)

    def get_values_from_xml(self, cr, uid, file_to_import, context=None):
        '''
        Read the XML file and put data in values
        '''
        values = {}
        # Read the XML file
        xml_file = base64.decodestring(file_to_import)

        root = ET.fromstring(xml_file)
        if root.tag != 'data':
            return values

        records = []
        rec_lines = []
        rec = False

        index = 0
        for record in root:
            if record.tag == 'record':
                records.append(record)

        if len(records) > 0:
            rec = records[0]

        def get_field_index(node, index):
            if not index:
                index = 0
            if node.getchildren():
                for subnode in node:
                    index = get_field_index(subnode, index)
                return index
            else:
                index += 1
                values[index] = [node.attrib['name'], node.text or '']
                return index

        for field in rec:
            if field.attrib['name'] != 'move_lines':
                index = get_field_index(field, index)
            else:
                index += 1
                values[index] = ['line_number', 'product_code',
                                 'product_name', 'product_qty',
                                 'uom_id', 'price_unit', 'currency_id',
                                 'prodlot_id', 'expiry_date',
                                 'packing_list', 'message_esc1',
                                 'message_esc2']
                for line in field:
                    rec_lines.append(line)

        for line in rec_lines:
            index += 1
            values[index] = []
            for fl in line:
                if not fl.getchildren():
                    values[index].append(fl.text or '')
                else:
                    for sfl in fl:
                        values[index].append(sfl.text or '')

        return values

    def get_values_from_excel(self, cr, uid, file_to_import, context=None):
        '''
        Read the Excel XML file and put data in values
        '''
        values = {}
        # Read the XML Excel file
        xml_file = base64.decodestring(file_to_import)
        fileobj = SpreadsheetXML(xmlstring=xml_file)

        # Read all lines
        rows = fileobj.getRows()

        # Get values per line
        index = 0
        for row in rows:
            index += 1
            values.setdefault(index, [])
            for cell_nb in range(len(row)):
                cell_data = row.cells and row.cells[cell_nb] and \
                            row.cells[cell_nb].data
                values[index].append(cell_data)

        return values

    # Simulation routing
    def simulate(self, dbname, uid, ids, context=None):
        '''
        Import the file and fill data in the simulation screen
        '''
        cr = pooler.get_db(dbname).cursor()
        # cr = dbname
        try:
            wl_obj = self.pool.get('wizard.import.in.line.simulation.screen')
            prod_obj = self.pool.get('product.product')
            uom_obj = self.pool.get('product.uom')

            # Declare global variables (need this explicit declaration to clear
            # them at the end of the process
            global PRODUCT_CODE_ID
            global UOM_NAME_ID
            global CURRENCY_NAME_ID
            global PRODLOT_NAME_ID
            global SIMU_LINES

            if context is None:
                context = {}

            if isinstance(ids, (int, long)):
                ids = [ids]

            for wiz in self.browse(cr, uid, ids, context=context):
                nb_treated_lines = 0
                prodlot_cache = {}
                # No file => Return to the simulation screen
                if not wiz.file_to_import:
                    self.write(cr, uid, [wiz.id], {'message': _('No file to import'),
                                                   'state': 'draft'}, context=context)
                    continue

                for line in wiz.line_ids:
                    # Put data in cache
                    if line.move_product_id:
                        PRODUCT_CODE_ID.setdefault(line.move_product_id.default_code, line.move_product_id.id)
                    if line.move_uom_id:
                        UOM_NAME_ID.setdefault(line.move_uom_id.name, line.move_uom_id.id)
                    if line.move_currency_id:
                        CURRENCY_NAME_ID.setdefault(line.move_currency_id.name, line.move_currency_id.id)

                    '''
                    First of all, we build a cache for simulation screen lines
                    '''
                    l_num = line.line_number
                    l_prod = line.move_product_id and line.move_product_id.id or False
                    l_uom = line.move_uom_id and line.move_uom_id.id or False
                    # By simulation screen
                    SIMU_LINES.setdefault(wiz.id, {})
                    SIMU_LINES[wiz.id].setdefault('line_ids', [])
                    SIMU_LINES[wiz.id]['line_ids'].append(line.id)
                    # By line number
                    SIMU_LINES[wiz.id].setdefault(l_num, {})
                    SIMU_LINES[wiz.id][l_num].setdefault('line_ids', [])
                    SIMU_LINES[wiz.id][l_num]['line_ids'].append(line.id)
                    # By product
                    SIMU_LINES[wiz.id][l_num].setdefault(l_prod, {})
                    SIMU_LINES[wiz.id][l_num][l_prod].setdefault('line_ids', [])
                    SIMU_LINES[wiz.id][l_num][l_prod]['line_ids'].append(line.id)
                    # By UoM
                    SIMU_LINES[wiz.id][l_num][l_prod].setdefault(l_uom, {})
                    SIMU_LINES[wiz.id][l_num][l_prod][l_uom].setdefault('line_ids', [])
                    SIMU_LINES[wiz.id][l_num][l_prod][l_uom]['line_ids'].append(line.id)
                    # By Qty
                    SIMU_LINES[wiz.id][l_num][l_prod][l_uom].setdefault(line.move_product_qty, [])
                    SIMU_LINES[wiz.id][l_num][l_prod][l_uom][line.move_product_qty].append(line.id)

                # Variables
                lines_to_ignored = []  # Bad formatting lines
                file_format_errors = []
                values_header_errors = []
                values_line_errors = []
                message = ''

                header_values = {}

                if wiz.filetype == 'excel':
                    values = self.get_values_from_excel(cr, uid, wiz.file_to_import, context=context)
                else:
                    values = self.get_values_from_xml(cr, uid, wiz.file_to_import, context=context)

                '''
                We check for each line if the number of columns is consistent
                with the expected number of columns :
                  * For PO header information : 2 columns
                  * For the line information : 12 columns
                '''
                # Check number of columns on lines

                for x in xrange(1, NB_OF_HEADER_LINES + 1):
                    if len(values.get(x, [])) != 2:
                        lines_to_ignored.append(x)
                        error_msg = _('Line %s of the imported file: The header \
    information must be on two columns: Column A for name of the field and column\
     B for value.') % x
                        file_format_errors.append(error_msg)

                if len(values.get(NB_OF_HEADER_LINES + 1, [])) != NB_LINES_COLUMNS:
                    error_msg = _('Line 8 of the Excel file: This line is \
    mandatory and must have %s columns. The values on this line must be the name \
    of the field for IN lines.') % NB_LINES_COLUMNS
                    file_format_errors.append(error_msg)

                for x in xrange(NB_OF_HEADER_LINES + 2, len(values) + 1):
                    if len(values.get(x, [])) != NB_LINES_COLUMNS:
                        lines_to_ignored.append(x)
                        error_msg = _('Line %s of the imported file: The line \
    information must be on %s columns. The line %s has %s columns') % (x, NB_LINES_COLUMNS, x, len(values.get(x, [])))
                        file_format_errors.append(error_msg)

                nb_file_lines = len(values) - NB_OF_HEADER_LINES - 1
                self.write(cr, uid, [wiz.id], {'nb_file_lines': nb_file_lines}, context=context)

                if len(file_format_errors):
                    message = _('''## IMPORT STOPPED ##

    Nothing has been imported because of bad file format. See below:

    ## File format errors ##\n\n''')
                    for err in file_format_errors:
                        message += '%s\n' % err

                    self.write(cr, uid, [wiz.id], {'message': message, 'state': 'error'}, context)
                    res = self.go_to_simulation(cr, uid, [wiz.id], context=context)
                    cr.commit()
                    cr.close(True)
                    return res

                '''
                New, we know that the file has the good format, you can import
                data for header.
                '''
                # Line 1: Freight
                freight_ref = values.get(1, ['', ''])[1]
                header_values['imp_freight_number'] = freight_ref

                # Line 2: Picking Reference
                picking_ref = values.get(2, ['', ''])[1]

                # Line 3: Origin
                origin = values.get(3, ['', ''])[1]
                header_values['imp_origin'] = origin


                # Line 5: Transport mode
                transport_mode = values.get(5, ['', ''])[1]
                header_values['imp_transport_mode'] = transport_mode

                # Line 6: Notes
                imp_notes = values.get(6, ['', ''])[1]
                header_values['imp_notes'] = imp_notes

                # Line 7: Message ESC header
                esc_message = values.get(7, ['', ''])[1]
                header_values['message_esc'] = esc_message

                '''
                The header values have been imported, start the importation of
                lines
                '''
                file_lines = {}
                file_in_lines = {}
                new_in_lines = []
                not_ok_file_lines = {}
                # Loop on lines
                for x in xrange(NB_OF_HEADER_LINES + 2, len(values) + 1):
                    # Check mandatory fields
                    not_ok = False
                    file_line_error = []
                    for manda_field in LINES_COLUMNS:
                        if manda_field[2] == 'mandatory' and not values.get(x, [])[manda_field[0]]:
                            not_ok = True
                            err1 = _('The column \'%s\' mustn\'t be empty%s') % (manda_field[1], manda_field[0] == 0 and ' - Line not imported' or '')
                            err = _('Line %s of the file: %s') % (x, err1)
                            values_line_errors.append(err)
                            file_line_error.append(err1)

                    if not values.get(x, [''])[0]:
                        line_number = False
                    else:
                        line_number = int(values.get(x, [''])[0])

                    if not_ok:
                        not_ok_file_lines[x] = ' - '.join(err for err in file_line_error)

                    # Get values
                    product_id = False
                    uom_id = False
                    qty = 0.00

                    vals = values.get(x, [])
                    # Product
                    if vals[1]:
                        product_id = PRODUCT_CODE_ID.get(vals[1], False)
                    if not product_id and vals[1]:
                        prod_ids = prod_obj.search(cr, uid, [('default_code', '=', vals[1])], context=context)
                        if prod_ids:
                            product_id = prod_ids[0]
                            PRODUCT_CODE_ID.setdefault(vals[1], product_id)

                    # UoM
                    if vals[4]:
                        uom_id = UOM_NAME_ID.get(vals[4], False)
                        if not uom_id:
                            uom_ids = uom_obj.search(cr, uid, [('name', '=', vals[4])], context=context)
                            if uom_ids:
                                uom_id = uom_ids[0]
                                UOM_NAME_ID.setdefault(vals[4], uom_id)

                    # Qty
                    if vals[3]:
                        qty = float(vals[3])

                    # Batch and expiry date
                    # Put the batch + expiry date in a cache to create
                    # the batch that don't exist only during the import
                    # not at simulation time
                    if vals[7] and vals[8]:
                        exp_value = vals[8]
                        if type(vals[8]) == type(DateTime.now()):
                            exp_value = exp_value.strftime('%Y-%m-%d')
                        elif vals[8] and isinstance(vals[8], str):
                            try:
                                time.strptime(vals[8], '%Y-%m-%d')
                                exp_value = vals[8]
                            except ValueError:
                                exp_value = False

                        if exp_value and not prodlot_cache.get(product_id, {}).get(str(vals[7])):
                            prodlot_cache.setdefault(product_id, {})
                            prodlot_cache[product_id].setdefault(str(vals[7]), exp_value)

                    file_lines[x] = (line_number, product_id, uom_id, qty)

                '''
                Get the best matching line:
                    1/ Within lines with same line number, same product, same UoM and same qty
                    2/ Within lines with same line number, same product and same UoM
                    3/ Within lines with same line number and same product
                    4/ Within lines with same line number

                If a matching line is found in one of these cases, keep the link between the
                file line and the simulation screen line.
                '''
                to_del = []
                for x, fl in file_lines.iteritems():
                    # Search lines with same product, same UoM and same qty
                    matching_lines = SIMU_LINES.get(wiz.id, {}).get(fl[0], {})
                    tmp_wl_ids = matching_lines.get(fl[1], {}).get(fl[2], {}).get(fl[3], [])
                    no_match = True
                    for l in tmp_wl_ids:
                        if l not in file_in_lines:
                            file_in_lines[l] = [(x, 'match')]
                            to_del.append(x)
                            no_match = False
                            break

                    if tmp_wl_ids and no_match:
                        file_in_lines[l].append((x, 'split'))
                        to_del.append(x)
                # Clear the dict
                for x in to_del:
                    del file_lines[x]
                to_del = []


                for x, fl in file_lines.iteritems():
                    # Search lines with same product, same UoM
                    matching_lines = SIMU_LINES.get(wiz.id, {}).get(fl[0], {})
                    tmp_wl_ids = matching_lines.get(fl[1], {}).get(fl[2], {}).get('line_ids', [])
                    no_match = True
                    for l in tmp_wl_ids:
                        if l not in file_in_lines:
                            file_in_lines[l] = [(x, 'match')]
                            to_del.append(x)
                            no_match = False
                            break
                    if tmp_wl_ids and no_match:
                        file_in_lines[l].append((x, 'split'))
                        to_del.append(x)
                # Clear the dict
                for x in to_del:
                    del file_lines[x]
                to_del = []

                for x, fl in file_lines.iteritems():
                    # Search lines with same product
                    matching_lines = SIMU_LINES.get(wiz.id, {}).get(fl[0], {})
                    tmp_wl_ids = matching_lines.get(fl[1], {}).get('line_ids', [])
                    no_match = True
                    for l in tmp_wl_ids:
                        if l not in file_in_lines:
                            file_in_lines[l] = [(x, 'match')]
                            to_del.append(x)
                            no_match = False
                            break
                    if tmp_wl_ids and no_match:
                        file_in_lines[l].append((x, 'split'))
                        to_del.append(x)
                # Clear the dict
                for x in to_del:
                    del file_lines[x]
                to_del = []

                for x, fl in file_lines.iteritems():
                    # Search lines with same line number
                    matching_lines = SIMU_LINES.get(wiz.id, {}).get(fl[0], {})
                    tmp_wl_ids = matching_lines.get('line_ids', [])
                    no_match = True
                    for l in tmp_wl_ids:
                        if l not in file_in_lines:
                            file_in_lines[l] = [(x, 'match')]
                            to_del.append(x)
                            no_match = False
                            break
                    if tmp_wl_ids and no_match:
                        file_in_lines[l].append((x, 'split'))
                        to_del.append(x)
                # Clear the dict
                for x in to_del:
                    del file_lines[x]
                to_del = []

                # For file lines with no simu. screen lines with same line number,
                # create a new simu. screen line
                for x in file_lines.keys():
                    new_in_lines.append(x)

                # Split the simu. screen line or/and update the values according
                # to linked file line.
                for in_line, file_lines in file_in_lines.iteritems():
                    if in_line in SIMU_LINES[wiz.id]['line_ids']:
                        index_in_line = SIMU_LINES[wiz.id]['line_ids'].index(in_line)
                        SIMU_LINES[wiz.id]['line_ids'].pop(index_in_line)
                    for file_line in file_lines:
                        nb_treated_lines += 1
                        percent_completed = nb_treated_lines / nb_file_lines * 100
                        self.write(cr, uid, [wiz.id], {'nb_treated_lines': nb_treated_lines,
                                                       'percent_completed': percent_completed}, context=context)
                        vals = values.get(file_line[0], [])
                        if file_line[1] == 'match':
                            err_msg = wl_obj.import_line(cr, uid, in_line, vals, prodlot_cache, context=context)
                            if file_line[0] in not_ok_file_lines:
                                wl_obj.write(cr, uid, [in_line], {'type_change': 'error', 'error_msg': not_ok_file_lines[file_line[0]]}, context=context)
                        elif file_line[1] == 'split':
                            new_wl_id = wl_obj.copy(cr, uid, in_line,
                                                             {'move_product_id': False,
                                                              'move_product_qty': 0.00,
                                                              'move_uom_id': False,
                                                              'move_price_unit': 0.00,
                                                              'move_currenty_id': False,
                                                              'type_change': 'split',
                                                              'imp_batch_name': '',
                                                              'imp_batch_id': False,
                                                              'imp_exp_date': False,
                                                              'error_msg': '',
                                                              'parent_line_id': in_line,
                                                              'move_id': False}, context=context)
                            err_msg = wl_obj.import_line(cr, uid, new_wl_id, vals, prodlot_cache, context=context)
                            if file_line[0] in not_ok_file_lines:
                                wl_obj.write(cr, uid, [new_wl_id], {'type_change': 'error', 'error_msg': not_ok_file_lines[file_line[0]]}, context=context)
                        # Commit modifications
                        cr.commit()

                    if err_msg:
                        for err in err_msg:
                            err = 'Line %s of the Excel file: %s' % (file_line[0], err)
                            values_line_errors.append(err)


                # Create new lines
                for in_line in new_in_lines:
                    nb_treated_lines += 1
                    percent_completed = nb_treated_lines / nb_file_lines * 100
                    self.write(cr, uid, [wiz.id], {'nb_treated_lines': nb_treated_lines,
                                                   'percent_completed': percent_completed}, context=context)
                    if in_line in SIMU_LINES[wiz.id]['line_ids']:
                        index_in_line = SIMU_LINES[wiz.id]['line_ids'].index(in_line)
                        SIMU_LINES[wiz.id]['line_ids'].pop(index_in_line)
                    vals = values.get(in_line, [])
                    new_wl_id = wl_obj.create(cr, uid, {'type_change': 'new',
                                                        'line_number': values.get(in_line, [''])[0] and int(values.get(in_line, [''])[0]) or False,
                                                        'simu_id': wiz.id}, context=context)
                    err_msg = wl_obj.import_line(cr, uid, new_wl_id, vals, prodlot_cache, context=context)
                    if in_line in not_ok_file_lines:
                        wl_obj.write(cr, uid, [new_wl_id], {'type_change': 'error', 'error_msg': not_ok_file_lines[in_line]}, context=context)

                    if err_msg:
                        for err in err_msg:
                            err = 'Line %s of the Excel file: %s' % (in_line, err)
                            values_line_errors.append(err)
                    # Commit modifications
                    cr.commit()

                # Lines to delete
                for in_line in SIMU_LINES[wiz.id]['line_ids']:
                    wl_obj.write(cr, uid, in_line, {'type_change': 'del'}, context=context)

                '''
                We generate the message which will be displayed on the simulation
                screen. This message is a merge between all errors.
                '''
                # Generate the message
                if len(values_header_errors):
                    message += '\n## Error on header values ##\n\n'
                    for err in values_header_errors:
                        message += '%s\n' % err

                if len(values_line_errors):
                    message += '\n## Error on line values ##\n\n'
                    for err in values_line_errors:
                        message += '%s\n' % err

                header_values['message'] = message
                header_values['state'] = 'simu_done'
                header_values['percent_completed'] = 100.0
                self.write(cr, uid, [wiz.id], header_values, context=context)

                res = self.go_to_simulation(cr, uid, [wiz.id], context=context)
                cr.commit()
                cr.close(True)
                return res

            cr.commit()
            cr.close(True)

            # Clear the cache
            PRODUCT_CODE_ID = {}
            UOM_NAME_ID = {}
            CURRENCY_NAME_ID = {}
            SIMU_LINES = {}
        except Exception, e:
            self.write(cr, uid, ids, {'message': e}, context=context)
            cr.commit()
            cr.close(True)

        return {'type': 'ir.actions.act_window_close'}


    def _import(self, cr, uid, ids, context=None):
        '''
        Create memeory moves and return to the standard incoming processing wizard
        '''
        line_obj = self.pool.get('wizard.import.in.line.simulation.screen')
        mem_move_obj = self.pool.get('stock.move.in.processor')

        if context is None:
            context = {}

        if isinstance(ids, (int, long)):
            ids = [ids]

        simu_id = self.browse(cr, uid, ids[0], context=context)

        context['active_id'] = simu_id.picking_id.id
        context['active_ids'] = [simu_id.picking_id.id]
        partial_id = self.pool.get('stock.incoming.processor').create(cr, uid, {'picking_id': simu_id.picking_id.id, 'date': simu_id.picking_id.date}, context=context)
        line_ids = line_obj.search(cr, uid, [('simu_id', '=', simu_id.id), '|', ('type_change', 'not in', ('del', 'error', 'new')), ('type_change', '=', False)], context=context)

        mem_move_ids, move_ids = line_obj.put_in_memory_move(cr, uid, line_ids, partial_id, context=context)

        # delete extra lines
        del_lines = mem_move_obj.search(cr, uid, [('wizard_id', '=', partial_id), ('id', 'not in', mem_move_ids), ('move_id', 'in', move_ids)], context=context)
        mem_move_obj.unlink(cr, uid, del_lines, context=context)

        self.pool.get('stock.picking').write(cr, uid, [simu_id.picking_id.id], {'last_imported_filename': simu_id.filename,
                                                                                'note': simu_id.imp_notes}, context=context)

        context['from_simu_screen'] = True
        return {'type': 'ir.actions.act_window',
                'res_model': 'stock.incoming.processor',
                'res_id': partial_id,
                'view_type': 'form',
                'view_mode': 'form',
                'target': 'same',
                'context': context}

wizard_import_in_simulation_screen()


class wizard_import_in_line_simulation_screen(osv.osv):
    _name = 'wizard.import.in.line.simulation.screen'
    _rec_name = 'line_number'
    _order = 'line_number_ok, line_number, id'

    def _get_values(self, cr, uid, ids, field_name, args, context=None):
        '''
        Compute values according to values in line
        '''
        if context is None:
            context = {}

        if isinstance(ids, (int, long)):
            ids = [ids]

        res = {}
        for line in self.browse(cr, uid, ids, context=context):
            price_unit = 0.00
            if line.move_id.purchase_line_id:
                price_unit = line.move_id.purchase_line_id.price_unit
            elif line.move_product_id:
                price_unit = line.move_product_id.standard_price

            if line.move_id.picking_id and line.move_id.picking_id.purchase_id \
               and line.move_id.picking_id.purchase_id.pricelist_id \
               and line.move_id.picking_id.purchase_id.pricelist_id.currency_id:
                curr_id = line.move_id.picking_id.purchase_id.pricelist_id.currency_id.id
            elif line.move_id and line.move_id.price_currency_id:
                curr_id = line.move_id.price_currency_id.id
            elif line.parent_line_id and line.parent_line_id.move_currency_id:
                curr_id = line.parent_line_id.move_currency_id.id
            else:
                curr_id = False


            product = line.imp_product_id or line.move_product_id
            res[line.id] = {
                'lot_check': product.batch_management,
                'exp_check': product.perishable,
                'kc_check': product.kc_txt,
                'dg_check': product.dg_txt,
                'np_check': product.cs_txt,
                'move_price_unit': price_unit,
                'move_currency_id': curr_id,
            }

        return res


    def _get_l_num(self, cr, uid, ids, field_name, args, context=None):
        '''
        Compute the line number
        '''
        if isinstance(ids, (int, long)):
            ids = [ids]

        res = {}

        for line in self.browse(cr, uid, ids, context=context):
            res[line.id] = {'line_number_ok': not line.line_number or line.line_number == 0,
                            'str_line_number': line.line_number and line.line_number != 0 and line.line_number or ''}

        return res


    def _get_imported_values(self, cr, uid, ids, field_name, args, context=None):
        '''
        Compute some field with imported values
        '''
        if isinstance(ids, (int, long)):
            ids = [ids]

        res = {}
        for line in self.browse(cr, uid, ids, context=context):
            res[line.id] = {'imp_cost': 0.00,
                            'discrepancy': 0.00}
            if line.simu_id.state != 'draft':
                res[line.id]['imp_cost'] = line.imp_product_qty * line.imp_price_unit
                res[line.id]['discrepancy'] = res[line.id]['imp_cost'] - (line.move_product_qty * line.move_price_unit)

        return res

    _columns = {
        'simu_id': fields.many2one('wizard.import.in.simulation.screen', string='Simu ID', required=True, ondelete='cascade'),
        # Values from move line
        'move_id': fields.many2one('stock.move', string='Move', readonly=True),
        'move_product_id': fields.many2one('product.product', string='Product', readonly=True),
        'move_product_qty': fields.float(digits=(16, 2), string='Ordered Qty', readonly=True),
        'move_uom_id': fields.many2one('product.uom', string='Ordered UoM', readonly=True),
        'move_price_unit': fields.function(_get_values, method=True, type='float', string='Price Unit',
                                           digits=(16, 2), store=True, readonly=True, multi='computed'),
        'move_currency_id': fields.function(_get_values, method=True, type='many2one', relation='res.currency',
                                            string='Curr.', store=True, readonly=True, multi='computed'),
        # Values for the simu line
        'line_number': fields.integer(string='Line'),
        'line_number_ok': fields.function(_get_l_num, method=True, type='boolean',
                                          string='Line number ok', readonly=True, multi='line_num',
                                          store={'wizard.import.in.line.simulation.screen': (lambda self, cr, uid, ids, c={}: ids, ['line_number'], 20)}),
        'str_line_number': fields.function(_get_l_num, method=True, type='char', size=32,
                                           string='Line', readonly=True, multi='line_num',
                                           store={'wizard.import.in.line.simulation.screen': (lambda self, cr, uid, ids, c={}: ids, ['line_number'], 20)}),
        'type_change': fields.selection([('', ''),
                                         ('split', 'Split'),
                                         ('error', 'Error'),
                                         ('del', 'Del.'),
                                         ('new', 'New')], string='CHG', readonly=True),
        'error_msg': fields.text(string='Error message', readonly=True),
        'parent_line_id': fields.many2one('wizard.import.in.line.simulation.screen', string='Parent line', readonly=True),
        # Values after import
        'imp_product_id': fields.many2one('product.product', string='Product', readonly=True),
        'imp_asset_id': fields.many2one('product.asset', string='Asset', readonly=True),
        'imp_product_qty': fields.float(digits=(16, 2), string='Qty to Process', readonly=True),
        'imp_uom_id': fields.many2one('product.uom', string='UoM', readonly=True),
        'imp_price_unit': fields.float(digits=(16, 2), string='Price Unit', readonly=True),
        'imp_cost': fields.function(_get_imported_values, method=True, type='float', multi='imported',
                                    digits=(16, 2), string='Cost', readonly=True, store=False),
        'discrepancy': fields.function(_get_imported_values, method=True, type='float', multi='imported',
                                       digits=(16, 2), string='Discre.', readonly=True, store=False),
        'imp_currency_id': fields.many2one('res.currency', string='Curr.', readonly=True),
        'imp_batch_id': fields.many2one('stock.production.lot', string='Batch Number', readonly=True),
        'imp_batch_name': fields.char(size=128, string='Batch Number', readonly=True),
        'imp_exp_date': fields.date(string='Expiry date', readonly=True),
        'imp_packing_list': fields.char(size=256, string='Packing list', readonly=True),
        'message_esc1': fields.char(size=256, string='Message ESC 1', readonly=True),
        'message_esc2': fields.char(size=256, string='Message ESC 2', readonly=True),
        # Computed fields
        'lot_check': fields.function(
            _get_values,
            method=True,
            type='boolean',
            string='B.Num',
            readonly=True,
            store=False,
            multi='computed',
        ),
        'exp_check': fields.function(
            _get_values,
            method=True,
            type='boolean',
            string='Exp',
            readonly=True,
            store=False,
            multi='computed',
        ),
        'kc_check': fields.function(
            _get_values,
            method=True,
            type='char',
            size=8,
            string='KC',
            readonly=True,
            store=False,
            multi='computed',
        ),
        'dg_check': fields.function(
            _get_values,
            method=True,
            type='char',
            size=8,
            string='DG',
            readonly=True,
            store=False,
            multi='computed',
        ),
        'np_check': fields.function(
            _get_values,
            method=True,
            type='char',
            size=8,
            string='CS',
            readonly=True,
            store=False,
            multi='computed',
        ),
        'integrity_status': fields.selection(
            selection=INTEGRITY_STATUS_SELECTION,
            string=' ',
            readonly=True,
        ),
    }

    _defaults = {
        'integrity_status': 'empty',
    }

    def import_line(self, cr, uid, ids, values, prodlot_cache=None, context=None):
        '''
        Write the line with the values
        '''
        prod_obj = self.pool.get('product.product')
        uom_obj = self.pool.get('product.uom')
        prodlot_obj = self.pool.get('stock.production.lot')

        if isinstance(ids, (int, long)):
            ids = [ids]

        if context is None:
            context = {}

        if prodlot_cache is None:
            prodlot_cache = {}

        errors = []
        warnings = []

        for line in self.browse(cr, uid, ids, context=context):
            write_vals = {}

            # Product
            prod_id = False
            if (values[1] and values[1] == line.move_product_id.default_code):
                prod_id = line.move_product_id and line.move_product_id.id or False
                write_vals['imp_product_id'] = prod_id
            else:
                prod_id = False
                if values[1]:
                    prod_id = PRODUCT_CODE_ID.get(values[1])

                if not prod_id and values[1]:
                    prod_ids = prod_obj.search(cr, uid, [('default_code', '=', values[1]), ], context=context)
                    if not prod_ids:
                        errors.append(_('Product not found in database'))
                    else:
                        write_vals['imp_product_id'] = prod_ids[0]
                else:
                    write_vals['imp_product_id'] = prod_id

            product = False
            if write_vals.get('imp_product_id'):
                product = prod_obj.browse(cr, uid, write_vals.get('imp_product_id'), context=context)


            # Product Qty
            err_msg = _('Incorrect float value for field \'Product Qty\'')
            try:
                qty = float(values[3])
                write_vals['imp_product_qty'] = qty
            except Exception:
                errors.append(err_msg)
                write_vals['type_change'] = 'error'

            # UoM
            uom_value = values[4]
            if str(uom_value) == line.move_uom_id.name:
                write_vals['imp_uom_id'] = line.move_uom_id.id
            else:
                uom_id = UOM_NAME_ID.get(str(uom_value))
                if not uom_id:
                    uom_ids = uom_obj.search(cr, uid, [('name', '=', str(uom_value))], context=context)
                    if uom_ids:
                        write_vals['imp_uom_id'] = uom_ids[0]
                    else:
                        errors.append(_('UoM not found in database'))
                else:
                    write_vals['imp_uom_id'] = uom_id

            # Check UoM consistency
            if write_vals.get('imp_uom_id') and product:
                prod_uom_c_id = product.uom_id.category_id.id
                uom_c_id = uom_obj.browse(cr, uid, write_vals['imp_uom_id']).category_id.id
                if prod_uom_c_id != uom_c_id:
                    errors.append(_("Given UoM is not compatible with the product UoM"))

            # Unit price
            err_msg = _('Incorrect float value for field \'Price Unit\'')
            try:
                unit_price = float(values[5])
                write_vals['imp_price_unit'] = unit_price
            except Exception:
                errors.append(err_msg)

            # Currency
            currency_value = values[6]
            line_currency = False
            if line.move_currency_id:
                line_currency = line.move_currency_id
            elif line.parent_line_id and line.parent_line_id.move_currency_id:
                line_currency = line.parent_line_id.move_currency_id

            if line_currency:
                write_vals['imp_currency_id'] = line_currency.id
                if str(currency_value) != line_currency.name:
                    err_msg = _('The currency on the Excel file is not the same as the currency of the IN line - You must have the same currency on both side - Currency of the initial line kept.')
                    errors.append(err_msg)

            # Batch
            batch_value = values[7]
            lot_check = line.lot_check
            exp_check = line.exp_check
            if product:
                lot_check = product.batch_management
                exp_check = product.perishable
            if not lot_check and not exp_check and batch_value:
                warnings.append(_('A batch is defined on the imported file but the product doesn\'t require batch number - Batch ignored'))
            elif batch_value:
                batch_id = PRODLOT_NAME_ID.get(str(batch_value))
                batch_ids = prodlot_obj.search(cr, uid, [('product_id', '=', write_vals['imp_product_id'])], context=context)
                if not batch_id or batch_id not in batch_ids:
                    batch_id = None # UFTP-386: If the batch number does not belong to the batch_idS of the given product --> set it to None again!
                    batch_ids = prodlot_obj.search(cr, uid, [('name', '=', str(batch_value)), ('product_id', '=', write_vals['imp_product_id'])], context=context)
                    if batch_ids:
                        batch_id = batch_ids[0]
                        PRODLOT_NAME_ID.setdefault(str(batch_value), batch_id)
                    else:
                        if lot_check and prodlot_cache.get(write_vals['imp_product_id'], {}).get(str(batch_value)):
                            write_vals.update({
                                'imp_batch_name': str(batch_value),
                                'imp_exp_date': prodlot_cache[write_vals['imp_product_id']][str(batch_value)],
                            })
                        else:
                            write_vals['imp_batch_name'] = str(batch_value)

                if batch_id:
                    write_vals.update({
                        'imp_batch_id': batch_id,
                        'imp_batch_name': str(batch_value),
                    })
                else:
                    # UFTP-386: Add the warning message indicating that the batch does not exist for THIS product (but for others!)
                    # If the batch is a completely new, no need to warn.
                    batch_ids = prodlot_obj.search(cr, uid, [('name', '=', str(batch_value))], context=context)
                    if batch_ids:
                        warnings.append(_('The given batch does not exist for the given product, but will be created automatically during the process.'))
                        write_vals.update({'imp_batch_name': str(batch_value),})

            # Expired date
            exp_value = values[8]
            if not lot_check and not exp_check and exp_value:
                warnings.append(_('An expired date is defined on the imported file but the product doesn\'t require expired date - Expired date ignored'))
            elif exp_value:
                if exp_value and type(exp_value) == type(DateTime.now()):
                    write_vals['imp_exp_date'] = exp_value.strftime('%Y-%m-%d')
                elif exp_value and isinstance(exp_value, str):
                    try:
                        time.strptime(exp_value, '%Y-%m-%d')
                        write_vals['imp_exp_date'] = exp_value
                    except ValueError:
                        err_msg = _('Incorrect date value for field \'Expired date\'')
                        errors.append(err_msg)
                elif exp_value:
                    err_msg = _('Incorrect date value for field \'Expired date\'')
                    errors.append(err_msg)

                if write_vals.get('imp_exp_date') and write_vals.get('imp_batch_id') and lot_check:
                    batch_exp_date = prodlot_obj.browse(cr, uid, write_vals.get('imp_batch_id'), context=context).life_date
                    if batch_exp_date != write_vals.get('imp_exp_date'):
                        warnings.append(_('The \'Expired date\' value doesn\'t match with the expired date of the Batch - The expired date of the Batch was kept.'))
                        write_vals['imp_exp_date'] = batch_exp_date
                elif write_vals.get('imp_exp_date') and write_vals.get('imp_batch_name') and lot_check:
                    if prodlot_cache.get(write_vals['imp_product_id'], {}).get(write_vals['imp_batch_name'], False):
                        if prodlot_cache.get(write_vals['imp_product_id'], {}).get(write_vals['imp_batch_name'], False) != write_vals['imp_exp_date']:
                            warnings.append(_('The \'Expired date\' value doesn\'t match with the expired date of the Batch - The expired date of the Batch was kept.'))
                            write_vals['imp_exp_date'] = prodlot_cache.get(write_vals['imp_product_id'], {}).get(write_vals['imp_batch_name'], False)
            elif not exp_value and write_vals.get('imp_batch_id') and lot_check:
                write_vals['imp_exp_date'] = prodlot_obj.browse(cr, uid, write_vals.get('imp_batch_id'), context=context).life_date
            elif not exp_value and write_vals.get('imp_batch_name'):
                if lot_check and prodlot_cache.get(write_vals['imp_product_id'], {}).get(write_vals['imp_batch_name'], False):
                    warnings.append(_('The \'Expired date\' is not defined in file - The expired date of the Batch was put instead.'))


            if exp_check and not lot_check and batch_value:
                write_vals.update({
                    'imp_batch_id': False,
                    'imp_batch_name': False,
                })
                if write_vals.get('imp_exp_date'):
                    warnings.append(_('A batch is defined on the imported file but the product doesn\'t require batch number - Batch ignored, expiry date kept'))
                else:
                    warnings.append(_('A batch is defined on the imported file but the product doesn\'t require batch number - Batch ignored'))

            # If no batch defined, search batch corresponding with expired date or create a new one
            if product and lot_check and not write_vals.get('imp_batch_id'):
                exp_date = write_vals.get('imp_exp_date')

                if batch_value and exp_date:
                    # If a name and an expiry date for batch are defined, create a new batch
                    prodlot_cache.setdefault(product.id, {})
                    prodlot_cache[product.id].setdefault(str(batch_value), exp_date)
                    write_vals.update({
                        'imp_batch_name': str(batch_value),
                        'imp_exp_date': exp_date,
                    })

                if not write_vals.get('imp_batch_id') and not write_vals.get('imp_batch_name'):
                    errors.append(_('No batch found in database and you need to define a name AND an expiry date if you expect an automatic creation.'))
                    write_vals['imp_batch_id'] = False

            # Packing list
            write_vals['imp_packing_list'] = values[9]

            # Message ESC 1
            write_vals['message_esc1'] = values[10]
            # Message ESC 2
            write_vals['message_esc2'] = values[11]

            write_vals['integrity_status'] = self.check_integrity_status(cr, uid, write_vals, context=context)
            if write_vals['integrity_status'] != 'empty' or len(errors) > 0:
                write_vals['type_change'] = 'error'

            if line.type_change == 'new':
                write_vals['type_change'] = 'error'
                errors.append(_('Line does not correspond to original IN'))

            error_msg = line.error_msg or ''
            for err in errors:
                if error_msg:
                    error_msg += ' - '
                error_msg += err

            for warn in warnings:
                if error_msg:
                    error_msg += ' - '
                error_msg += warn

            write_vals['error_msg'] = error_msg

            self.write(cr, uid, [line.id], write_vals, context=context)

        return errors

    def get_error_msg(self, cr, uid, ids, context=None):
        '''
        Display the error message
        '''
        if isinstance(ids, (int, long)):
            ids = [ids]

        for line in self.browse(cr, uid, ids, context=context):
            if line.error_msg:
                raise osv.except_osv(_('Warning'), line.error_msg)
            if line.integrity_status != 'empty':
                sel = self.fields_get(cr, uid, ['integrity_status'])
                integrity_message = dict(sel['integrity_status']['selection']).get(getattr(line, 'integrity_status'), getattr(line, 'integrity_status'))
                name = '%s,%s' % (self._name, 'integrity_status')
                tr_ids = self.pool.get('ir.translation').search(cr, uid, [('type', '=', 'selection'), ('name', '=', name), ('src', '=', integrity_message)])
                if tr_ids:
                    integrity_message = self.pool.get('ir.translation').read(cr, uid, tr_ids, ['value'])[0]['value']

                raise osv.except_osv(_('Warning'), integrity_message)

        return True

    def check_integrity_status(self, cr, uid, vals, context=None):
        '''
        Return the integrity_status of the line
        '''
        product_obj = self.pool.get('product.product')
        prodlot_obj = self.pool.get('stock.production.lot')
        product = vals.get('imp_product_id') and product_obj.browse(cr, uid, vals['imp_product_id'], context=context) or False
        prodlot_id = vals.get('imp_batch_id') and prodlot_obj.browse(cr, uid, vals['imp_batch_id'], context=context) or False
        exp_date = vals.get('imp_exp_date')
        prodlot_name = vals.get('imp_batch_name')

        if not product:
            return 'empty'

        if not (product.perishable or product.batch_management):
            if exp_date or prodlot_id:
                return 'no_lot_needed'

        if product.batch_management:
            if not prodlot_id and not prodlot_name:
                return 'missing_lot'

            if prodlot_id and prodlot_id.type != 'standard':
                return 'wrong_lot_type_need_standard'

        if product.perishable:
            if not exp_date:
                return 'missing_date'

            if not product.batch_management and prodlot_id and prodlot_id.type != 'internal':
                return 'wrong_lot_type_need_internal'

        return 'empty'

    def _get_lot_in_cache(self, cr, uid, lot_cache, product_id, name, exp_date, context=None):
        '''
        Get the lot from the cache or from the DB
        '''
        lot_obj = self.pool.get('stock.production.lot')

        if context is None:
            context = {}

        lot_cache.setdefault(product_id, {})
        lot_cache[product_id].setdefault(name, False)

        if lot_cache[product_id][name]:
            batch_id = lot_cache[product_id][name]
        else:
            lot_ids = lot_obj.search(cr, uid, [
                ('product_id', '=', product_id),
                ('name', '=', name),
                ('life_date', '=', exp_date),
            ], context=context)

            if lot_ids:
                batch_id = lot_ids[0]
            else:
                batch_id = lot_obj.create(cr, uid, {
                    'product_id': product_id,
                    'name': name,
                    'life_date': exp_date,
                }, context=context)

            lot_cache[product_id][name] = batch_id

        return batch_id

    def put_in_memory_move(self, cr, uid, ids, partial_id, context=None):
        '''
        Create a stock.move.memory.in for each lines
        '''
        move_obj = self.pool.get('stock.move.in.processor')

        if isinstance(ids, (int, long)):
            ids = [ids]

        move_ids = []
        mem_move_ids = []
        lot_cache = {}
        for line in self.browse(cr, uid, ids, context=context):
            if line.type_change in ('del', 'error', 'new'):
                continue

            move = False
            if line.type_change == 'split':
                move = line.parent_line_id.move_id
            else:
                move = line.move_id

            batch_id = line.imp_batch_id and line.imp_batch_id.id or False
            if not batch_id and line.imp_batch_name and line.imp_exp_date:
                batch_id = self._get_lot_in_cache(
                    cr,
                    uid,
                    lot_cache,
                    line.imp_product_id.id,
                    line.imp_batch_name,
                    line.imp_exp_date,
                    context=context,
                )

            vals = {'change_reason': '%s - %s' % (line.message_esc1, line.message_esc2),
                    'cost': line.imp_price_unit,
                    'currency': line.imp_currency_id.id,
                    'expiry_date': line.imp_exp_date,
                    'line_number': line.line_number,
                    'move_id': move.id,
                    'prodlot_id': batch_id,
                    'product_id': line.imp_product_id.id,
                    'uom_id': line.imp_uom_id.id,
                    'ordered_quantity': move.product_qty,
                    'quantity': line.imp_product_qty,
                    'wizard_id': partial_id}

            mem_move_ids.append(move_obj.create(cr, uid, vals, context=context))
            if move:
                move_ids.append(move.id)

        return mem_move_ids, move_ids

wizard_import_in_line_simulation_screen()
