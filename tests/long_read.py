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

avant = datetime.datetime.now()


oerp = OERP(server=credentials.SRV_ADDRESS, database="HQ1", protocol='xmlrpc', port=credentials.XMLRPC_PORT)
u = oerp.login(credentials.UNIFIELD_ADMIN, credentials.UNIFIELD_PASSWORD)
stock_move = oerp.get('stock.move.in.processor')
ids = stock_move.read([183, 184, 185, 186, 187, 188, 189, 190, 191, 192, 193, 194, 195, 196, 197, 198, 199, 200, 201, 202, 203, 204, 205, 206, 207, 208, 209, 210, 211, 212], ['line_number', 'currency', 'uom_id', 'cost', 'kc_check', 'ordered_quantity', 'ordered_uom_id', 'composition_list_id', 'asset_id', 'ssl_check', 'type_check', 'location_id', 'np_check', 'ordered_uom_category', 'integrity_status', 'exp_check', 'prodlot_id', 'expiry_date', 'product_id', 'lot_check', 'batch_location_ids', 'dg_check', 'kit_check', 'asset_check', 'quantity', '__last_update'], {'lang': u'en_MF', 'client': 'web', 'tz': False, 'department_id': False})

#ids = stock_move.read([183, 184, 185, 186, 187, 188, 189, 190, 191, 192, 193, 194, 195, 196, 197, 198, 199, 200, 201, 202, 203, 204, 205, 206, 207, 208, 209, 210, 211, 212], ['line_number', 'currency',  'cost', 'kc_check', 'composition_list_id', 'asset_id', 'ssl_check', 'np_check', 'integrity_status', 'exp_check', 'prodlot_id',  'batch_location_ids', 'dg_check', 'kit_check', 'asset_check', 'quantity', '__last_update'], {'lang': u'en_MF', 'client': 'web', 'tz': False, 'department_id': False})
#'lot_check', batch_location_ids

#object execute ('HQ1', 1, 'admin', u'stock.move.in.processor', 'read', [183, 184, 185, 186, 187, 188, 189, 190, 191, 192, 193, 194, 195, 196, 197, 198, 199, 200, 201, 202, 203, 204, 205, 206, 207, 208, 209, 210, 211, 212], ['line_number', 'currency', 'uom_id', 'cost', 'kc_check', 'ordered_quantity', 'ordered_uom_id', 'composition_list_id', 'asset_id', 'ssl_check', 'type_check', 'location_id', 'np_check', 'ordered_uom_category', 'integrity_status', 'exp_check', 'prodlot_id', 'expiry_date', 'product_id', 'lot_check', 'batch_location_ids', 'dg_check', 'kit_check', 'asset_check', 'quantity', '__last_update'], {'lang': u'en_MF', 'client': 'web', 'tz': False, 'department_id': False})

apres = datetime.datetime.now()

print apres - avant

