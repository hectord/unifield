# -*- coding: utf-8 -*-
##############################################################################
#
#    OpenERP, Open Source Management Solution
#    Copyright (C) 2011 MSF, TeMPO Consulting.
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

from report import report_sxw
from spreadsheet_xml.spreadsheet_xml_write import SpreadsheetReport
import pooler

class report_fully_report(report_sxw.rml_parse):
    def __init__(self, cr, uid, name, context=None):
        super(report_fully_report, self).__init__(cr, uid, name, context=context)
        self.localcontext.update({
            'getMoveLines': self.getMoveLines,
            'getAnalyticLines': self.getAnalyticLines,
            'getImportedMoveLines': self.getImportedMoveLines,
            'getRegRef': self.getRegRef,
            'getFreeRef': self.getFreeRef,
            'getDownPaymentReversals': self.getDownPaymentReversals,
        })

    def getRegRef(self, reg_line):
        invoice = False
        if reg_line.direct_invoice_move_id:
            return reg_line.direct_invoice_move_id.name
        if reg_line.imported_invoice_line_ids:
            num = []
            for inv in reg_line.imported_invoice_line_ids:
                num.append(inv.move_id.name)
            return " ".join(num)
        if reg_line.from_import_cheque_id and reg_line.from_import_cheque_id.move_id:
            return reg_line.from_import_cheque_id.move_id.name
        return reg_line.ref or ''

    def filter_regline(self, regline_br):
        """
        :param regline_br: browsed regline
        :return: True to show detail of the reg line False to not display
        """
        # US-69

        # exclude ALL detail of register line of account of given user_type
        # (redondencies of invoice detail)
        # http://jira.unifield.org/browse/US-69?focusedCommentId=38845&page=com.atlassian.jira.plugin.system.issuetabpanels:comment-tabpanel#comment-38845
        excluded_acc_type_codes = [
            'tax',
            'cash',
            'receivables',
        ]
        if regline_br and regline_br.account_id and \
            regline_br.account_id.user_type:
                if regline_br.account_id.user_type.code and \
                    regline_br.account_id.user_type.code in \
                    excluded_acc_type_codes:
                    return False
        return True

    def get_move_lines(self, move_ids):
        # We need move lines linked to the given move ID. Except the invoice counterpart.
        #+ Lines that have is_counterpart to True is the invoice counterpart. We do not need it.
        res = []
        if  not move_ids:
            return res

        aml_obj = pooler.get_pool(self.cr.dbname).get('account.move.line')
        domain = [
            ('move_id', 'in', move_ids),
            ('is_counterpart', '=', False)
        ]
        aml_ids = aml_obj.search(self.cr, self.uid, domain)
        if aml_ids:
            res = aml_obj.browse(self.cr, self.uid, aml_ids)
        # US_297: Sort by invoice.number instead line_number
        return sorted(res, key=lambda x: (x.invoice.number, x.line_number))

    def getMoveLines(self, move_brs, regline_br):
        """
        Fetch all lines except the partner counterpart one
        :param move_brs: browsed moves (JIs)
        :type move_brs: list
        :param regline_br: browsed regline
        """
        if not move_brs:
            return []
        if not self.filter_regline(regline_br):
            return []  # not any detail for this reg line
        return self.get_move_lines([m.id for m in move_brs])

    def getImportedMoveLines(self, ml_brs, regline_br):
        """
        Fetch all lines except the partner counterpart one
        :param ml_brs: list of browsed move lines
        :type ml_brs: list
        :param regline_br: browsed regline
        """
        if not self.filter_regline(regline_br):
            return []  # not any detail for this reg line
        if not ml_brs:
            return []

        # exclude detail for Balance/Sheet entries (whatever the Account type) booked in a HR journal are imported in a register
        # http://jira.unifield.org/browse/US-69?focusedCommentId=38845&page=com.atlassian.jira.plugin.system.issuetabpanels:comment-tabpanel#comment-38845
        move_ids = [
            ml.move_id.id for ml in ml_brs if not ( \
                ml.journal_id and ml.journal_id.type == 'hr' and \
                ml.account_id and ml.account_id.user_type and \
                ml.account_id.user_type.report_type in ('asset', 'liability', ))
        ]
        return self.get_move_lines(move_ids)

    def getAnalyticLines(self, analytic_ids):
        """
        Get anlytic lines history from given analytic lines
        """
        res = []
        if not analytic_ids:
            return res
        if isinstance(analytic_ids, (int, long)):
            analytic_ids = [analytic_ids]
        al_obj = pooler.get_pool(self.cr.dbname).get('account.analytic.line')
        al_ids = al_obj.get_corrections_history(self.cr, self.uid, analytic_ids)
        if al_ids:
            res = al_obj.browse(self.cr, self.uid, al_ids)
        return res

    def getFreeRef(self, acc_move_line):
        '''
        Return the "manual" invoice reference associated with the account move line if it exists
        (field Reference in DI and Free Reference in SI)
        Note: for Supplier Refund and SI with Source Doc that are synched from Project to Coordo,
        the free ref will appear in Project only (US-970)
        '''
        db = pooler.get_pool(self.cr.dbname)
        acc_inv = db.get('account.invoice')
        free_ref = False
        if acc_move_line:
            acc_move = acc_move_line.move_id
            inv_id = acc_inv.search(self.cr, self.uid, [('move_id', '=', acc_move.id)])
            if inv_id:
                inv = acc_inv.browse(self.cr, self.uid, inv_id)
                free_ref = inv and inv[0].reference
            if not free_ref:
                # display the free ref if it is different from the "standard" ref
                if acc_move.name != acc_move.ref:
                    free_ref = acc_move.ref
        return free_ref or ''

    def getDownPaymentReversals(self, reg_line):
        '''
        If the register line corresponds to a down payment that has been totally or partially reversed,
        returns a list of the related account move line(s), else returns an empty list.
        '''
        dp_reversals = []
        db = pooler.get_pool(self.cr.dbname)
        acc_move_line_obj = db.get('account.move.line')
        second_acc_move_line_id = False
        if reg_line and reg_line.account_id.type_for_register == 'down_payment' and reg_line.first_move_line_id and reg_line.first_move_line_id.move_id:
            acc_move = reg_line.first_move_line_id.move_id
            acc_move_line_id = acc_move_line_obj.search(self.cr, self.uid, [('move_id', '=', acc_move.id), ('id', '!=', reg_line.first_move_line_id.id)])
            acc_move_line = acc_move_line_obj.browse(self.cr, self.uid, acc_move_line_id)
            # totally reconciled
            reconcile_id = acc_move_line[0] and acc_move_line[0].reconcile_id or False
            if reconcile_id:
                second_acc_move_line_id = acc_move_line_obj.search(self.cr, self.uid, [('reconcile_id', '=', reconcile_id.id), ('id', '!=', acc_move_line[0].id)])
            else:
            # partially reconciled
                reconcile_partial_id = acc_move_line[0] and acc_move_line[0].reconcile_partial_id or False
                if reconcile_partial_id:
                    second_acc_move_line_id = acc_move_line_obj.search(self.cr, self.uid, [('reconcile_partial_id', '=', reconcile_partial_id.id), ('id', '!=', acc_move_line[0].id)])
            if second_acc_move_line_id:
                dp_reversals = acc_move_line_obj.browse(self.cr, self.uid, second_acc_move_line_id)
        return dp_reversals

SpreadsheetReport('report.fully.report','account.bank.statement','addons/register_accounting/report/fully_report_xls.mako', parser=report_fully_report)
# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
