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

def get_back_browse(self, cr, uid, context):
    background_id = context.get('background_id')
    if background_id:
        return self.pool.get('memory.background.report').browse(cr, uid, background_id)
    return False

class account_line_csv_export(osv.osv_memory):
    _name = 'account.line.csv.export'
    _description = 'Account Entries CSV Export'

    _columns = {
        'file': fields.binary(string='File to export', required=True, readonly=True),
        'filename': fields.char(size=128, string='Filename', required=True),
        'message': fields.char(size=256, string='Message', readonly=True),
    }

    def _account_move_line_to_csv(self, cr, uid, ids, writer, currency_id, context=None):
        """
        Take account_move_line and return a csv string
        """
        # Some verifications
        if not context:
            context = {}
        field_sel = self.pool.get('ir.model.fields').get_browse_selection
        back_browse = get_back_browse(self, cr, uid, context)

        if isinstance(ids, (int, long)):
            ids = [ids]
        if not writer:
            raise osv.except_osv(_('Error'), _('An error occured. Please contact an administrator to resolve this problem.'))
        # Prepare some value
        currency_name = ""
        if currency_id:
            currency_obj = self.pool.get('res.currency')
            currency_name = currency_obj.read(cr, uid, [currency_id], ['name'], context=context)[0].get('name', False)
        # Prepare csv head
        head = [_('Proprietary Instance'), _('Journal Code'), _('Entry Sequence'), _('Description'), _('Reference'), _('Document Date'), _('Posting Date'), _('Period'), _('Account'), _('Third party'), _('Book. Debit'), _('Book. Credit'), _('Book. currency')]
        if not currency_id:
            head += [_('Func. Debit'), _('Func. Credit'), _('Func. Currency')]
        else:
            head += [_('Output Debit'), _('Output Credit'), _('Output Currency')]
        head += [_('Reconcile'), _('State')]
        writer.writerow(map(lambda x: x.encode('utf-8'), head))
        # Sort items
        ids.sort()
        # Then write lines
        account_move_line_obj = self.pool.get('account.move.line')
        len_ids = len(ids)
        l = 0
        steps = 1000
        while l < len_ids:
            if back_browse:
                back_browse.update_percent(l/float(len_ids))
            old_l = l
            l += steps
            new_ids = ids[old_l:l]
            for ml in account_move_line_obj.browse(cr, uid, new_ids, context=context):
                csv_line = []
                #instance_id (Proprietary Instance)
                csv_line.append(ml.instance_id and ml.instance_id.code and ml.instance_id.code.encode('utf-8') or '')
                # journal_id
                csv_line.append(ml.journal_id and ml.journal_id.code and ml.journal_id.code.encode('utf-8') or '')
                #move_id (Entry Sequence)
                csv_line.append(ml.move_id and ml.move_id.name and ml.move_id.name.encode('utf-8') or '')
                #name
                csv_line.append(ml.name and ml.name.encode('utf-8') or '')
                #ref
                csv_line.append(ml.ref and ml.ref.encode('utf-8') or '')
                #document_date
                csv_line.append(ml.document_date or '')
                #date
                csv_line.append(ml.date or '')
                #period_id
                csv_line.append(ml.period_id and ml.period_id.name and ml.period_id.name.encode('utf-8') or '')
                #account_id code - name
                account_code = ml.account_id and ml.account_id.code and ml.account_id.code.encode('utf-8') or ''
                account_description = ml.account_id and ml.account_id.name and ml.account_id.name.encode('utf-8') or ''
                csv_line.append("%s - %s" % (account_code or '', account_description or ''))
                #partner_txt
                csv_line.append(ml.partner_txt and ml.partner_txt.encode('utf-8') or '')
                #debit_currency
                csv_line.append(ml.debit_currency or 0.0)
                #credit_currency
                csv_line.append(ml.credit_currency or 0.0)
                #currency_id
                csv_line.append(ml.currency_id and ml.currency_id.name and ml.currency_id.name.encode('utf-8') or '')
                if not currency_id or (currency_id and currency_id == ml.currency_id):
                    # uf-2327 no currency or same as booking
                    #debit
                    csv_line.append(ml.debit or 0.0)
                    #credit
                    csv_line.append(ml.credit or 0.0)
                    #functional_currency_id
                    csv_line.append(ml.functional_currency_id and ml.functional_currency_id.name and ml.functional_currency_id.name.encode('utf-8') or '')
                else:
                    context['date'] = ml.source_date or ml.date  # uf-2333 [FIX] reversal line: source_date or posting_date
                    amount = account_move_line_obj.calculate_output(cr, uid, currency_id, ml, round=False, context=context)
                    if amount < 0.0:
                        csv_line.append(0.0)
                        csv_line.append(abs(amount) or 0.0)
                    else:
                        #output amount (debit/credit) regarding booking currency
                        amount = currency_obj.compute(cr, uid, ml.currency_id.id, currency_id, ml.amount_currency, round=False, context=context)
                        if amount < 0.0:
                            csv_line.append(0.0)
                            csv_line.append(abs(amount) or 0.0)
                        else:
                            csv_line.append(abs(amount) or 0.0)
                            csv_line.append(0.0)
                    #output currency
                    csv_line.append(currency_name.encode('utf-8') or '')
                    #reconcile
                    csv_line.append(ml.reconcile_txt and ml.reconcile_txt.encode('utf-8') or '')
                    #state
                    csv_line.append(field_sel(cr, uid, ml, 'move_state', context).encode('utf-8'))
                    # Write line
                    writer.writerow(csv_line)

            #############################
            ###
            # This function could be used with a fields parameter in this method in order to create a CSV with field that could change
            ###
            #        for i, field in enumerate(fields):
            #            if i != 0:
            #                res += ';'
            #            res += str(field)
            #        res+= '\n'
            #        for ml in self.pool.get('account.move.line').browse(cr, uid, ids, context=context):
            #            for i, field in enumerate(fields):
            #                if i != 0:
            #                    res += ';'
            #                res+= ustr(getattr(ml, field, ''))
            #            res+= '\n'
            #############################
        return True

    def _account_analytic_line_to_csv(self, cr, uid, ids, writer, currency_id, context=None):
        """
        Take account_analytic_line and return a csv string
        """
        # Some verifications
        if not context:
            context = {}
        if isinstance(ids, (int, long)):
            ids = [ids]
        back_browse = get_back_browse(self, cr, uid, context)
        # Is funding pool column needed?
        display_fp = context.get('display_fp', False)
        if not writer:
            raise osv.except_osv(_('Error'), _('An error occured. Please contact an administrator to resolve this problem.'))
        # Prepare some value
        currency_name = ""
        field_sel = self.pool.get('ir.model.fields').get_browse_selection
        if currency_id:
            currency_obj = self.pool.get('res.currency')
            currency_name = currency_obj.read(cr, uid, [currency_id], ['name'], context=context)[0].get('name', False)
        user = self.pool.get('res.users').browse(cr, uid, uid, context=context)
        company_currency = user and user.company_id and user.company_id.currency_id and user.company_id.currency_id.name or ""
        # Prepare csv head
        head = [_('Proprietary Instance'), _('Journal Code'), _('Entry Sequence'), _('Description'), _('Reference'), _('Document Date'), _('Posting Date'), _('Period'), _('General Account')]
        if display_fp:
            head += [_('Destination'), _('Cost Center'), _('Funding Pool')]
        else:
            head += [_('Analytic Account')]
        head += [_('Third Party'), _('Booking Amount'), _('Book. Currency')]
        if not currency_id:
            head += [_('Func. Amount'), _('Func. Currency')]
        else:
            head += [_('Output Amount'), _('Output Currency')]
        head+= [_('Reversal Origin'), _('Entry status')]
        writer.writerow(map(lambda x: x.encode('utf-8'), head))
        # Sort items
        ids.sort()
        # Then write lines
        len_ids = len(ids)
        l = 0
        steps = 1000
        while l < len_ids:
            if back_browse:
                back_browse.update_percent(l/float(len_ids))
            old_l = l
            l += steps
            new_ids = ids[old_l:l]
            for al in new_ids and self.pool.get('account.analytic.line').browse(cr, uid, new_ids, context=context) or []:
                csv_line = []
                #instance_id
                csv_line.append(al.instance_id and al.instance_id.code and al.instance_id.code.encode('utf-8') or '')
                # journal_id
                csv_line.append(al.journal_id and al.journal_id.code and al.journal_id.code.encode('utf-8') or '')
                #sequence
                csv_line.append(al.move_id and al.move_id.move_id and al.move_id.move_id.name and al.move_id.move_id.name.encode('utf-8') or '')
                #name (description)
                csv_line.append(al.name and al.name.encode('utf-8') or '')
                #ref
                csv_line.append(al.ref and al.ref.encode('utf-8') or '')
                #document_date
                csv_line.append(al.document_date or '')
                #date
                csv_line.append(al.date or '')
                #period
                csv_line.append(al.period_id and al.period_id.name and al.period_id.name.encode('utf-8') or '')
                #general_account_id (general account) code  - name
                account_code = al.general_account_id and al.general_account_id.code and al.general_account_id.code.encode('utf-8') or ''
                account_description = al.general_account_id and al.general_account_id.name and al.general_account_id.name.encode('utf-8') or ''
                csv_line.append("%s - %s" % (account_code or '', account_description or ''))
                if display_fp:
                    # destination_id
                    csv_line.append(al.destination_id and al.destination_id.code and al.destination_id.code.encode('utf-8') or '')
                    #cost_center_id
                    csv_line.append(al.cost_center_id and al.cost_center_id.code and al.cost_center_id.code.encode('utf-8') or '')
                #account_id name (analytic_account)
                csv_line.append(al.account_id and al.account_id.code and al.account_id.code.encode('utf-8') or '')
                #third party
                csv_line.append(al.partner_txt and al.partner_txt.encode('utf-8') or '')
                #amount_currency
                csv_line.append(al.amount_currency or 0.0)
                #currency_id
                csv_line.append(al.currency_id and al.currency_id.name and al.currency_id.name.encode('utf-8') or '')
                if not currency_id:
                    #functional amount
                    csv_line.append(al.amount or 0.0)
                    #company currency
                    csv_line.append(company_currency.encode('utf-8') or '')
                else:
                    #output debit/credit
                    context['date'] = al.source_date or al.date  # uftp-361 [FIX] reversal line: source_date or posting_date
                    if al.is_reversal == True:
                        context.update({'date': al.document_date})
                    if al.last_corrected_id:
                        context.update({'date': al.document_date})
                    amount = currency_obj.compute(cr, uid, al.currency_id.id, currency_id, al.amount_currency, round=True, context=context)
                    csv_line.append(amount or 0.0)
                    #output currency
                    csv_line.append(currency_name.encode('utf-8') or '')
                csv_line.append(al.reversal_origin and al.reversal_origin.name and al.reversal_origin.name.encode('utf-8') or '')
                csv_line.append(al.move_state and field_sel(cr, uid, al, 'move_state', context).encode('utf-8') or '')
                # Write Line
                writer.writerow(csv_line)
        return True

    def _account_bank_statement_line_to_csv(self, cr, uid, ids, writer, currency_id, context=None):
        """
        Take account_bank_statement_line and return a csv string
        """
        # Some verifications
        if not context:
            context = {}
        if isinstance(ids, (int, long)):
            ids = [ids]
        if not writer:
            raise osv.except_osv(_('Error'), _('An error occured. Please contact an administrator to resolve this problem.'))

        # Prepare some value
        currency_name = ""
        field_sel = self.pool.get('ir.model.fields').get_browse_selection
        if currency_id:
            currency_obj = self.pool.get('res.currency')
            currency_name = currency_obj.read(cr, uid, [currency_id], ['name'], context=context)[0].get('name', False)
        # Prepare csv head
        head = [_('Document Date'), _('Posting Date'), _('Sequence'), _('Description'), _('Reference'), _('Account'), _('Third party'), _('Amount In'), _('Amount Out'), _('Currency'), _('Output In'), _('Output Out'), _('Output Currency')]
        head += [_('State'), _('Register Name')]
        writer.writerow(map(lambda x: x.encode('utf-8'), head))
        # Sort items
        ids.sort()
        # Then write lines
        for absl in self.pool.get('account.bank.statement.line').browse(cr, uid, ids, context=context):
            csv_line = []
            #document_date
            csv_line.append(absl.document_date or '')
            #date
            csv_line.append(absl.date or '')
            #sequence_for_reference (Entry Sequence)
            csv_line.append(absl.sequence_for_reference and absl.sequence_for_reference.encode('utf-8') or '')
            #name
            csv_line.append(absl.name and absl.name.encode('utf-8') or '')
            #ref
            csv_line.append(absl.ref and absl.ref.encode('utf-8') or '')
            #account_id code - name
            account_code = absl.account_id and absl.account_id.code and absl.account_id.code.encode('utf-8') or ''
            account_description = absl.account_id and absl.account_id.name and absl.account_id.name.encode('utf-8') or ''
            csv_line.append("%s - %s" % (account_code or '', account_description or ''))
            #partner_txt
            csv_line.append(absl.partner_id and absl.partner_id.name and absl.partner_id.name.encode('utf-8') or absl.employee_id and absl.employee_id.name and absl.employee_id.name.encode('utf-8') or absl.transfer_journal_id and absl.transfer_journal_id.code and absl.transfer_journal_id.code.encode('utf-8') or '')
            #debit_currency
            csv_line.append(absl.amount_in or 0.0)
            #credit_currency
            csv_line.append(absl.amount_out or 0.0)
            #currency_id
            csv_line.append(absl.currency_id and absl.currency_id.name and absl.currency_id.name.encode('utf-8') or '')
            if not currency_id:
                #debit
                csv_line.append(absl.functional_in or 0.0)
                #credit
                csv_line.append(absl.functional_out or 0.0)
                #functional_currency_id
                csv_line.append(absl.functional_currency_id and absl.functional_currency_id.name and absl.functional_currency_id.name.encode('utf-8') or '')
            else:
                #output amount (debit/credit) regarding booking currency
                amount = currency_obj.compute(cr, uid, absl.currency_id.id, currency_id, absl.amount, round=True, context=context)
                if amount < 0.0:
                    csv_line.append(0.0)
                    csv_line.append(abs(amount) or 0.0)
                else:
                    csv_line.append(abs(amount) or 0.0)
                    csv_line.append(0.0)
                #output currency
                csv_line.append(currency_name.encode('utf-8') or '')
            #state
            csv_line.append(field_sel(cr, uid, absl, 'state', context).encode('utf-8'))
            #statement
            csv_line.append(absl.statement_id and absl.statement_id.name and absl.statement_id.name.encode('utf-8') or '')
            # Write line
            writer.writerow(csv_line)
        return True

account_line_csv_export()
# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
