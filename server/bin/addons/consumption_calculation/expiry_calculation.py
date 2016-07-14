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

from osv import osv, fields
from tools.translate import _

from mx.DateTime import *
from datetime import date, timedelta, datetime

import time

class expiry_quantity_report(osv.osv_memory):
    _name = 'expiry.quantity.report'
    _description = 'Products Expired'

    def _get_date_to(self, cr, uid, ids, field_name, arg, context=None):
        '''
        Compute the end date for the calculation
        '''
        if context is None:
            context = {}

        res = {}

        for report in self.browse(cr, uid, ids, context=context):
            res[report.id] = (date.today() + timedelta(weeks=report.week_nb)).strftime('%Y-%m-%d')

        return res

    _columns = {
        'location_id': fields.many2one('stock.location', string='Location'),
        'input_output_ok': fields.boolean(string='Exclude Input and Output locations'),
        'week_nb': fields.integer(string='Period of calculation (Today till XX weeks)', required=True),
        'date_to': fields.function(_get_date_to, method=True, type='date', string='Limit date', readonly=True),
        'line_ids': fields.one2many('expiry.quantity.report.line', 'report_id', string='Products', readonly=True),
    }

    def print_report_wizard(self, cr, uid, ids, context=None):
        '''
        Print the report directly from the wizard: pdf
        '''
        self.process_lines(cr, uid, ids, context=context)
        return self.print_report(cr, uid, ids, context=context)

    def print_report_wizard_xls(self, cr, uid, ids, context=None):
        '''
        Print the report directly from the wizard: xls
        '''
        self.process_lines(cr, uid, ids, context=context)
        return self.print_report_xls(cr, uid, ids, context=context)

    def _print_report(self, cr, uid, ids, report_name, context=None):
        '''
        Print the report of expiry report
        '''
        datas = {'ids': ids}

        return {
            'type': 'ir.actions.report.xml',
            'report_name': report_name,
            'datas': datas,
            'nodestroy': True,
            'context': context,
        }

    def print_report(self, cr, uid, ids, context=None):
        '''
        Print the report of expiry report: pdf
        '''
        return self._print_report(cr, uid, ids, 'expiry.report', context=None)

    def print_report_xls(self, cr, uid, ids, context=None):
        '''
        Print the report of expiry report: xls
        '''
        return self._print_report(cr, uid, ids, 'expiry.report_xls', context=None)

    def process_lines(self, cr, uid, ids, context=None):
        '''
        Creates all lines of expired products
        '''
        if context is None:
            context = {}

        move_obj = self.pool.get('stock.move')
        lot_obj = self.pool.get('stock.production.lot')
        loc_obj = self.pool.get('stock.location')
        lots = {}
        loc_ids = []

        report = self.browse(cr, uid, ids[0], context=context)
        lot_ids = lot_obj.search(cr, uid, [('life_date', '<=', (date.today() + timedelta(weeks=report.week_nb)).strftime('%Y-%m-%d'))])
        domain = [('date', '<=', (date.today()  + timedelta(weeks=report.week_nb)).strftime('%Y-%m-%d')), ('state', '=', 'done'), ('prodlot_id', 'in', lot_ids)]
        domain_out = [('date', '<=', (date.today()  + timedelta(weeks=report.week_nb)).strftime('%Y-%m-%d')), ('state', '=', 'done'), ('prodlot_id', 'in', lot_ids)]

        not_loc_ids = []
        # Remove input and output location
        if report.input_output_ok:
            wh_ids = self.pool.get('stock.warehouse').search(cr, uid, [], context=context)
            for wh in self.pool.get('stock.warehouse').browse(cr, uid, wh_ids, context=context):
                not_loc_ids.extend(loc_obj.search(cr, uid, [('location_id', 'child_of', wh.lot_input_id.id)], context=context))
                not_loc_ids.extend(loc_obj.search(cr, uid, [('location_id', 'child_of', wh.lot_output_id.id)], context=context))

        if report.location_id:
            # Search all children locations of the report location
            loc_ids = loc_obj.search(cr, uid, [('location_id', 'child_of', report.location_id.id), ('quarantine_location', '=', False), ('usage', '=', 'internal'), ('id', 'not in', not_loc_ids)], context=context)
        else:
            # Search all locations according to parameters
            loc_ids = loc_obj.search(cr, uid, [('usage', '=', 'internal'), ('quarantine_location', '=', False), ('id', 'not in', not_loc_ids)], context=context)

        # Return the good view
        view_id = self.pool.get('ir.model.data').get_object_reference(cr, uid, 'consumption_calculation', 'expiry_quantity_report_processed_loc_view')[1]
        domain.append(('location_dest_id', 'in', loc_ids))
        domain_out.append(('location_id', 'in', loc_ids))

        move_ids = move_obj.search(cr, uid, domain, context=context)
        for move in move_obj.browse(cr, uid, move_ids, context=context):
            if move.prodlot_id:
                lot_id = move.prodlot_id.id
                # Add the lot in the list
                if lot_id not in lots:
                    lots[lot_id] = {}

                # Add the location in the lot list
                if move.location_dest_id.id not in lots[lot_id]:
                    lots[lot_id][move.location_dest_id.id] = 0.00

                lots[lot_id][move.location_dest_id.id] += move.product_qty


        move_out_ids = move_obj.search(cr, uid, domain_out, context=context)
        for move in move_obj.browse(cr, uid, move_out_ids, context=context):
            if move.prodlot_id and move.prodlot_id.id in lots and move.location_id.id in lots[move.prodlot_id.id]:
                lots[move.prodlot_id.id][move.location_id.id] -= move.product_qty

        for lot_location in lots:
            lot_brw = lot_obj.browse(cr, uid, lot_location, context=context)
            for location in lots[lot_location]:
                if lots[lot_location][location] > 0.00:
                    context.update({'location': location, 'compute_child': False})
                    real_qty = lot_obj.browse(cr, uid, lot_location, context=context).product_id.qty_available
                    self.pool.get('expiry.quantity.report.line').create(cr, uid, {'product_id': lot_brw.product_id.id,
                                                                                  'real_stock': real_qty,
                                                                                  'expired_qty': lots[lot_location][location],
                                                                                  'batch_number': lot_brw.name,
                                                                                  'expiry_date': lot_brw.life_date,
                                                                                  'location_id': location,
                                                                                  'report_id': ids[0],
                                                                                  }, context=context)

        return {'type': 'ir.actions.act_window',
                'res_model': 'expiry.quantity.report',
                'view_type': 'form',
                'view_mode': 'form',
                'nodestroy': True,
                'view_id': [view_id],
                'res_id': ids[0],
        }

expiry_quantity_report()


class expiry_quantity_report_line(osv.osv_memory):
    _name = 'expiry.quantity.report.line'
    _description = 'Products expired line'
    _order = 'expiry_date, location_id, product_id asc'

    _columns = {
        'report_id': fields.many2one('expiry.quantity.report', string='Report', required=True),
        'product_id': fields.many2one('product.product', string='Product', required=True),
        'product_code': fields.related('product_id', 'default_code', string='Ref.', type='char'),
        'product_name': fields.related('product_id', 'name', string='Name', type='char'),
        'uom_id': fields.related('product_id', 'uom_id', string='UoM', type='many2one', relation='product.uom'),
        'real_stock': fields.float(digits=(16, 2), string='Real stock'),
        'expired_qty': fields.float(digits=(16, 2), string='Batch exp.'),
        #'batch_number': fields.many2one('production.lot', string='Batch'),
        'batch_number': fields.char(size=64, string='Batch'),
        'expiry_date': fields.date(string='Exp. date'),
        'location_id': fields.many2one('stock.location', string='Loc.'),
    }

expiry_quantity_report_line()


LIKELY_EXPIRE_STATUS = [
    ('draft', 'Draft'),
    ('in_progress', 'In Progress'),
    ('ready', 'Ready')
]
CONSUMPTION_TYPE = [
    ('fmc', 'FMC -- Forecasted Monthly Consumption'),
    ('amc', 'AMC -- Average Monthly Consumption'),
    ('rac', 'RAC -- Real Average Consumption'),
]
class product_likely_expire_report(osv.osv):
    _name = 'product.likely.expire.report'
    _description = 'Products list likely to expire'
    _rec_name = 'location_id'
    _order = 'requestor_date desc, id'

    def _get_status(self, cr, uid, ids, field_name, args, context=None):
        '''
        Return the same status as status
        '''
        res = {}
        for r in self.read(cr, uid, ids, ['status'], context=context):
            res[r['id']] = r['status']
        return res

    _columns = {
        'location_id': fields.many2one('stock.location', string='Location'),
        'msf_instance': fields.char(size=64, string='Location', readonly=True),
        'input_output_ok': fields.boolean(string='Exclude Input and Output locations'),
        'date_from': fields.date(string='From', required=True, readonly=True),
        'date_to': fields.date(string='To', required=True),
        'consumption_type': fields.selection(CONSUMPTION_TYPE, string='Consumption', required=True),
        'line_ids': fields.one2many('product.likely.expire.report.line', 'report_id', string='Lines', readonly=True),
        'consumption_from': fields.date(string='From'),
        'consumption_to': fields.date(string='To'),
        'only_non_zero': fields.boolean(string='Only products with total expired > 0'),
        'requestor_id': fields.many2one('res.users', string='Requestor'),
        'requestor_date': fields.datetime(string='Date of the demand'),
        'fake_status': fields.function(_get_status, method=True, type='selection', selection=LIKELY_EXPIRE_STATUS, readonly=True, string='Status'),
        'status': fields.selection(LIKELY_EXPIRE_STATUS, string='Status'),
    }

    _defaults = {
        'date_from': lambda *a: time.strftime('%Y-%m-%d'),
        'consumption_to': lambda *a: time.strftime('%Y-%m-%d'),
        'consumption_type': lambda *a: 'fmc',
        'msf_instance': lambda *a: 'MSF Instance',
        'requestor_id': lambda obj, cr, uid, c: uid,
        'requestor_date': lambda *a: time.strftime('%Y-%m-%d %H:%M:%S'),
        'status': 'draft',
    }

    def period_change(self, cr, uid, ids, consumption_from, consumption_to, consumption_type, context=None):
        '''
        Get the first or last day of month
        '''
        res = {}

        if consumption_type == 'amc':
            if consumption_from:
                res.update({'consumption_from': (DateFrom(consumption_from) + RelativeDateTime(day=1)).strftime('%Y-%m-%d')})
            if consumption_to:
                res.update({'consumption_to': (DateFrom(consumption_to) + RelativeDateTime(months=1, day=1, days=-1)).strftime('%Y-%m-%d')})

        return {'value': res}


    def _get_average_consumption(self, cr, uid, product_id, consumption_type, date_from, date_to, context=None):
        '''
        Return the average consumption for all locations
        '''
        if context is None:
            context = {}

        product_obj = self.pool.get('product.product')
        res = 0.00

        if context.get('manual_consumption'):
            return context.get('manual_consumption')

        new_context = context.copy()
        new_context.update({'from_date': date_from,
                            'to_date': date_to,
                            'average': True})

        if consumption_type == 'fmc':
            res = product_obj.browse(cr, uid, product_id, context=new_context).reviewed_consumption
        elif consumption_type == 'amc':
            res = product_obj.compute_amc(cr, uid, product_id, context=new_context)
        else:
            res = product_obj.browse(cr, uid, product_id, context=new_context).monthly_consumption

        return res

    def process_lines(self, cr, uid, ids, context=None):
        '''
        Create one line by product for the period
        '''
        if context is None:
            context = {}
        if ids:
            if isinstance(ids, (int, long)):
                ids = [ids]
            report = self.browse(cr, uid, ids[0], context=context)
            if report:
                if report.status == 'in_progress':
                    # currently in progress
                    return {}
                elif report.status == 'ready':
                    # report already build, show it
                    return self.open_report(cr, uid, ids, context=context)

        import threading
        self.write(cr, uid, ids, {'status': 'in_progress'},
                   context=context)
        cr.commit()
        new_thread = threading.Thread(target=self._process_lines,
                        args=(cr, uid, ids, context))
        new_thread.start()
        new_thread.join(10.0)
        if new_thread.isAlive():
            # more than 10 secs to compute data
            # displaying 'waiting form'
            view_id = self.pool.get('ir.model.data').get_object_reference(
                cr, uid, 'consumption_calculation',
                'product_likely_expire_report_waiting_view')[1]
            return {
                'type': 'ir.actions.act_window',
                'res_model': 'product.likely.expire.report',
                'view_type': 'form',
                'view_mode': 'form',
                'res_id': ids[0],
                'view_id': [view_id],
                'context': context,
                'target': 'same',
            }

        return self.open_report(cr, uid, ids, context=context)

    def _process_lines(self, cr, uid, ids, context=None):
        '''
        Creates all moves with expiry quantities for all
        lot life date
        '''
        if context is None:
            context = {}
        if isinstance(ids, (int, long)):
            ids = [ids]

        # background cursor
        import pooler
        new_cr = pooler.get_db(cr.dbname).cursor()

        move_obj = self.pool.get('stock.move')
        lot_obj = self.pool.get('stock.production.lot')
        loc_obj = self.pool.get('stock.location')
        product_obj = self.pool.get('product.product')
        line_obj = self.pool.get('product.likely.expire.report.line')
        item_obj = self.pool.get('product.likely.expire.report.item')
        item_line_obj = self.pool.get('product.likely.expire.report.item.line')

        view_id = self.pool.get('ir.model.data').get_object_reference(new_cr, uid, 'consumption_calculation', 'product_likely_expire_report_form_processed')[1]
        report = self.browse(new_cr, uid, ids[0], context=context)

        if report.date_to <= report.date_from:
            raise osv.except_osv(_('Error'), _('You cannot have \'To date\' older than \'From date\''))

        if report.consumption_type in ('amc', 'rac') and report.consumption_from > report.consumption_to:
            raise osv.except_osv(_('Error'), _('You cannot have \'To date\' older than \'From date\''))

        if report.consumption_type in ('amc', 'rac'):
            context.update({'from': report.consumption_from, 'to': report.consumption_to})
        else:
            context.update({'from': report.date_from, 'to': report.date_to})

        location_ids = []
        not_loc_ids = []
        only_product_ids = []

        if context.get('only_product_ids'):
            only_product_ids = context.get('only_product_ids')

        if report.input_output_ok:
            wh_ids = self.pool.get('stock.warehouse').search(new_cr, uid, [], context=context)
            for wh in self.pool.get('stock.warehouse').browse(new_cr, uid, wh_ids, context=context):
                not_loc_ids.extend(loc_obj.search(new_cr, uid, [('location_id', 'child_of', wh.lot_input_id.id)], context=context))
                not_loc_ids.extend(loc_obj.search(new_cr, uid, [('location_id', 'child_of', wh.lot_output_id.id)], context=context))

        if report.location_id:
            # Get all locations
            location_ids = loc_obj.search(new_cr, uid, [('location_id', 'child_of', report.location_id.id), ('quarantine_location', '=', False), ('id', 'not in', not_loc_ids)], order='location_id', context=context)
        else:
            # Get all locations
            wh_location_ids = loc_obj.search(new_cr, uid, [('usage', '=', 'internal'), ('quarantine_location', '=', False), ('id', 'not in', not_loc_ids)], order='location_id', context=context)

            move_ids = move_obj.search(new_cr, uid, [('prodlot_id', '!=', False)], context=context)
            for move in move_obj.browse(new_cr, uid, move_ids, context=context):
                if move.location_id.id not in location_ids:
                    if move.location_id.usage == 'internal' and not move.location_id.quarantine_location and move.location_id.id in wh_location_ids:
                        location_ids.append(move.location_id.id)
                if move.location_dest_id.id not in location_ids and not move.location_dest_id.quarantine_location and move.location_dest_id.id in wh_location_ids:
                    if move.location_dest_id.usage == 'internal':
                        location_ids.append(move.location_dest_id.id)

        context.update({'location_id': location_ids, 'location': location_ids})

        lot_domain = [('stock_available', '>', 0.00)]
        if only_product_ids:
            lot_domain.append(('product_id', 'in', only_product_ids))

        lot_ids = lot_obj.search(new_cr, uid, lot_domain, order='product_id, life_date', context=context)

        from_date = DateFrom(report.date_from)
        to_date = DateFrom(report.date_to) + RelativeDateTime(day=1, months=1, days=-1)

        # Set all months between from_date and to_date
        dates = []
        while (from_date < to_date):
            dates.append(from_date)
            from_date = from_date + RelativeDateTime(months=1, day=1)

        # Create a report line for each product
        products = {}
        for lot in lot_obj.browse(new_cr, uid, lot_ids, context=context):
            if lot.product_id and lot.product_id.id not in products:
                products.update({lot.product_id.id: {}})
                consumption = self._get_average_consumption(new_cr, uid, lot.product_id.id,
                                                            report.consumption_type,
                                                            context.get('from', report.date_from),
                                                            context.get('to', report.date_to),
                                                            context=context)

                products[lot.product_id.id].update({'line_id': line_obj.create(new_cr, uid, {'report_id': report.id,
                                                                                         'product_id': lot.product_id.id,
                                                                                         'in_stock': lot.product_id.qty_available,
                                                                                         'total_expired': 0.00,
                                                                                         'consumption': consumption,}, context=context)})

                # Create an item for each date
                seq = 0
                total_cons = 0.00
                already_cons = 0.00
                rest = 0.00
                total_expired = 0.00
                start_month_flag = True
                last_expiry_date = False
                for month in dates:
                    # Remove one day to include the expiry date as possible consumable day
                    if not last_expiry_date: last_expiry_date = month - RelativeDateTime(days=1)

                    item_id = item_obj.create(new_cr, uid, {'name': month.strftime('%m/%y'),
                                                        'line_id': products[lot.product_id.id]['line_id']}, context=context)
                    available_qty = 0.00
                    expired_qty = 0.00
                    seq += 1

                    # Create a line for each lot which expired in this month
                    domain = [('product_id', '=', lot.product_id.id),
                             ('stock_available', '>', 0.00),
                             ('life_date', '<', (month + RelativeDateTime(months=1, day=1)).strftime('%Y-%m-%d'))]

                    if not start_month_flag:
                        domain.append(('life_date', '>=', month.strftime('%Y-%m-%d')))
                        item_obj.write(new_cr, uid, [item_id], {'period_start': (month + RelativeDateTime(day=1)).strftime('%Y-%m-%d')}, context=context)
                    else:
                        item_obj.write(new_cr, uid, [item_id], {'period_start': report.date_from}, context=context)
                        # Uncomment the first line if you want products already expired in the first month
                        #domain.append(('life_date', '>=', month.strftime('%Y-%m-01')))
                        # Comment line if you want all products already expired
                        #if not context.get('only_product_ids'):
                        #    domain.append(('life_date', '>=', month.strftime('%Y-%m-%d')))


                    # Remove the token after the first month processing
                    start_month_flag = False

                    product_lot_ids = lot_obj.search(new_cr, uid, domain, order='life_date', context=context)

                    # Create an item line for each lot and each location
                    for product_lot in lot_obj.browse(new_cr, uid, product_lot_ids, context=context):
                        lot_days = Age(DateFrom(product_lot.life_date), last_expiry_date)
                        lot_coeff = (lot_days.years*365.0 + lot_days.months*30.0 + lot_days.days)/30.0
                        if lot_coeff >= 0.00: last_expiry_date = DateFrom(product_lot.life_date)
                        if lot_coeff < 0.00: lot_coeff = 0.00
                        lot_cons = self.pool.get('product.uom')._compute_qty(new_cr, uid, lot.product_id.uom_id.id, round(lot_coeff*consumption,2), lot.product_id.uom_id.id) + rest

                        if lot_cons > 0.00:
                            if lot_cons >= product_lot.stock_available:
                                already_cons += product_lot.stock_available
                                rest = lot_cons - product_lot.stock_available
                                l_expired_qty = 0.00
                            else :
                                l_expired_qty = product_lot.stock_available - lot_cons
                                already_cons += lot_cons
                                rest = 0.00
                        else:
                            l_expired_qty = product_lot.stock_available
                        expired_qty += l_expired_qty

                        lot_context = context.copy()
                        lot_context.update({'prodlot_id': product_lot.id})
                        product = product_obj.browse(new_cr, uid, lot.product_id.id, context=lot_context)
                        lot_expired_qty = l_expired_qty
                        for location in location_ids:
                            new_lot_context = lot_context.copy()
                            new_lot_context.update({'location': location, 'compute_child': False})
                            product2 = product_obj.browse(new_cr, uid, lot.product_id.id, context=new_lot_context)
                            if product2.qty_available > 0.00:
                                # Create the item line
                                if product2.qty_available <= lot_expired_qty:
                                    new_lot_expired = product2.qty_available
                                    lot_expired_qty -= product2.qty_available
                                else:
                                    new_lot_expired = lot_expired_qty
                                    lot_expired_qty = 0.00
                                item_line_obj.create(new_cr, uid, {'item_id': item_id,
                                                               'lot_id': product_lot.id,
                                                               'location_id': location,
                                                               'available_qty': product2.qty_available,
                                                               'expired_qty': new_lot_expired}, context=context)

                        available_qty += product.qty_available

                    item_obj.write(new_cr, uid, [item_id], {'available_qty': available_qty,
                                                        'expired_qty': expired_qty}, context=context)
                    total_expired += expired_qty

                if report.only_non_zero and total_expired <= 0.00:
                    line_obj.unlink(new_cr, uid, [products[lot.product_id.id]['line_id']], context=context)
                else:
                    line_obj.write(new_cr, uid, [products[lot.product_id.id]['line_id']], {'total_expired': total_expired}, context=context)

        new_date = []
        for date in dates:
            new_date.append(date.strftime('%m/%y'))

        context.update({'dates': new_date})
        self.write(new_cr, uid, ids, {'status': 'ready'}, context=context)

        new_cr.commit()
        new_cr.close(True)

        return {
            'type': 'ir.actions.act_window',
            'res_model': 'product.likely.expire.report',
            'res_id': report.id,
            'view_id': [view_id],
            'view_type': 'form',
            'view_mode': 'form',
            'context': context,
            'target': 'dummy'
        }


    def fields_view_get(self, cr, uid, view_id=None, view_type='form', context=None, toolbar=False, submenu=False):
        if not context:
            context = {}

        res = super(product_likely_expire_report, self).fields_view_get(cr, uid, view_id, view_type, context=context)

        line_view = """<tree string="Expired products">
                <field name="product_id"/>
                <field name="consumption"/>
                """

        dates = context.get('dates', [])
        for month in dates:
            line_view += '<field name="%s" />' % month
            line_view += '<button name="go_to_item_%s" type="object" string="Go to item" icon="gtk-info" context="{item_date: %s}" />' % (month, month)

        line_view += """<field name="in_stock"/>
                        <field name="total_expired" />
                        </tree>"""

        if res['fields'].get('line_ids', {}).get('views', {}).get('tree', {}).get('arch', {}):
            res['fields']['line_ids']['views']['tree']['arch'] = line_view

        return res

    def get_report_dates_str(self, report):
        """ return list(str) of month headers """
        res = []
        for dates, dates_str in self.get_report_dates_multi(report):
            res.append(dates_str)
        return res

    def get_report_dates_multi(self, report):
        """ return list(tuple(date, str)) of month headers (1st day of month)"""
        if not report:
            return []
        res = []
        from_date = DateFrom(report.date_from)
        to_date = DateFrom(report.date_to) + RelativeDateTime(day=1, months=1, days=-1)
        while (from_date < to_date):
            res.append((from_date, from_date.strftime('%m/%y'), ))
            from_date = from_date + RelativeDateTime(months=1, day=1)
        return res

    def open_report(self, cr, uid, ids, context=None):
        '''
        Open the report
        '''
        # compute dates to inject to context
        if context is None:
            context = {}
        if not ids:
            return {}
        if isinstance(ids, (int, long)):
            ids = [ids]
        report = self.browse(cr, uid, ids[0], context=context)
        if not report:
            return {}

        new_context = context.copy()
        new_context['dates'] = self.get_report_dates_str(report)
        view_id = self.pool.get('ir.model.data').get_object_reference(
            cr, uid, 'consumption_calculation',
            'product_likely_expire_report_form_processed')[1]
        return {
            'type': 'ir.actions.act_window',
            'res_model': 'product.likely.expire.report',
            'view_id': [view_id],
            'view_type': 'form',
            'view_mode': 'form',
            'target': 'dummy',
            'context': new_context,
            'res_id': ids[0],
        }

    def in_progress(self, cr, uid, ids, context=None):
        '''
        Return dummy
        '''
        return self._go_to_list(cr, uid, ids, context=context)

    def _go_to_list(self, cr, uid, ids, context=None):
        '''
        Returns to the list of reports
        '''
        return {
                'type': 'ir.actions.act_window',
                'res_model': 'product.likely.expire.report',
                'view_mode': 'tree,form',
                'view_type': 'form',
                'target': 'dummy',
                'context': context,
            }

    def _has_expiry(self, cr, uid, ids, context=None):
        if not ids:
            return False
        if isinstance(ids, (int, long)):
            ids = [ids]
        pler = self.browse(cr, uid, ids[0], context=context)
        if pler and pler.line_ids:
            return True
        return False

    def print_report_xls(self, cr, uid, ids, context=None):
        '''
        Print the report (Excel)
        '''
        if not self._has_expiry(cr, uid, ids, context=context):
            raise osv.except_osv(_("Warning"), _("There is not any product in expiry"))
        datas = {'ids': ids}

        return {
            'type': 'ir.actions.report.xml',
            'report_name': 'product.likely.expire.report_xls',
            'datas': datas,
            'nodestroy': True,
            'context': context,
        }

    def print_report_pdf(self, cr, uid, ids, context=None):
        '''
        Print the report (PDF)
        '''
        if not self._has_expiry(cr, uid, ids, context=context):
            raise osv.except_osv(_("Warning"), _("There is not any product in expiry"))
        datas = {'ids': ids}

        return {
            'type': 'ir.actions.report.xml',
            'report_name': 'product.likely.expire.report_pdf',
            'datas': datas,
            'nodestroy': True,
            'context': context,
        }

product_likely_expire_report()


class product_likely_expire_report_line(osv.osv):
    _name = 'product.likely.expire.report.line'
    _rec_name = 'report_id'

    def _get_total_value(self, cr, uid, ids, fieldname, args, context=None):
        res = { }
        if not ids:
            return res
        if isinstance(ids, (int, long)):
            ids = [ids]
        for o in self.browse(cr, uid, ids, context=context):
            if o.product_id:
                res[o.id] = o.product_id.standard_price * o.total_expired
            else:
                res[o.id] = 0.
        return res

    _columns = {
            'report_id': fields.many2one('product.likely.expire.report', string='Report', required=True, ondelete='cascade'),
            'product_id': fields.many2one('product.product', string='Product', required=True),
            'consumption': fields.float(digits=(16,2), string='Monthly Consumption', required=True),
            'in_stock': fields.float(digits=(16,2), string='In stock'),
            'total_expired': fields.float(digits=(16,2), string='Total expired'),
            'total_value': fields.function(_get_total_value, type='float', string='Total Value', method=True),
    }

    def __getattr__(self, name, *args, **kwargs):
        if name[:11] == 'go_to_item_':
            date = name[11:]
            self.date = date
            return self.go_to_item
        else:
            return super(product_likely_expire_report_line, self).__getattr__(name, *args, **kwargs)

    def fields_get(self, cr, uid, fields=None, context=None):
        if context is None:
            context = {}

        res = super(product_likely_expire_report_line, self).fields_get(cr, uid, fields, context)
        dates = context.get('dates', [])

        for month in dates:
            res.update({month: {'selectable': True,
                               'type': 'many2one',
                               'relation': 'product.likely.expire.report.item',
                               'string': month}})

        return res

    def go_to_item(self, cr, uid, ids, context=None):
        if context is None:
            context = {}

        if not context.get('item_date', self.date):
            raise osv.except_osv(_('Error'), _('You haven\'t choose an item to open'))

        item_date = context.get('item_date', self.date)
        item_ids = self.pool.get('product.likely.expire.report.item').search(cr, uid, [('name', '=', item_date), ('line_id', '=', ids[0])], context=context)
        if not item_ids:
            raise osv.except_osv(_('Error'), _('You haven\'t choose an item to open'))

        return {'type': 'ir.actions.act_window',
                'res_model': 'product.likely.expire.report.item',
                'res_id': item_ids[0],
                'view_type': 'form',
                'view_mode': 'form',
                'context': context,
                'target': 'new'}


    def read(self, cr, uid, ids, vals, context=None, load='_classic_read'):
        '''
        Set values for all dates
        '''

        res = super(product_likely_expire_report_line, self).read(cr, uid, ids, vals, context=context, load=load)

        item_obj = self.pool.get('product.likely.expire.report.item')
        for r in res:
            exp_ids = item_obj.search(cr, uid, [('line_id', '=', r['id'])], context=context)
            for exp in item_obj.browse(cr, uid, exp_ids, context=context):
                r.update({exp.name: ''})
                if exp.expired_qty > 0.00:
                    name = '%s (%s)' % (exp.available_qty, exp.expired_qty)
                else:
                    # Be careful to the undividable spaces
                    name = '      %s' % (exp.available_qty)

                r.update({exp.name: name})

        return res


product_likely_expire_report_line()


class product_likely_expire_report_item(osv.osv):
    _name = 'product.likely.expire.report.item'
    _rec_name = 'line_id'

    _columns = {
            'line_id': fields.many2one('product.likely.expire.report.line', string='Line', ondelete='cascade'),
            'name': fields.char(size=64, string='Month'),
            'available_qty': fields.float(digits=(16,2), string='Available Qty.'),
            'expired_qty': fields.float(digits=(16,2), string='Expired Qty.'),
            'period_start': fields.date(string='Period start', readonly=True),
            'line_ids': fields.one2many('product.likely.expire.report.item.line', 'item_id', string='Batchs'),
    }

product_likely_expire_report_item()


class product_likely_expire_report_item_line(osv.osv):
    _name = 'product.likely.expire.report.item.line'
    _order = 'expired_date, location_id'
    _rec_name = 'item_id'

    _columns = {
            'item_id': fields.many2one('product.likely.expire.report.item', strig='Item', ondelete='cascade'),
            'lot_id': fields.many2one('stock.production.lot', string='Batch number'),
            'location_id': fields.many2one('stock.location', string='Location'),
            'available_qty': fields.float(digits=(16,2), string='Available Qty.'),
            'expired_qty': fields.float(digits=(16,2), string='Expired Qty.'),
            'expired_date': fields.related('lot_id', 'life_date', type='date', string='Expiry date', store=True),
    }

product_likely_expire_report_item_line()


class product_product(osv.osv):
    _name = 'product.product'
    _inherit = 'product.product'

    def get_expiry_qty(self, cr, uid, product_id, location_id, monthly_consumption, d_values=None, context=None):
        '''
        Get the expired quantity of product
        '''
        if context is None:
            context = {}

        if d_values is None:
            d_values = {}

        monthly_consumption = 'rac'

        # Get the monthly consumption
        if d_values.get('reviewed_consumption', False):
            monthly_consumption = 'fmc'
        elif d_values.get('past_consumption', False):
            monthly_consumption = 'amc'
        else:
            monthly_consumption_val = d_values.get('manual_consumption', 0.00)
            context.update({'manual_consumption': monthly_consumption_val})

        product = self.browse(cr, uid, product_id, context=context)
        # Get the delivery lead time of the product if the leadtime is not defined in rule and no supplier found in product form
        delivery_leadtime = product.procure_delay and round(int(product.procure_delay)/30.0, 2) or 1
        # Get the leadtime of the rule if defined
        if 'leadtime' in d_values and d_values.get('leadtime', 0.00) != 0.00:
            delivery_leadtime = d_values.get('leadtime')
        elif product.seller_ids:
            # Get the supplier lead time if supplier is defined
            # The seller delay is defined in days, so divide it by 30.0 to have a LT in months
            delivery_leadtime = product.seller_delay and round(int(product.seller_delay)/30.0, 2) or 1

        delta = (delivery_leadtime + d_values.get('coverage', 0.00))*30.0

        report_data = {'date_from': today().strftime('%Y-%m-%d'),
                       'date_to': (today() + RelativeDateTime(days=delta)).strftime('%Y-%m-%d'),
                       'consumption_type': monthly_consumption,
                       'consumption_from': d_values.get('consumption_period_from'),
                       'consumption_to': d_values.get('consumption_period_to'),
                       'location_id': location_id}
        
        report_obj = self.pool.get('product.likely.expire.report')
        line_obj = self.pool.get('product.likely.expire.report.line')

        exp_context = context.copy()
        exp_context.update({'only_product_ids': [product_id]})
        report_id = report_obj.create(cr, uid, report_data, context=exp_context)
        # Process report
        report_obj.process_lines(cr, uid, report_id, context=exp_context)

        lines = line_obj.search(cr, uid, [('report_id', '=', report_id)], context=context)
        for line in line_obj.browse(cr, uid, lines, context=context):
            if line.product_id.id == product_id:
                return line.total_expired

product_product()

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
