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
    "name": "Stock Replenishment Schedule",
    "version": "1.0",
    "depends": [
                "base",
                "stock",
                "procurement",
    ],
    "author": "TeMPO Consulting, MSF",
    "website": "",
    "category": "Warehouse",
    "description": """
        This module aims to add an object to schedule
        automatic dates to replenishment
    """,
    "init_xml": [
    ],
    'update_xml': [
        'scheduler_view.xml',
        'scheduler_data.xml',
        'security/ir.model.access.csv',
    ],
    'demo_xml': [
    ],
    "test": [
        'test/daily_test.yml',
        'test/weekly_test.yml',
        'test/monthly_test.yml',
        'test/yearly_test.yml',
    ],
    'installable': True,
    'active': False,
#    'certificate': 'certificate',
}

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
