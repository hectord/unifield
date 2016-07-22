# -*- coding: utf-8 -*-
##############################################################################
#
#    OpenERP, Open Source Management Solution
#    Copyright (C) 2004-2010 Tiny SPRL (<http://tiny.be>).
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
    'name': 'MSF Audit Trail',
    'version': '1.0',
    'category': 'Generic Modules/Others',
    'description': """
    This module gives the administrator the rights
    to track every user operation on all the objects
    of the system.

    Administrator can subscribe rules for read,write and
    delete on objects and can check logs.
    """,
    'author': 'OpenERP SA, TeMPO Consulting, MSF',
    'website': 'http://www.unifield.org',
    'depends': ['base', 'purchase', 'account'],
    'init_xml': [],
    'update_xml': [
        'wizard/audittrail_view_log_view.xml',
        'audittrail_view.xml',
        'security/ir.model.access.csv',
        'security/audittrail_security.xml',
        'data/audittrail_data_picking.yml',
        'data/audittrail_data_sale.yml',
        'data/audittrail_data_purchase.yml',
        'data/audittrail_data_products.yml',
        'audittrail_report.xml',
        'audittrail_invoice_data.yml',
    ],
    'demo_xml': [],
    'installable': True,
    'active': False,
}
# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4: