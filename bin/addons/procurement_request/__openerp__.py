# -*- coding: utf-8 -*-
##############################################################################
#
#    OpenERP, Open Source Management Solution
#    Copyright (C) 2011 TeMPO Consulting, MSF 
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
    "name": "Internal Request",
    "version": "1.0",
    "depends": ["base", 
                "sale", 
                "sale_override", 
                "stock_override", 
                "msf_order_date", 
                "stock",
                "threshold_value",
                "procurement_cycle",
                "procurement_auto",
		],
    "author": "TeMPO Consulting, MSF",
    "website": "",
    "category": "Sales & Purchases",
    "description": """
    This modules aims to create a new document called Internal Request to 
    identify the needs of all and source from stock or from order
    """,
    "init_xml": [
    ],
    'update_xml': [
        'procurement_request_view.xml',
        'procurement_request_sequence.xml',
        'procurement_request_workflow.xml',
        'procurement_request_wizard.xml',
        'procurement_request_report.xml',
        'wizard/wizard_import_list_view.xml',
    ],
    'demo_xml': [
    ],
    'test': [
        'test/data.yml',
        'test/proc_request.yml',
        'test/deactivate_product_valid_ir.yml',
        'test/deactivate_product_validate_ir.yml',
    ],
    'installable': True,
    'active': False,
#    'certificate': 'certificate',
}

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
