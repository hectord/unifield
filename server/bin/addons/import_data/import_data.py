# -*- coding: utf-8 -*-
##############################################################################
#
#    OpenERP, Open Source Management Solution
#    Copyright (C) 2011 TeMPO Consulting, MSF
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
import csv
import threading
from tempfile import TemporaryFile
import base64
import pooler
import tools
from mx import DateTime
import re
import logging


class import_data(osv.osv_memory):
    _name = 'import_data'
    _description = 'Import Datas'

    def _set_code_name(self, cr, uid, data, row, headers):
        if not data.get('name'):
            data['name'] = row[0]
        if not data.get('code'):
            data['code'] = row[0]

    def _set_nomen_level(self, cr, uid, data, row, headers):

        if data.get('parent_id', False):
            n_obj = self.pool.get('product.nomenclature')
            parent_ids = n_obj.search(cr, uid, [('msfid', '=', data['parent_id'])], limit=1)
            if parent_ids:
                parent_id = parent_ids[0]

                v = self.onChangeParentId(cr, uid, id, data.get('type'),
                                          parent_id)
                if v['value']['level']:
                    data['level'] = v['value']['level']
                data['parent_id'] = parent_id
            else:
                raise osv.except_osv(_('Warning !'),
                                     _('Parent Nomenclature "%s" not found')
                                     % (data['parent_id']))

    def _set_product_category(self, cr, uid, data, row, headers):
        n_obj = self.pool.get('product.nomenclature')
        aa_obj = self.pool.get('account.account')
        context = {}

        family_msfid = data.get('family_id', False)
        if family_msfid:
            nomen_ids = n_obj.search(cr, uid, [('msfid', '=', family_msfid)], limit=1, context=context)
            if nomen_ids:
                data['family_id'] = nomen_ids[0]
            else:
                raise osv.except_osv(_('Warning !'),
                                     _('Product category MSFID "%s" not found')
                                     % (family_msfid))
        else:
            raise osv.except_osv(_('Warning !'),
                                 _('Product category MSFID required'))

        paec_code = data.get('property_account_expense_categ', False)
        if paec_code:
            paec_ids = aa_obj.search(cr, uid, [('code', '=', paec_code)], context=context)
            if paec_ids:
                data['property_account_expense_categ'] = paec_ids[0]
            else:
                raise osv.except_osv(_('Warning !'),
                                     _('Account code "%s" not found')
                                     % (paec_code))
        else:
            data['property_account_expense_categ'] = None

        paic_code = data.get('property_account_income_categ', False)
        if paic_code:
            paic_ids = aa_obj.search(cr, uid, [('code', '=', paic_code)], context=context)
            if paic_ids:
                data['property_account_income_categ'] = paic_ids[0]
            else:
                raise osv.except_osv(_('Warning !'),
                                     _('Account code "%s" not found')
                                     % (paic_code))
        else:
            data['property_account_income_categ'] = None

        dea_code = data.get('donation_expense_account', False)
        if dea_code:
            dea_ids = aa_obj.search(cr, uid, [('code', '=', dea_code)], context=context)
            if dea_ids:
                data['donation_expense_account'] = dea_ids[0]
            else:
                raise osv.except_osv(_('Warning !'),
                                     _('Expense account code "%s" not found')
                                     % (dea_code))
        else:
            data['donation_expense_account'] = None

    def _set_full_path_nomen(self, cr, uid, headers, row, col):
        if not col:
            # modify headers if needed
            for n,h in enumerate(headers):
                m = re.match("^nomen_manda_([0123]).name$", h)
                if m:
                    col[int(m.group(1))] = n
                    headers[n] = "nomen_manda_%s.complete_name"%(m.group(1), )

        if row:
            for manda in sorted(col.keys()):
                if manda != 0:
                    row[col[manda]] = ' | '.join([row[col[manda-1]], row[col[manda]]])
        return col

    def _set_default_value(self, cr, uid, data, row, headers):
        # Create new list of headers with the name of each fields (without dots)
        new_headers = []
        for h in headers:
            if '.' in h:
                new_headers.append(h.split('.')[0])
            else:
                new_headers.append(h)

        # Get the default value
        defaults = self.pool.get('product.product').default_get(cr, uid, new_headers)
        # If no value in file, set the default value
        for h in new_headers:
            if h in defaults and (not h in data or not data[h]):
                data[h] = defaults[h]

    post_hook = {
        'account.budget.post': _set_code_name,
        'product.nomenclature': _set_nomen_level,
        'product.product': _set_default_value,
        'product.category': _set_product_category,
    }

    pre_hook = {
        'product.product': _set_full_path_nomen,
    }

    post_load_hook = {
    }

    def _get_image(self, cr, uid, context=None):
        return self.pool.get('ir.wizard.screen')._get_image(cr, uid)

    _columns = {
        'ignore': fields.integer('Number of headers to ignore', required=True),
        'file': fields.binary('File', required=True),
        'debug': fields.boolean('Debug to server log'),
        'object': fields.selection([
            ('product.nomenclature','Product Nomenclature'),
            ('product.category','Product Category'),
            ('product.product', 'Product'),
            ('res.partner.category','Partner Category'),
            ('res.partner','Partner'),
            ('stock.location','Location'),
            ('stock.warehouse','Warehouse'),
            ('account.analytic.account','Analytic Account'),
            ('crossovered.budget','Budget'),
            ('account.budget.post','Budget Line'),
            ('product.supplierinfo', 'Supplier Info'),
            ], 'Object' ,required=True),
        'config_logo': fields.binary('Image', readonly='1'),
        'import_mode': fields.selection([('update', 'Update'), ('create', 'Create')], string='Update or create ?'),
    }

    _defaults = {
        'ignore': lambda *a : 1,
        'config_logo': _get_image,
        'debug': False,
        'import_mode': lambda *a: 'create',
    }

    def _import(self, cr, uid, ids, context=None, use_new_cursor=True, auto_import=False):
        """if context includes 'import_data_field_max_size' dict,
        this dict specifies the max tolerated field length at import
        (key: field name, value: field size)
        """
        dbname = cr.dbname
        if use_new_cursor:
            cr = pooler.get_db(cr.dbname).cursor()

        if context is None:
            context = {}

        if isinstance(ids, (int, long)):
            ids = [ids]

        processed = []
        rejected = []

        obj = self.read(cr, uid, ids[0])
        import_mode = obj.get('import_mode')

        objname = ""
        for sel in self._columns['object'].selection:
            if sel[0] == obj['object']:
                objname = sel[1]
                break

        fileobj = TemporaryFile('w+')
        fileobj.write(base64.decodestring(obj['file']))
        fileobj.seek(0)
        impobj = self.pool.get(obj['object'])
        delimiter = ";"
        if impobj._name == 'product.nomenclature' or impobj._name == 'product.category':
            delimiter = ","
        reader = csv.reader(fileobj, quotechar='"', delimiter=delimiter)
        headers = []

        if impobj._name == 'product.product':
            # Create the cache
            if not hasattr(self, '_cache'):
                self._cache = {}
            self._cache.setdefault(dbname, {})

            if not hasattr(self.pool.get('product.nomenclature'), '_cache'):
                self.pool.get('product.nomenclature')._cache = {}
            self.pool.get('product.nomenclature')._cache.setdefault(dbname, {})

            # Clear the cache
            self._cache[dbname] = {'product.nomenclature': {'name': {}, 'complete_name': {}},
                                   'product.uom': {'name': {}},
                                   'product.asset.type': {'name': {}},
                                   'product.international.status': {'name': {}},
                                   }
            # Product nomenclature
            cr.execute('SELECT name, id FROM product_nomenclature;')
            for nv in cr.dictfetchall():
                self._cache[dbname]['product.nomenclature']['name'].update({nv['name']: nv['id']})
            # Product category
            cr.execute('SELECT id, family_id FROM product_category;')
            for pc in cr.dictfetchall():
                self.pool.get('product.nomenclature')._cache[dbname].update({pc['family_id']: pc['id']})
            # Product nomenclature complete name
            cr.execute('''SELECT id, name FROM
(
(SELECT
    n0.id, n0.name AS name
FROM product_nomenclature n0
WHERE n0.level = 0)
UNION
(SELECT n1.id, n0.name ||' | '|| n1.name AS name
FROM product_nomenclature n1
  LEFT JOIN product_nomenclature n0 ON n1.parent_id = n0.id
WHERE n1.level = 1)
UNION
(SELECT n2.id, n0.name ||' | '|| n1.name ||' | '|| n2.name AS name
FROM product_nomenclature n1
  LEFT JOIN product_nomenclature n0 ON n1.parent_id = n0.id
  LEFT JOIN product_nomenclature n2 ON n2.parent_id = n1.id
WHERE n2.level = 2)
UNION
(SELECT n3.id, n0.name ||' | '|| n1.name ||' | '|| n2.name ||' | '|| n3.name AS name
FROM product_nomenclature n1
  LEFT JOIN product_nomenclature n0 ON n1.parent_id = n0.id
  LEFT JOIN product_nomenclature n2 ON n2.parent_id = n1.id
  LEFT JOIN product_nomenclature n3 ON n3.parent_id = n2.id
WHERE n3.level = 3)
) AS cn''')
            for cnv in cr.dictfetchall():
                self._cache[dbname]['product.nomenclature']['complete_name'].update({cnv['name']: cnv['id']})
            # Product UoM
            cr.execute('SELECT name, id FROM product_uom;')
            for uv in cr.dictfetchall():
                self._cache[dbname]['product.uom']['name'].update({uv['name']: uv['id']})
            # Asset type
            cr.execute('SELECT name, id FROM product_asset_type;')
            for av in cr.dictfetchall():
                self._cache[dbname]['product.asset.type']['name'].update({av['name']: av['id']})
            # International status
            cr.execute('SELECT name, id FROM product_international_status;')
            for iv in cr.dictfetchall():
                self._cache[dbname]['product.international.status']['name'].update({iv['name']: iv['id']})

        errorfile = TemporaryFile('w+')
        writer = False
        if not auto_import:
            writer = csv.writer(errorfile, quotechar='"', delimiter=';')

        fields_def = impobj.fields_get(cr, uid, context=context)
        i = 0
        while reader and obj['ignore'] > i:
            i += 1
            r = reader.next()
            if r and r[0].split('.')[0] in fields_def:
                headers = r[:]

        def _get_obj(header, value, fields_def):
            list_obj = header.split('.')
            relation = fields_def[list_obj[0]]['relation']
            if impobj._name == 'product.product' and value in self._cache.get(dbname, {}).get(relation, {}).get(list_obj[1], {}):
                return self._cache[dbname][relation][list_obj[1]][value]
            new_obj = self.pool.get(relation)
            newids = new_obj.search(cr, uid, [(list_obj[1], '=', value)], limit=1)
            if not newids:
                # no obj
                raise osv.except_osv(_('Warning !'), _('%s does not exist')%(value,))

            if impobj._name == 'product.product':
                self._cache[dbname].setdefault(relation, {})
                self._cache[dbname][relation].setdefault(list_obj[1], {})
                self._cache[dbname][relation][list_obj[1]][value] = newids[0]
            return newids[0]

        def process_data(field, value, fields_def):
            if not value or field not in fields_def:
                return
            if '.' not in field:
                # type datetime, date, bool, int, float
                if fields_def[field]['type'] == 'boolean':
                    value = value.lower() not in ('0', 'false', 'off','-', 'no', 'n')
                elif fields_def[field]['type'] == 'selection':
                    if impobj == 'product.product' and self._cache[dbname].get('product.product.%s.%s' % (field, value), False):
                        value = self._cache[dbname]['product.product.%s.%s' % (field, value)]
                    else:
                        for key, val in fields_def[field]['selection']:
                            if value.lower() in [tools.ustr(key).lower(), tools.ustr(val).lower()]:
                                value = key
                                if impobj == 'product.product':
                                    self._cache[dbname].setdefault('product.product.%s' % field, {})
                                    self._cache[dbname]['product.product.%s.%s' % (field, value)] = key
                                break
                elif fields_def[field]['type'] == 'date':
                    dt = DateTime.strptime(value,"%d/%m/%Y")
                    value = dt.strftime("%Y-%m-%d")
                elif fields_def[field]['type'] == 'float':
                    # remove space and unbreakable space
                    value = re.sub('[  ]+', '', value)
                    value = float(value.replace(',', '.'))
                return value

            else:
                if fields_def[field.split('.')[0]]['type'] in 'many2one':
                    return _get_obj(field, value, fields_def)

            raise osv.except_osv(_('Warning !'), _('%s does not exist')%(value,))

        def write_error_row(row, index, error=""):
            if not auto_import and writer:
                row.append(error)
                writer.writerow(row)
            else:
                rejected.append((index, row, error))

        i = 1
        nb_error = 0
        nb_succes = 0
        nb_update_success = 0
        col_datas = {}
        if self.pre_hook.get(impobj._name):
            # for headers mod.
            col_datas = self.pre_hook[impobj._name](impobj, cr, uid, headers, {}, col_datas)
        if not auto_import and writer:
            writer.writerow(headers)

        for row in reader:
            newo2m = False
            delimiter = False
            o2mdatas = {}
            i += 1
            if i%101 == 0 and obj['debug']:
                logging.getLogger('import data').info('Object: %s, Item: %s'%(obj['object'],i))

            if not row:
                continue
            empty = True
            for r in row:
                if r:
                    empty = False
                    break
            if empty:
                continue
            data = {}
            try:
                n = 0
                line_ok = True
                if self.pre_hook.get(impobj._name):
                    self.pre_hook[impobj._name](impobj, cr, uid, headers, row, col_datas)

                if impobj._name == 'product.nomenclature' or \
                   impobj._name == 'product.category':
                    import_mode = 'update'

                for n,h in enumerate(headers):
                    row[n] = row[n].rstrip()

                    # UFTP-327
                    # if required reject cells with exceeded field length
                    if 'import_data_field_max_size' in context:
                        if h in context['import_data_field_max_size']:
                            max_size = context['import_data_field_max_size'][h]
                            if len(row[n]) > max_size:
                                msg_tpl = "field '%s' value exceed field length of %d"
                                msg = msg_tpl % (h , max_size, )
                                logging.getLogger('import data').info(
                                    'Error %s'% (msg, ))
                                cr.rollback()
                                error = "Line %s, row: %s, %s" % (i, n, msg, )
                                write_error_row(row, i, error)
                                nb_error += 1
                                line_ok = False
                                break

                    if newo2m and ('.' not in h or h.split('.')[0] != newo2m or h.split('.')[1] == delimiter):
                        data.setdefault(newo2m, []).append((0, 0, o2mdatas.copy()))
                        o2mdatas = {}
                        delimiter = False
                        newo2m = False
                    if '.' not in h:
                        # type datetime, date, bool, int, float
                        value = process_data(h, row[n], fields_def)
                        if value is not None:
                            data[h] = value
                    else:
                        points = h.split('.')
                        if row[n] and fields_def[points[0]]['type'] == 'one2many':
                            newo2m = points[0]
                            delimiter = points[1]
                            new_fields_def = self.pool.get(fields_def[newo2m]['relation']).fields_get(cr, uid, context=context)
                            o2mdatas[points[1]] = process_data('.'.join(points[1:]), row[n], new_fields_def)
                        elif fields_def[points[0]]['type'] in 'many2one':
                            if import_mode == 'update' and not row[n]:
                                data[points[0]] = False
                            elif row[n]:
                                data[points[0]] = _get_obj(h, row[n], fields_def) or False
                        elif fields_def[points[0]]['type'] in 'many2many' and row[n]:
                            data.setdefault(points[0], []).append((4, _get_obj(h, row[n], fields_def)))
                if not line_ok:
                    continue
                if newo2m and o2mdatas:
                    data.setdefault(newo2m, []).append((0, 0, o2mdatas.copy()))

                if self.post_hook.get(impobj._name):
                    self.post_hook[impobj._name](impobj, cr, uid, data, row, headers)

                if import_mode == 'update':

                    # Search if an object already exist. If not, create it.
                    ids_to_update = []

                    if impobj._name == 'product.product':
                        # UF-2254: Allow to update the product, use xmlid_code now for searching
                        ids_to_update = impobj.search(cr, uid, [('xmlid_code',
                            '=', data['xmlid_code'])], order='NO_ORDER')
                    elif impobj._name == 'product.nomenclature':
                        ids_to_update = impobj.search(cr, uid, [('msfid', '=',
                            data['msfid'])], order='NO_ORDER')
                    elif impobj._name == 'product.category':
                        ids_to_update = impobj.search(cr, uid, [('msfid', '=',
                            data['msfid'])], order='NO_ORDER')

                    if ids_to_update:
                        #UF-2170: remove the standard price value from the list for update product case
                        if 'standard_price' in data:
                            del data['standard_price']
                        impobj.write(cr, uid, ids_to_update, data)
                        nb_update_success += 1
                        cr.commit()
                    else:
                        impobj.create(cr, uid, data, context={'from_import_menu': True})
                        nb_succes += 1
                        cr.commit()
                else:
                    impobj.create(cr, uid, data, context={'from_import_menu': True})
                    nb_succes += 1
                    cr.commit()
                processed.append((i, row))
            except osv.except_osv, e:
                logging.getLogger('import data').info('Error %s'%e.value)
                cr.rollback()
                error = "Line %s, row: %s, %s"%(i, n, e.value)
                write_error_row(row, i, error)
                nb_error += 1
            except Exception, e:
                cr.rollback()
                logging.getLogger('import data').info('Error %s'%e)
                error = "Line %s, row: %s, %s"%(i, n, e)
                write_error_row(row, i, error)
                nb_error += 1

        if self.post_load_hook.get(impobj._name):
            self.post_load_hook[impobj._name](impobj, cr, uid)
        fileobj.close()
        if not auto_import:
            import_type = 'Import'
            if import_mode == 'update':
                import_type = 'Update'
                summary = '''Datas Import Summary:
    Object: %s
    Records updated: %s
    Records created: %s
    '''%(objname, nb_update_success, nb_succes)
            else:
                summary = '''Datas Import Summary:
    Object: %s
    Records created: %s
    '''%(objname, nb_succes)

            if nb_error:
                summary += '''Records rejected: %s

    Find in attachment the rejected lines'''%(nb_error)

            request_obj = self.pool.get('res.request')
            req_id = request_obj.create(cr, uid,
                {'name': "%s %s"%(import_type, objname,),
                'act_from': uid,
                'act_to': uid,
                'body': summary,
                })
            if req_id:
                request_obj.request_send(cr, uid, [req_id])

            if nb_error:
                errorfile.seek(0)
                attachment = self.pool.get('ir.attachment')
                attachment.create(cr, uid, {
                    'name': 'rejected-lines.csv',
                    'datas_fname': 'rejected-lines.csv',
                    'description': 'Rejected Lines',
                    'res_model': 'res.request',
                    'res_id': req_id,
                    'datas': base64.encodestring(errorfile.read()),
                })

        if impobj == 'product.product':
            # Clear the cache
            self._cache[dbname] = {}
            self.pool.get('product.nomenclature')._cache[dbname] = {}

        errorfile.close()
        cr.commit()
        if use_new_cursor:
            cr.close(True)

        if auto_import:
            return processed, rejected, headers

    def import_csv(self, cr, uid, ids, context=None):
        thread = threading.Thread(target=self._import, args=(cr, uid, ids, context))
        thread.start()
        return {'type': 'ir.actions.act_window_close'}

import_data()

class import_product(osv.osv_memory):
    _name = 'import_product'
    _inherit = 'import_data'

    _defaults = {
        'object': lambda *a: 'product.product',
    }

    def import_csv(self, cr, uid, ids, context=None):
        # UFTP-327
        fg = self.pool.get('product.product').fields_get(cr, uid,
            fields=['default_code', 'xmlid_code'], context=context)
        if fg and 'default_code' in fg and 'size' in fg['default_code']:
            context['import_data_field_max_size'] = {
                'default_code': fg['default_code']['size'],
                'xmlid_code': fg['xmlid_code']['size'],
            }

        super(import_product, self).import_csv(cr, uid, ids, context=context)
        view_id = self.pool.get('ir.model.data').get_object_reference(cr, uid, 'import_data', 'import_product_end')[1]
        return {'type': 'ir.actions.act_window',
                'res_model': 'import_product',
                'view_mode': 'form',
                'view_type': 'form',
                'view_id': [view_id],
                'target': 'new'}

import_product()


class import_nomenclature(osv.osv_memory):
    _name = 'import_nomenclature'
    _inherit = 'import_data'

    _defaults = {
        'object': lambda *a: 'product.nomenclature',
    }

    def import_csv(self, cr, uid, ids, context=None):
        super(import_nomenclature, self).import_csv(cr, uid, ids, context=context)
        view_id = self.pool.get('ir.model.data').get_object_reference(cr, uid, 'import_data', 'import_nomenclature_end')[1]
        return {'type': 'ir.actions.act_window',
                'res_model': 'import_nomenclature',
                'view_mode': 'form',
                'view_type': 'form',
                'view_id': [view_id],
                'target': 'new'}

import_nomenclature()


class import_product_category(osv.osv_memory):
    _name = 'import_category'
    _inherit = 'import_data'

    _defaults = {
        'object': lambda *a: 'product.category',
    }

    def import_csv(self, cr, uid, ids, context=None):
        super(import_product_category, self).import_csv(cr, uid, ids, context=context)
        view_id = self.pool.get('ir.model.data').get_object_reference(cr, uid, 'import_data', 'import_category_end')[1]
        return {'type': 'ir.actions.act_window',
                'res_model': 'import_category',
                'view_mode': 'form',
                'view_type': 'form',
                'view_id': [view_id],
                'target': 'new'}

import_product_category()


class update_product(osv.osv_memory):
    _name = 'update_product'
    _inherit = 'import_product'

    _defaults = {
        'object': lambda *a: 'product.product',
        'import_mode': lambda *a: 'update',
    }

update_product()

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
