# -*- coding: utf-8 -*-
##############################################################################
#
#    OpenERP, Open Source Management Solution
#    Copyright (C) MSF, TeMPO Consulting.
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
import netsvc
from tools.translate import _

class analytic_distribution(osv.osv):
    _name = 'analytic.distribution'
    _inherit = 'analytic.distribution'

    def _get_distribution_state(self, cr, uid, distrib_id, parent_id, account_id, context=None):
        """
        Return distribution state
        """
        if context is None:
            context = {}
        # Have an analytic distribution on another account than analytic-a-holic account make no sense. So their analytic distribution is valid
        logger = netsvc.Logger()
        if account_id:
            account =  self.pool.get('account.account').read(cr, uid, account_id, ['is_analytic_addicted'])
            if account and not account.get('is_analytic_addicted', False):
                return 'valid'
        if not distrib_id:
            if parent_id:
                return self._get_distribution_state(cr, uid, parent_id, False, account_id, context)
            logger.notifyChannel("analytic distribution", netsvc.LOG_WARNING, _("%s: NONE!") % (distrib_id or ''))
            return 'none'
        distrib = self.browse(cr, uid, distrib_id)
        # Search MSF Private Fund element, because it's valid with all accounts
        try:
            fp_id = self.pool.get('ir.model.data').get_object_reference(cr, uid, 'analytic_distribution',
            'analytic_account_msf_private_funds')[1]
        except ValueError:
            fp_id = 0
        account = self.pool.get('account.account').read(cr, uid, account_id, ['destination_ids'])
        # Check Cost Center lines with destination/account link
        for cc_line in distrib.cost_center_lines:
            if cc_line.destination_id.id not in account.get('destination_ids', []):
                logger.notifyChannel("analytic distribution", netsvc.LOG_WARNING, _("%s: Error, destination not compatible with G/L account in CC lines") % (distrib_id or ''))
                return 'invalid'
        # Check Funding pool lines regarding:
        # - destination / account
        # - If analytic account is MSF Private funds
        # - Cost center and funding pool compatibility
        for fp_line in distrib.funding_pool_lines:
            if fp_line.destination_id.id not in account.get('destination_ids', []):
                logger.notifyChannel("analytic distribution", netsvc.LOG_WARNING, _("%s: Error, destination not compatible with G/L account for FP lines") % (distrib_id or ''))
                return 'invalid'
            # If fp_line is MSF Private Fund, all is ok
            if fp_line.analytic_id.id == fp_id:
                continue
            if (account_id, fp_line.destination_id.id) not in [x.account_id and x.destination_id and (x.account_id.id, x.destination_id.id) for x in fp_line.analytic_id.tuple_destination_account_ids]:
                logger.notifyChannel("analytic distribution", netsvc.LOG_WARNING, _("%s: Error, account/destination tuple not compatible with given FP analytic account") % (distrib_id or ''))
                return 'invalid'
            if fp_line.cost_center_id.id not in [x.id for x in fp_line.analytic_id.cost_center_ids]:
                logger.notifyChannel("analytic distribution", netsvc.LOG_WARNING, _("%s: Error, CC is not compatible with given FP analytic account") % (distrib_id or ''))
                return 'invalid'
        return 'valid'

    def analytic_state_from_info(self, cr, uid, account_id, destination_id, cost_center_id, analytic_id, context=None):
        """
        Give analytic state from the given information.
        Return result and some info if needed.
        """
        # Checks
        if context is None:
            context = {}
        # Prepare some values
        res = 'valid'
        info = ''
        ana_obj = self.pool.get('account.analytic.account')
        account = self.pool.get('account.account').browse(cr, uid, account_id, context=context)
        fp = ana_obj.browse(cr, uid, analytic_id, context=context)
        try:
            fp_id = self.pool.get('ir.model.data').get_object_reference(cr, uid, 'analytic_distribution', 'analytic_account_msf_private_funds')[1]
        except ValueError:
            fp_id = 0
        is_private_fund = False
        if analytic_id == fp_id:
            is_private_fund = True
        # DISTRIBUTION VERIFICATION
        # Check account user_type
        if account.user_type_code != 'expense':
            return res, _('Not an expense account')
        # Check that destination is compatible with account
        if destination_id not in [x.id for x in account.destination_ids]:
            return 'invalid', _('Destination not compatible with account')
        if not is_private_fund:
            # Check that cost center is compatible with FP (except if FP is MSF Private Fund)
            if cost_center_id not in [x.id for x in fp.cost_center_ids]:
                return 'invalid', _('Cost Center not compatible with FP')
            # Check that tuple account/destination is compatible with FP (except if FP is MSF Private Fund):
            if (account_id, destination_id) not in [x.account_id and x.destination_id and (x.account_id.id, x.destination_id.id) for x in fp.tuple_destination_account_ids]:
                return 'invalid', _('account/destination tuple not compatible with given FP analytic account')
        return res, info

analytic_distribution()
# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
