#!/usr/bin/env python
# -*- coding: utf-8 -*-
##############################################################################
#
#    OpenERP, Open Source Management Solution
#    Copyright (C) 2012 TeMPO Consulting, MSF. All Rights Reserved
#    Developer: Olivier DOSSMANN
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

class purchase_order(osv.osv):
    _name = 'purchase.order'
    _inherit = 'purchase.order'

    def create(self, cr, uid, vals, context=None):
        '''
        Change invoice method for in-kind donation PO to 'order' after its creation
        '''
        if not context:
            context = {}
        res = super(purchase_order, self).create(cr, uid, vals, context)
        if vals.get('order_type', False) and vals.get('order_type') == 'in_kind':
            vals.update({'invoice_method': 'picking'})

        return res

    def write(self, cr, uid, ids, vals, context=None):
        """
        Change invoice method for in-kind donation PO after a write
        """
        if not context:
            context = {}
        res = super(purchase_order, self).write(cr, uid, ids, vals, context)
        if vals.get('order_type', False) and vals.get('order_type') == 'in_kind':
            cr.execute("UPDATE purchase_order SET invoice_method = 'picking' WHERE id in %s", (tuple(ids),))
        return res

    def onchange_internal_type(self, cr, uid, ids, order_type, partner_id, categ, dest_partner_id=False, warehouse_id=False, delivery_requested_date=False):
        """
        Change invoice method for in-kind donation
        """
        res = super(purchase_order, self).onchange_internal_type(cr, uid, ids, order_type, partner_id, categ, dest_partner_id, warehouse_id, delivery_requested_date)
        if order_type in ['in_kind']:
            v = res.get('value', {})
            v.update({'invoice_method': 'picking'})
            res.update({'value': v})
        return res

purchase_order()
# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
