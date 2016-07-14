#!/usr/bin/env python
#-*- encoding:utf-8 -*-
##############################################################################
#
#    OpenERP, Open Source Management Solution
#    Copyright (C) TeMPO Consulting (<http://www.tempo-consulting.fr/>), MSF.
#    All Rigts Reserved
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
from tools.translate import _
from time import strftime
from tempfile import NamedTemporaryFile
from base64 import decodestring
from spreadsheet_xml.spreadsheet_xml import SpreadsheetXML
import threading
import pooler
from ..register_tools import open_register_view
from lxml import etree


class wizard_register_import(osv.osv_memory):
    _name = 'wizard.register.import'

    _columns = {
        'file': fields.binary(string="File", filters='*.xml, *.xls', required=True),
        'filename': fields.char(string="Imported filename", size=256),
        'progression': fields.float(string="Progression", readonly=True),
        'message': fields.char(string="Message", size=256, readonly=True),
        'state': fields.selection([('draft', 'Created'), ('inprogress', 'In Progress'), ('error', 'Error'), ('done', 'Done')], string="State", readonly=True, required=True),
        'error_ids': fields.one2many('wizard.register.import.errors', 'wizard_id', "Errors", readonly=True),
        'register_id': fields.many2one('account.bank.statement', 'Register', required=True, readonly=True),
    }

    _defaults = {
        'progression': lambda *a: 0.0,
        'state': lambda *a: 'draft',
    }

    def fields_view_get(self, cr, uid, view_id=None, view_type='form', context=None, toolbar=False, submenu=False):
        """
        Change table's headers name (to be well translated)
        """
        if not context:
            context = {}
        view = super(wizard_register_import, self).fields_view_get(cr, uid, view_id, view_type, context, toolbar, submenu)
        if view_type=='form':
            form = etree.fromstring(view['arch'])
            for el in [('document_date', 'Document Date'), ('posting_date', 'Posting Date'), ('cheque_number', 'Cheque Number'), ('description', 'Description'), ('reference', 'Reference'), ('account', 'Account'), ('third_party', 'Third Party'), ('amount_in', 'Amount In'), ('amount_out', 'Amount Out'), ('destination', 'Destination'), ('cost_center', 'Cost Centre'), ('funding_pool', 'Funding Pool'), ('proprietary_instance', "Proprietary instance's code"), ('journal', "Journal's code"), ('currency', "Currency's code"),('free1', "Free 1"),('free2', "Free 2")]:
                fields = form.xpath('/form//th[@class="' + el[0] + '"]')
                for field in fields:
                    field.text = _(el[1])
            fields = form.xpath
            view['arch'] = etree.tostring(form)
        return view

    def create(self, cr, uid, vals, context=None):
        """
        Add register regarding context @creation
        """
        if not context:
            return False
        res = super(wizard_register_import, self).create(cr, uid, vals, context=context)
        if context.get('active_ids', False):
            ids = res
            if isinstance(ids, (int, long)):
                ids = [ids]
            self.write(cr, uid, ids, {'register_id': context.get('active_ids')[0]}, context=context)
        return res

    def create_entries(self, cr, uid, ids, remaining_percent=50.0, context=None):
        """
        Create register lines with/without analytic distribution.
        If all needed info for analytic distribution are present: attempt to create analytic distribution.
        If this one is invalid, delete it!
        """
        # Checks
        if not context:
            context = {}
        # Fetch default funding pool: MSF Private Fund
        try:
            msf_fp_id = self.pool.get('ir.model.data').get_object_reference(cr, uid, 'analytic_distribution', 'analytic_account_msf_private_funds')[1]
        except ValueError:
            msf_fp_id = 0
        # Prepare some values
        absl_obj = self.pool.get('account.bank.statement.line')
        # Browse all wizards
        for w in self.read(cr, uid, ids, ['register_id']):
            w_id = w.get('id', False)
            register_id = w.get('register_id', False)
            account_obj = self.pool.get('account.account')
            # Search lines
            entries = self.pool.get('wizard.register.import.lines').search(cr, uid, [('wizard_id', '=', w_id)])
            if not entries:
                raise osv.except_osv(_('Error'), _('No lines.'))
            # Browse result
            fields = [
                'description',
                'ref',
                'document_date',
                'cheque_number',
                'account_id',
                'debit',
                'credit',
                'partner_id',
                'employee_id',
                'transfer_journal_id',
                'destination_id',
                'funding_pool_id',
                'cost_center_id',
                'date',
                'currency_id',
                'cheque_number',
                'free_1_id',
                'free_2_id'
            ]
            b_entries = self.pool.get('wizard.register.import.lines').read(cr, uid, entries, fields)
            current_percent = 100.0 - remaining_percent
            entries_number = len(b_entries)
            to_check = []
            # Create a register line for each entry
            for nb, l in enumerate(b_entries):
                # Prepare values
                account_id = l.get('account_id', False) and l.get('account_id')[0] or False
                partner_id = l.get('partner_id', False) and l.get('partner_id')[0] or False
                employee_id = l.get('employee_id', False) and l.get('employee_id')[0] or False
                transfer_journal_id = l.get('transfer_journal_id', False) and l.get('transfer_journal_id')[0] or False
                destination_id = l.get('destination_id', False) and l.get('destination_id')[0] or False
                funding_pool_id = l.get('funding_pool_id', False) and l.get('funding_pool_id')[0] or False
                cost_center_id = l.get('cost_center_id', False) and l.get('cost_center_id')[0] or False
                date = l.get('date', False)
                currency_id = l.get('currency_id', False) and l.get('currency_id')[0] or False
                account = account_obj.read(cr, uid, account_id, ['is_analytic_addicted'])
                cheque_number = l.get('cheque_number')
                free_1_id = l.get('free_1_id',False) and l.get('free_1_id')[0] or False
                free_2_id = l.get('free_2_id',False) and l.get('free_2_id')[0] or False

                vals = {
                    'name':                l.get('description', ''),
                    'ref':                 l.get('ref', ''),
                    'document_date':       l.get('document_date', False),
                    'date':                date,
                    'account_id':          account_id,
                    'amount':              l.get('debit', 0.0) - l.get('credit', 0.0),
                    'partner_id':          partner_id,
                    'employee_id':         employee_id,
                    'transfer_journal_id': transfer_journal_id,
                    'statement_id':        register_id,
                }
                if cheque_number:
                    vals['cheque_number'] = str(cheque_number)
                else:
                    vals['cheque_number'] = ''
                absl_id = absl_obj.create(cr, uid, vals, context)
                # Analytic distribution
                distrib_id = False
                # Create analytic distribution
                if account and account.get('is_analytic_addicted', False) and destination_id and cost_center_id and funding_pool_id:
                    distrib_id = self.pool.get('analytic.distribution').create(cr, uid, {}, context)
                    common_vals = {
                        'distribution_id': distrib_id,
                        'currency_id': currency_id,
                        'percentage': 100.0,
                        'date': date,
                        'source_date': date,
                        'destination_id': destination_id,
                    }
                    common_vals.update({'analytic_id': cost_center_id,})
                    self.pool.get('cost.center.distribution.line').create(cr, uid, common_vals)
                    common_vals.update({'analytic_id': funding_pool_id or msf_fp_id, 'cost_center_id': cost_center_id,})
                    self.pool.get('funding.pool.distribution.line').create(cr, uid, common_vals)

                    if free_1_id:
                        common_vals.update({'analytic_id': free_1_id,})
                        self.pool.get('free.1.distribution.line').create(cr,uid,common_vals)

                    if free_2_id:
                        common_vals.update({'analytic_id': free_2_id,})
                        self.pool.get('free.2.distribution.line').create(cr,uid,common_vals)

                    # Check analytic distribution. Use SKIP_WRITE_CHECK to not do anything else that writing analytic distribution field
                    absl_obj.write(cr, uid, [absl_id], {'analytic_distribution_id': distrib_id,}, context={'skip_write_check': True})
                    # Add this line to be check at the end of the process
                    to_check.append(absl_id)
                # Update wizard with current progression
                progression = current_percent + (nb + 1.0) / entries_number * remaining_percent
                self.write(cr, uid, [w_id], {'progression': progression})
            # Check analytic distribution on lines.
            #+ As explained in UF-1982 we disregard the analytic distribution if any problem on it
            to_delete = []
            to_delete_distrib = []
            for absl_data in absl_obj.read(cr, uid, to_check, ['analytic_distribution_state', 'analytic_distribution_id'], context):
                if absl_data.get('analytic_distribution_state', '') == 'valid':
                    continue
                to_delete.append(absl_data.get('id'))
                to_delete_distrib.append(absl_data.get('analytic_distribution_id', [False])[0])
            # Delete analytic distribution field on register lines
            absl_obj.write(cr, uid, to_delete, {'analytic_distribution_id': False}, context={'skip_write_check': True}) # do not do anything else than changing analytic_distribution_id field content (thanks to SKIP_WRITE_CHECK)
            # Delete analytic distribution
            self.pool.get('analytic.distribution').unlink(cr, uid, to_delete_distrib, context)
        return True

    def _import(self, dbname, uid, ids, context=None):
        """
        Do treatment before validation:
        - check data from wizard
        - check that file exists and that data are inside
        - check integrity of data in files
        """
        # Some checks
        if not context:
            context = {}

        # Prepare some values
        cr = pooler.get_db(dbname).cursor()
        created = 0
        processed = 0
        errors = []
        cheque_numbers = []
        try:
            msf_fp_id = self.pool.get('ir.model.data').get_object_reference(cr, uid, 'analytic_distribution', 'analytic_account_msf_private_funds')[1]
        except ValueError:
            msf_fp_id = 0

        try:
            # Update wizard
            self.write(cr, uid, ids, {'message': _('Cleaning up old imports…'), 'progression': 1.00}, context)
            # Clean up old temporary imported lines
            old_lines_ids = self.pool.get('wizard.register.import.lines').search(cr, uid, [])
            self.pool.get('wizard.register.import.lines').unlink(cr, uid, old_lines_ids)

            # Check wizard data
            for wiz in self.browse(cr, uid, ids, context):
                # Update wizard
                self.write(cr, uid, [wiz.id], {'message': _('Checking file…'), 'progression': 2.00}, context)
                # Check that a file was given
                if not wiz.file:
                    raise osv.except_osv(_('Error'), _('Nothing to import.'))
                # Update wizard
                self.write(cr, uid, [wiz.id], {'message': _('Copying file…'), 'progression': 3.00}, context)
                fileobj = NamedTemporaryFile('w+b', delete=False)
                fileobj.write(decodestring(wiz.file))
                fileobj.close()
                content = SpreadsheetXML(xmlfile=fileobj.name)
                if not content:
                    raise osv.except_osv(_('Warning'), _('No content.'))
                # Update wizard
                self.write(cr, uid, [wiz.id], {'message': _('Processing line…'), 'progression': 4.00}, context)
                rows = content.getRows()
                nb_rows = len([x for x in content.getRows()])
                # Update wizard
                self.write(cr, uid, [wiz.id], {'message': _('Reading headers…'), 'progression': 5.00}, context)
                # cols variable describe each column and its expected number
                cols = {
                    'document_date': 0,
                    'posting_date':  1,
                    'cheque_number': 2,
                    'description':   3,
                    'reference':     4,
                    'account':       5,
                    'third_party':   6,
                    'amount_in':     7,
                    'amount_out':    8,
                    'destination':   9,
                    'cost_center':   10,
                    'funding_pool':  11,
                    'free1':         12,
                    'free2':         13,
                }
                # Number of line to bypass in line's count
                base_num = 5 # because of Python that begins to 0.
                # Attempt to read 3 first lines
                first_line = self.pool.get('import.cell.data').get_line_values(cr, uid, ids, rows.next())
                try:
                    instance_code = first_line[1]
                except IndexError, e:
                    raise osv.except_osv(_('Warning'), _('Proprietary Instance not found.'))
                second_line = self.pool.get('import.cell.data').get_line_values(cr, uid, ids, rows.next())
                try:
                    journal_code = second_line[1]
                except IndexError, e:
                    raise osv.except_osv(_('Warning'),  _('No journal code found.'))
                third_line = self.pool.get('import.cell.data').get_line_values(cr, uid, ids, rows.next())
                try:
                    currency_code = third_line[1]
                except IndexError, e:
                    raise osv.except_osv(_('Warning'), _('No currency code found.'))
                # Check first info: proprietary instance
                instance_ids = self.pool.get('msf.instance').search(cr, uid, [('code', '=', instance_code)])
                if not instance_ids or len(instance_ids) > 1:
                    raise osv.except_osv(_('Warning'), _('Instance %s not found.') % (instance_code or '',))
                if isinstance(instance_ids, (int, long)):
                    instance_ids = [instance_ids]
                # Check second info: journal's code
                journal_ids = self.pool.get('account.journal').search(cr, uid, [('code', '=', journal_code)])
                if not journal_ids or len(journal_ids) > 1:
                    raise osv.except_osv(_('Warning'), _('Journal %s not found.') % (journal_code or '',))
                if isinstance(journal_ids, (int, long)):
                    journal_ids = [journal_ids]
                # Check third info: currency's code
                currency_ids = self.pool.get('res.currency').search(cr, uid, [('name', '=', currency_code)])
                if not currency_ids or len(currency_ids) > 1:
                    raise osv.except_osv(_('Warning'), _('Currency %s not found.') % (currency_code or '',))
                # Check that currency is active
                if isinstance(currency_ids, (int, long)):
                    currency_ids = [currency_ids]
                cur = self.pool.get('res.currency').browse(cr, uid, currency_ids, context)
                if not cur or not cur[0] or not cur[0].active:
                    raise osv.except_osv(_('Error'), _('Currency %s is not active!') % (cur.name))
                # Check that currency is the same as register's one
                register_currency = wiz.register_id.currency.id
                if register_currency not in currency_ids:
                    raise osv.except_osv('', _("the import's currency is %s whereas the register's currency is %s") % (cur[0].name, wiz.register_id.currency.name))
                # Search registers that correspond to this instance, journal's code and currency and check that our register is in the list
                register_ids = self.pool.get('account.bank.statement').search(cr, uid, [('instance_id', 'in', instance_ids), ('journal_id', 'in', journal_ids), ('currency', 'in', currency_ids)])
                if not register_ids or wiz.register_id.id not in register_ids:
                    raise osv.except_osv(_('Error'), _("The given register does not correspond to register's information from the file. Instance code: %s. Journal's code: %s. Currency code: %s.") % (wiz.register_id.instance_id.code, wiz.register_id.journal_id.code, wiz.register_id.currency.name))
                # Don't read the fourth line
                rows.next()
                # Update wizard
                self.write(cr, uid, [wiz.id], {'message': _('Reading lines…'), 'progression': 6.00}, context)
                # Remaining percent
                # 100 - 6 (94) is the remaining for:
                # - checking lines
                # - writing them
                # - validate the wizard and finish it
                # So we have 2% for miscellaneous transactions, 92% remaining with 46% checking lines and 46% to write them.
                remaining = (100.0 - 6.0 - 2.0) / 2.0
                # Check file's content
                for num, r in enumerate(rows):
                    # Update wizard
                    progression = ((float(num+1) * remaining) / float(nb_rows)) + 6
                    self.write(cr, uid, [wiz.id], {'message': _('Checking file…'), 'progression': progression}, context)
                    # Prepare some values
                    r_debit = 0
                    r_credit = 0
                    r_currency = register_currency
                    r_partner = False
                    r_account = False
                    r_destination = False
                    r_cc = False
                    r_fp = False
                    r_document_date = False
                    r_date = False
                    r_period = False
                    r_cheque_number = False
                    r_free1 = False
                    r_free2 = False
                    current_line_num = num + base_num
                    # Fetch all XML row values
                    line = self.pool.get('import.cell.data').get_line_values(cr, uid, ids, r)
                    # utp1043 pad the line with False if some trailing columns missing. Occurs on Excel 2003
                    line.extend([False for i in range(len(cols) - len(line))])
                    # Bypass this line if NO debit AND NO credit
                    try:
                        bd = line[cols['amount_in']]
                    except IndexError, e:
                        bd = 0.0
                    try:
                        bc = line[cols['amount_out']]
                    except IndexError, e:
                        bc = 0.0
                    if (not bd and not bc) or (bd == 0.0 and bc == 0.0):
                        errors.append(_('Line %s: Neither Amount IN or Amount OUT are present.') % (current_line_num,))
                        continue
                    if bd and bc and (bc != 0.0 or bd != 0.0):
                        errors.append(_('Line %s: Double amount, IN and OUT. Use only one!') % (current_line_num,))
                        continue
                    processed += 1
                    # Get amount
                    r_debit = bd
                    r_credit = bc

                    # Mandatory columns
                    if not line[cols['document_date']]:
                        errors.append(_('Line %s: Document date is missing.') % (current_line_num,))
                        continue
                    if not line[cols['posting_date']]:
                        errors.append(_('Line %s: Posting date is missing.') % (current_line_num,))
                        continue
                    if line[cols['document_date']] and not line[cols['description']]:
                        errors.append(_('Line %s: Description is missing.') % (current_line_num,))
                        continue
                    if not line[cols['account']]:
                        errors.append(_('Line %s: Account is missing.') % (current_line_num,))
                        continue
                    if r[cols['document_date']].type != 'datetime':
                        errors.append(_('Line %s: Document date wrong excel format. Use a date one.') % (current_line_num,))
                        continue
                    r_document_date = line[cols['document_date']].strftime('%Y-%m-%d')
                    if r[cols['posting_date']].type != 'datetime':
                        errors.append(_('Line %s: Posting date wrong excel format. Use a date one.') % (current_line_num))
                        continue
                    r_date = line[cols['posting_date']].strftime('%Y-%m-%d')
                    r_description = line[cols['description']]
                    # Check document/posting dates
                    if line[cols['document_date']] > line[cols['posting_date']]:
                        errors.append(_("Line %s. Document date '%s' should be earlier than or equal to Posting date '%s'.") % (current_line_num, line[cols['document_date']], line[cols['posting_date']],))
                        continue
                    # Check that a period exist and is open
                    period_ids = self.pool.get('account.period').get_period_from_date(cr, uid, r_date, context)
                    if not period_ids:
                        errors.append(_('Line %s. No period found for given date: %s') % (current_line_num, r_date))
                        continue
                    r_period = period_ids[0]
                    # Check that period correspond to those from register
                    if r_period != wiz.register_id.period_id.id:
                        errors.append(_('Line %s: Posting date \'%s\' is not in the same period as given register.') % (current_line_num, r_date))
                        continue
                    # Check G/L account
                    account_code = str(line[cols['account']]).split(' ') and str(line[cols['account']]).split(' ')[0] or str(line[cols['account']])
                    account_ids = self.pool.get('account.account').search(cr, uid, [('code', '=', account_code)])
                    if not account_ids:
                        errors.append(_('Line %s. G/L account %s not found!') % (current_line_num, account_code,))
                        continue
                    r_account = account_ids[0]
                    account_obj = self.pool.get('account.account')
                    restricted_ids = account_obj.search(cr, uid, [('restricted_area', '=', 'register_lines'), ('id', '=', r_account)])
                    if not restricted_ids and account_code != '10210':
                        errors.append(_('Line %s. G/L account %s is restricted.') % (current_line_num, account_code,))
                        continue
                    account = account_obj.read(cr, uid, r_account, ['type_for_register', 'is_analytic_addicted', 'code', 'name', ], context)
                    type_for_register = account.get('type_for_register', '')

                    # cheque_number
                    r_cheque_number = line[cols['cheque_number']]
                    # cheque unicity
                    register_type = wiz.register_id.journal_id.type
                    if register_type == 'cheque':
                        if r_cheque_number:
                            if r_cheque_number in cheque_numbers:
                                errors.append(_('Line %s. Cheque number %s is duplicated from another line') % (current_line_num,r_cheque_number,))
                            absl = self.pool.get('account.bank.statement.line')
                            cheque_number_id = absl.search(cr, uid, [('cheque_number','=',r_cheque_number)],context=context)
                            if cheque_number_id:
                               errors.append(_('Line %s. Cheque number %s has already been entered into the system.') % (current_line_num,r_cheque_number,))
                            cheque_numbers.append(r_cheque_number)
                        else:
                            errors.append(_('Line %s. Cheque number is missing') % (current_line_num,))
                    # Check that Third party exists (if not empty)
                    tp_label = _('Partner')
                    partner_type = 'partner'
                    third_party_journal_ids = None
                    if line[cols['third_party']]:
                        if type_for_register == 'advance':
                            tp_ids = self.pool.get('hr.employee').search(cr, uid, [('name', '=', line[cols['third_party']])])
                            tp_label = _('Employee')
                            partner_type = 'employee'
                        elif type_for_register in ['transfer', 'transfer_same']:
                            tp_ids = self.pool.get('account.journal').search(cr, uid, [('code', '=', line[cols['third_party']])])
                            tp_label = _('Journal')
                            partner_type = 'journal'
                            tp_journal = self.pool.get('account.journal').browse(cr, uid, tp_ids, context=context)[0]
                            if type_for_register == 'transfer':
                                if tp_journal.currency.id == register_currency:
                                    errors.append(_('Line %s. A Transfer Journal must have a different currency than the register.') % (current_line_num,))
                            if type_for_register == 'transfer_same':
                                if tp_journal.currency.id != register_currency:
                                    errors.append(_('Line %s. A Transfer Same Journal must have the same currency as the register.') % (current_line_num,))
                        else:
                            tp_ids = self.pool.get('res.partner').search(cr, uid, [('name', '=', line[cols['third_party']])])
                            partner_type = 'partner'
                        if not tp_ids:
                            # Search now if employee exists
                            tp_ids = self.pool.get('hr.employee').search(cr, uid, [('name', '=', line[cols['third_party']])])
                            tp_label = _('Employee')
                            partner_type = 'employee'
                            # If really not, raise an error for this line
                            if not tp_ids:
                                errors.append(_('Line %s. Third party not found: %s') % (current_line_num, line[cols['third_party']],))
                                continue
                        r_partner = tp_ids[0]

                        # US-672 TP compat with account
                        tp_check_res = self.pool.get('account.account').is_allowed_for_thirdparty(
                            cr, uid, [r_account],
                            employee_id=partner_type == 'employee' and r_partner or False,
                            transfer_journal_id=partner_type == 'journal' and r_partner or False,
                            partner_id=partner_type == 'partner' and r_partner or False,
                            context=context)[r_account]
                        if not tp_check_res:
                            errors.append(_("Line %s. Thirdparty not compatible with account '%s - %s'") % (current_line_num, account['code'], account['name'], ))
                            continue

                    # free 1
                    if line[cols['free1']]:
                        free1 = line[cols['free1']]
                        free_1_ids = self.pool.get('account.analytic.account').search(cr, uid, [('category', '=', 'FREE1'), ('code', '=', free1)])
                        if free_1_ids:
                            r_free1 = free_1_ids[0]


                    # free 2
                    if line[cols['free2']]:
                        free2 = line[cols['free2']]
                        free_2_ids = self.pool.get('account.analytic.account').search(cr, uid, [('category', '=', 'FREE2'), ('code', '=', free2)])
                        if free_2_ids:
                            r_free2 = free_2_ids[0]

                    # Check analytic axis only if G/L account is an analytic-a-holic account
                    if account.get('is_analytic_addicted', False):
                        # Check Destination
                        try:
                            if line[cols['destination']]:
                                destination_ids = self.pool.get('account.analytic.account').search(cr, uid, [('category', '=', 'DEST'), '|', ('name', '=', line[cols['destination']]), ('code', '=', line[cols['destination']])])
                                if destination_ids:
                                    r_destination = destination_ids[0]
                        except IndexError, e:
                            pass
                        # Check Cost Center
                        try:
                            if line[cols['cost_center']]:
                                cc_ids = self.pool.get('account.analytic.account').search(cr, uid, [('category', '=', 'OC'), '|', ('name', '=', line[cols['cost_center']]), ('code', '=', line[cols['cost_center']])])
                                if cc_ids:
                                    r_cc = cc_ids[0]
                        except IndexError, e:
                            pass
                        # Check funding pool
                        try:
                            if line[cols['funding_pool']]:
                                fp_ids = self.pool.get('account.analytic.account').search(cr, uid, [('category', '=', 'FUNDING'), '|', ('name', '=', line[cols['funding_pool']]), ('code', '=', line[cols['funding_pool']])])
                                if fp_ids:
                                    r_fp = fp_ids[0]

                        except IndexError, e:
                            pass
                        # NOTE: There is no need to check G/L account, Cost Center and Destination regarding document/posting date because this check is already done at Journal Entries validation.

                    # Registering data regarding these "keys":
                    # - G/L Account
                    # - Third Party
                    # - Destination
                    # - Cost Centre
                    # - Booking Currency
                    vals = {
                        'description': r_description or '',
                        'ref': line[4]  or '',
                        'account_id': r_account or False,
                        'debit': r_debit or 0.0,
                        'credit': r_credit or 0.0,
                        'cost_center_id': r_cc or False,
                        'destination_id': r_destination or False,
                        'funding_pool_id': r_fp or msf_fp_id,
                        'document_date': r_document_date or False,
                        'date': r_date or False,
                        'currency_id': r_currency or False,
                        'wizard_id': wiz.id,
                        'period_id': r_period or False,
                        'cheque_number': r_cheque_number or False,
                        'free_1_id': r_free1 or False,
                        'free_2_id': r_free2 or False,
                    }
                    if type_for_register == 'advance':
                        vals.update({'employee_id': r_partner,})
                    elif type_for_register in ['transfer', 'transfer_same']:
                        vals.update({'transfer_journal_id': r_partner})
                    else:
                        if partner_type == 'partner':
                            vals.update({'partner_id': r_partner,})
                        elif partner_type == 'employee':
                            vals.update({'employee_id': r_partner,})
                    line_res = self.pool.get('wizard.register.import.lines').create(cr, uid, vals, context)
                    if not line_res:
                        errors.append(_('Line %s. A problem occured for line registration. Please contact an Administrator.') % (current_line_num,))
                        continue
                    created += 1

            # Update wizard
            self.write(cr, uid, ids, {'message': _('Check complete. Reading potential errors or write needed changes.'), 'progression': 53.0}, context)

            wiz_state = 'done'
            # If errors, cancel probable modifications
            if errors:
                cr.rollback()
                created = 0
                message = _('Import FAILED.')
                # Delete old errors
                error_ids = self.pool.get('wizard.register.import.errors').search(cr, uid, [], context)
                if error_ids:
                    self.pool.get('wizard.register.import.errors').unlink(cr, uid, error_ids ,context)
                # create errors lines
                for e in errors:
                    self.pool.get('wizard.register.import.errors').create(cr, uid, {'wizard_id': wiz.id, 'name': e}, context)
                wiz_state = 'error'
            else:
                # Update wizard
                self.write(cr, uid, ids, {'message': _('Writing changes…'), 'progression': 54.0}, context)
                # Create all journal entries
                self.create_entries(cr, uid, ids, 46.0, context)
                message = _('Import successful.')

            # Update wizard
            self.write(cr, uid, ids, {'message': message, 'state': wiz_state, 'progression': 100.0}, context)

            # Close cursor
            cr.commit()
            cr.close(True)
        except osv.except_osv as osv_error:
            cr.rollback()
            self.write(cr, uid, ids, {'message': _("An error occured %s: %s") % (osv_error.name, osv_error.value), 'state': 'done', 'progression': 100.0})
            cr.close(True)
        except Exception as e:
            cr.rollback()
            self.write(cr, uid, ids, {'message': _("An error occured: %s") % (e and e.args and e.args[0] or ''), 'state': 'done', 'progression': 100.0})
            cr.close(True)
        return True

    def button_validate(self, cr, uid, ids, context=None):
        """
        Launch a thread (to check file and write changes) and return to this wizard.
        """
        if not context:
            context = {}
        # Launch a thread
        thread = threading.Thread(target=self._import, args=(cr.dbname, uid, ids, context))
        thread.start()

        # Write changes
        self.write(cr, uid, ids, {'state': 'inprogress'}, context)
        # Return a dict to avoid problem of panel bar to the right
        return {
         'type': 'ir.actions.act_window',
         'res_model': 'wizard.register.import',
         'view_type': 'form',
         'view_mode': 'form',
         'res_id': ids[0],
         'context': context,
         'target': 'new',
        }

    def button_update(self, cr, uid, ids, context=None):
        """
        Update view to see progress bar
        """
        return False

    def button_return(self, cr, uid, ids, context=None):
        """
        Return to the register
        """
        if not context:
            context = {}
        res = {'type': 'ir.actions.act_window_close'}
        wiz = self.browse(cr, uid, ids, context)
        if wiz and wiz[0].register_id:
            res = open_register_view(self, cr, uid, wiz[0].register_id.id, context)
        return res

wizard_register_import()

class wizard_register_import_lines(osv.osv):
    _name = 'wizard.register.import.lines'
    _rec_name = 'document_date'
    _order = 'id desc'
    _columns = {
        'description': fields.text("Description", required=False, readonly=True),
        'ref': fields.text("Reference", required=False, readonly=True),
        'document_date': fields.date("Document date", required=True, readonly=True),
        'date': fields.date("Posting date", required=True, readonly=True),
        'account_id': fields.many2one('account.account', "G/L Account", required=True, readonly=True),
        'destination_id': fields.many2one('account.analytic.account', "Destination", required=False, readonly=True),
        'cost_center_id': fields.many2one('account.analytic.account', "Cost Center", required=False, readonly=True),
        'funding_pool_id': fields.many2one('account.analytic.account', "Funding Pool", required=False, readonly=True),
        'debit': fields.float("Debit", required=False, readonly=True),
        'credit': fields.float("Credit", required=False, readonly=True),
        'currency_id': fields.many2one('res.currency', "Currency", required=True, readonly=True),
        'partner_id': fields.many2one('res.partner', "Partner", required=False, readonly=True),
        'employee_id': fields.many2one('hr.employee', "Employee", required=False, readonly=True),
        'period_id': fields.many2one('account.period', "Period", required=True, readonly=True),
        'wizard_id': fields.integer("Wizard", required=True, readonly=True),
        'transfer_journal_id': fields.many2one('account.journal', 'Transfer Journal', required=False, readonly=True,),
        'cheque_number': fields.text("Cheque Number", required=False, readonly=True),
        'free_1_id': fields.many2one('account.analytic.account', string="Free 1", domain="[('category', '=', 'FREE1'), ('type', '!=', 'view'), ('state', '=', 'open')]"),
        'free_2_id': fields.many2one('account.analytic.account', string="Free 2", domain="[('category', '=', 'FREE2'), ('type', '!=', 'view'), ('state', '=', 'open')]"),
    }

    _defaults = {
        'description': lambda *a: '',
        'ref': lambda *a: '',
        'document_date': lambda *a: strftime('%Y-%m-%d'),
        'date': lambda *a: strftime('%Y-%m-%d'),
        'debit': lambda *a: 0.0,
        'credit': lambda *a: 0.0,
    }

wizard_register_import_lines()

class wizard_register_import_errors(osv.osv_memory):
    _name = 'wizard.register.import.errors'

    _columns = {
        'name': fields.text("Description", readonly=True, required=True),
        'wizard_id': fields.many2one('wizard.register.import', "Wizard", required=True, readonly=True),
    }

wizard_register_import_errors()
# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
