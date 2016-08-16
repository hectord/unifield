# -*- coding: utf-8 -*-
##############################################################################
#
#    OpenERP, Open Source Management Solution
#    Copyright (C) 2014 TeMPO Consulting, MSF
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU Affero General Public License as
#    published by the Free Software Foundation, either version 3 of the
#    License, or (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#
#    GNU Affero General Public License for more details.
#    You should have received a copy of the GNU Affero General Public License
#    along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
##############################################################################

from mx.DateTime.DateTime import DateFrom, RelativeDateTime, Age, now
import threading
import time

from osv import fields
from osv import osv
from osv.orm import browse_record
from tools.translate import _
import pooler


LIKELY_EXPIRE_STATUS = [
    ('draft', 'Draft'),
    ('in_progress', 'In Progress'),
    ('ready', 'Ready'),
    ('error', 'Error'),
]
CONSUMPTION_TYPE = [
    ('fmc', 'FMC -- Forecasted Monthly Consumption'),
    ('amc', 'AMC -- Average Monthly Consumption'),
    ('rac', 'RAC -- Real Average Consumption'),
]


class weekly_forecast_report(osv.osv):
    '''
    Weekly forecast report
    '''
    _name = 'weekly.forecast.report'
    _description = 'Stock forecast by week'
    _rec_name = 'location_id'
    _order = 'requestor_date desc, id'

    _columns = {
        'location_id': fields.many2one(
            'stock.location',
            string='Location',
            required=True,
        ),
        'interval': fields.integer(
            string='Interval',
            required=True,
        ),
        'interval_type': fields.selection(
            [('week', 'Weeks'), ('month', 'Months')],
            string='Interval type',
            required=True,
        ),
        'consumption_type': fields.selection(
            CONSUMPTION_TYPE,
            string='Consumption',
            required=True,
        ),
        'consumption_from': fields.date(
            string='From',
        ),
        'consumption_to': fields.date(
            string='To',
        ),
        'requestor_id': fields.many2one(
            'res.users',
            string='Requestor',
        ),
        'requestor_date': fields.datetime(
            string='Date of te demand',
        ),
        'status': fields.selection(
            LIKELY_EXPIRE_STATUS,
            string='Status',
            readonly=True,
        ),
        'xml_data': fields.text(
            string='XML data',
            readonly=True,
        ),
        'progress': fields.float(
            digits=(16, 2),
            string='Progression',
            readonly=True,
        ),
        'progress_comment': fields.text(
            string='Status of the progression',
            readonly=True,
        ),
        'sublist_id': fields.many2one(
            'product.list',
            string='List/Sublist',
        ),
        'nomen_manda_0': fields.many2one(
            'product.nomenclature',
            'Main Type',
        ),
        'nomen_manda_1': fields.many2one(
            'product.nomenclature',
            'Group',
        ),
        'nomen_manda_2': fields.many2one(
            'product.nomenclature',
            'Family',
        ),
        'nomen_manda_3': fields.many2one(
            'product.nomenclature',
            'Root',
        ),
    }

    _defaults = {
        'requestor_id': lambda self, cr, uid, c={}: uid,
        'requestor_date': lambda *a: time.strftime('%Y-%m-%d %H:%M:%S'),
        'consumption_to': lambda *a: time.strftime('%Y-%m-%d'),
        'consumption_type': 'fmc',
        'status': 'draft',
    }

    def copy(self, cr, uid, report_id, defaults=None, context=None):
        """
        Reset value on copy.

        :param cr: Cursor to the database
        :param uid: ID of the user that launches the method
        :param report_id: ID of the weekly.forecast.report object to duplicate
        :param defaults: Default values for the new object
        :param context: Context of the call

        :return The ID of the new object
        """
        if context is None:
            context = {}

        if defaults is None:
            defaults = {}

        defaults.update({
            'status': 'draft',
            'progress': 0.00,
            'progress_comment': '',
            'xml_data': '',
            'requestor_date': time.strftime('%Y-%m-%d %H:%M:%S'), # Fixed the wrong typo date format
        })
        return super(weekly_forecast_report, self).copy(cr, uid, report_id, defaults, context=context)

    def period_change(self, cr, uid, ids, consumption_from, consumption_to, consumption_type, context=None):
        """
        Get the first or last day of month
        """
        res = {}

        if consumption_type == 'amc':
            if consumption_from:
                res.update({
                    'consumption_from': (DateFrom(consumption_from) + RelativeDateTime(day=1)).strftime('%Y-%m-%d'),
                })
            if consumption_to:
                res.update({
                    'consumption_to': (DateFrom(consumption_to) + RelativeDateTime(months=1, day=1, days=-1)).strftime('%Y-%m-%d'),
                })

        return {'value': res}

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
                # Report values
                self._check_report_values(report)

                if report.status == 'in_progress':
                    # currently in progress
                    return {
                        'type': 'ir.actions.act_window',
                        'res_model': 'weekly.forecast.report',
                        'res_id': ids[0],
                        'view_type': 'form',
                        'view_mode': 'form,tree',
                        'context': context,
                        'target': 'crush',
                    }
                elif report.status == 'ready':
                    # report already build, show it
                    return self.open_report(cr, uid, ids, context=context)

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
                'weekly_forecast_report_waiting_view')[1]
            return {
                'type': 'ir.actions.act_window',
                'res_model': 'weekly.forecast.report',
                'view_type': 'form',
                'view_mode': 'form',
                'res_id': ids[0],
                'view_id': [view_id],
                'context': context,
                'target': 'same',
            }

        return self.open_report(cr, uid, ids, context=context)

    def open_report(self, cr, uid, ids, context=None):
        """
        Open the Excel file

        :param cr: Cursor to the database
        :param uid: ID of the use that runs the method
        :param ids: List of ID of the weekly.forecast.report
        :param context: Context of the call

        :return Return a dictionary with the action to open the report
        :rtype dict
        """
        datas = {
            'ids': ids,
            'target_filename': 'Periodical Forecast Report',
        }
        return {
            'type': 'ir.actions.report.xml',
            'report_name': 'weekly.forecast.report_xls',
            'datas': datas,
            'nodestroy': True,
            'context': context,
        }

    def in_progress(self, cr, uid, ids, context=None):
        """
        Refresh the tree view

        :param cr: Cursor to the database
        :param uid: ID of the use that runs the method
        :param ids: List of ID of the weekly.forecast.report
        :param context: Context of the call

        :return Return a dictionary with the action to open the report
        :rtype dict
        """
        return {
            'type': 'ir.actions.act_window',
            'res_model': 'weekly.forecast.report',
            'view_type': 'form',
            'view_mode': 'tree,form',
            'context': context,
        }

    def _check_report_values(self, report_brw, context=None):
        """
        Check if the consistency of the values of the report.

        :param report_brw: browse_record of a weekly.forecast.report to check
        :param context: Context of the call (will be updated by this method)

        :return True if all is ok, raise an error otherwise
        :rtype boolean
        """
        if not isinstance(report_brw, browse_record):
            raise osv.except_osv(
                _('Error'),
                _('The parameter \'report_brw\' of the method _check_report_values() must be a browse_record instance'),
            )

        if context is None:
            context = {}

        if report_brw.interval <= 0 or report_brw.interval > 20 or not report_brw.interval_type:
            raise osv.except_osv(
                _('Error'),
                _('The number of intervals must be between 1 and 20'),
            )

        if report_brw.consumption_type in ('amc', 'rac') and report_brw.consumption_from > report_brw.consumption_to:
            raise osv.except_osv(
                _('Error'),
                _('You cannot have \'To date\' older than \'From date\''),
            )

        if report_brw.consumption_type in ('amc', 'rac'):
            context.update({'from': report_brw.consumption_from, 'to': report_brw.consumption_to})

        return True

    def _process_lines(self, cr, uid, ids, context=None):
        """
        For each product of the DB, display the forecasted stock
        quantity value according to consumption, expired and in-pipe values.

        :param cr: Cursor to the database
        :param uid: ID of the user that called this method
        :param ids: ID or list of ID of weekly.forecast.report to generate
        :param context: Context of the call

        :return True if all is ok
        :rtype boolean
        """
        # Objects
        product_obj = self.pool.get('product.product')
        loc_obj = self.pool.get('stock.location')
        uom_obj = self.pool.get('product.uom')

        if context is None:
            context = {}

        if isinstance(ids, (int, long)):
            ids = [ids]

        # background cursor
        new_cr = pooler.get_db(cr.dbname).cursor()
        try:
            for report in self.browse(new_cr, uid, ids, context=context):
                product_domain = [('type', '=', 'product')]
                product_ids = []
                nomen_name_for_loc = None
                if report.nomen_manda_0:
                    nom = False
                    # Get all products for the defined nomenclature
                    if report.nomen_manda_3:
                        nom = report.nomen_manda_3.id
                        field = 'nomen_manda_3'
                    elif report.nomen_manda_2:
                        nom = report.nomen_manda_2.id
                        field = 'nomen_manda_2'
                    elif report.nomen_manda_1:
                        nom = report.nomen_manda_1.id
                        field = 'nomen_manda_1'
                    elif report.nomen_manda_0:
                        nom = report.nomen_manda_0.id
                        field = 'nomen_manda_0'
                        nomen_name_for_loc = report.nomen_manda_0.name

                    if nom:
                        product_domain.append((field, '=', nom))

                if report.sublist_id:
                    context.update({'search_default_list_ids': report.sublist_id.id})
                    for line in report.sublist_id.product_ids:
                        product_ids.append(line.name.id)

                    if product_ids:
                        product_domain.append(('id', 'in', product_ids))

                nb_products = product_obj.search(new_cr, uid, product_domain, count=True, context=context)
                # Get all locations
                location_ids = loc_obj.search(new_cr, uid, [
                    ('location_id', 'child_of', report.location_id.id),
                    ('quarantine_location', '=', False),
                ], order='location_id', context=context)

                if location_ids:
                    loc_name = loc_obj.read(new_cr, uid, location_ids[0], ['name',], context=context)
                    if loc_name:
                        loc_name = loc_name['name']
                        if loc_name in ['LOG', 'MED'] and loc_name != nomen_name_for_loc:
                            nomen_id = self.pool.get('product.nomenclature').search(new_cr, uid, [('level', '=', 0), ('name', '=', loc_name)], context=context)[0]
                            product_domain.append(('nomen_manda_0', '=', nomen_id))

                #UFTP-225: If the location is from Stock/MED/LOG, take also the Input location for the report
                stock_ids = loc_obj.search(new_cr, uid, [('location_category', '=', 'stock')], context=context)
                for loc in location_ids:
                    if loc in stock_ids:
                        # search for Input location, and add it into the location list
                        input_stock_ids = loc_obj.search(new_cr, uid, [('location_category', '=', 'transition'), ('name', '=', 'Input')], context=context)
                        location_ids.extend(input_stock_ids)
                        break

                context.update({
                    'location_id': location_ids,
                    'location': location_ids,
                })

                # Compute intervals
                intervals = []
                dict_int_from = {}
                i = 0
                while i != report.interval:
                    i += 1
                    if report.interval_type == 'week':
                        interval_name = 'Week %s' % i
                        interval_from = now() + RelativeDateTime(weeks=i-1, hour=0, minute=0, second=0)
                        interval_to = now() + RelativeDateTime(weeks=i, days=-1, hour=23, minute=59, second=59)
                    else:
                        interval_name = 'Month %s' % i
                        interval_from = now() + RelativeDateTime(months=i-1, hour=0, minute=0, second=0)
                        interval_to = now() + RelativeDateTime(months=i, days=-1, hour=23, minute=59, second=59)

                    intervals.append((interval_name, interval_from, interval_to))
                    dict_int_from.setdefault(interval_from.strftime('%Y-%m-%d'), interval_name)

                percent_completed = 0.00
                progress_comment = ""
                product_ids = []
                product_cons = {}
                in_pipe_vals = {}
                exp_vals = {}

                ##### First, get the list of product_id
                product_ids = product_obj.search(new_cr, uid, product_domain, context=context)
                product_ids = list(set(product_ids))

                if len(product_ids) > 0:
                    ##### UFTP-220: Filter this list of products for those only appeared in the selected location of the report, not all product
                    new_cr.execute("select distinct product_id from report_stock_inventory where location_id in %s and product_id in %s", (tuple(location_ids),tuple(product_ids),) )
                    product_ids = []
                    for row in new_cr.dictfetchall():
                        product_ids.append(row['product_id'])
                    product_ids = list(set(product_ids)) # just to make sure that the list is duplicate-free

                ##### We still need to get the list of products with AMC and FMC > 0
                fmc_line_obj = self.pool.get('monthly.review.consumption.line')
                tmp_product_ids = []
                amc_fmc_product_ids = fmc_line_obj.search(new_cr, uid, ['|', ('amc', '>', 0), ('fmc', '>', 0)], context=context)
                if len(amc_fmc_product_ids) > 0:
                    amc_fmc_product_ids = fmc_line_obj.read(new_cr, uid, amc_fmc_product_ids, ['name',], context=context) # read the name, which is product_id
                    for temp in amc_fmc_product_ids:
                        if temp['name'] and temp['name'][0]:
                            tmp_product_ids.append(temp['name'][0])

                temp_domain = product_domain
                temp_domain.append(('id', 'in', tmp_product_ids))
                tmp_product_ids = product_obj.search(new_cr, uid, temp_domain, context=context) # search with domain again

                product_ids.extend(tmp_product_ids)
                product_ids = list(set(product_ids)) # just to make sure that the list is duplicate-free

                ##### Now, from this list, perform calculation for consumption, in-pipeline and expired quantity
                nb_products = len(product_ids) # reupdate the number of real products to calculate
                t = 0
                jump = 100
                while t < nb_products:
                    # Get consumption, in-pipe and expired quantities for each product
                    product_cons.update(self._get_product_consumption(new_cr, uid, product_ids, location_ids, report, context=context))
                    in_pipe_vals.update(self._get_in_pipe_vals(new_cr, uid, product_ids, location_ids, report, context=context))
                    exp_vals.update(self._get_expiry_batch(new_cr, uid, product_cons, location_ids, report, context=context))

                    percent_completed = (t/nb_products) * 100
                    progress_comment = """
                        Calculation of consumption values by product: %(treated_products)s/%(nb_products)s

                        Calculation of in-pipe quantities by product and interval: %(treated_products)s/%(nb_products)s

                        Calculation of expiry quantities by product and interval: %(treated_products)s/%(nb_products)s

                        ------------------------------------------------------------------------------------------------

                        Calculate the forecasted quantity by product and period: 0/%(nb_products)s

                    """ % {
                        'treated_products': t,
                        'nb_products': nb_products,
                    }
                    self.write(new_cr, uid, [report.id], {
                        'status': 'in_progress',
                        'progress': percent_completed,
                        'progress_comment': progress_comment,
                    }, context=context)
                    new_cr.commit()
                    t = t + jump

                line_values = """<Row></Row><Row>
                      <Cell ss:StyleID=\"header\"><Data ss:Type=\"String\">Product Code</Data></Cell>
                      <Cell ss:StyleID=\"header\"><Data ss:Type=\"String\">Description</Data></Cell>
                      <Cell ss:StyleID=\"header\"><Data ss:Type=\"String\">Unit Price</Data></Cell>
                      <Cell ss:StyleID=\"header\"><Data ss:Type=\"String\">Stock value</Data></Cell>
                      <Cell ss:StyleID=\"header\"><Data ss:Type=\"String\">AMC/FMC</Data></Cell>
                      <Cell ss:StyleID=\"header\"><Data ss:Type=\"String\">Current Stock Qty</Data></Cell>
                      <Cell ss:StyleID=\"header\"><Data ss:Type=\"String\">Pipeline Qty</Data></Cell>
                      <Cell ss:StyleID=\"header\"><Data ss:Type=\"String\">Expiry Qty</Data></Cell>"""

                for interval in intervals:
                    line_values += """<Cell ss:StyleID=\"header\"><Data ss:Type=\"String\">%(interval_name)s</Data></Cell>""" % {
                        'interval_name': interval[0],
                    }

                line_values += """</Row>"""
                context.update({'from_date': False, 'to_date': False,})

                stock_products = product_obj.read(new_cr, uid, product_ids, [
                    'qty_available',
                    'default_code',
                    'name',
                    'standard_price',
                    'uom_id',
                ], context=context)

                j = 0
                # UFTP-220: get a list of rules that has either one of 3 columns yes, and add the product_ids of these lines for checking it.
                rule_prod_ids = []
                new_cr.execute("select distinct product_id from procurement_rules_report where auto_supply_ok = 'yes' or order_cycle_ok = 'yes' or min_max_ok = 'yes' or threshold_ok = 'yes'")
                for row in new_cr.dictfetchall():
                    rule_prod_ids.append(row['product_id'])

                for product in stock_products:
                    product_id = product['id']
                    j += 1
                    cons = product_cons[product_id][1]
                    if not cons and not product['qty_available']:
                        if product_id not in rule_prod_ids:
                            continue

                    weekly_cons = cons
                    if report.interval_type == 'week':
                        weekly_cons = round(cons / 30 * 7, 2)
                        weekly_cons = uom_obj._change_round_up_qty(new_cr, uid, product['uom_id'][0], weekly_cons, 'cons', result={})['value'].get('cons', 0.0)

                    line_values += """<Row>
                          <Cell ss:StyleID=\"line\"><Data ss:Type=\"String\">%(product_code)s</Data></Cell>
                          <Cell ss:StyleID=\"line\"><Data ss:Type=\"String\">%(product_name)s</Data></Cell>
                          <Cell ss:StyleID=\"line\"><Data ss:Type=\"Number\">%(unit_price)s</Data></Cell>
                          <Cell ss:StyleID=\"line\" ss:Formula=\"=RC[-1]*RC[2]\"><Data ss:Type=\"Number\"></Data></Cell>
                          <Cell ss:StyleID=\"line\"><Data ss:Type=\"Number\">%(consumption)s</Data></Cell>
                          <Cell ss:StyleID=\"line\"><Data ss:Type=\"Number\">%(stock_qty)s</Data></Cell>
                          <Cell ss:StyleID=\"line\"><Data ss:Type=\"Number\">%(pipe_qty)s</Data></Cell>
                          <Cell ss:StyleID=\"line\"><Data ss:Type=\"Number\">%(exp_qty)s</Data></Cell>""" % {
                        'product_code': product['default_code'],
                        'product_name': product['name'],
                        'unit_price': product['standard_price'],
                        'consumption': cons,
                        'stock_qty': product['qty_available'],
                        'pipe_qty': in_pipe_vals.get(product_id, {}).get('total', 0.00),
                        'exp_qty': exp_vals[product_id]['total'],
                    }

                    inter = {}
                    for in_name, in_from, in_to in intervals:
                        inter.setdefault(in_name, {
                            'date_from': in_from,
                            'date_to': in_to,
                            'exp_qty': 0.00,
                            'pipe_qty': 0.00,
                        })

                    # Return the last from date of interval closest to date
                    def get_interval_by_date(date):
                        date = DateFrom(date)
                        if date < now():
                            date = now()
                        if report.interval_type == 'week':
                            st_day = now().day_of_week
                            last_date = date + RelativeDateTime(weekday=(st_day, 0))
                            if date.iso_week[2] == last_date.iso_week[2]:
                                return date
                            elif date.iso_week[2] > last_date.iso_week[2]:
                                return last_date
                            else:
                                return date + RelativeDateTime(weeks=-1) + RelativeDateTime(weekday=(st_day, 0))
                        else:
                            st_day = now().day
                            if date.day >= st_day:
                                return date + RelativeDateTime(day=st_day)
                            else:
                                return date + RelativeDateTime(months=-1, day=st_day)

                    # Put expired quantity into the good interval
                    for exp_key, exp_val in exp_vals[product_id].iteritems():
                        if exp_key != 'total':
                            date_key = get_interval_by_date(exp_key).strftime('%Y-%m-%d')
                            int_name = dict_int_from.get(date_key, False)
                            if int_name:
                                inter[int_name]['exp_qty'] += exp_val

                    # Put In-pipe quantity into the good interval
                    for inp_key, inp_val in in_pipe_vals.get(product_id, {}).iteritems():
                        if inp_key != 'total':
                            date_key = get_interval_by_date(inp_key).strftime('%Y-%m-%d')
                            int_name = dict_int_from.get(date_key, False)
                            if int_name:
                                inter[int_name]['pipe_qty'] += inp_val

                    # Sort the key of the dict, to have the values in good order
                    # TODO: Use OrderedDict instead of this sort of dict keys but only available on Python 2.7
                    interval_keys = inter.keys()
                    interval_keys.sort(key=lambda x: int(x[5:]))
                    last_value = product['qty_available']
                    for interval_name in interval_keys:
                        interval_values = inter.get(interval_name)
                        last_value = last_value - weekly_cons - interval_values['exp_qty'] + interval_values['pipe_qty']
                        # UFTP-225: if the value of week is negative, just set it as 0 in display
                        if last_value < 0:
                            last_value = 0
                        line_values += """<Cell ss:StyleID=\"%(line_style)s\" ss:Formula=\"\"><Data ss:Type=\"Number\">%(value)s</Data></Cell>""" % {
                            'line_style': last_value >= 0.00 and 'line' or 'redline',
                            'value': last_value,
                        }

                    # Ponderation of 50 percent on this part of the process
                    percent_completed = (0.5 + ((float(j)/nb_products) * 0.50)) * 100.00
                    progress_comment = """
                            Calculation of consumption values by product: %(nb_products)s/%(nb_products)s

                            Calculation of in-pipe quantities by product and interval: %(nb_products)s/%(nb_products)s

                            Calculation of expiry quantities by product and interval: %(nb_products)s/%(nb_products)s

                            ------------------------------------------------------------------------------------------------

                            Calculate the forecasted quantity by product and period: %(treated_products)s/%(nb_products)s

                    """ % {
                        'treated_products': j,
                        'nb_products': nb_products,
                    }
                    self.write(new_cr, uid, [report.id], {
                        'status': 'in_progress',
                        'progress': percent_completed,
                        'progress_comment': progress_comment,
                    }, context=context)
                    new_cr.commit()

                    line_values += """
                        </Row>
                    """
                self.write(new_cr, uid, [report.id], {'xml_data': line_values, 'status': 'ready', 'progress': 100.00}, context=context)

            new_cr.commit()
        except Exception as e:
            new_cr.rollback()
            progress_comment = """
            An error occured during the processing of the report.\n
            Details of the error:\n
            %s
            """ % str(e)
            self.write(new_cr, uid, [report.id], {'status': 'error', 'progress_comment': progress_comment}, context=context)
            new_cr.commit()

        new_cr.close(True)

        return True

    def _get_product_consumption(self, cr, uid, product_ids, location_ids, report, context=None):
        """
        Computes and return a list of tuples like (product_id, product_consumption).

        :param cr: Cursor to the database
        :param uid: ID of the user that called this methed
        :param product_ids: List of ID of product.product
        :param location_ids: List of ID of stock.location
        :param report: browse_record of a weekly.forecast.report
        :param context: Context of the call

        :return A dictionary with ID of product as key and the expired quantity
                for this product in the given stock locations by date.
        :rtype dict
        """
        # Objects
        product_obj = self.pool.get('product.product')

        if context is None:
            context = {}

        context.update({
            'from_date': report.consumption_from,
            'to_date': report.consumption_to,
            'location_id': location_ids,
            'location': location_ids,
        })

        res = {}

        cons_field = 'product_amc'
        if report.consumption_type == 'fmc':
            cons_field = 'reviewed_consumption'
        elif report.consumption_type == 'rac':
            cons_field = 'monthly_consumption'

        products = product_obj.read(cr, uid, product_ids, ['perishable', 'batch_management', cons_field], context=context)
        for product in products:
            p_cons = product[cons_field]
            res[product['id']] = (product, p_cons)

        return res

    def _get_expiry_batch(self, cr, uid, product_cons, location_ids, report, context=None):
        """
        Returns a dictionary with for each product in products, the expiry quantities per date.

        :param cr: Cursor to the database
        :param uid: ID of the user that called this method
        :param product_cons: List of tuples like (product_id, product_cons_value)
        :param location_ids: List of ID of stock.location
        :param report: browse_record of a weekly.forecast.report
        :param context: Context of the call

        :return A dictionary with ID of product as key and the expired quantity
                for this product in the given stock locations by date.
        :rtype dict
        """
        # Objects
        lot_obj = self.pool.get('stock.production.lot')
        uom_obj = self.pool.get('product.uom')

        if context is None:
            context = {}

        context.update({
            'location_id': location_ids,
            'location': location_ids,
        })

        res = {}

        if report.interval_type == 'week':
            report_end_date = now() + RelativeDateTime(weeks=report.interval)
        else:
            report_end_date = now() + RelativeDateTime(months=report.interval)

        for product, av_cons in product_cons.itervalues():
            res.setdefault(product['id'], {'total': 0.00})
            if not product['perishable'] and not product['batch_management']:
                continue

            prodlot_ids = lot_obj.search(cr, uid, [
                ('product_id', '=', product['id']),
                ('stock_available', '>', 0.00),
#                ('life_date', '>=', time.strftime('%Y-%m-%d')),
                ('life_date', '<=', report_end_date.strftime('%Y-%m-%d')),
            ], order='life_date', context=context)

            last_expiry_date = now() - RelativeDateTime(days=1)
            total_expired = 0.00
            rest = 0.00
            already_cons = 0.00
            for lot in lot_obj.browse(cr, uid, prodlot_ids, context=context):
                l_expired_qty = 0.00
                lot_days = Age(DateFrom(lot.life_date), last_expiry_date)
                lot_coeff = (lot_days.years*365.0 + lot_days.months*30.0 + lot_days.days)/30.0

                if lot_coeff >= 0.00:
                    last_expiry_date = DateFrom(lot.life_date)
                if lot_coeff < 0.00:
                    lot_coeff = 0.00

                lot_cons = uom_obj._compute_qty(cr, uid, lot.product_id.uom_id.id, round(lot_coeff*av_cons, 2), lot.product_id.uom_id.id) + rest
                if lot_cons > 0.00:
                    if lot_cons >= lot.stock_available:
                        already_cons += lot.stock_available
                        rest = lot_cons - lot.stock_available
                        l_expired_qty = 0.00
                    else:
                        l_expired_qty = lot.stock_available - lot_cons
                        already_cons += lot_cons
                        rest = 0.00
                else:
                    l_expired_qty = lot.stock_available

                if l_expired_qty:
                    total_expired += l_expired_qty
                    res[product['id']].setdefault(lot.life_date, 0.00)
                    res[product['id']].setdefault('total', 0.00)
                    res[product['id']][lot.life_date] += l_expired_qty
                    res[product['id']]['total'] += l_expired_qty

        return res

    def _get_in_pipe_vals(self, cr, uid, product_ids, location_ids, report, context=None):
        """
        Returns a dictionary with for each product in product_ids, the quantity in-pipe.

        :param cr: Cursor to the database
        :param uid: ID of the user that called this method
        :param product_ids: List of ID of product.product
        :param location_ids: List of ID of stock.location
        :param report: browse_record of a weekly.forecast.report
        :param context: Context of the call

        :return A dictionary with ID of product as key and in-pipe quantity for
                this product in the givent stock locations by date
        :rtype dict
        """
        if context is None:
            context = {}

        res = {}

        cr.execute("""
            SELECT product_id, sum(qty) AS qty, date
            FROM
            ((SELECT
               p.id AS product_id,
               sum(-s.product_qty/u1.factor/u2.factor) AS qty,
               s.date AS date
            FROM
               stock_move s
               LEFT JOIN product_product p ON p.id = s.product_id
               LEFT JOIN product_template pt ON p.product_tmpl_id = pt.id
               LEFT JOIN product_uom u1 ON s.product_uom = u1.id
               LEFT JOIN product_uom u2 ON pt.uom_id = u2.id
            WHERE
               s.location_id IN %(location_ids)s
               AND
               s.product_id IN %(product_ids)s
               AND
               s.state IN ('assigned', 'confirmed')
               AND
               s.id NOT IN 
                    (SELECT
                        l.move_dest_id
                     FROM
                        purchase_order_line l
                        LEFT JOIN purchase_order o ON o.id = l.order_id
                     WHERE
                        l.move_dest_id IS NOT NULL
                        AND
                        o.state NOT IN ('approved', 'except_picking', 'except_invoice', 'done')
                    )
            GROUP BY p.id, s.date)
        UNION
            (SELECT
               p.id AS product_id,
               sum(s.product_qty/u1.factor/u2.factor) AS qty,
               s.date AS date
            FROM
               stock_move s
               LEFT JOIN product_product p ON p.id = s.product_id
               LEFT JOIN product_template pt ON p.product_tmpl_id = pt.id
               LEFT JOIN product_uom u1 ON s.product_uom = u1.id
               LEFT JOIN product_uom u2 ON pt.uom_id = u2.id
            WHERE
              s.location_dest_id IN %(location_ids)s
              AND
              s.product_id IN %(product_ids)s
              AND
              s.state IN ('assigned', 'confirmed')
              AND
              s.id NOT IN 
                   (SELECT
                       l.move_dest_id
                    FROM
                       purchase_order_line l
                       LEFT JOIN purchase_order o ON o.id = l.order_id
                    WHERE
                       l.move_dest_id IS NOT NULL
                       AND
                       o.state NOT IN ('approved', 'except_picking', 'except_invoice', 'done')
                   )
            GROUP BY p.id, s.date))
            AS subrequest
            GROUP BY product_id, date;
        """, {
            'location_ids': tuple(location_ids),
            'product_ids': tuple(product_ids)
        })

        for r in cr.dictfetchall():
            res.setdefault(r['product_id'], {'total': 0.00})
            res[r['product_id']].setdefault(r['date'], 0.00)
            res[r['product_id']][r['date']] += r['qty']
            res[r['product_id']].setdefault('total', 0.00)
            res[r['product_id']]['total'] += r['qty']

        return res

##############################################################################################################################
# The code below aims to enable filtering products regarding their nomenclature.
# NB: the difference with the other same kind of product filters (with nomenclature and sublist) is that here we are dealing with osv_memory
##############################################################################################################################
    def onChangeSearchNomenclature(self, cr, uid, id, position, type, nomen_manda_0, nomen_manda_1, nomen_manda_2, nomen_manda_3, num=True, context=None):
        res = self.pool.get('product.product').onChangeSearchNomenclature(cr, uid, 0, position, type, nomen_manda_0, nomen_manda_1, nomen_manda_2, nomen_manda_3, False, context={'withnum': 1})
        if nomen_manda_0:
            res.setdefault('value', {}).setdefault('sublist_id', False)
        return res

    def get_nomen(self, cr, uid, id, field):
        return self.pool.get('product.nomenclature').get_nomen(cr, uid, self, id, field, context={'withnum': 1})

    def write(self, cr, uid, ids, vals, context=None):
        if vals.get('sublist_id',False):
            vals.update({'nomen_manda_0':False,'nomen_manda_1':False,'nomen_manda_2':False,'nomen_manda_3':False})
        if vals.get('nomen_manda_0',False):
            vals.update({'sublist_id':False})
        if vals.get('nomen_manda_1',False):
            vals.update({'sublist_id':False})
        ret = super(weekly_forecast_report, self).write(cr, uid, ids, vals, context=context)
        return ret
##############################################################################
# END of the definition of the product filters and nomenclatures
##############################################################################

weekly_forecast_report()

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
