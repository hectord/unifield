#!/usr/bin/env python
#-*- encoding:utf-8 -*-
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
from osv import fields
import decimal_precision as dp

class account_analytic_line(osv.osv):
    _name = 'account.analytic.line'
    _inherit = 'account.analytic.line'

    """
    As amount_currency field is changed in analytic_override module (which depends on analytic only) and that amount_currency is a field declared in account module (OpenERP addons), so we need to use the __init__() in this account_override module to avoid some problems as described in UF-2354.
    """
    def __init__(self, pool, cr):
        """
        Permits to OpenERP not attempt to update DB field with the old field_function
        """
        super(account_analytic_line, self).__init__(pool, cr)
        if self.pool._store_function.get(self._name, []):
            newstore = []
            for fct in self.pool._store_function[self._name]:
                if fct[1] not in ['currency_id', 'amount_currency']:
                    newstore.append(fct)
            self.pool._store_function[self._name] = newstore

    def join_without_redundancy(self, text='', string=''):
        return self.pool.get('account.move.line').join_without_redundancy(text, string)

    _columns = {
        'amount_currency': fields.float(string="Book. Amount", digits_compute=dp.get_precision('Account'), readonly=True, required=True, help="The amount expressed in an optional other currency.",),
        'currency_id': fields.many2one('res.currency', string="Book. Currency", required=True, readonly=True),
        'journal_id': fields.many2one('account.analytic.journal', 'Journal Code', required=True, ondelete='restrict', select=True, readonly=True),
        'journal_type': fields.related('journal_id', 'type', 'Journal type', readonly=True),
        'move_id': fields.many2one('account.move.line', 'Entry Sequence', ondelete='restrict', select=True, readonly=True, domain="[('account_id.user_type.code', 'in', ['expense', 'income'])]"), # UF-1719: Domain added for search view
    }

account_analytic_line()
# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
