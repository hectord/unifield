# -*- coding: utf-8 -*-
##############################################################################
#
#    Author: Yannick Vaucher, Guewen Baconnier
#    Copyright 2012 Camptocamp SA
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

import datetime

from dateutil.relativedelta import relativedelta

from osv import osv, fields
from tools.translate import _

class WizardCurrencyrevaluation(osv.osv_memory):
    _name = 'wizard.currency.revaluation'

    _columns = {
                'revaluation_method': fields.selection(
                    [('liquidity_month', _("Liquidity (Month-end)")),
                     ('liquidity_year', _("Liquidity (Year-end)")),
                     ('other_bs', _("Other B/S (Year-end)")),
                     ],
                    string=_("Revaluation method"), required=True),
                'fiscalyear_id': fields.many2one(
                    'account.fiscalyear', string=_("Fiscal year"),
                    domain=[('state', '=', 'draft')],
                    required=True),
                'period_id': fields.many2one(
                    'account.period', string=_("Period"),
                    domain="[('fiscalyear_id', '=', fiscalyear_id)]"),
                'currency_table_id': fields.many2one(
                    'res.currency.table', string=_("Currency table"),
                    domain=[('state', '=', 'valid')]),
                'journal_id': fields.many2one(
                    'account.journal', string=_("Entry journal"),
                    help=_("Journal used for revaluation entries."),
                    readonly=True),
                'result_period_id': fields.many2one(
                    'account.period', string=_(u"Entry period"), required=True,
                    domain="[('fiscalyear_id', '=', fiscalyear_id), ('state', '!=', 'created')]",
                    help=_("Period used for revaluation entries."),
                    readonly=True),
                'posting_date': fields.date(
                    _('Entry date'), readonly=True,
                    help=_("Revaluation entry date (document and posting date)")),
                'label': fields.char(
                    'Entry description',
                     size=100,
                     help="This label will be inserted in entries description."
                         " You can use %(account)s, %(currency)s"
                         " and %(rate)s keywords.",
                     required=True),
    }

    def _get_default_fiscalyear_id(self, cr, uid, context=None):
        """Get default fiscal year to process."""
        if context is None:
            context = {}
        user_obj = self.pool.get('res.users')
        cp = user_obj.browse(cr, uid, uid, context=context).company_id
        current_date = datetime.date.today().strftime('%Y-%m-%d')
        fiscalyear_obj = self.pool.get('account.fiscalyear')
        fiscalyear_ids = fiscalyear_obj.search(
            cr, uid,
            [('date_start', '<', current_date),
             ('date_stop', '>', current_date),
             ('company_id', '=', cp.id)],
            limit=1,
            context=context)
        return fiscalyear_ids and fiscalyear_ids[0] or False

    _defaults = {
        'label': "%(currency)s %(account)s %(rate)s",
        'revaluation_method': lambda *args: 'liquidity_month',
        'fiscalyear_id': _get_default_fiscalyear_id,
    }

    def _is_revaluated(self, cr, uid, period_id, revaluation_method=False,
        context=None):
        """
        check if the revaluation has already been run by checking
        for a non-zero entry in the REV journal in the current instance
        and according to reval method filter by account type liquidity or not
        at line level
        """
        journal_obj = self.pool.get('account.journal')
        comp_id = self.pool.get('res.users').browse(cr, uid, uid,
            context=context).company_id
        instance_id = comp_id.instance_id.id

        # get rev journal of instance
        domain = [
            ('type', '=', 'revaluation'),
            ('instance_id', '=', instance_id),
        ]
        rev_journal_id = journal_obj.search(cr, uid, domain)[0]

        # default domain in term of rev journal and period
        domain = [
            ('journal_id', '=', rev_journal_id),
            ('period_id', '=', period_id),
        ]

        account_model = 'account.move'
        account_ids_domain = False
        if revaluation_method in ('liquidity_year', 'other_bs'):
            # filter by liquidity account type or not  for end year methods
            # => to filter by account type we are at line level
            account_model = 'account.move.line'
            account_liquidity_ids = self.pool.get('account.account').search(cr,
                uid, [('type', '=', 'liquidity')], context=context)
            if comp_id.revaluation_default_account:
                # do not count rev default account itself
                account_ids_domain = [
                    ('account_id', '!=', comp_id.revaluation_default_account.id),
                ]
            else:
                account_ids_domain = []
            if account_liquidity_ids:
                op = 'in' if revaluation_method == 'liquidity_year' else 'not in'
                account_ids_domain += [
                    ('account_id', op, account_liquidity_ids),
                ]
        else:
            period_obj = self.pool.get('account.period')
            period_br = period_obj.browse(cr, uid, [period_id],
                context=context)[0]
            if period_br.number == 1:
                # UFTP-385/US-957
                # Jan month revaluation and a previous FY
                # (potentially yearly revaluated)
                # Since US-957 we tolerate any manual rev journal entries
                # (potentially reval entries of the yearly reval autos entries)
                # => we do not allow any rev entries of an already done jan
                # reval
                fy_ids = self.pool.get('account.fiscalyear').search(cr, uid, [
                        ('date_start', '<', period_br.fiscalyear_id.date_start),
                    ], limit=1, order='date_start', context=context)
                if fy_ids:  # a previous FY
                    account_model = 'account.move.line'
                    domain.append(('name', 'like',
                        "Revaluation - %s" % (period_br.name, )))

        if account_ids_domain:
            domain += account_ids_domain
        reval_move_count = self.pool.get(account_model).search(cr, uid, domain,
            count=True, context=context)
        return True if reval_move_count and reval_move_count > 0 else False

    def default_get(self, cr, uid, fields, context=None):
        """'default_get' method overridden."""
        res = super(WizardCurrencyrevaluation, self).default_get(
            cr, uid, fields, context=context)

        user_obj = self.pool.get('res.users')
        period_obj = self.pool.get('account.period')
        journal_obj = self.pool.get('account.journal')
        # Fiscalyear
        cp = user_obj.browse(cr, uid, uid, context=context).company_id
        current_date = datetime.date.today().strftime('%Y-%m-%d')
        fiscalyear_obj = self.pool.get('account.fiscalyear')
        fiscalyear_ids = fiscalyear_obj.search(
            cr, uid,
            [('date_start', '<', current_date),
             ('date_stop', '>', current_date),
             ('company_id', '=', cp.id)],
            limit=1,
            context=context)
        res['fiscalyear_id'] = fiscalyear_ids and fiscalyear_ids[0] or False

        # Period
        period_date = datetime.date.today()
        # NOTE: the method 'get_period_from_date()' supplied by the
        #       'account_tools' module is used here
        period_ids = period_obj.get_period_from_date(
            cr, uid, period_date.strftime('%Y-%m-%d'))
        res['period_id'] = period_ids and period_ids[0] or False
        res['result_period_id'] = res['period_id']

        # Journal
        # UFTP-44: journal of instance and of type 'revaluation'
        if cp:
            domain = [
                ('instance_id', '=', cp.instance_id.id),
                ('type', '=', 'revaluation'),
            ]
            journal_ids = journal_obj.search(cr, uid, domain, context=context)
        else:
            journal_ids = False
        if not journal_ids:
            raise osv.except_osv(
                _(u"Error"),
                _(u"No revaluation journal found!"))
        res['journal_id'] = journal_ids and journal_ids[0] or False
        # Book revaluation account check
        revaluation_account = cp.revaluation_default_account
        if not revaluation_account:
            raise osv.except_osv(_('Settings Error!'), _('Revaluation account is not set in company settings'))
        if not self.pool.get('res.company').check_revaluation_default_account_has_sup_destination(cr, uid, cp, context=context):
            raise osv.except_osv(_('Settings Error!'),_('The default revaluation account must have a default destination SUP'))
        # Entry period
        # Posting date
        res['posting_date'] = False
        if res['period_id']:
            period = period_obj.browse(
                cr, uid, res['period_id'], context=context)
            res['posting_date'] = period.date_stop
        return res


    def on_change_revaluation_method(
            self, cr, uid, ids, method, fiscalyear_id, period_id):
        """'on_change' method for the 'revaluation_method', 'fiscalyear_id' and
        'period_id' fields.
        """
        if not method or not fiscalyear_id or not period_id:
            return {}
        value = {}
        warning = {}
        fiscalyear_obj = self.pool.get('account.fiscalyear')
        period_obj = self.pool.get('account.period')
        move_obj = self.pool.get('account.move')
        fiscalyear = fiscalyear_obj.browse(cr, uid, fiscalyear_id)

        # Set values according to the user input
        value['result_period_id'] = period_id

        period = period_obj.browse(cr, uid, period_id, context=None)
        value['posting_date'] = period.date_stop
        value['period_id'] = period_id
        if method != 'liquidity_month':
            value['posting_date'] = fiscalyear.date_stop
            check_period13_res = self._check_period_opened(cr, uid,
                fiscalyear.id, 13)  # UFTP-385 period 13 for year end
            if check_period13_res[1]:
                value['result_period_id'] = check_period13_res[1]
            else:
                value['result_period_id'] = False
            if not check_period13_res[0] and check_period13_res[2]:
                warning = {
                    'title': _('Warning!'),
                    'message': check_period13_res[2]
                }
        res = {'value': value, 'warning': warning}
        return res

    def on_change_fiscalyear_id(self, cr, uid, ids, method, fiscalyear_id):
        """'on_change' method for the 'fiscalyear_id' field."""

        if not method or not fiscalyear_id:
            return {}
        value = {}
        warning = {}
        fiscalyear_obj = self.pool.get('account.fiscalyear')
        period_obj = self.pool.get('account.period')
        fiscalyear = fiscalyear_obj.browse(cr, uid, fiscalyear_id)
        if method in ['liquidity_month']:
            if fiscalyear_id:
                # If the current fiscal year is the actual one, we get the
                # previous month as the right period (except for january)
                if fiscalyear_id == self._get_default_fiscalyear_id(cr, uid):
                    period_date = datetime.date.today()
                    if period_date.month > 1:
                        period_date = period_date - relativedelta(months=1)
                # If the selected fiscal year is not the actual one, we get its
                # start period
                else:
                    period_date = datetime.datetime.strptime(
                        fiscalyear.date_start, '%Y-%m-%d')
                # NOTE: the method 'get_period_from_date()' supplied by the
                #       'account_tools' module is used here
                period_ids = period_obj.get_period_from_date(
                    cr, uid, period_date.strftime('%Y-%m-%d'))
                period_id = period_ids and period_ids[0] or False
                value['period_id'] = period_id
                value['result_period_id'] = period_id
                period = period_obj.browse(cr, uid, period_id)
                value['posting_date'] = period.date_stop
        elif method in ('other_bs', 'liquidity_year'):
            value['posting_date'] = fiscalyear.date_stop
            period_ids = period_obj.search(
                cr, uid,
                [('state', '!=', 'created'),
                 ('fiscalyear_id', '=', fiscalyear.id),
                 ('number', '=', 13)])
            if period_ids:
                value['result_period_id'] = period_ids[0]
        res = {'value': value, 'warning': warning}
        return res

    def on_change_result_period_id(self, cr, uid, ids, result_period_id, context=None):
        """'on_change' method for the 'result_period_id' field."""
        if context is None:
            context = {}
        value = {}
        warning = {}
        if result_period_id:
            period_obj = self.pool.get('account.period')
            period = period_obj.browse(cr, uid, result_period_id, context=context)
            value['posting_date'] = period.date_stop
            value['result_period_id'] = result_period_id
        return {'value': value, 'warning': warning}

    def _compute_unrealized_currency_gl(self, cr, uid,
                                        currency_id,
                                        balances,
                                        revaluation_date,
                                        context=None):
        """
        Update data dict with the unrealized currency gain and loss
        plus add 'currency_rate' which is the value used for rate in
        computation

        @param int currency_id: currency to revaluate
        @param dict balances: contains foreign balance and balance

        @return: updated data for foreign balance plus rate value used
        """
        context = context or {}

        currency_obj = self.pool.get('res.currency')

        # Compute unrealized gain loss
        ctx_rate = context.copy()
        ctx_rate['date'] = revaluation_date
        user_obj = self.pool.get('res.users')
        cp_currency_id = user_obj.browse(cr, uid, uid, context=context).company_id.currency_id.id

        currency = currency_obj.browse(cr, uid, currency_id, context=ctx_rate)

        foreign_balance = adjusted_balance = balances.get('foreign_balance', 0.0)
        balance = balances.get('balance', 0.0)
        unrealized_gain_loss =  0.0
        if foreign_balance:
            ctx_rate['revaluation'] = True
            adjusted_balance = currency_obj.compute(
                cr, uid, currency_id, cp_currency_id, foreign_balance,
                context=ctx_rate)
            # Substract reval lines from amount
            unrealized_gain_loss =  adjusted_balance - balance
        else:
            if balance:
                if currency_id != cp_currency_id:
                    unrealized_gain_loss =  0.0 - balance
                else:
                    unrealized_gain_loss = 0.0
            else:
                unrealized_gain_loss =  0.0
        return {'unrealized_gain_loss': unrealized_gain_loss,
                'currency_rate': currency.rate,
                'revaluated_balance': adjusted_balance}

    def _format_label(self, cr, uid, text, account_id, currency_id,
                      rate, context=None):
        """
        Return a text with replaced keywords by values

        @param str text: label template, can use
            %(account)s, %(currency)s, %(rate)s
        @param int account_id: id of the account to display in label
        @param int currency_id: id of the currency to display
        @param float rate: rate to display
        """
        account_obj = self.pool.get('account.account')
        currency_obj = self.pool.get('res.currency')
        account = account_obj.browse(cr, uid,
                                     account_id,
                                    context=context)
        currency = currency_obj.browse(cr, uid, currency_id, context=context)
        data = {'account': account.code or False,
                'currency': currency.name or False,
                'rate': rate or False}
        return text % data

    def _write_adjust_balance(self, cr, uid, account_id, currency_id,
                              partner_id, amount, label, rate, form, sums,
                              context=None):
        """
        Generate entries to adjust balance in the revaluation accounts

        @param account_id: ID of account to be reevaluated
        @param amount: Amount to be written to adjust the balance
        @param label: Label to be written on each entry
        @param form: Wizard browse record containing data

        @return: ids of created move_lines
        """
        if context is None:
            context = {}

        def create_move():
            account = self.pool.get('account.account').browse(
                cr, uid, account_id, context=context)
            currency = self.pool.get('res.currency').browse(
                cr, uid, currency_id, context=context)

            base_move = {'name': label,
                         'ref': "%s-%s-%s" % (currency.name, account.code, rate),
                         'journal_id': form.journal_id.id,
                         'period_id': form.period_id.id,
                         'document_date': form.posting_date,
                         'date': form.posting_date}
            return move_obj.create(cr, uid, base_move, context=context)

        def create_move_line(move_id, line_data, sums):
            line_name = "Revaluation - %s" % form.fiscalyear_id.name
            if form.revaluation_method == 'liquidity_month':
                line_name = "Revaluation - %s" % form.period_id.name
            base_line = {'name': line_name,
                         'currency_id': currency_id,
                         'amount_currency': 0.0,
                         'document_date': form.posting_date,
                         'date': form.posting_date,
                         'is_revaluated_ok': True,
                         }
            base_line.update(line_data)
            base_line['gl_foreign_balance'] = sums.get('foreign_balance', 0.0)
            base_line['gl_balance'] = sums.get('balance', 0.0)
            base_line['gl_revaluated_balance'] = sums.get('revaluated_balance', 0.0)
            base_line['gl_currency_rate'] = sums.get('currency_rate', 0.0)
            return move_line_obj.create(cr, uid, base_line, context=context)

        account_obj = self.pool.get('account.account')
        move_obj = self.pool.get('account.move')
        move_line_obj = self.pool.get('account.move.line')
        distrib_obj = self.pool.get('analytic.distribution')
        cc_distrib_obj = self.pool.get('cost.center.distribution.line')
        fp_distrib_obj = self.pool.get('funding.pool.distribution.line')
        account_ana_obj = self.pool.get('account.analytic.account')
        model_data_obj = self.pool.get('ir.model.data')

        # revaluation_account
        user = self.pool.get('res.users').browse(cr, uid, [uid], context=context)
        if user and user[0] and user[0].company_id:
            revaluation_account = user[0].company_id.revaluation_default_account
            revaluation_account_id = revaluation_account.id
        else:
            raise osv.except_osv(_('Settings Error!'), _('Revaluation account is not set in company settings'))

        # Prepare the analytic distribution for the account revaluation entry
        # if the account has a 'expense' or 'income' type
        distribution_id = False
        if revaluation_account.user_type.code in ['expense', 'income']:
            destination_id = model_data_obj.get_object_reference(
                cr, uid, 'analytic_distribution', 'analytic_account_destination_support')[1]

            # UFTP-189: Show warning message when the fx gain/loss is missing to select (before it was fix for me)
            cc_list = account_ana_obj.search(cr, uid, [('for_fx_gain_loss', '=', True)], context=context)
            if len(cc_list) == 0:
                raise osv.except_osv(_('Warning'), _('Please activate an analytic account with "For FX gain/loss" to allow revaluation!'))
            cost_center_id = cc_list[0]
            funding_pool_id = model_data_obj.get_object_reference(cr, uid, 'analytic_distribution', 'analytic_account_msf_private_funds')[1]
            distribution_id = distrib_obj.create(cr, uid, {}, context=context)
            cc_distrib_obj.create(
                cr, uid,
                {'distribution_id': distribution_id,
                 'analytic_id': cost_center_id,
                 'destination_id': destination_id,
                 'currency_id': currency_id,
                 'percentage': 100.0,
                 'source_date': form.posting_date,
                },
                context=context)
            fp_distrib_obj.create(
                cr, uid,
                {'distribution_id': distribution_id,
                 'analytic_id': funding_pool_id,
                 'destination_id': destination_id,
                 'cost_center_id': cost_center_id,
                 'currency_id': currency_id,
                 'percentage': 100.0,
                 'source_date': form.posting_date,
                },
                context=context)

        move_id = False
        created_ids = []
        # over revaluation
        if amount >= 0.02:
            if revaluation_account_id:
                move_id = create_move()
                # Create a move line to Debit account to be revaluated
                line_data = {
                    'debit': amount,
                    'debit_currency': False,
                    'move_id': move_id,
                    'account_id': account_id,
                }
                created_ids.append(create_move_line(move_id, line_data, sums))
                # Create a move line to Credit revaluation account
                line_data = {
                    'credit': amount,
                    'credit_currency': False,
                    'move_id': move_id,
                    'account_id': revaluation_account_id,
                    'analytic_distribution_id': distribution_id,
                }
                created_ids.append(create_move_line(move_id, line_data, sums))
        # under revaluation
        elif amount <= -0.02:
            amount = -amount
            if revaluation_account_id:
                move_id = create_move()

                # Create a move line to Debit revaluation loss account
                line_data = {
                    'debit': amount,
                    'move_id': move_id,
                    'account_id': revaluation_account_id,
                    'analytic_distribution_id': distribution_id,
                }

                created_ids.append(create_move_line(move_id, line_data, sums))
                # Create a move line to Credit account to be revaluated
                line_data = {
                    'credit': amount,
                    'move_id': move_id,
                    'account_id': account_id,
                }
                created_ids.append(create_move_line(move_id, line_data, sums))
        # Hard post the move
        if move_id:
            move_obj.post(cr, uid, [move_id], context=context)
        return move_id, created_ids

    def revaluate_currency(self, cr, uid, ids, context=None):
        """
        Compute unrealized currency gain and loss and add entries to
        adjust balances

        @return: dict to open an Entries view filtered on generated move lines
        """
        if context is None:
            context = {}
        user_obj = self.pool.get('res.users')
        period_obj = self.pool.get('account.period')
        account_obj = self.pool.get('account.account')
        currency_obj = self.pool.get('res.currency')
        seq_obj = self.pool.get('ir.sequence')

        company = user_obj.browse(cr, uid, uid).company_id

        created_ids = []

        if isinstance(ids, (int, long)):
            ids = [ids]
        form = self.browse(cr, uid, ids[0], context=context)

        period_13_id = False
        if form.revaluation_method in ('liquidity_year', 'other_bs'):
            # check if period 13 is valid for end year reval
            # (must exist and must be opened)
            check_period13_res = self._check_period_opened(cr, uid,
                form.fiscalyear_id.id, 13)
            if not check_period13_res[0] and check_period13_res[2]:
                raise osv.except_osv(_('Warning!'), check_period13_res[2])
            period_13_id = check_period13_res[1]

            # period 13 is opened but check if N+1 FY 1st period is opened
            # as it is used for reversal lines
            next_fy_ok = False
            next_fiscalyear_id = self._get_next_fiscalyear_id(
                cr, uid, form.fiscalyear_id.id, context=context)
            if next_fiscalyear_id:
                reversal_period_id = self._get_first_fiscalyear_period_id(
                    cr, uid, next_fiscalyear_id, context=context)
                if reversal_period_id:
                    next_fy_state = period_obj.read(cr, uid,
                        [reversal_period_id], ['state'],
                        context=context)[0]['state']
                    if next_fy_state == 'draft':  # open
                        next_fy_ok = True
            if not next_fy_ok:
                msg = "For year revaluation, start period of next FY must be" \
                    " opened to store revaluation reversal entries"
                raise osv.except_osv(_('Warning!'), msg)

        # Set the currency table in the context for later computations
        if form.revaluation_method in ['liquidity_year', 'other_bs']:
            context['currency_table_id'] = form.currency_table_id.id

        # Get all currency names to map them with main currencies later
        currency_codes_from_table = {}
        if form.revaluation_method in ['liquidity_year', 'other_bs']:
            for currency in form.currency_table_id.currency_ids:
                currency_codes_from_table[currency.name] = currency.id

        # Get posting date (as the field is readonly, its value is not sent
        # to the server by the web client
        # and get revaluation date
        if period_13_id:
            # period_13_id set: end of year revaluation
            form.period_id.id = period_13_id
            form.posting_date = form.fiscalyear_id.date_stop
            revaluation_date = form.fiscalyear_id.date_stop  # compute reval for FY
        else:
            form.posting_date = form.period_id.date_stop
            revaluation_date = form.period_id.date_stop

        # Search for accounts Balance Sheet or Liquidity to be eevaluated
        """Determine accounts to be used in the revaluation based on the "included in reval" checkbox.
        Liquidity revaluation will only concern accounts that have this checkbox set to True and the internal type Liquidity"
        B/S revaluation will only concern accounts that have this checkbox set to True and the internal type is not Liquidity"""
        account_ids = []
        if form.revaluation_method in ['liquidity_month', 'liquidity_year']:
            account_ids_domain = [
                ('currency_revaluation', '=', True),
                ('type', '=', 'liquidity'),
            ]
        elif form.revaluation_method == 'other_bs':
            account_ids_domain = [
                ('currency_revaluation', '=', True),
                ('type', '!=', 'liquidity'),
            ]
        account_ids = account_obj.search(cr, uid, account_ids_domain, context=context)
        if not account_ids:
            raise osv.except_osv(
                _('Settings Error!'),
                _("No account to be revaluated found. "
                  "Please check 'Included in revaluation' "
                  "for at least one account in account form."))

        special_period_ids = [ p.id for p in form.fiscalyear_id.period_ids \
            if p.special == True and p.number != 0 ]
        if not special_period_ids:
            raise osv.except_osv(_('Error!'),
                                 _('No special period found for the fiscalyear %s') %
                                   form.fiscalyear_id.code)

        period_ids = []
        if form.revaluation_method == 'liquidity_month':
            if form.period_id.number > 12:
                raise osv.except_osv(
                    _('Error!'),
                    _("You can not perform a monthly revaluation on '%s'") % (
                    form.period_id.name, )
                )
            period_ids = [form.period_id.id]
        else:
            # NOTE: US-1251 exclude IB entries period 0 for monthly and yearly
            period_ids = []
            for period in form.fiscalyear_id.period_ids:
                if 0 < period.number < 13:
                    period_ids.append(period.id)
        if not period_ids:
            raise osv.except_osv(
                _('Error!'),
                _('No period found for the fiscalyear %s') % (
                    form.fiscalyear_id.code))
        # Check periods state
        periods_not_field_closed = []
        for period in period_obj.browse(cr, uid, period_ids, context=context):
            if period.number != 0 and period.state in ['created', 'draft']:
                periods_not_field_closed.append(period.name)

        # check if revaluation has already been run for this period
        # UFTP-385 not checked for year end as is it over months revaluation
        # in this case to check revaluation year already done we check only
        # period 13
        if form.revaluation_method == 'liquidity_month':
            revalcheck_period_ids = period_ids
        else:
            revalcheck_period_ids = [period_13_id]
        for period_id in revalcheck_period_ids:
            if self._is_revaluated(cr, uid, period_id, form.revaluation_method,
                context=None):
                if form.revaluation_method == 'liquidity_month':
                    period_name = period_obj.browse(cr, uid, period_id,
                        context=context).name
                    msg = _(u"%s has already been revaluated") % (period_name, )
                else:
                    msg = _(u"End year revaluation already performed")
                raise osv.except_osv(_(u"Error"), msg)

        # Get balance sums
        account_sums = account_obj.compute_revaluations(
            cr, uid, account_ids, period_ids, form.fiscalyear_id.id,
            revaluation_date, form.revaluation_method, context=context)
        for account_id, account_tree in account_sums.iteritems():
            for currency_id, sums in account_tree.iteritems():
                new_currency_id = currency_id
                # If the method is 'other_bs' or 'liquidity_year', check if the
                # account move currency is declared in the currency table and
                # get it there
                if form.revaluation_method in ['liquidity_year', 'other_bs']:
                    currency = currency_obj.browse(cr, uid, currency_id, context=context)
                    if currency.id != company.currency_id.id and currency.name not in currency_codes_from_table:
                        raise osv.except_osv(
                            _("Error"),
                            _("The currency %s is not declared in the currency table.") % currency.name)
                    new_currency_id = currency_codes_from_table[currency.name]
                if not sums['balance']:
                    continue
                # Update sums with compute amount currency balance
                diff_balances = self._compute_unrealized_currency_gl(
                    cr, uid, new_currency_id, sums, revaluation_date,
                    context=context)
                account_sums[account_id][currency_id].update(diff_balances)
        # Create entries only after all computation have been done
        for account_id, account_tree in account_sums.iteritems():
            for currency_id, sums in account_tree.iteritems():
                new_currency_id = currency_id
                # If the method is 'other_bs' or 'liquidity_year', get the
                # account move currency in the currency table
                if form.revaluation_method in ['liquidity_year', 'other_bs']:
                    currency = currency_obj.browse(cr, uid, currency_id, context=context)
                    new_currency_id = currency_codes_from_table[currency.name]
                adj_balance = sums.get('unrealized_gain_loss', 0.0)
                if not adj_balance:
                    continue

                rate = sums.get('currency_rate', 0.0)
                label = '/'

                # Write an entry to adjust balance
                move_id, new_ids = self._write_adjust_balance(
                    cr, uid,
                    account_id, currency_id, False, adj_balance,
                    label, rate, form, sums, context=context)
                if move_id:
                    created_ids.extend(new_ids)
                    # Create a second journal entry that will offset the first one
                    # if the revaluation method is 'Other B/S'
                    if form.revaluation_method in ['liquidity_year', 'other_bs']:
                        move_id, rev_line_ids = self._reverse_other_bs_move_lines(
                            cr, uid, form, move_id, new_ids, context=context)
                        created_ids.extend(rev_line_ids)

        if created_ids:
            # Set all booking amount to 0 for revaluation lines
            cr.execute('UPDATE account_move_line '
                       'SET debit_currency = 0, credit_currency = 0, amount_currency = 0'
                       'WHERE id IN %s', (tuple(created_ids),))
            # Return the view
            return {'domain': "[('id','in', %s)]" % (created_ids,),
                    'name': _("Created revaluation lines"),
                    'view_type': 'form',
                    'view_mode': 'tree,form',
                    'auto_search': True,
                    'res_model': 'account.move.line',
                    'view_id': False,
                    'search_view_id': False,
                    'type': 'ir.actions.act_window'}
        else:
            raise osv.except_osv(_("Warning"),
                                 _("No revaluation accounting entry have been posted."))

    def _get_next_fiscalyear_id(self, cr, uid, fiscalyear_id, context=None):
        """Return the next fiscal year ID."""
        if context is None:
            context = {}
        fiscalyear_obj = self.pool.get('account.fiscalyear')
        fiscalyear = fiscalyear_obj.browse(
            cr, uid, fiscalyear_id, context=context)
        date_stop = datetime.datetime.strptime(
            fiscalyear.date_stop, '%Y-%m-%d')
        next_year_start = date_stop + relativedelta(years=1)
        next_fiscalyear_ids = fiscalyear_obj.search(
            cr, uid,
            [('state', '=', 'draft'),
             ('date_start', '<=', next_year_start.strftime('%Y-%m-%d')),
             ('date_stop', '>=', next_year_start.strftime('%Y-%m-%d'))],
            context=context)
        if not next_fiscalyear_ids:
            raise osv.except_osv(
                _("Error"),
                _("The next fiscal year does not exist."))
        return next_fiscalyear_ids[0]

    def _get_first_fiscalyear_period_id(self, cr, uid, fiscalyear_id,
            context=None):
        """Return the first period ID of a fiscal year."""
        if context is None:
            context = {}
        fiscalyear_obj = self.pool.get('account.fiscalyear')
        period_obj = self.pool.get('account.period')
        period_ids = period_obj.search(
            cr, uid,
            [('fiscalyear_id', '=', fiscalyear_id), ('number', '=', 1)],
            context=context)
        if not period_ids:
            fiscalyear = fiscalyear_obj.browse(
                cr, uid, fiscalyear_id, context=context)
            raise osv.except_osv(
                _("Error"),
                _("No first period found in the fiscal year %s.") % (
                    fiscalyear.name))
        return period_ids[0]

    def _reverse_other_bs_move_lines(
            self, cr, uid, form, move_id, line_ids, context=None):
        """Reverse 'Other B/S' revaluation entries."""
        if context is None:
            context = {}
        move_obj = self.pool.get('account.move')
        line_obj = self.pool.get('account.move.line')
        aal_obj = self.pool.get('account.analytic.line')
        period_obj = self.pool.get('account.period')
        # Get reserved move
        rev_move = move_obj.browse(cr, uid, move_id, context=context)
        # Compute the posting date:
        # Get the start date of the first period of the next fiscal year
        fiscalyear_id = self._get_next_fiscalyear_id(
            cr, uid, form.fiscalyear_id.id, context=context)
        period_id = self._get_first_fiscalyear_period_id(
            cr, uid, fiscalyear_id, context=context)
        period = period_obj.browse(cr, uid, period_id, context=context)
        posting_date = period.date_start
        # Create a new move
        move_vals = {
            'journal_id': form.journal_id.id,
            'period_id': period_id,
            'date': posting_date,
            'ref': rev_move.ref,
        }
        move_id = move_obj.create(cr, uid, move_vals, context=context)
        # Reverse lines + associate them to the newly created move
        rev_line_ids = []
        lines_to_reconcile = []
        for line in line_obj.browse(cr, uid, line_ids, context=context):
            # Prepare default value for new line
            vals = {
                'move_id': move_id,
                'date': posting_date,
                'document_date': posting_date,
                'journal_id': form.journal_id.id,
                'period_id': period_id,
            }
            # Copy the line
            rev_line_id = line_obj.copy(cr, uid, line.id, vals, context=context)
            # Do the reverse
            amt = -1 * line.amount_currency
            vals.update({
                'debit': line.credit,
                'credit': line.debit,
                'amount_currency': amt,
                'journal_id': form.journal_id.id,
                'name': line_obj.join_without_redundancy(line.name, 'REV'),
                'reversal_line_id': line.id,
                'account_id': line.account_id.id,
                'source_date': line.date,
                'reversal': True,
                'reference': line.move_id and line.move_id.name or '',
                'ref': line.move_id and line.move_id.name or '',
            })
            line_obj.write(cr, uid, [rev_line_id], vals, context=context)
            # Keep lines to reconcile
            if line.account_id.reconcile:
                lines_to_reconcile.append((line.id, rev_line_id))
            # Search analytic lines from first move line
            aal_ids = aal_obj.search(cr, uid, [('move_id', '=', line.id)])
            aal_obj.write(cr, uid, aal_ids, {'is_reallocated': True})
            # Search analytic lines from reversed line and flag them as "is_reversal"
            new_aal_ids = aal_obj.search(cr, uid, [('move_id', '=', rev_line_id)])
            aal_obj.write(cr, uid, new_aal_ids, {'is_reversal': True,})
            rev_line_ids.append(rev_line_id)
        # Hard post the move
        move_obj.post(cr, uid, [move_id], context=context)
        # Reconcile lines
        for line_id, rev_line_id in lines_to_reconcile:
            line_obj.reconcile_partial(
                cr, uid, [line_id, rev_line_id], context=context)
        return move_id, rev_line_ids


    def _check_period_opened(self, cr, uid, fiscalyear_id, period_number,
        context=None):
        """
        check if given period from number is opened
        period_id is passed in result for info if not opened
        :param fiscalyear_id: fiscalyear_id id
        :param period_number: period number
        :type period_number: int
        :return: (ok, period_id, msg)
        :rtype: tuple(boolean, int/False, str/False)
        """
        res = (False, False, False)
        period_obj = self.pool.get('account.period')
        domain = [
            ('state', '=', 'draft'),  # draft <=> open in openerp period
            ('fiscalyear_id', '=', fiscalyear_id),
            ('number', '=', period_number),
        ]

        # search for opened period
        period_ids = period_obj.search(cr, uid, domain, context=context)
        if period_ids:
            # period 13 opened found
            res = (True, period_ids[0], False)
        else:
            # not found, check if exist with any state to get its id
            domain = [
                ('fiscalyear_id', '=', fiscalyear_id),
                ('number', '=', period_number),
            ]
            period_ids = period_obj.search(cr, uid, domain, context=context)
            if not period_ids:
                res = (False, False, _('Period 13 is not found'))
            else:
                res = (False, period_ids[0], _('Period 13 is not opened'))
        return res

WizardCurrencyrevaluation()

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
