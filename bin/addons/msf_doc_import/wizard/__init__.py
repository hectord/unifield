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

from tools.translate import _

# if you update a file in PO_COLUMNS_HEADER_FOR_INTEGRATION, check also NEW_COLUMNS_HEADER, you also need to modify the method export_po_integration, get_po_row_values and get_po_header_row_values.
# in PO_COLUMNS_HEADER_FOR_INTEGRATION, you have all the importable columns possible
PO_COLUMNS_HEADER_FOR_INTEGRATION = [
    (_('Line'), 'number'),
    (_('Ext. Ref.'), 'string'),
    (_('Product Code'), 'string'),
    (_('Product Description'), 'string'),
    (_('Product Qty*'), 'number'),
    (_('Product UoM*'), 'string'),
    (_('Price Unit*'), 'number'),
    (_('Currency*'), 'string'),
    (_('Origin*'), 'string'),
    (_('Delivery Reqd Date'), 'date'),
    (_('Delivery Confd Date*'), 'date'),
    (_('Nomen Name'), 'string'),
    (_('Nomen Group'), 'string'),
    (_('Nomen Family'), 'string'),
    (_('Comment'), 'string'),
    (_('Notes'), 'string'),
    (_('Project Ref.*'), 'string'),
]

PO_COLUMNS_FOR_INTEGRATION = [x for (x, y) in PO_COLUMNS_HEADER_FOR_INTEGRATION]

# if you update a file in NEW_COLUMNS_HEADER, you also need to modify the method export_po_integration, get_po_row_values and get_po_header_row_values.
# in NEW_COLUMNS_HEADER, you choose which columns you want to actually import (it is filtered on what you want if you compare with PO_COLUMNS_HEADER_FOR_INTEGRATION)
NEW_COLUMNS_HEADER = [
('Line', 'number'), ('Product Code', 'string'), ('Product Description', 'string'), ('Quantity', 'number'), ('UoM', 'string'), ('Price', 'number'), ('Delivery Request Date', 'date'),
('Delivery Confirmed Date', 'date'),('Origin', 'string'), ('Comment', 'string'), ('Notes', 'string'), ('Supplier Reference', 'string'), ('Incoterm', 'string')]

#Important NOTE: I didn't set the fields of type date with the attribute 'date' (2nd part of the tuple) because for Excel, when a date is empty, the field becomes '1899-30-12' as default. So I set 'string' instead for the fields date.

PO_COLUMNS_HEADER_FOR_IMPORT=[
(_('Product Code'), 'string'), (_('Product Description'), 'string'), (_('Quantity'), 'number'), (_('UoM'), 'string'), (_('Price'), 'number'),
(_('Delivery Request Date'), 'date'), (_('Currency'), 'string'), (_('Comment'), 'string'), (_('Justification Code'), 'string'), (_('Justification Coordination'), 'string'), (_('HQ Remarks'), 'string'), (_('Justification Y/N'), 'string')]
PO_LINE_COLUMNS_FOR_IMPORT = [x for (x, y) in PO_COLUMNS_HEADER_FOR_IMPORT]

FO_COLUMNS_HEADER_FOR_IMPORT=[
(_('Product Code'), 'string'), (_('Product Description'), 'string'), (_('Quantity'), 'number'), (_('UoM'), 'string'), (_('Price'), 'number'),
(_('Delivery requested date'), 'date'), (_('Currency'), 'string'), (_('Comment'), 'string')]
FO_LINE_COLUMNS_FOR_IMPORT = [x for (x, y) in FO_COLUMNS_HEADER_FOR_IMPORT]

INT_COLUMNS_HEADER_FOR_IMPORT = [
(_('Product Code'), 'string'), (_('Product Description'), 'string'), (_('Quantity'), 'number'), (_('UoM'), 'string'), (_('Kit'), 'string'),
(_('Asset'), 'string'), (_('Batch Number'), 'string'), (_('Expiry Date'), 'DateTime'), (_('Source Location'), 'string'), (_('Destination Location'), 'string')]
INT_LINE_COLUMNS_FOR_IMPORT = [x for (x, y) in INT_COLUMNS_HEADER_FOR_IMPORT]

IN_COLUMNS_HEADER_FOR_IMPORT = [
(_('Product Code'), 'string'), (_('Product Description'), 'string'), (_('Quantity'), 'number'), (_('UoM'), 'string'), (_('Kit'), 'string'),
(_('Asset'), 'string'), (_('Batch Number'), 'string'), (_('Expiry Date'), 'DateTime'), (_('Source Location'), 'string'), (_('Destination Location'), 'string')]
IN_LINE_COLUMNS_FOR_IMPORT = [x for (x, y) in IN_COLUMNS_HEADER_FOR_IMPORT]

OUT_COLUMNS_HEADER_FOR_IMPORT = [
(_('Product Code'), 'string'), (_('Product Description'), 'string'), (_('Quantity'), 'number'), (_('UoM'), 'string'), (_('Kit'), 'string'),
(_('Asset'), 'string'), (_('Batch Number'), 'string'), (_('Expiry Date'), 'DateTime'), (_('Source Location'), 'string'), (_('Destination Location'), 'string')]
OUT_LINE_COLUMNS_FOR_IMPORT = [x for (x, y) in OUT_COLUMNS_HEADER_FOR_IMPORT]

IR_COLUMNS_HEADER_FOR_IMPORT=[
(_('Product Code'), 'string'), (_('Product Description'), 'string'), (_('Quantity'), 'number'), (_('Cost Price'), 'number'), (_('UoM'), 'string'),
(_('Currency'), 'string'), (_('Comment'), 'string')]
IR_COLUMNS_FOR_IMPORT = [x for (x, y) in IR_COLUMNS_HEADER_FOR_IMPORT]

TENDER_COLUMNS_HEADER_FOR_IMPORT=[
(_('Product Code'), 'string'), (_('Product Description'), 'string'), (_('Quantity'), 'number'), (_('UoM'), 'string'),
(_('Price'), 'number'), (_('Delivery Requested Date'), 'DateTime')]
TENDER_COLUMNS_FOR_IMPORT = [x for (x, y) in TENDER_COLUMNS_HEADER_FOR_IMPORT]

AUTO_SUPPLY_COLUMNS_HEADER_FOR_IMPORT = [
(_('Product Code'), 'string'), (_('Product Description'), 'string'), (_('UoM'), 'string'), (_('Qty'), 'number')]
AUTO_SUPPLY_LINE_COLUMNS_FOR_IMPORT = [x for (x,y) in AUTO_SUPPLY_COLUMNS_HEADER_FOR_IMPORT]

ORDER_CYCLE_COLUMNS_HEADER_FOR_IMPORT = [
(_('Product Code'), 'string'), (_('Product Description'), 'string'), (_('UoM'), 'string'), (_('Safety stock'), 'number')]
ORDER_CYCLE_LINE_COLUMNS_FOR_IMPORT = [x for (x,y) in ORDER_CYCLE_COLUMNS_HEADER_FOR_IMPORT]

THRESHOLD_COLUMNS_HEADER_FOR_IMPORT = [
(_('Product Code'), 'string'), (_('Product Description'), 'string'), (_('UoM'), 'string'), (_('Product Qty'), 'number'), (_('Threshold value'), 'number')]
THRESHOLD_LINE_COLUMNS_FOR_IMPORT = [x for (x,y) in THRESHOLD_COLUMNS_HEADER_FOR_IMPORT]

STOCK_WAREHOUSE_ORDERPOINT_COLUMNS_HEADER_FOR_IMPORT = [
(_('Product Code'), 'string'), (_('Product Description'), 'string'), (_('UoM'), 'string'), (_('Product Min Qty'), 'number'), (_('Product Max Qty'), 'number'), (_('Qty Multiple'), 'number'), ]
STOCK_WAREHOUSE_ORDERPOINT_LINE_COLUMNS_FOR_IMPORT = [x for (x,y) in STOCK_WAREHOUSE_ORDERPOINT_COLUMNS_HEADER_FOR_IMPORT]

PRODUCT_LIST_COLUMNS_HEADER_FOR_IMPORT = [
(_('Product Code'), 'string'), (_('Product Description'), 'string'), (_('Comment'), 'string')]
PRODUCT_LIST_COLUMNS_FOR_IMPORT = [x for (x,y) in PRODUCT_LIST_COLUMNS_HEADER_FOR_IMPORT]

SUPPLIER_CATALOG_COLUMNS_HEADER_FOR_IMPORT = [
    (_('Product Code'), 'string'),
    (_('Product Description'), 'string'),
    (_('UoM'), 'string'),
    (_('Min. Qty'), 'number'),
    (_('Unit Price'), 'number',),
    (_('SoQ Rounding'), 'number'),
    (_('Min. Order Qty.'), 'number'),
    (_('Comment'), 'string'),
]
SUPPLIER_CATALOG_COLUMNS_FOR_IMPORT = [x for (x,y) in SUPPLIER_CATALOG_COLUMNS_HEADER_FOR_IMPORT]

import wizard_import_po
import stock_partial_picking
import wizard_import_po_line
import wizard_import_fo_line
import wizard_import_ir_line
import wizard_import_picking_line
import wiz_common_import
import wizard_import_tender_line
import wizard_delete_lines
import wizard_import_auto_supply_line
import wizard_import_order_cycle_line
import wizard_import_threshold_value_line
import wizard_import_stock_warehouse_order_point_line
import wizard_import_product_list
import wizard_import_supplier_catalogue
import wizard_po_simulation_screen
import wizard_in_simulation_screen
