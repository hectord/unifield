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
from tools.translate import _
import base64
from msf_doc_import import GENERIC_MESSAGE
from spreadsheet_xml.spreadsheet_xml_write import SpreadsheetCreator
from msf_doc_import.wizard import PRODUCT_LIST_COLUMNS_HEADER_FOR_IMPORT as columns_header_for_product_list_import
from msf_doc_import.wizard import PRODUCT_LIST_COLUMNS_FOR_IMPORT as columns_for_product_list_import

class product_list(osv.osv):
    _inherit = 'product.list'

    def wizard_import_product_list_line(self, cr, uid, ids, context=None):
        '''
        Launches the wizard to import lines from a file
        '''
        if context is None:
            context = {}
        if isinstance(ids, (int, long)):
            ids = [ids]
        context.update({'active_id': ids[0]})
        columns_header = [(_(f[0]), f[1]) for f in columns_header_for_product_list_import]
        default_template = SpreadsheetCreator('Template of import', columns_header, [])
        file = base64.encodestring(default_template.get_xml(default_filters=['decode.utf8']))
        export_id = self.pool.get('wizard.import.product.list').create(cr, uid, {'file': file,
                                                                                 'filename_template': 'Product List template.xls',
                                                                                 'message': """%s %s"""  % (_(GENERIC_MESSAGE), ', '.join([_(f) for f in columns_for_product_list_import]), ),
                                                                                 'filename': 'Lines_Not_Imported.xls',
                                                                                 'list_id': ids[0],
                                                                                 'state': 'draft',}, context)
        return {'type': 'ir.actions.act_window',
                'res_model': 'wizard.import.product.list',
                'res_id': export_id,
                'view_type': 'form',
                'view_mode': 'form',
                'target': 'crush',
                'context': context,
                }

product_list()
