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

import base64
from os import path

from osv import fields
from osv import osv
from tools.translate import _

from msf_doc_import import GENERIC_MESSAGE
from msf_doc_import.wizard import INT_COLUMNS_HEADER_FOR_IMPORT as columns_header_for_internal_import
from msf_doc_import.wizard import INT_LINE_COLUMNS_FOR_IMPORT as columns_for_internal_import
from msf_doc_import.wizard import IN_COLUMNS_HEADER_FOR_IMPORT as columns_header_for_incoming_import
from msf_doc_import.wizard import IN_LINE_COLUMNS_FOR_IMPORT as columns_for_incoming_import
from msf_doc_import.wizard import OUT_COLUMNS_HEADER_FOR_IMPORT as columns_header_for_delivery_import
from msf_doc_import.wizard import OUT_LINE_COLUMNS_FOR_IMPORT as columns_for_delivery_import
from spreadsheet_xml.spreadsheet_xml_write import SpreadsheetCreator


class stock_picking(osv.osv):
    """
    We override the class for import of Internal moves
    """
    _inherit = 'stock.picking'

    _columns = {
        'filetype': fields.selection([('excel', 'Excel file'),
                                      ('xml', 'XML file')], string='Type of file',),
        'last_imported_filename': fields.char(size=128, string='Filename'),
    }

    def export_template_file(self, cr, uid, ids, context=None):
        '''
        Export the template file in Excel or Pure XML format
        '''
        if isinstance(ids, (int, long)):
            ids = [ids]

        pick = self.browse(cr, uid, ids[0], context=context)
        if not pick.filetype:
            raise osv.except_osv(_('Error'), _('You must select a file type before print the template'))

        report_name = pick.filetype == 'excel' and 'incoming.shipment.xls' or 'incoming.shipment.xml'

        datas = {'ids': ids}

        return {'type': 'ir.actions.report.xml',
                'report_name': report_name,
                'datas': datas,
                'context': context,
        }

    def wizard_import_pick_line(self, cr, uid, ids, context=None):
        '''
        Launches the wizard to import lines from a file
        '''
        # Objects
        wiz_obj = self.pool.get('wizard.import.pick.line')

        context = context is None and {} or context

        if isinstance(ids, (int, long)):
            ids = [ids]

        context.update({'active_id': ids[0]})

        picking = self.browse(cr, uid, ids[0], context=context)
        if picking.type == 'in':
            header_cols = columns_header_for_incoming_import
            cols = columns_for_incoming_import
        elif picking.type == 'out' and picking.subtype == 'standard':
            header_cols = columns_header_for_delivery_import
            cols = columns_for_delivery_import
        else:
            header_cols = columns_header_for_internal_import
            cols = columns_for_incoming_import

        columns_header = [(_(f[0]), f[1]) for f in header_cols]
        default_template = SpreadsheetCreator(_('Template of import'), columns_header, [])
        file = base64.encodestring(default_template.get_xml(default_filters=['decode.utf8']))
        export_id = wiz_obj.create(cr, uid, {'file': file,
                                             'filename_template': 'template.xls',
                                             'filename': 'Lines_Not_Imported.xls',
                                             'message': """%s %s""" % (_(GENERIC_MESSAGE), ', '.join([_(f) for f in cols])),
                                             'picking_id': ids[0],
                                             'state': 'draft',}, context=context)

        return {'type': 'ir.actions.act_window',
                'res_model': 'wizard.import.pick.line',
                'res_id': export_id,
                'view_type': 'form',
                'view_mode': 'form',
                'target': 'crush',
                'context': context,
                }

    def check_lines_to_fix(self, cr, uid, ids, context=None):
        if isinstance(ids, (int, long)):
            ids = [ids]

        message = ''
        plural = ''

        for var in self.browse(cr, uid, ids, context=context):
            if var.move_lines:
                for var in var.move_lines:
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


stock_picking()


class stock_move(osv.osv):
    _inherit = 'stock.move'

    def write(self, cr, uid, ids, vals, context=None):
        vals.update({
            'to_correct_ok': False,
            'text_error': False,
        })
        return super(stock_move, self).write(cr, uid, ids, vals, context=context)


stock_move()
