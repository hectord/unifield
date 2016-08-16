#!/usr/bin/env python
#-*- encoding:utf-8 -*-
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

{
    "name" : "Registers",
    "version" : "1.0",
    "description" : """
        This module aims to add some registers into accounting menu and change the method to do accounting by using
        all registers.
    """,
    "author" : "TeMPO Consulting, MSF",
    'website': 'http://tempo-consulting.fr',
    "category" : "Tools",
    # WARNING : account_analytic_plans has been added in order to cut modification done in account_analytic_plans by fields_view_get on account_move_line
    "depends" : [
        "base",
        "msf_audittrail",
        "account",
        "hr",
        "account_payment",
        "account_accountant",
        "analytic_distribution",
        "purchase_override",
        # As finance contains account_override and account_override has included account_activable, no need for account_override and account_activable
        "finance",
        "msf_homere_interface",
    ],
    "init_xml" : [],
    "update_xml" : [
        'security/ir.model.access.csv',
        'wizard/import_invoice_on_registers_view.xml',
        'wizard/import_cheque_on_bank_registers_view.xml',
        'account_view.xml',
        'account_bank_statement_workflow.xml',
        'wizard/wizard_closing_cashbox.xml',
        'wizard/wizard_cashbox_write_off.xml',
        'wizard/wizard_register_reopen.xml',
        'wizard/wizard_temp_posting.xml',
        'wizard/wizard_hard_posting.xml',
        'wizard/wizard_liquidity_position.xml',
        'account_cash_statement_sequence.xml',
        'wizard/wizard_cash_return.xml',
        'account_invoice_view.xml',
        'wizard/register_creation.xml',
        'wizard/wizard_confirm_bank.xml',
        'wizard/invoice_date.xml',
        'wizard/down_payment.xml',
        'purchase_view.xml',
        'wizard/transfer_with_change.xml',
        'register_accounting_report.xml',
        'account_wizard.xml',
        'wizard/wizard_register_import.xml',
        'wizard/account_direct_invoice_wizard_view.xml',
    ],
    "demo_xml" : [],
    "test": [
        'test/00_register_accounting_data.yml',
        'test/10_account_cash_statement.yml',
        'test/13_account_bank_statement.yml',
        'test/16_account_cheque_register.yml',
        'test/20_cash_and_bank_transfers.yml',
        'test/25_operational_advance_management.yml',
        'test/30_cashbox_balance.yml',
        'test/35_direct_expense.yml',
        'test/40_direct_invoice.yml',
        'test/50_import_cheque_from_bank.yml',
        'test/60_wizard_register_creation.yml',
        'test/70_bug_closing_balance_on_cashbox.yml',
        'test/80_import_invoice.yml',
        'test/85_import_invoice_rate_before_import.yml',
        'test/90_down_payments.yml',
        'test/99_fully_report.yml',
    ],
    "installable": True,
    "active": False
}

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
