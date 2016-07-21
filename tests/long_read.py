#encoding=utf-8

from credentials import *

import re
import sys
import shutil
import os, os.path
import utils
from oerplib import OERP
import credentials


import datetime


#oerp = OERP(server="ct1", database="OCG_LB1_TRP_1707_2227", protocol='xmlrpc', port=8069)
#u = oerp.login("ourOwnDB", "ourOwnDB")

oerp = OERP(server=credentials.SRV_ADDRESS, database="HQ1", protocol='xmlrpc', port=credentials.XMLRPC_PORT)
u = oerp.login(credentials.UNIFIELD_ADMIN, credentials.UNIFIELD_PASSWORD)

avant = datetime.datetime.now()

# example 1
#stock_move = oerp.get('stock.move.in.processor')
#ids = stock_move.read([183, 184, 185, 186, 187, 188, 189, 190, 191, 192, 193, 194, 195, 196, 197, 198, 199, 200, 201, 202, 203, 204, 205, 206, 207, 208, 209, 210, 211, 212], ['line_number', 'currency', 'uom_id', 'cost', 'kc_check', 'ordered_quantity', 'ordered_uom_id', 'composition_list_id', 'asset_id', 'ssl_check', 'type_check', 'location_id', 'np_check', 'ordered_uom_category', 'integrity_status', 'exp_check', 'prodlot_id', 'expiry_date', 'product_id', 'lot_check', 'batch_location_ids', 'dg_check', 'kit_check', 'asset_check', 'quantity', '__last_update'], {'lang': u'en_MF', 'client': 'web', 'tz': False, 'department_id': False})

#exemple 2
stock_move = oerp.get('purchase.order.line')
#ids = stock_move.read([279, 280, 281, 282, 283, 284, 285, 286, 287, 288, 289, 290, 291, 292, 293, 294, 295, 296, 297, 298, 299, 300, 301, 302, 303, 304, 305, 306, 307, 308, 309, 310, 311, 312, 313], ['comment', 'line_number', 'order_state_purchase_order_line', 'product_uom', 'fake_state', 'price_subtotal', 'currency_id', 'nomenclature_description', 'default_code', 'product_qty', 'to_correct_ok', 'supplier_code', 'kit_pol_check', 'po_state_stored', 'rfq_ok', 'analytic_distribution_state_recap', 'soq_updated', 'confirmed_delivery_date', 'kc_dg', 'supplier_name', 'inactive_error', 'internal_code', 'account_4_distribution', 'date_planned', 'default_name', 'internal_name', 'inactive_product', 'tender_line_id', '__last_update'], {'lang': u'en_MF', 'client': 'web', 'tz': False, 'department_id': False})
ids = stock_move.read([279, 280, 281, 282, 283, 284, 285, 286, 287, 288, 289, 290, 291, 292, 293, 294, 295, 296, 297, 298, 299, 300, 301, 302, 303, 304, 305, 306, 307, 308, 309, 310, 311, 312, 313], ['analytic_distribution_state_recap'], {'lang': u'en_MF', 'client': 'web', 'tz': False, 'department_id': False})

apres1 = datetime.datetime.now()

print (apres1 - avant).total_seconds() * 1000


def check(model, fields, ids):

    stock_move = oerp.get(model)
    elements = fields

    before = 0

    for i in xrange(1, len(elements)):

        elem1 = elements[:i]

        avant = datetime.datetime.now()
        ret_ids = stock_move.read(ids, elem1, {'lang': u'en_MF', 'client': 'web', 'tz': False, 'department_id': False})
        apres1 = datetime.datetime.now()

        t1 = (apres1 - avant).total_seconds() * 1000

        print elem1[-1], t1 - before
        before = t1


