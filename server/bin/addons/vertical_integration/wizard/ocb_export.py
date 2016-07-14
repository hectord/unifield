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

from osv import fields
from osv import osv
from tools.translate import _

from time import strftime
from time import strptime

class ocb_export_wizard(osv.osv_memory):
    _name = "ocb.export.wizard"

    _columns = {
        'instance_id': fields.many2one('msf.instance', 'Top proprietary instance', required=True),
        'fiscalyear_id': fields.many2one('account.fiscalyear', 'Fiscal year', required=True),
        'period_id': fields.many2one('account.period', 'Period', required=True),
        'selection': fields.selection([('unexported', 'Not yet exported'), ('all', 'All lines')], string="Select", required=True),
    }

    _defaults = {
        'fiscalyear_id': lambda self, cr, uid, c: self.pool.get('account.fiscalyear').find(cr, uid, strftime('%Y-%m-%d'), context=c),
        'selection': lambda *a: 'unexported',
    }

    def button_export(self, cr, uid, ids, context=None):
        """
        Launch a report to generate the ZIP file.
        """
        # Prepare some values
        wizard = self.browse(cr, uid, ids[0], context=context)
        data = {}
        # add parameters
        data['form'] = {}
        if wizard.instance_id:
            # Get projects below instance
            data['form'].update({'instance_id': wizard.instance_id.id,})
            data['form'].update({'instance_ids': [wizard.instance_id.id] + [x.id for x in wizard.instance_id.child_ids]})
        period_name = ''
        if wizard.period_id:
            data['form'].update({'period_id': wizard.period_id.id})
            period_name = strftime('%Y%m', strptime(wizard.period_id.date_start, '%Y-%m-%d'))
            # US-822: check period
            # 1) can not pick 16 as included in 12 for OCB
            # 2) when picking 12: target mission FY should be closed
            # OCB cancels the check 2) but keep it in case they rollback
            # => they want to export whereas there is PL RESULT entries or not
            # for the target coordo
            if wizard.period_id.number == 16:
                msg = _("You can not select '%s' as already included in' \
                    '  December export")  % (
                        wizard.period_id.name or 'Period 16', )
                raise osv.except_osv(_('Warning'), msg)
            """elif wizard.period_id.number == 12:
                domain = [
                    ('instance_id', '=', wizard.instance_id.id),
                    ('fy_id', '=', wizard.period_id.fiscalyear_id.id),
                    ('state', '=', 'mission-closed'),
                ]
                if not self.pool.get('account.fiscalyear.state').search(cr, uid,
                    domain, count=True, context=context):
                    msg = _("Target instance '%s' should be at least' \
                        yearly closed")  % (wizard.instance_id.code, )
                    raise osv.except_osv(_('Error'), msg)"""
        if wizard.fiscalyear_id:
            data['form'].update({'fiscalyear_id': wizard.fiscalyear_id.id})
        data['form'].update({'selection': wizard.selection})

        target_file_name_pattern = '%s_%s_formatted data UF to OCB HQ system' 
        data['target_filename'] = target_file_name_pattern % (
            wizard.instance_id and wizard.instance_id.code or '',
            period_name)

        return {'type': 'ir.actions.report.xml', 'report_name': 'hq.ocb', 'datas': data}

ocb_export_wizard()
# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
