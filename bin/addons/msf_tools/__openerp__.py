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
    "name": "MSF Tools",
    "version": "1.0",
    "depends": ["base",
                "product",
                "object_query",
                ],
    "author": "MSF, TeMPO Consulting",
    "website": "",
    "category": "Specific Modules",
    "description": """
        Interface for Msf Tools
    """,
    "init_xml": [
    ],
    'update_xml': [
        'views/automated_import_view.xml',
        'views/automated_import_function_view.xml',
        'views/automated_import_job_view.xml',
        'security/ir.model.access.csv',
        'automated_import_data.xml',
    ],
    'demo_xml': [
    ],
    'test': [# tests should be performed in base classes to avoid cyclic dependencies
    ],
    'installable': True,
    'active': False,
}
