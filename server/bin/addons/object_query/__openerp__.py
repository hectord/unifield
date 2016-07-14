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
    "name" : "MSF Partners",
    "version" : "1.0",
    "author" : "TeMPO Consulting, MSF",
    "category": "Others",
    "description": """
        This modules aims to differentiate Internal/External partners
        It also aims to create a new type of partner: Manufacturer
    """,
    "website": "http://unifield.msf.org",
    "depends" : [
        "base",
        "product",
        "sale",
        "purchase",
    ],
    "init_xml": [
        'query_data.xml',
    ],
    "update_xml": [
        'query_view.xml',
        'security/ir.model.access.csv'
    ],
    "demo_xml": [],
    "test": [],
    "installable": True,
    "active": False,
}
