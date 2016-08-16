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
    "name" : "Webkit Report Engine",
    "description" : """This module override the module webkit_report in order to have proper MSF data
    and not camptocamp data (such as the logo).
                    """,
    "version" : "0.1",
    "depends" : ["report_webkit"],
    "author" : "TeMPO Consulting, MSF",
    "category": "Reports/Webkit for Unifield",
    #"data": ["data.xml",
    #],
    "installable" : True,
    "active" : False,
}
