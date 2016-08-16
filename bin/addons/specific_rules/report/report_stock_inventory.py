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

import time
import threading

from osv import osv
from osv import fields
from report import report_sxw
from spreadsheet_xml.spreadsheet_xml_write import SpreadsheetReport
from tools.translate import _
from service.web_services import report_spool


class export_report_stock_inventory(osv.osv):
    _name = 'export.report.stock.inventory'

    _columns = {
        'company_id': fields.many2one(
            'res.company',
            string='DB/Instance name',
            readonly=True,
        ),
        'name': fields.datetime(
            string='Generated on',
            readonly=True,
        ),
        'product_id': fields.many2one(
            'product.product',
            string='Specific product',
            help="""If a product is choosen, only quantities of this product
will be shown.""",
        ),
        'prodlot_id': fields.many2one(
            'stock.production.lot',
            string='Specific batch',
        ),
        'expiry_date': fields.date(
            string='Specific expiry date',
        ),
        'location_id': fields.many2one(
            'stock.location',
            string='Specific location',
            help="""If a location is choosen, only product quantities in this
location will be shown.""",
            required=True,
        ),
        'state': fields.selection(
            selection=[
                ('draft', 'Draft'),
                ('in_progress', 'In Progress'),
                ('ready', 'Ready'),
            ],
            string='State',
            readonly=True,
        ),
    }

    _defaults = {
        'state': lambda *a: 'draft',
        'company_id': lambda s,cr,uid,c: s.pool.get('res.company').\
                _company_default_get(
                    cr, uid, 'export.report.stock.inventory', context=c),
    }

    def update(self, cr, uid, ids, context=None):
        return {}

    def generate_report(self, cr, uid, ids, context=None):
        """
        Select the good lines on the report.stock.inventory table
        """
        rsi_obj = self.pool.get('report.stock.inventory')
        lot_obj = self.pool.get('stock.production.lot')
        data_obj = self.pool.get('ir.model.data')

        if context is None:
            context = {}

        for report in self.browse(cr, uid, ids, context=context):
            domain = [
                ('location_id.usage', '=', 'internal'),
                ('product_id.type', '=', 'product'),
                ('product_qty', '!=', 0.00),
                ('state', '=', 'done'),
            ]
            if report.prodlot_id:
                domain.append(('prodlot_id', '=', report.prodlot_id.id))
            else:
                if report.product_id:
                    domain.append(('product_id', '=', report.product_id.id))
                if report.expiry_date:
                    domain.append(('expired_date', '=', report.expiry_date))
            if report.location_id:
                domain.append(('location_id', '=', report.location_id.id))

            context['domain'] = domain

            rsi_ids = rsi_obj.search(cr, uid, domain, context=context)
            if not rsi_ids:
                continue

            self.write(cr, uid, [report.id], {
                'name': time.strftime('%Y-%m-%d %H:%M:%S'),
                'state': 'in_progress',
            })

            datas = {
                'ids': [report.id],
                'lines': rsi_ids,
            }

            cr.commit()
            new_thread = threading.Thread(
                target=self.generate_report_bkg,
                args=(cr, uid, report.id, datas, context)
            )
            new_thread.start()
            new_thread.join(30.0)

            res = {
                'type': 'ir.actions.act_window',
                'res_model': self._name,
                'view_type': 'form',
                'view_mode': 'form,tree',
                'res_id': report.id,
                'context': context,
                'target': 'same',
            }
            if new_thread.isAlive():
                view_id = data_obj.get_object_reference(
                    cr, uid,
                    'specific_rules',
                    'export_report_stock_inventory_info_view')[1]
                res['view_id'] = [view_id]

            return res

        raise osv.except_osv(
            _('Error'),
            _('No inventory lines found for these parameters'),
        )

    def generate_report_bkg(self, cr, uid, ids, datas, context=None):
        """
        Generate the report in background
        """
        if context is None:
            context = {}

        if isinstance(ids, (int, long)):
            ids = [ids]

        import pooler
        new_cr = pooler.get_db(cr.dbname).cursor()

        rp_spool = report_spool()
        result = rp_spool.\
            exp_report(
                cr.dbname, uid,
                'stock.inventory.xls', ids, datas, context)

        file_res = {'state': False}
        while not file_res.get('state'):
            file_res = rp_spool.exp_report_get(cr.dbname, uid, result)
            time.sleep(0.5)
        attachment = self.pool.get('ir.attachment')
        attachment.create(new_cr, uid, {
            'name': 'stock_inventory_%s.xls' % (
                time.strftime('%Y_%m_%d_%H_%M')),
            'datas_fname': 'stock_inventory_%s.xls' % (
                time.strftime('%Y_%m_%d_%H_%M')),
            'description': 'Stock inventory',
            'res_model': 'export.report.stock.inventory',
            'res_id': ids[0],
            'datas': file_res.get('result'),
        })
        self.write(new_cr, uid, ids, {'state': 'ready'}, context=context)

        new_cr.commit()
        new_cr.close(True)

        return True

    def onchange_prodlot(self, cr, uid, ids, prodlot_id):
        """
        Change the product when change the prodlot
        """
        if not prodlot_id:
            return {
                'value': {
                    'product_id': False,
                    'expiry_date': False,
                },
            }

        prodlot = self.pool.get('stock.production.lot').\
            browse(cr, uid, prodlot_id)
        return {
            'value': {
                'product_id': prodlot.product_id.id,
                'expiry_date': prodlot.life_date,
            },
        }

    def create(self, cr, uid, vals, context=None):
        """
        Call onchange_prodlot if a lot is defined
        """
        if vals.get('prodlot_id'):
            vals.update(
                self.onchange_prodlot(
                    cr, uid, False, vals.get('prodlot_id')
                ).get('value', {})
            )

        return super(export_report_stock_inventory, self).\
            create(cr, uid, vals, context=context)

    def write(self, cr, uid, ids, vals, context=None):
        """
        Call onchange_prodlot if a lot is defined
        """
        if vals.get('prodlot_id'):
            vals.update(
                self.onchange_prodlot(
                    cr, uid, ids, vals.get('prodlot_id')
                ).get('value', {})
            )

        return super(export_report_stock_inventory, self).\
            write(cr, uid, ids, vals, context=context)

export_report_stock_inventory()


class parser_report_stock_inventory_xls(report_sxw.rml_parse):

    def __init__(self, cr, uid, name, context=None):
        super(parser_report_stock_inventory_xls, self).\
            __init__(cr, uid, name, context=context)
        self.localcontext.update({
            'time': time,
            'getLines': self.getLines,
        })

    def getLines(self):
        res = {}
        for line in self.pool.get('report.stock.inventory').browse(
            self.cr,
            self.uid,
            self.datas['lines'],
            context=self.localcontext
        ):
            if not line.product_id.default_code in res:
                res[line.product_id.default_code] = {
                    'product_code': line.product_id.default_code,
                    'product_name': line.product_id.name,
                    'uom': line.product_id.uom_id.name,
                    'sum_qty': 0.00,
                    'sum_value': 0.00,
                    'lines': {},
                }

            res[line.product_id.default_code]['sum_qty'] += line.product_qty
            res[line.product_id.default_code]['sum_value'] += line.value
            batch_id = 'no_batch'
            batch_name = ''
            expiry_date = False

            if line.prodlot_id:
                batch_id = line.prodlot_id.id
                batch_name = line.prodlot_id.name
                expiry_date = line.prodlot_id.life_date

            if batch_id not in res[line.product_id.default_code]['lines']:
                res[line.product_id.default_code]['lines'][batch_id] = {
                    'batch': batch_name,
                    'expiry_date': expiry_date,
                    'qty': 0.00,
                    'value': 0.00,
                }

            res[line.product_id.default_code]['lines'][batch_id]['qty'] += line.product_qty
            res[line.product_id.default_code]['lines'][batch_id]['value'] += line.value

        fres = []
        for k in sorted(res.keys()):
            fres.append(res[k])

        return fres


class report_stock_inventory_xls(SpreadsheetReport):

    def __init(self, name, table, rml=False, parser=report_sxw.rml_parse,
               header='external', store=False):
        super(report_stock_inventory_xls, self).__init__(
            name,
            table,
            rml=rml,
            parser=parser,
            header=header,
            store=store)

    def create(self, cr, uid, ids, data, context=None):
        a = super(report_stock_inventory_xls, self).create(
            cr, uid, ids, data, context=context)
        return (a[0], 'xls')

report_stock_inventory_xls(
    'report.stock.inventory.xls',
    'export.report.stock.inventory',
    'addons/specific_rules/report/report_stock_inventory_xls.mako',
    parser=parser_report_stock_inventory_xls,
    header='internal',
)
