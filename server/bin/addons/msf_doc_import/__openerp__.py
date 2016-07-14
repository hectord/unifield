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

{
    "name": "Import Files in Excel Format",
    "version": "0.1",
    "description": "This module enables to import file in xls format",
    "author": "MSF - TeMPO Consulting",
    "category": "Sale",
    "depends": [
        "sale",
        "purchase",
        "tender_flow",
        "msf_supply_doc_export",
        "spreadsheet_xml",
        "finance",
        "register_accounting",
        "return_claim",
        "specific_rules",
        "product_attributes",
    ],
    "init_xml": [],
    "update_xml": [
        'doc_import_report.xml',
        'view/sale_order_import_lines_view.xml',
        'view/internal_request_import_line_view.xml',
        'view/tender_import_line_view.xml',
        'view/purchase_order_import_line_view.xml',
        'view/initial_stock_inventory_line_view.xml',
        'view/stock_cost_reevaluation_view.xml',
        'view/product_list_view.xml',
        'view/account_view.xml',
        'view/stock_picking_import_lines_view.xml',
        'view/replenishment_rules_view.xml',
        'view/supplier_catalogue_view.xml',
        'wizard/wizard_import_po_line_view.xml',
        'wizard/wizard_import_fo_line.xml',
        'wizard/wizard_import_tender_line.xml',
        'wizard/wizard_imprort_ir_line.xml',
        'wizard/wizard_import_picking_line.xml',
        'wizard/wizard_import_auto_supply_line.xml',
        'wizard/wizard_import_order_cycle_line.xml',
        'wizard/wizard_import_threshold_value_line.xml',
        'wizard/wizard_import_stock_warehouse_order_point_line.xml',
        'wizard/wizard_import_product_list.xml',
        'wizard/wizard_import_supplier_catalogue.xml',
        'wizard/wizard_po_simulation_screen_view.xml',
        'wizard/wizard_in_simulation_screen_view.xml',
        'view/composition_kit_import_line_view.xml',
        'wizard/wizard_import_po_view.xml',
        'wizard/wizard_delete_lines_view.xml',
        'wizard/wiz_common_import_view.xml',
        'data/msf_doc_import_data.xml',
        'data/inactive_categ.xml',
        'workflow/purchase_workflow.xml',
        'workflow/sale_workflow.xml',
        'workflow/tender_flow_workflow.xml',
        'workflow/procurement_request_workflow.xml',
        'doc_import_report.xml'
    ],
    "demo_xml": [],
    "test": [
        'test/data.yml',
# test for the import in English
        'test/import_ir.yml',
        'test/import_po.yml',
        'test/import_migration.yml',
        'test/import_so.yml',
        'test/import_composition_kit.yml',
        'test/import_tender.yml',
    ],
    "installable": True,
    "active": False
}
