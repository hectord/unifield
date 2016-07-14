#!/usr/bin/env python
# -*- coding: utf-8 -*-
##############################################################################
#
#    OpenERP, Open Source Management Solution
#    Copyright (C) 2011 TeMPO Consulting, MSF. All Rights Reserved
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

class account_move_reconcile(osv.osv):
    _name = "account.move.reconcile"
    _inherit = "account.move.reconcile"

    def reconcile_partial_check(self, cr, uid, ids, type='auto', context=None):
        """
        WARNING: This method has been taken from account module from OpenERP
        """
        # @@@override@account.account.py
        total = 0.0
        for rec in self.browse(cr, uid, ids, context=context):
            for line in rec.line_partial_ids:
                total += (line.debit_currency or 0.0) - (line.credit_currency or 0.0)
        if not total:
            self.pool.get('account.move.line').write(cr, uid,
                map(lambda x: x.id, rec.line_partial_ids),
                {'reconcile_id': rec.id }
            )
        # @@@end
        return True

    def name_get(self, cr, uid, ids, context=None):
        """
        WARNING: This method has been taken from account module from OpenERP
        """
        # @@@override@account.account.py
        if not ids:
            return []
        result = []
        for r in self.browse(cr, uid, ids, context=context):
            total = reduce(lambda y,t: (t.debit_currency or 0.0) - (t.credit_currency or 0.0) + y, r.line_partial_ids, 0.0)
            if total:
                name = '%s (%.2f)' % (r.name, total)
                result.append((r.id,name))
            else:
                result.append((r.id,r.name))
        # @@@end
        return result

account_move_reconcile()
# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
