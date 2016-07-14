# -*- coding: utf-8 -*-
##############################################################################
#
#    OpenERP, Open Source Management Solution
#    Copyright (C) 2011 MSF, TeMPO consulting
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

    # To avoid issues with existing OpenERP code (account move line for example),
    # the state are:
    #  - 'created' for Draft
    #  - 'draft' for Open
    #  - 'done' for HQ-Closed
ACCOUNT_PERIOD_STATE_SELECTION = [
    ('created','Draft'),
    ('draft', 'Open'),
    ('field-closed', 'Field-Closed'),
    ('mission-closed', 'Mission-Closed'),
    ('done', 'HQ-Closed')
]

ACCOUNT_FY_STATE_SELECTION = [
    ('draft', 'Open'),
    ('mission-closed', 'Mission-Closed'),
    ('done', 'HQ-Closed')
]

import account
import account_period
import account_fiscalyear
import account_journal_period
import account_year_end_closing
import wizard

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
