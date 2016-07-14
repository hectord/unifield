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
from osv import fields
from tools.translate import _
from time import strftime
from tempfile import NamedTemporaryFile
from base64 import decodestring
from spreadsheet_xml.spreadsheet_xml import SpreadsheetXML
from csv import DictReader
import threading
import pooler
from msf_doc_import import ACCOUNTING_IMPORT_JOURNALS

class msf_doc_import_accounting(osv.osv_memory):
    _name = 'msf.doc.import.accounting'

    _columns = {
        'date': fields.date(string="Date", required=True),
        'file': fields.binary(string="File", filters='*.xml, *.xls', required=True),
        'filename': fields.char(string="Imported filename", size=256),
        'progression': fields.float(string="Progression", readonly=True),
        'message': fields.char(string="Message", size=256, readonly=True),
        'state': fields.selection([('draft', 'Created'), ('inprogress', 'In Progress'), ('error', 'Error'), ('done', 'Done')], string="State", readonly=True, required=True),
        'error_ids': fields.one2many('msf.doc.import.accounting.errors', 'wizard_id', "Errors", readonly=True),
    }

    _defaults = {
        'date': lambda *a: strftime('%Y-%m-%d'),
        'progression': lambda *a: 0.0,
        'state': lambda *a: 'draft',
        'message': lambda *a: _('Initialization…'),
    }

    def create_entries(self, cr, uid, ids, journal_id, context=None):
        """
        Create journal entry 
        """
        # Checks
        if not context:
            context = {}
        try:
            msf_fp_id = self.pool.get('ir.model.data').get_object_reference(cr, uid, 'analytic_distribution', 'analytic_account_msf_private_funds')[1]
        except ValueError:
            msf_fp_id = 0
        # Browse all wizards
        for w in self.browse(cr, uid, ids):
            # Search lines
            entries = self.pool.get('msf.doc.import.accounting.lines').search(cr, uid, [('wizard_id', '=', w.id)])
            if not entries:
                raise osv.except_osv(_('Error'), _('No lines…'))
            # Browse result
            b_entries = self.pool.get('msf.doc.import.accounting.lines').browse(cr, uid, entries)
            # Update wizard
            self.write(cr, uid, [w.id], {'message': _('Grouping by currencies…'), 'progression': 10.0})
            # Search all currencies (to create moves)
            available_currencies = {}
            for entry in b_entries:
                if (entry.currency_id.id, entry.period_id.id) not in available_currencies:
                    available_currencies[(entry.currency_id.id, entry.period_id.id)] = []
                available_currencies[(entry.currency_id.id, entry.period_id.id)].append(entry)
            # Update wizard
            self.write(cr, uid, ids, {'message': _('Writing a move for each currency…'), 'progression': 20.0})
            num = 1
            nb_currencies = float(len(available_currencies))
            current_percent = 20.0
            remaining_percent = 80.0
            step = float(remaining_percent / nb_currencies)
            for c_id, p_id in available_currencies:
                # Create a move
                move_vals = {
                    'currency_id': c_id,
                    'manual_currency_id': c_id,
                    'journal_id': journal_id,
                    'document_date': w.date,
                    'date': w.date,
                    'period_id': p_id,
                    'status': 'manu',
                    'imported': True,
                }
                move_id = self.pool.get('account.move').create(cr, uid, move_vals, context)
                for l_num, l in enumerate(available_currencies[(c_id, p_id)]):
                    # Update wizard
                    progression = 20.0 + ((float(l_num) / float(len(b_entries))) * step) + (float(num - 1) * step)
                    self.write(cr, uid, [w.id], {'progression': progression})
                    distrib_id = False
                    # Create analytic distribution
                    if l.account_id.is_analytic_addicted:
                        distrib_id = self.pool.get('analytic.distribution').create(cr, uid, {}, context)
                        common_vals = {
                            'distribution_id': distrib_id,
                            'currency_id': c_id,
                            'percentage': 100.0,
                            'date': l.date,
                            'source_date': l.date,
                            'destination_id': l.destination_id.id,
                        }
                        common_vals.update({'analytic_id': l.cost_center_id.id,})
                        cc_res = self.pool.get('cost.center.distribution.line').create(cr, uid, common_vals)
                        common_vals.update({'analytic_id': l.funding_pool_id.id, 'cost_center_id': l.cost_center_id.id,})
                        fp_res = self.pool.get('funding.pool.distribution.line').create(cr, uid, common_vals)
                    # Create move line
                    move_line_vals = {
                        'move_id': move_id,
                        'name': l.description,
                        'reference': l.ref,
                        'account_id': l.account_id.id,
                        'period_id': p_id,
                        'document_date': l.document_date,
                        'date': l.date,
                        'journal_id': journal_id,
                        'debit_currency': l.debit,
                        'credit_currency': l.credit,
                        'currency_id': c_id,
                        'analytic_distribution_id': distrib_id,
                        'partner_id': l.partner_id and l.partner_id.id or False,
                        'employee_id': l.employee_id and l.employee_id.id or False,
                        'transfer_journal_id': l.transfer_journal_id and l.transfer_journal_id.id or False,
                    }
                    self.pool.get('account.move.line').create(cr, uid, move_line_vals, context, check=False)
                # Validate the Journal Entry for lines to be valid (if possible)
                self.write(cr, uid, [w.id], {'message': _('Validating journal entry…')})
                self.pool.get('account.move').validate(cr, uid, [move_id], context=context)
                # Update wizard
                progression = 20.0 + (float(num) * step)
                self.write(cr, uid, [w.id], {'progression': progression})
                num += 1
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
        from_yml = False
        if context.get('from_yml', False):
            from_yml = context.get('from_yml')
        # Do changes because of YAML tests
        if from_yml:
            cr = dbname
        else:
            cr = pooler.get_db(dbname).cursor()
        try:
            msf_fp_id = self.pool.get('ir.model.data').get_object_reference(cr, uid, 'analytic_distribution', 'analytic_account_msf_private_funds')[1]
        except ValueError:
            msf_fp_id = 0
        created = 0
        processed = 0
        errors = []
        current_instance = self.pool.get('res.users').browse(cr, uid, uid).company_id.instance_id.id or False

        try:
            # Update wizard
            self.write(cr, uid, ids, {'message': _('Cleaning up old imports…'), 'progression': 1.00})
            # Clean up old temporary imported lines
            old_lines_ids = self.pool.get('msf.doc.import.accounting.lines').search(cr, uid, [])
            self.pool.get('msf.doc.import.accounting.lines').unlink(cr, uid, old_lines_ids)

            # Check wizard data
            for wiz in self.browse(cr, uid, ids):
                # Update wizard
                self.write(cr, uid, [wiz.id], {'message': _('Checking file…'), 'progression': 2.00})
                # UF-2045: Check that the given date is in an open period
                wiz_period_ids = self.pool.get('account.period').get_period_from_date(cr, uid, wiz.date, context)
                if not wiz_period_ids:
                    raise osv.except_osv(_('Warning'), _('No period found!'))
                period = self.pool.get('account.period').browse(cr, uid, wiz_period_ids[0], context)
                if not period or period.state in ['created', 'done']:
                    raise osv.except_osv(_('Warning'), _('Period is not open!'))
                date = wiz.date or False

                # Check that a file was given
                if not wiz.file:
                    raise osv.except_osv(_('Error'), _('Nothing to import.'))
                # Update wizard
                self.write(cr, uid, [wiz.id], {'message': _('Copying file…'), 'progression': 3.00})
                fileobj = NamedTemporaryFile('w+b', delete=False)
                fileobj.write(decodestring(wiz.file))
                fileobj.close()
                content = SpreadsheetXML(xmlfile=fileobj.name)
                if not content:
                    raise osv.except_osv(_('Warning'), _('No content'))
                # Update wizard
                self.write(cr, uid, [wiz.id], {'message': _('Processing line…'), 'progression': 4.00})
                rows = content.getRows()
                nb_rows = len([x for x in content.getRows()])
                # Update wizard
                self.write(cr, uid, [wiz.id], {'message': _('Reading headers…'), 'progression': 5.00})
                # Use the first row to find which column to use
                cols = {}
                col_names = ['Journal Code', 'Description', 'Reference', 'Document Date', 'Posting Date', 'G/L Account', 'Partner', 'Employee', 'Journal', 'Destination', 'Cost Centre', 'Funding Pool', 'Booking Debit', 'Booking Credit', 'Booking Currency']
                for num, r in enumerate(rows):
                    header = [x and x.data for x in r.iter_cells()]
                    for el in col_names:
                        if el in header:
                            cols[el] = header.index(el)
                    break
                # Number of line to bypass in line's count
                base_num = 2

                # global journal code for the file
                file_journal_id = 0
                aj_obj = self.pool.get('account.journal')

                for el in col_names:
                    if not el in cols:
                        raise osv.except_osv(_('Error'), _("'%s' column not found in file.") % (el or '',))
                # All lines
                money = {}
                # Update wizard
                self.write(cr, uid, [wiz.id], {'message': _('Reading lines…'), 'progression': 6.00})
                # Check file's content
                for num, r in enumerate(rows):
                    # Update wizard
                    percent = (float(num+1) / float(nb_rows+1)) * 100.0
                    progression = ((float(num+1) * 94) / float(nb_rows)) + 6
                    self.write(cr, uid, [wiz.id], {'message': _('Checking file…'), 'progression': progression})
                    # Prepare some values
                    r_debit = 0
                    r_credit = 0
                    r_currency = False
                    r_partner = False
                    r_employee = False
                    r_journal = False
                    r_account = False
                    r_destination = False
                    r_fp = False
                    r_cc = False
                    # UTP-1047: Use Document date column (contrary of UTP-766)
                    r_document_date = False
                    current_line_num = num + base_num
                    # Fetch all XML row values
                    line = self.pool.get('import.cell.data').get_line_values(cr, uid, ids, r)
                    # Check document date
                    if not line[cols['Document Date']]:
                        errors.append(_('Line %s. No document date specified!') % (current_line_num,))
                        continue
                    r_document_date = line[cols['Document Date']].strftime('%Y-%m-%d')
                    # Bypass this line if NO debit AND NO credit
                    try:
                        bd = line[cols['Booking Debit']]
                    except IndexError, e:
                        continue
                    try:
                        bc = line[cols['Booking Credit']]
                    except IndexError, e:
                        continue
                    if not line[cols['Booking Debit']] and not line[cols['Booking Credit']]:
                        continue
                    processed += 1
                    # Check that currency is active
                    if not line[cols['Booking Currency']]:
                        errors.append(_('Line %s. No currency specified!') % (current_line_num,))
                        continue
                    curr_ids = self.pool.get('res.currency').search(cr, uid, [('name', '=', line[cols['Booking Currency']])])
                    if not curr_ids:
                        errors.append(_('Line %s. Currency not found: %s') % (current_line_num, line[cols['Booking Currency']],))
                        continue
                    for c in self.pool.get('res.currency').browse(cr, uid, curr_ids):
                        if not c.active:
                            errors.append(_('Line %s. Currency is not active: %s') % (current_line_num, line[cols['Booking Currency']],))
                            continue
                    r_currency = curr_ids[0]
                    if not line[cols['Booking Currency']] in money:
                        money[line[cols['Booking Currency']]] = {}
                    if not 'debit' in money[line[cols['Booking Currency']]]:
                        money[line[cols['Booking Currency']]]['debit'] = 0
                    if not 'credit' in money[line[cols['Booking Currency']]]:
                        money[line[cols['Booking Currency']]]['credit'] = 0
                    if not 'name' in money[line[cols['Booking Currency']]]:
                        money[line[cols['Booking Currency']]]['name'] = line[cols['Booking Currency']]
                    # Increment global debit/credit
                    if line[cols['Booking Debit']]:
                        money[line[cols['Booking Currency']]]['debit'] += line[cols['Booking Debit']]
                        r_debit = line[cols['Booking Debit']]
                    if line[cols['Booking Credit']]:
                        money[line[cols['Booking Currency']]]['credit'] += line[cols['Booking Credit']]
                        r_credit = line[cols['Booking Credit']]

                    # Check which journal it is to be posted to: should be of type OD, MIG or INT
                    if not line[cols['Journal Code']]:
                        errors.append(_('Line %s. No Journal Code specified') % (current_line_num,))
                        continue
                    else:
                        # check for a valid journal code
                        aj_ids = aj_obj.search(cr, uid, [('code', '=', line[cols['Journal Code']]), ('instance_id', '=', current_instance)])
                        if not aj_ids:
                            errors.append(_('Line %s. Journal Code not found: %s.') % (current_line_num, line[cols['Journal Code']]))
                            continue
                        else:
                            aj_data = aj_obj.read(cr, uid, aj_ids, ['type'])[0]
                            if aj_data.get('type', False) is False or aj_data.get('type', False) not in ACCOUNTING_IMPORT_JOURNALS:
                                journal_list = ', '.join([x[1] for x in aj_obj.get_journal_type(cr, uid) if x[0] in ACCOUNTING_IMPORT_JOURNALS])
                                errors.append(_('Line %s. Import of entries only allowed on the following journal(s): %s') % (current_line_num, journal_list))
                                continue
                        aj_id = aj_ids[0]
                        if num == 0:
                            file_journal_id = aj_id
                        else:
                            if file_journal_id != aj_id:
                                errors.append(_('Line %s. Only a single Journal Code can be specified per file') % (current_line_num,))
                                continue

                    # Check G/L account
                    if not line[cols['G/L Account']]:
                        errors.append(_('Line %s. No G/L account specified!') % (current_line_num,))
                        continue
                    account_ids = self.pool.get('account.account').search(cr, uid, [('code', '=', line[cols['G/L Account']])])
                    if not account_ids:
                        errors.append(_('Line %s. G/L account %s not found!') % (current_line_num, line[cols['G/L Account']],))
                        continue
                    r_account = account_ids[0]
                    account = self.pool.get('account.account').browse(cr, uid, r_account)

                    # Third party
                    # Check that Third party exists (if not empty)
                    tp_label = False
                    tp_content = False
                    if line[cols['Partner']]:
                        tp_ids = self.pool.get('res.partner').search(cr, uid, [('name', '=', line[cols['Partner']])])
                        if not tp_ids:
                            tp_label = _('Partner')
                            tp_content = line[cols['Partner']]
                        else:
                            r_partner = tp_ids[0]
                    if line[cols['Employee']]:
                        tp_ids = self.pool.get('hr.employee').search(cr, uid, [('name', '=', line[cols['Employee']])])
                        if not tp_ids:
                            tp_label = _('Employee')
                            tp_content = line[cols['Employee']]
                        else:
                            r_employee = tp_ids[0]
                    if line[cols['Journal']]:
                        tp_ids = self.pool.get('account.journal').search(cr, uid, ['|', ('name', '=', line[cols['Journal']]), ('code', '=', line[cols['Journal']]), ('instance_id', '=', current_instance)])
                        if not tp_ids:
                            tp_label = _('Journal')
                            tp_content = line[cols['Journal']]
                        else:
                            r_journal = tp_ids[0]
                    if tp_label and tp_content:
                        errors.append(_('Line %s. %s not found: %s') % (current_line_num, tp_label, tp_content,))
                        continue

                    list_third_party = []
                    if r_employee:
                        list_third_party.append(r_employee)
                    if r_partner:
                        list_third_party.append(r_partner)
                    if r_journal:
                        list_third_party.append(r_journal)
                    if len(list_third_party) > 1:
                        errors.append(_('Line %s. You cannot only add partner or employee or journal.') % (current_line_num,))
                        continue

                    # US-672 check Third party compat with account
                    if r_employee or r_journal or r_partner:
                        tp_check_res = self.pool.get('account.account').is_allowed_for_thirdparty(
                            cr, uid, [r_account],
                            employee_id=r_employee,
                            transfer_journal_id=r_journal,
                            partner_id=r_partner,
                            context=context)[r_account]
                        if not tp_check_res:
                            errors.append(_("Line %s. Thirdparty not compatible with account '%s - %s'") % (current_line_num, account.code, account.name, ))
                            continue

                    # Check analytic axis only if G/L account is analytic-a-holic
                    if account.is_analytic_addicted:
                        # Check Destination
                        if not line[cols['Destination']]:
                            errors.append(_('Line %s. No destination specified!') % (current_line_num,))
                            continue
                        destination_ids = self.pool.get('account.analytic.account').search(cr, uid, [('category', '=', 'DEST'), '|', ('name', '=', line[cols['Destination']]), ('code', '=', line[cols['Destination']])])
                        if not destination_ids:
                            errors.append(_('Line %s. Destination %s not found!') % (current_line_num, line[cols['Destination']],))
                            continue
                        r_destination = destination_ids[0]
                        # Check Cost Center
                        if not line[cols['Cost Centre']]:
                            errors.append(_('Line %s. No cost center specified!') % (current_line_num,))
                            continue
                        # If necessary cast the CC into a string, otherwise the below search would crash
                        if not isinstance(line[cols['Cost Centre']], basestring):
                            line[cols['Cost Centre']] = '%s' % (line[cols['Cost Centre']])
                        cc_ids = self.pool.get('account.analytic.account').search(cr, uid, [('category', '=', 'OC'), '|', ('name', '=', line[cols['Cost Centre']]), ('code', '=', line[cols['Cost Centre']])])
                        if not cc_ids:
                            errors.append(_('Line %s. Cost Center %s not found!') % (current_line_num, line[cols['Cost Centre']]))
                            continue
                        r_cc = cc_ids[0]
                        # Check Cost Center type
                        cc = self.pool.get('account.analytic.account').browse(cr, uid, r_cc, context)
                        if cc.type == 'view':
                            errors.append(_('Line %s. %s is a VIEW type Cost Center!') % (current_line_num, line[cols['Cost Centre']]))
                            continue
                        # Check Funding Pool (added since UTP-1082)
                        r_fp = msf_fp_id
                        if line[cols['Funding Pool']]:
                            fp_ids = self.pool.get('account.analytic.account').search(cr, uid, [('category', '=', 'FUNDING'), '|', ('name', '=', line[cols['Funding Pool']]), ('code', '=', line[cols['Funding Pool']])])
                            if not fp_ids:
                                errors.append(_('Line %s. Funding Pool %s not found!') % (current_line_num, line[cols['Funding Pool']]))
                                continue
                            r_fp = fp_ids[0]
                    # NOTE: There is no need to check G/L account, Cost Center and Destination regarding document/posting date because this check is already done at Journal Entries validation.

                    # Registering data regarding these "keys":
                    # - G/L Account
                    # - Third Party
                    # - Destination
                    # - Cost Centre
                    # - Booking Currency
                    vals = {
                        'description': line[cols['Description']] or '',
                        'ref': line[cols['Reference']] or '',
                        'account_id': r_account or False,
                        'debit': r_debit or 0.0,
                        'credit': r_credit or 0.0,
                        'cost_center_id': r_cc or False,
                        'destination_id': r_destination or False,
                        'document_date': r_document_date or False,
                        'funding_pool_id': r_fp or False,
                        'date': date or False,
                        'currency_id': r_currency or False,
                        'wizard_id': wiz.id,
                        'period_id': period and period.id or False,
                        'employee_id': r_employee or False,
                        'partner_id': r_partner or False,
                        'transfer_journal_id': r_journal or False,
                    }
                    # UTP-1056: Add employee possibility. So we need to check if employee and/or partner is authorized
                    partner_needs = self.pool.get('account.bank.statement.line').onchange_account(cr, uid, False, account_id=account.id, context=context)
                    if not partner_needs:
                        errors.append(_('Line %s. No info about given account: %s') % (current_line_num, account.code,))
                        continue
                    # Check result
                    partner_options = partner_needs['value']['partner_type']['options']
                    if r_partner and ('res.partner', 'Partner') not in partner_options:
                        errors.append(_('Line %s. You cannot use a partner for the given account: %s.') % (current_line_num, account.code))
                        continue
                    if r_employee and ('hr.employee', 'Employee') not in partner_options:
                        errors.append(_('Line %s. You cannot use an employee for the given account: %s.') % (current_line_num, account.code))
                        continue
                    if r_journal and ('account.journal', 'Journal') not in partner_options:
                        errors.append(_('Line %s. You cannot use a journal for the given account: %s.') % (current_line_num, account.code))
                    line_res = self.pool.get('msf.doc.import.accounting.lines').create(cr, uid, vals, context)
                    if not line_res:
                        errors.append(_('Line %s. A problem occured for line registration. Please contact an Administrator.') % (current_line_num,))
                        continue
                    created += 1
                # Check if all is ok for the file
                ## The lines should be balanced for each currency
                for c in money:
                    if abs(money[c]['debit'] - money[c]['credit']) >= 10**-2:
                        raise osv.except_osv(_('Error'), _('Currency %s is not balanced: %s') % (money[c]['name'], (money[c]['debit'] - money[c]['credit']),))
            # Update wizard
            self.write(cr, uid, ids, {'message': _('Check complete. Reading potential errors or write needed changes.'), 'progression': 100.0})

            wiz_state = 'done'
            # If errors, cancel probable modifications
            if errors:
                cr.rollback()
                created = 0
                message = _('Import FAILED.')
                # Delete old errors
                error_ids = self.pool.get('msf.doc.import.accounting.errors').search(cr, uid, [], context)
                if error_ids:
                    self.pool.get('msf.doc.import.accounting.errors').unlink(cr, uid, error_ids ,context)
                # create errors lines
                for e in errors:
                    self.pool.get('msf.doc.import.accounting.errors').create(cr, uid, {'wizard_id': wiz.id, 'name': e}, context)
                wiz_state = 'error'
            else:
                # Update wizard
                self.write(cr, uid, ids, {'message': _('Writing changes…'), 'progression': 0.0})
                # Create all journal entries
                self.create_entries(cr, uid, ids, file_journal_id, context)
                message = _('Import successful.')

            # Update wizard
            self.write(cr, uid, ids, {'message': message, 'state': wiz_state, 'progression': 100.0})

            # Close cursor
            if not from_yml:
                cr.commit()
                cr.close(True)
        except osv.except_osv as osv_error:
            cr.rollback()
            self.write(cr, uid, ids, {'message': _("An error occured. %s: %s") % (osv_error.name, osv_error.value,), 'state': 'done', 'progression': 100.0})
            if not from_yml:
                cr.close(True)
        except Exception as e:
            cr.rollback()
            self.write(cr, uid, ids, {'message': _("An error occured: %s") % (e.args and e.args[0] or '',), 'state': 'done', 'progression': 100.0})
            if not from_yml:
                cr.close(True)
        return True

    def button_validate(self, cr, uid, ids, context=None):
        """
        Launch process in a thread and return a wizard
        """
        # Some checks
        if not context:
            context = {}
        if context.get('from_yml', False):
            res = self.write(cr, uid, ids, {'state': 'inprogress'}, context=context)
            self._import(cr, uid, ids, context=context)
        else:
            # Launch a thread if we come from web
            thread = threading.Thread(target=self._import, args=(cr.dbname, uid, ids, context))
            thread.start()
            res = self.write(cr, uid, ids, {'state': 'inprogress'}, context=context)
        return res

    def button_update(self, cr, uid, ids, context=None):
        """
        Update view
        """
        return False

msf_doc_import_accounting()

class msf_doc_import_accounting_lines(osv.osv):
    _name = 'msf.doc.import.accounting.lines'
    _rec_name = 'document_date'

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
        'transfer_journal_id': fields.many2one('account.journal', 'Journal', required=False, readonly=True),
        'period_id': fields.many2one('account.period', "Period", required=True, readonly=True),
        'wizard_id': fields.integer("Wizard", required=True, readonly=True),
    }

    _defaults = {
        'description': lambda *a: '',
        'ref': lambda *a: '',
        'document_date': lambda *a: strftime('%Y-%m-%d'),
        'date': lambda *a: strftime('%Y-%m-%d'),
        'debit': lambda *a: 0.0,
        'credit': lambda *a: 0.0,
    }

msf_doc_import_accounting_lines()

class msf_doc_import_accounting_errors(osv.osv_memory):
    _name = 'msf.doc.import.accounting.errors'

    _columns = {
        'name': fields.text("Description", readonly=True, required=True),
        'wizard_id': fields.many2one('msf.doc.import.accounting', "Wizard", required=True, readonly=True),
    }

msf_doc_import_accounting_errors()
# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
