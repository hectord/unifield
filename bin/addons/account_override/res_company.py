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
from osv import fields

class res_company(osv.osv):
    _name = 'res.company'
    _inherit = 'res.company'

    _columns = {
        'import_invoice_default_account': fields.many2one('account.account', string="Re-billing Inter-section account", 
            help="Default account for an import invoice on a Debit note"),
        'intermission_default_counterpart': fields.many2one('account.account', string="Intermission counterpart", 
            help="Default account used for partner in Intermission Voucher IN/OUT"),
        'additional_allocation': fields.boolean('Additional allocation condition?', help="If you check this attribute, analytic allocation will be required for income accounts with an account code starting with \"7\"; if unchecked, the analytic allocation will be required for all income accounts."),
        'revaluation_default_account': fields.many2one('account.account', string="Revaluation account", 
            help="Default account used for revaluation"),
    }
    
    def check_revaluation_default_account_has_sup_destination(self, cr, uid, company, context=None):
        if company and company.revaluation_default_account:
            reval_account = company.revaluation_default_account
            if reval_account.default_destination_id \
                and reval_account.default_destination_id.code == 'SUP':
                return True
            for dest in reval_account.destination_ids:
                if dest.code == 'SUP':
                    return True
            return False
        return True
    
    def _check_revaluation_default_account(self, cr, uid, ids, context=None):
        if isinstance(ids, (int, long)):
            ids = [ids]
        for obj in self.browse(cr, uid, ids, context=context):
            if not self.check_revaluation_default_account_has_sup_destination(cr, uid, obj, context=context):
                raise osv.except_osv('Settings Error!','The default revaluation account must have a default destination SUP')
        return True
        
    _constraints = [
        (_check_revaluation_default_account, 'The default revaluation account must have a default destination SUP', ['revaluation_default_account'])
    ]

res_company()
# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
