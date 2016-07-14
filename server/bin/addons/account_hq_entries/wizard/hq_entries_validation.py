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
from tools.translate import _
from time import strftime

class hq_entries_validation(osv.osv_memory):
    _name = 'hq.entries.validation'
    _description = 'HQ entries validation'

    _columns = {
        'txt': fields.char("Text", size=128, readonly="1"),
        'line_ids': fields.many2many('hq.entries', 'hq_entries_validation_rel', 'wizard_id', 'line_id', "Selected lines", help="Lines previously selected by the user", readonly=True),
        'process_ids': fields.many2many('hq.entries', 'hq_entries_validation_process_rel', 'wizard_id', 'line_id', "Valid lines", help="Lines that would be processed", readonly=True),
        'running': fields.boolean('Is running'),
    }

    _defaults = {
        'running': False,
    }

    def default_get(self, cr, uid, fields, context=None):
        # check transaction before showing wizard
        line_ids = context and context.get('active_ids', []) or []
        if isinstance(line_ids, (int, long)):
            line_ids = [line_ids]

        self.pool.get('hq.entries').check_hq_entry_transaction(cr, uid,
            line_ids, self._name, context=context)

        return super(hq_entries_validation, self).default_get(cr, uid, fields,
            context=context)

    # UTP-1101: Extract the method to create AD for being called also for the REV move
    def create_distribution_id(self, cr, uid, currency_id, line, account):
        current_date = strftime('%Y-%m-%d')
        line_cc_first = line.cost_center_id_first_value and line.cost_center_id_first_value.id or False
        line_cc_id = line.cost_center_id and line.cost_center_id.id  or False
        line_account_first = line.account_id_first_value and line.account_id_first_value.id or False

        cc_id = line_cc_first or line_cc_id or False
        fp_id = line.analytic_id and line.analytic_id.id or False
        if line_cc_id != line_cc_first or line_account_first != line.account_id.id:
            fp_id = self.pool.get('ir.model.data').get_object_reference(cr, uid, 'analytic_distribution', 'analytic_account_msf_private_funds')[1]
        f1_id = line.free_1_id and line.free_1_id.id or False
        f2_id = line.free_2_id and line.free_2_id.id or False
        destination_id = line.destination_id_first_value and line.destination_id_first_value.id or account.default_destination_id and account.default_destination_id.id or False
        distrib_id = self.pool.get('analytic.distribution').create(cr, uid, {})
        if distrib_id:
            common_vals = {'distribution_id':distrib_id,
                'currency_id':currency_id,
                'percentage':100.0,
                'date':line.date or current_date,
                'source_date':line.date or current_date,
                'destination_id':destination_id}
            common_vals.update({'analytic_id':cc_id})
            self.pool.get('cost.center.distribution.line').create(cr, uid, common_vals)
            common_vals.update({'analytic_id':fp_id, 'cost_center_id':cc_id})
            self.pool.get('funding.pool.distribution.line').create(cr, uid, common_vals)
            del common_vals['cost_center_id']
            del common_vals['destination_id']
            if f1_id:
                common_vals.update({'analytic_id':f1_id})
                self.pool.get('free.1.distribution.line').create(cr, uid, common_vals)
            if f2_id:
                common_vals.update({'analytic_id':f2_id})
                self.pool.get('free.2.distribution.line').create(cr, uid, common_vals)
        return distrib_id

    def create_move(self, cr, uid, ids, period_id=False, currency_id=False, date=None, journal=None, orig_acct=None, context=None):
        """
        Create a move with given hq entries lines
        Return created lines (except counterpart lines)
        """
        # Some verifications
        if context is None:
            context = {}
        if isinstance(ids, (int, long)):
            ids = [ids]
        if not period_id:
            raise osv.except_osv(_('Error'), _('Period is missing!'))
        if not currency_id:
            raise osv.except_osv(_('Error'), _('Currency is missing!'))
        if not date:
            date = strftime('%Y-%m-%d')
        # Prepare some values
        res = {}
        counterpart_account_id = self.pool.get('res.users').browse(cr, uid, uid).company_id.counterpart_hq_entries_default_account and \
            self.pool.get('res.users').browse(cr, uid, uid).company_id.counterpart_hq_entries_default_account.id or False
        if not counterpart_account_id:
            raise osv.except_osv(_('Warning'), _('Default counterpart for HQ Entries is not set. Please configure it to Company Settings.'))

        if ids:
            # prepare some values
            journal_ids = self.pool.get('account.journal').search(cr, uid, [('type', '=', 'hq'),
                                                                            ('is_current_instance', '=', True)])
            if not journal_ids:
                raise osv.except_osv(_('Warning'), _('No HQ journal found!'))
            journal_id = journal_ids[0]
            # Use defined journal (if given)
            if journal:
                journal_id = journal
            # create move
            move_id = self.pool.get('account.move').create(cr, uid, {
                'date': date,
                'document_date': date,
                'journal_id': journal_id,
                'period_id': period_id,
            })
            total_debit = 0
            total_credit = 0

            # Check if document_date is the same as all lines
            hqentries_obj = self.pool.get('hq.entries')
            for line in hqentries_obj.browse(cr, uid, ids, context=context):
                if not line.account_id_first_value:
                    raise osv.except_osv(_('Error'), _('An account is missing!'))
                # create new distribution (only for expense accounts)
                distrib_id = self.create_distribution_id(cr, uid, currency_id, line, line.account_id_first_value)
                vals = {
                    'account_id': line.account_id_first_value.id,
                    'period_id': period_id,
                    'journal_id': journal_id,
                    'date': line.date,
                    'date_maturity': line.date,
                    'document_date': line.document_date,
                    'move_id': move_id,
                    'analytic_distribution_id': distrib_id,
                    'name': line.name or '',
                    'currency_id': currency_id,
                    'partner_txt': line.partner_txt or '',
                    'reference': line.ref or ''
                }
                # Fetch debit/credit
                debit = 0.0
                credit = 0.0
                amount = line.amount or 0.0
                if amount < 0.0:
                    credit = abs(amount)
                else:
                    debit = abs(amount)
                vals.update({'debit_currency': debit, 'credit_currency': credit,})
                move_line_id = self.pool.get('account.move.line').create(cr, uid, vals, context={}, check=False)
                res[line.id] = move_line_id
                # Increment totals
                total_debit += debit
                total_credit += credit
            # counterpart line
            counterpart_vals = {}
            account_ids = self.pool.get('account.account').search(cr, uid, [('id', '=', counterpart_account_id)])
            if account_ids:
                counterpart_vals.update({'account_id': account_ids[0],})
            if orig_acct:
                counterpart_vals.update({'account_id': orig_acct,})
            # vals
            counterpart_vals.update({
                'period_id': period_id,
                'journal_id': journal_id,
                'move_id': move_id,
                'date': date,
                'date_maturity': date,
                'document_date': date,
                'name': 'HQ Entry Counterpart',
                'currency_id': currency_id,
            })
            counterpart_debit = 0.0
            counterpart_credit = 0.0
            if (total_debit - total_credit) < 0:
                counterpart_debit = abs(total_debit - total_credit)
            else:
                counterpart_credit = abs(total_debit - total_credit)
            counterpart_vals.update({'debit_currency': counterpart_debit, 'credit_currency': counterpart_credit,})
            self.pool.get('account.move.line').create(cr, uid, counterpart_vals, context={}, check=False)
            # Post move
            self.pool.get('account.move').post(cr, uid, [move_id])
        return res

    def process_split(self, cr, uid, lines, context=None):
        """
        Create a journal entry with the original HQ Entry.
        Create a journal entry with all split lines and a specific counterpart.
        Mark HQ Lines as user_validated.
        """
        aml_obj = self.pool.get('account.move.line')

        # Checks
        if context is None:
            context = {}
        if not lines:
            return False
        # Prepare some values
        original_lines = set()
        original_move_ids = []
        ana_line_obj = self.pool.get('account.analytic.line')
        od_journal_ids = self.pool.get('account.journal').search(cr, uid, [('type', '=', 'correction'), ('is_current_instance', '=', True)])
        if not od_journal_ids:
            raise osv.except_osv(_('Error'), _('No correction journal found!'))
        od_journal_id = od_journal_ids[0]
        all_lines = set()
        pure_ad_cor_ji_ids = []

        # Split lines into 2 groups:
        #+ original ones
        #+ split ones
        for line in lines:
            if line.is_original:
                original_lines.add(line)
                all_lines.add(line.id)
            elif line.is_split:
                original_lines.add(line.original_id)
                all_lines.add(line.original_id.id)
        # Create the original line as it is (and its reverse)
        for line in original_lines:
            # PROCESS ORIGINAL LINES
            res_move = self.create_move(cr, uid, line.id, line.period_id.id, line.currency_id.id, date=line.date, context=context)
            original_move = aml_obj.browse(cr, uid, res_move[line.id])

            move_id = original_move.move_id.id
            original_move_ids.append(move_id)
            # Add split lines to "all lines"
            for sl in line.split_ids:
                all_lines.add(sl.id)
            # PROCESS SPLIT LINES
            #if any([x.account_changed for x in line.split_ids]):
            # utp101 mark the original line as reversed
            aml_obj.write(cr, uid, original_move.id, {'corrected': True, 'have_an_historic': True} , context=context)
            original_account_id = original_move.account_id.id

            new_res_move = self.create_move(cr, uid, [x.id for x in line.split_ids], line.period_id.id, line.currency_id.id, date=line.date, journal=od_journal_id, orig_acct=original_account_id)
            # original move line
            original_ml_result = res_move[line.id]
            # Mark new journal items as corrections for the first one
            new_expense_ml_ids = new_res_move.values()
            pure_ad_cor_ji_ids += new_expense_ml_ids
            corr_name = 'COR1 - ' + original_move.name
            aml_obj.write(cr, uid, new_expense_ml_ids, {'corrected_line_id': original_ml_result, 'name': corr_name }, context=context, check=False, update_check=False)

            # get the move_id
            corr_moves = aml_obj.browse(cr, uid, new_expense_ml_ids, context=context)
            corr_move_id = corr_moves[0].move_id.id
            original_account_id = original_move.account_id.id
            # get the counterpart id
            counterpart_id = aml_obj.search(cr, uid, ['&',('move_id','=',corr_move_id),('corrected_line_id','=',False)], context=context)

            # Create also the AD from the original line and update it into the counterpart move
            if not line.account_id_first_value:
                raise osv.except_osv(_('Error'), _('An account is missing!'))
            # create new distribution (only for expense accounts)
            distrib_id = self.create_distribution_id(cr, uid, line.currency_id.id, line, line.account_id_first_value)
            aml_obj.write(cr, uid, counterpart_id, {
                'reversal': True,
                'name': 'REV - ' + original_move.name,
                'account_id': original_account_id,
                'analytic_distribution_id': distrib_id,
                'reversal_line_id': original_move.id,
                'partner_txt': original_move.partner_txt or '',
                'reference': line.ref or ' ', # UFTP-342: if HQ entry reference is empty, do not display anything. As a field function exists for account_move_line object, so we add a blank char to avoid this problem
                }, context=context, check=False, update_check=False)

            # create the analytic lines as a reversed copy of the original
            initial_ana_ids = ana_line_obj.search(cr, uid, [('move_id.move_id', '=', move_id)])  # original move_id
            res_reverse = ana_line_obj.reverse(cr, uid, initial_ana_ids, posting_date=line.date)
            acor_journal_ids = self.pool.get('account.analytic.journal').search(cr, uid, [('type', '=', 'correction'), ('is_current_instance', '=', True)])
            if not acor_journal_ids:
                raise osv.except_osv(_('Error'), _('No correction journal found!'))
            acor_journal_id = acor_journal_ids[0]
            if not acor_journal_id:
                raise osv.except_osv(_('Warning'), _('No analytic correction journal found!'))
            ana_line_obj.write(cr, uid, res_reverse, {'journal_id': acor_journal_id, 'move_id': counterpart_id[0]}) # UTP-1106: change move_id link as it's wrong one

            # Mark new analytic items as correction for original line
            # - take original move line
            # - search linked analytic line
            # - use new journal items (from split lines) to find their analytic lines
            # - browse the name to add COR1
            # - add "last_corrected_id" link for all these new analytic lines to the first one (original analytic line)
            original_aal_ids = ana_line_obj.search(cr, uid, [('move_id', '=', original_ml_result)])
            new_aal_ids = ana_line_obj.search(cr, uid, [('move_id', 'in', new_expense_ml_ids)])
            browse_aals = ana_line_obj.browse(cr, uid, new_aal_ids, context=context)
            for aal in browse_aals:
                cor_name = 'COR1 - ' + aal.name
                ana_line_obj.write(cr, uid, aal.id, {'last_corrected_id': original_aal_ids[0],'name': cor_name})
            # also write the OD entry_sequence to the REV aal
            # ana_line_obj.write(cr, uid, res_reverse, {'journal_id': acor_journal_id, 'entry_sequence': aal.entry_sequence})
            cr.execute('''update account_analytic_line set entry_sequence = '%s' where id = %s''' % (aal.entry_sequence, res_reverse[0]))

        # US-1333/1 - BKLG-12 pure AD correction flag marker for splitted lines
        # (do this bypassing model write)
        if pure_ad_cor_ji_ids:
            osv.osv.write(aml_obj, cr, uid, list(set(pure_ad_cor_ji_ids)),
                {'last_cor_was_only_analytic': True,})

        # Mark ALL lines as user_validated
        self.pool.get('hq.entries').write(cr, uid, list(all_lines), {'user_validated': True}, context=context)
        return original_move_ids

    def button_validate(self, cr, uid, ids, context=None):
        """
        Validate all given lines (process_ids)
        """
        # Some verifications
        if context is None:
            context = {}
        if isinstance(ids, (int, long)):
            ids = [ids]
        for wiz in self.browse(cr, uid, ids, context=context):
            if wiz.running:
                return {}
            self.write(cr, uid, [wiz.id], {'running': True})
            active_ids = [x.id for x in wiz.process_ids]
            if isinstance(active_ids, (int, long)):
                active_ids = [active_ids]
            # Fetch some data
            ana_line_obj = self.pool.get('account.analytic.line')
            distrib_fp_line_obj = self.pool.get('funding.pool.distribution.line')
            distrib_cc_line_obj = self.pool.get('cost.center.distribution.line')
            # Search an analytic correction journal
            acor_journal_id = False
            acor_journal_ids = self.pool.get('account.analytic.journal').search(cr, uid, [('type', '=', 'correction'),
                                                                                          ('is_current_instance', '=', True)])
            if acor_journal_ids:
                acor_journal_id = acor_journal_ids[0]
            # Tag active_ids as user validated
            to_write = {}
            account_change = []
            cc_change = []
            cc_account_change = []
            split_change = []
            current_date = strftime('%Y-%m-%d')
            pure_ad_cor_ji_ids = []

            # US-672/2 account/partner compatible check pass
            account_partner_not_compat_log = []
            for line in self.pool.get('hq.entries').browse(cr, uid, active_ids,
                context=context):
                if not line.is_account_partner_compatible:
                    entry_msg = "%s - %s: %s - %s / %s" % (
                        line.name or '', line.ref or '',
                        line.account_id.code, line.account_id.name or '',
                        line.partner_txt or '')
                    account_partner_not_compat_log.append(entry_msg)
            if account_partner_not_compat_log:
                account_partner_not_compat_log.insert(0,
                    _('Following entries have account/partner not compatible:'))
                raise osv.except_osv(_('Error'),
                    "\n".join(account_partner_not_compat_log))

            for line in self.pool.get('hq.entries').browse(cr, uid, active_ids, context=context):
                #UF-1956: interupt validation if currency is inactive
                if line.currency_id.active is False:
                    self.write(cr, uid, [wiz.id], {'running': False})
                    raise osv.except_osv(_('Warning'), _('Currency %s is not active!') % (line.currency_id and line.currency_id.name or '',))
                if line.analytic_state != 'valid':
                    self.write(cr, uid, [wiz.id], {'running': False})
                    raise osv.except_osv(_('Warning'), _('Invalid analytic distribution!'))
                # UTP-760: Do other modifications for split lines
                if line.is_original or line.is_split:
                    split_change.append(line)
                    continue
                if not line.user_validated:
                    to_write.setdefault(line.currency_id.id, {}).setdefault(line.period_id.id, {}).setdefault(line.date, []).append(line.id)

                    if line.account_id.id != line.account_id_first_value.id:
                        if line.cost_center_id.id != line.cost_center_id_first_value.id or line.destination_id.id != line.destination_id_first_value.id:
                            cc_account_change.append(line)
                        else:
                            account_change.append(line)
                    elif line.cost_center_id.id != line.cost_center_id_first_value.id or line.destination_id.id != line.destination_id_first_value.id:
                        if line.cost_center_id_first_value and line.cost_center_id_first_value.id:
                            cc_change.append(line)
            all_lines = {}
            for currency in to_write:
                for period in to_write[currency]:
                    for date in to_write[currency][period]:
                        lines = to_write[currency][period][date]
                        write = self.create_move(cr, uid, lines, period, currency, date)
                        all_lines.update(write)
                        if write:
                            self.pool.get('hq.entries').write(cr, uid, write.keys(), {'user_validated': True}, context=context)

            for line in account_change:
                corrected_distrib_id = self.pool.get('analytic.distribution').create(cr, uid, {
                        'funding_pool_lines': [(0, 0, {
                                'percentage': 100,
                                'analytic_id': line.analytic_id.id,
                                'cost_center_id': line.cost_center_id.id,
                                'currency_id': line.currency_id.id,
                                'source_date': line.date,
                                'destination_id': line.destination_id.id,
                            })]
                        })
                self.pool.get('account.move.line').correct_account(cr, uid, all_lines[line.id], line.date, line.account_id.id, corrected_distrib_id)

            for line in cc_change:
                # actual distrib_id
                distrib_id = self.pool.get('account.move.line').read(cr, uid, all_lines[line.id], ['analytic_distribution_id'])['analytic_distribution_id'][0]
                # update the distribution
                distrib_fp_lines = distrib_fp_line_obj.search(cr, uid, [('cost_center_id', '=', line.cost_center_id_first_value.id), ('distribution_id', '=', distrib_id)])
                distrib_fp_line_obj.write(cr, uid, distrib_fp_lines, {'cost_center_id': line.cost_center_id.id, 'source_date': line.date, 'destination_id': line.destination_id.id})
                distrib_cc_lines = distrib_cc_line_obj.search(cr, uid, [('analytic_id', '=', line.cost_center_id_first_value.id), ('distribution_id', '=', distrib_id)])
                distrib_cc_line_obj.write(cr, uid, distrib_cc_lines, {'analytic_id': line.cost_center_id.id, 'source_date': line.date, 'destination_id': line.destination_id.id})

                # reverse ana lines
                fp_old_lines = ana_line_obj.search(cr, uid, [
                    ('cost_center_id', '=', line.cost_center_id_first_value.id),
                    ('destination_id', '=', line.destination_id_first_value.id),
                    ('move_id', '=', all_lines[line.id])
                    ])
                # UTP-943: Add original date as reverse date
                res_reverse = ana_line_obj.reverse(cr, uid, fp_old_lines, posting_date=line.date)
                # Give them analytic correction journal (UF-1385 in comments)
                if not acor_journal_id:
                    self.write(cr, uid, [wiz.id], {'running': False})
                    raise osv.except_osv(_('Warning'), _('No analytic correction journal found!'))
                ana_line_obj.write(cr, uid, res_reverse, {'journal_id': acor_journal_id})
                # create new lines
                if not fp_old_lines: # UTP-546 - this have been added because of sync that break analytic lines generation
                    continue
                # UTP-1118: posting date should be those from initial HQ entry line
                cor_ids = ana_line_obj.copy(cr, uid, fp_old_lines[0], {'date': line.date, 'source_date': line.date, 'cost_center_id': line.cost_center_id.id,
                    'account_id': line.analytic_id.id, 'destination_id': line.destination_id.id, 'journal_id': acor_journal_id, 'last_correction_id': fp_old_lines[0]})
                # update new ana line
                cor_vals = {'last_corrected_id': fp_old_lines[0]}
                # Add COR before analytic line name (UTP-1118: missing info)
                cor_data = ana_line_obj.read(cr, uid, cor_ids, ['name'])
                for piece_of_cor_data in cor_data:
                    cor_name = cor_data.get('name', '')
                    new_name = self.pool.get('account.move.line').join_without_redundancy(cor_name, 'COR')
                    if new_name:
                        cor_vals.update({'name': new_name})
                ana_line_obj.write(cr, uid, cor_ids, cor_vals)
                # UTP-1118: Change entry sequence so that it's compatible with analytic journal (correction)
                if isinstance(cor_ids, (int, long)):
                    cor_ids = [cor_ids]
                cor_ids += res_reverse

                gl_journal_ids = self.pool.get('account.journal').search(cr, uid, [('type', '=', 'correction'), ('is_current_instance', '=', True)])
                if not gl_journal_ids:
                    self.write(cr, uid, [wiz.id], {'running': False})
                    raise osv.except_osv(_('Error'), _('No correction journal found!'))
                gl_journal_obj = self.pool.get('account.journal').browse(cr, uid, gl_journal_ids[0], context=context)
                journal_sequence_id = gl_journal_obj.sequence_id.id
                journal_code = gl_journal_obj.code
                seq_obj = self.pool.get('ir.sequence')
                seqnum = False
                for ana_line in ana_line_obj.browse(cr, uid, cor_ids, context=context):
                    if not seqnum:
                        seqnum = seq_obj.get_id(cr, uid, journal_sequence_id,
                            context={'fiscalyear_id': ana_line.period_id.fiscalyear_id.id})
                    prefix = ana_line.instance_id.move_prefix
                    entry_seq = "%s-%s-%s" % (prefix, journal_code, seqnum)
                    cr.execute('UPDATE account_analytic_line SET entry_sequence = %s WHERE id = %s', (entry_seq, ana_line.id))
                # update old ana lines
                ana_line_obj.write(cr, uid, fp_old_lines, {'is_reallocated': True})

                # register pure AD
                pure_ad_cor_ji_ids.append(all_lines[line.id])

            for line in cc_account_change:
                # call correct_account with a new arg: new_distrib
                corrected_distrib_id = self.pool.get('analytic.distribution').create(cr, uid, {
                        'cost_center_lines': [(0, 0, {
                                'percentage': 100,
                                'analytic_id': line.cost_center_id.id,
                                'currency_id': line.currency_id.id,
                                'source_date': line.date,
                                'destination_id': line.destination_id.id,
                            })],
                        'funding_pool_lines': [(0, 0, {
                                'percentage': 100,
                                'analytic_id': line.analytic_id.id,
                                'cost_center_id': line.cost_center_id.id,
                                'currency_id': line.currency_id.id,
                                'source_date': line.date,
                                'destination_id': line.destination_id.id,
                            })]
                    })
                self.pool.get('account.move.line').correct_account(cr, uid, all_lines[line.id], line.date, line.account_id.id, corrected_distrib_id)

            # US-1333/1 - BKLG-12 pure AD correction flag marker
            # (do this bypassing model write)
            if pure_ad_cor_ji_ids:
                osv.osv.write(self.pool.get('account.move.line'), cr, uid,
                    list(set(pure_ad_cor_ji_ids)),
                    {'last_cor_was_only_analytic': True,})

            # Do split lines process
            original_move_ids = self.process_split(cr, uid, split_change, context=context)

            # Return HQ Entries Tree View in current view
            action_id = self.pool.get('ir.model.data').get_object_reference(cr, uid, 'account_hq_entries', 'action_hq_entries_tree')
            res = self.pool.get('ir.actions.act_window').read(cr, uid, action_id[1], [], context=context)
            res['target'] = 'crush'

            return res

hq_entries_validation()
# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
