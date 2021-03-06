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
    "name" : "MSF Modules",
    "version" : "1.0",
    "author" : "TeMPO Consulting, MSF",
    "category": "Others",
    "description": """
        This module aims in adding a reason type for all stock picking documents
meaning all stock moves in order to make a specific and precise statistics on 
stock moves.
    """,
    "website": "http://unifield.msf.org",
    "init_xml": [
    ],
    "depends" : [
        "stock",
        "sale",
        "procurement",
    ],
    "update_xml": [
        "reason_type_view.xml",
        "stock_view.xml",
        "reason_type_data.xml",
        "security/ir.model.access.csv",
    ],
    "demo_xml": [
    ],
    "test": [
        "test/chained_location.yml",
    ],
    "installable": True,
    "active": False,
}

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
