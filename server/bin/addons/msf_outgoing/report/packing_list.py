# -*- coding: utf-8 -*-
##############################################################################
#
#    OpenERP, Open Source Management Solution
#    Copyright (C) 2011 MSF, TeMPO Consulting
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
import pooler
from osv import osv
from tools.translate import _
from report import report_sxw
from report_webkit.webkit_report import WebKitParser


def getIds(self, cr, uid, ids, context):
    if context is None:
        context = {}
    if context.get('from_domain') and 'search_domain' in context:
        table_obj = pooler.get_pool(cr.dbname).get(self.table)
        ids = table_obj.search(cr, uid, context.get('search_domain'), limit=5000)
    return ids


class packing_list(report_sxw.rml_parse):
    def __init__(self, cr, uid, name, context=None):
        super(packing_list, self).__init__(cr, uid, name, context=context)
        self.localcontext.update({
            'time': time,
            'getPackingList': self._get_packing_list,
            'getParcel': self._get_parcel,
            'getCompany': self._get_company_info,
        })

    def _get_packing_list(self, shipment):
        '''
        Return a list of PPL with, for each of them, the list of pack family
        that are linked.

        :param shipment: browse_record of a shipment

        :return: A list of tuples with the pre-packing list as first element and
                 the list of linked pack-family as second element
        :rtype: list
        '''
        res = {}
        for pf in shipment.pack_family_memory_ids:
            res.setdefault(pf.ppl_id.name, {
                'ppl': pf.ppl_id,
                'pf': [],
                'last': False,
                'total_volume': 0.00,
                'total_weight': 0.00,
                'nb_parcel': 0,
            })
            if not pf.not_shipped:
                res[pf.ppl_id.name]['pf'].append(pf)
                res[pf.ppl_id.name]['total_volume'] += pf.total_volume
                res[pf.ppl_id.name]['total_weight'] += pf.total_weight
                res[pf.ppl_id.name]['nb_parcel'] += pf.num_of_packs

        sort_keys = sorted(res.keys())

        result = []
        for key in sort_keys:
            result.append(res.get(key))

        result[-1]['last'] = True

        return result

    def _get_parcel(self, list_of_parcels):
        '''
        Return an ordered list of parcel.

        :param list_of_parcel: list of browse_record of pack.family.memory

        :return: An ordered list of browse_record of pack.family.memory
        :rtype: list
        '''
        list_of_parcels.sort(key=lambda p: p.from_pack)
        return list_of_parcels

    def _get_company_info(self, field):
        '''
        Return info from instance's company.

        :param field: Field to read

        :return: Information of the company
        :rtype: str
        '''
        company = self.pool.get('res.users').browse(self.cr, self.uid, self.uid).company_id.partner_id

        if field == 'name':
            return company.name
        else:
            if not company.address:
                return ''

            addr = company.address[0]

            if field == 'addr_name':
                return addr.name
            elif field == 'street':
                return addr.street
            elif field == 'street2':
                return addr.street2
            elif field == 'city':
                zip = ""
                if addr.zip is not False:
                    zip = addr.zip
                return '%s %s' % (zip, addr.city)
            elif field == 'country':
                return addr.country_id and addr.country_id.name or ''
            elif field == 'phone':
                return addr.phone or addr.mobile or ''

        return ''

    def set_context(self, objects, data, ids, report_type=None):
        '''
        opening check
        '''
        #for obj in objects:
            #if not obj.backshipment_id:
                #raise osv.except_osv(_('Warning !'), _('Packing List is only available for Shipment Objects (not draft)!'))

        return super(packing_list, self).set_context(objects, data, ids, report_type=report_type)

report_sxw.report_sxw('report.packing.list', 'shipment', 'addons/msf_outgoing/report/packing_list.rml', parser=packing_list, header="external")


class packing_list_xls(WebKitParser):

    def __init__(self, name, table, rml=False, parser=report_sxw.rml_parse, header='external', store=False):
        WebKitParser.__init__(self, name, table, rml=rml, parser=parser, header=header, store=store)

    def create_single_pdf(self, cr, uid, ids, data, report_xml, context=None):
        report_xml.webkit_debug = 1
        report_xml.header = " "
        report_xml.webkit_header.html = "${_debug or ''|n}"
        return super(packing_list_xls, self).create_single_pdf(cr, uid, ids, data, report_xml, context)

    def create(self, cr, uid, ids, data, context=None):
        ids = getIds(self, cr, uid, ids, context)
        a = super(packing_list_xls, self).create(cr, uid, ids, data, context)
        return (a[0], 'xls')

packing_list_xls('report.packing.list.xls', 'shipment', 'msf_outgoing/report/packing_list_xls.mako', parser=packing_list)
