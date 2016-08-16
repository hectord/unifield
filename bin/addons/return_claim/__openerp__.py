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

{
    "name": "MSF Return-Claim",
    "version": "0.1",
    "depends": ["purchase",
                "sale",
                "stock",
                "msf_config_locations", # for location ids from load common values
                "product_attributes", # for product menu
                "delivery_mechanism", # for do_incoming function
                "kit", # for compute availability with production lots
                ],
    "author": "MSF",
    "website": "",
    "category": "Specific Modules",
    "description": """
        Return and Claims
    """,
    "init_xml": [
    ],
    'update_xml': [
        'return_claim_view.xml',
        'return_claim_sequence.xml',
        'wizard/add_event_view.xml',
        'security/ir.model.access.csv',
    ],
    'demo_xml': [
    ],
    'test': [
        'test/return_claim_data.yml',
#       'test/return_claim_so_po_in.yml',
        'test/return_claim_from_scratch.yml',
        'test/return_claim_wizard_process.yml'
    ],
    'installable': True,
    'active': False,
}
