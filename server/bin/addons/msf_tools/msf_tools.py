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

import time
import tools
import inspect

from tools.translate import _
from dateutil.relativedelta import relativedelta
from datetime import datetime
from datetime import date
from decimal import Decimal, ROUND_UP

import netsvc

from tools import DEFAULT_SERVER_DATE_FORMAT, DEFAULT_SERVER_DATETIME_FORMAT

class lang(osv.osv):
    '''
    define getter for date / time / datetime formats
    '''
    _inherit = 'res.lang'

    def _get_format(self, cr, uid, type, context=None):
        '''
        generic function
        '''
        if context is None:
            context = {}
        type = type + '_format'
        assert type in self._columns, 'Specified format field does not exist'
        user_obj = self.pool.get('res.users')
        # get user context lang
        user_lang = user_obj.read(cr, uid, uid, ['context_lang'], context=context)['context_lang']
        # get coresponding id
        lang_id = self.search(cr, uid, [('code','=',user_lang)])
        # return format value or from default function if not exists
        format = lang_id and self.read(cr, uid, lang_id[0], [type], context=context)[type] or getattr(self, '_get_default_%s'%type)(cr, uid, context=context)
        return format

    def _get_db_format(self, cr, uid, type, context=None):
        '''
        generic function - for now constant values
        '''
        if context is None:
            context = {}
        if type == 'date':
            return '%Y-%m-%d'
        if type == 'time':
            return '%H:%M:%S'
        # default value
        return '%Y-%m-%d'
lang()


class date_tools(osv.osv):
    '''
    date related tools for msf project
    '''
    _name = 'date.tools'

    def get_date_format(self, cr, uid, context=None):
        '''
        get the date format for the uid specified user

        from msf_order_date module
        '''
        lang_obj = self.pool.get('res.lang')
        return lang_obj._get_format(cr, uid, 'date', context=context)

    def get_db_date_format(self, cr, uid, context=None):
        '''
        return constant value
        '''
        lang_obj = self.pool.get('res.lang')
        return lang_obj._get_db_format(cr, uid, 'date', context=context)

    def get_time_format(self, cr, uid, context=None):
        '''
        get the time format for the uid specified user

        from msf_order_date module
        '''
        lang_obj = self.pool.get('res.lang')
        return lang_obj._get_format(cr, uid, 'time', context=context)

    def get_db_time_format(self, cr, uid, context=None):
        '''
        return constant value
        '''
        lang_obj = self.pool.get('res.lang')
        return lang_obj._get_db_format(cr, uid, 'time', context=context)

    def get_datetime_format(self, cr, uid, context=None):
        '''
        get the datetime format for the uid specified user
        '''
        return self.get_date_format(cr, uid, context=context) + ' ' + self.get_time_format(cr, uid, context=context)

    def get_db_datetime_format(self, cr, uid, context=None):
        '''
        return constant value
        '''
        return self.get_db_date_format(cr, uid, context=context) + ' ' + self.get_db_time_format(cr, uid, context=context)

    def get_date_formatted(self, cr, uid, d_type='date', datetime=None, context=None):
        '''
        Return the datetime in the format of the user
        @param d_type: 'date' or 'datetime' : determines which is the out format
        @param datetime: date to format
        '''
        assert d_type in ('date', 'datetime'), 'Give only \'date\' or \'datetime\' as type parameter'

        if not datetime:
            datetime = time.strftime('%Y-%m-%d')

        if d_type == 'date':
            d_format = self.get_date_format(cr, uid)
            date = time.strptime(datetime, '%Y-%m-%d')
            return time.strftime(d_format, date)
        elif d_type == 'datetime':
            d_format = self.get_datetime_format(cr, uid)
            date = time.strptime(datetime, '%Y-%m-%d %H:%M:%S')
            return time.strftime(d_format, date)

    def orm2date(self, dt):
        if isinstance(dt, basestring):
            st = time.strptime(dt, DEFAULT_SERVER_DATE_FORMAT)
            dt = date(st[0], st[1], st[2])
        return dt

    def date2orm(self, dt):
        return dt.strftime(DEFAULT_SERVER_DATE_FORMAT)

    def datetime2orm(self, dt):
        return dt.strftime(DEFAULT_SERVER_DATETIME_FORMAT)

    def orm2datetime(self, dt):
        if isinstance(dt, basestring):
            st = time.strptime(dt, DEFAULT_SERVER_DATETIME_FORMAT)
            dt = datetime(st[0], st[1], st[2], st[3], st[4], st[5])
        return dt

date_tools()


class fields_tools(osv.osv):
    '''
    date related tools for msf project
    '''
    _name = 'fields.tools'

    def get_field_from_company(self, cr, uid, object=False, field=False, context=None):
        '''
        return the value for field from company for object
        '''
        # field is required for value
        if not field:
            return False
        # object
        company_obj = self.pool.get('res.company')
        # corresponding company
        company_id = company_obj._company_default_get(cr, uid, object, context=context)
        # get the value
        res = company_obj.read(cr, uid, [company_id], [field], context=context)[0][field]
        return res

    def get_selection_name(self, cr, uid, object=False, field=False, key=False, context=None):
        '''
        return the name from the key of selection field
        '''
        if not object or not field or not key:
            return False
        # get the selection values list
        if isinstance(object, str):
            object = self.pool.get(object)
        list = object._columns[field].selection
        name = [x[1] for x in list if x[0] == key][0]
        return name

    def get_ids_from_browse_list(self, cr, uid, browse_list=False, context=None):
        '''
        return the list of ids corresponding to browse list in parameter
        '''
        if not browse_list:
            return []

        result = [x.id for x in browse_list]
        return result

    def remove_sql_constraint(self, cr, table_name, field_name):
        """
        remove from field the constraint if it exists in current schema
        (orm does not remove _sql_constraint removed items)
        """
        # table name and constraint name (tablename_fieldname) params
        sql_params = (table_name, "%s_%s" % (table_name, field_name, ), )
        tpl_has_const = "select count(constraint_name) from" \
            " information_schema.constraint_column_usage where" \
            " table_name=%s and constraint_name=%s"
        cr.execute(tpl_has_const, sql_params)
        res_record = cr.fetchone()
        if res_record and res_record[0]:
            # drop existing constraint
            tpl_drop_const = "alter table %s drop constraint %s" % sql_params
            cr.execute(tpl_drop_const)

fields_tools()


class data_tools(osv.osv):
    '''
    data related tools for msf project
    '''
    _name = 'data.tools'

    def load_common_data(self, cr, uid, ids, context=None):
        '''
        load common data into context
        '''
        if context is None:
            context = {}
        context.setdefault('common', {})
        # objects
        date_tools = self.pool.get('date.tools')
        obj_data = self.pool.get('ir.model.data')
        comp_obj = self.pool.get('res.company')
        # date format
        db_date_format = date_tools.get_db_date_format(cr, uid, context=context)
        context['common']['db_date_format'] = db_date_format
        date_format = date_tools.get_date_format(cr, uid, context=context)
        context['common']['date_format'] = date_format
        # date is today
        date = time.strftime(db_date_format)
        context['common']['date'] = date
        # default company id
        company_id = comp_obj._company_default_get(cr, uid, 'stock.picking', context=context)
        context['common']['company_id'] = company_id

        # stock location
        stock_id = obj_data.get_object_reference(cr, uid, 'stock', 'stock_location_stock')[1]
        context['common']['stock_id'] = stock_id
        # kitting location
        kitting_id = obj_data.get_object_reference(cr, uid, 'stock', 'location_production')[1]
        context['common']['kitting_id'] = kitting_id
        # input location
        input_id = obj_data.get_object_reference(cr, uid, 'msf_cross_docking', 'stock_location_input')[1]
        context['common']['input_id'] = input_id
        # quarantine analyze
        quarantine_anal = obj_data.get_object_reference(cr, uid, 'stock_override', 'stock_location_quarantine_analyze')[1]
        context['common']['quarantine_anal'] = quarantine_anal
        # quarantine before scrap
        quarantine_scrap = obj_data.get_object_reference(cr, uid, 'stock_override', 'stock_location_quarantine_scrap')[1]
        context['common']['quarantine_scrap'] = quarantine_scrap
        # log
        log = obj_data.get_object_reference(cr, uid, 'stock_override', 'stock_location_logistic')[1]
        context['common']['log'] = log
        # cross docking
        cross_docking = obj_data.get_object_reference(cr, uid, 'msf_cross_docking', 'stock_location_cross_docking')[1]
        context['common']['cross_docking'] = cross_docking

        # kit reason type
        reason_type_id = obj_data.get_object_reference(cr, uid, 'reason_types_moves', 'reason_type_kit')[1]
        context['common']['reason_type_id'] = reason_type_id
        # reason type goods return
        rt_goods_return = obj_data.get_object_reference(cr, uid, 'reason_types_moves', 'reason_type_goods_return')[1]
        context['common']['rt_goods_return'] = rt_goods_return
        # reason type goods replacement
        rt_goods_replacement = obj_data.get_object_reference(cr, uid, 'reason_types_moves', 'reason_type_goods_replacement')[1]
        context['common']['rt_goods_replacement'] = rt_goods_replacement
        # reason type internal supply
        rt_internal_supply = obj_data.get_object_reference(cr, uid, 'reason_types_moves', 'reason_type_internal_supply')[1]
        context['common']['rt_internal_supply'] = rt_internal_supply

        return True

data_tools()


class sequence_tools(osv.osv):
    '''
    sequence tools
    '''
    _name = 'sequence.tools'

    def reorder_sequence_number(self, cr, uid, base_object, base_seq_field, dest_object, foreign_field, foreign_ids, seq_field, context=None):
        '''
        receive a browse list corresponding to one2many lines
        recompute numbering corresponding to specified field
        compute next number of sequence

        we must make sure we reorder in conservative way according to original order

        *not used presently*
        '''
        # Some verifications
        if context is None:
            context = {}
        if isinstance(foreign_ids, (int, long)):
            foreign_ids = [foreign_ids]

        # objects
        base_obj = self.pool.get(base_object)
        dest_obj = self.pool.get(dest_object)
        seq_obj = self.pool.get('ir.sequence')

        for foreign_id in foreign_ids:
            # will be ordered by default according to db id, it's what we want according to user sequence
            item_ids = dest_obj.search(cr, uid, [(foreign_field, '=', foreign_id)], context=context)
            if item_ids:
                # read line number and id from items
                item_data = dest_obj.read(cr, uid, item_ids, [seq_field], context=context)
                # check the line number: data are ordered according to db id, so line number must be equal to index+1
                for i in range(len(item_data)):
                    if item_data[i][seq_field] != i+1:
                        dest_obj.write(cr, uid, [item_data[i]['id']], {seq_field: i+1}, context=context)
                # reset sequence to length + 1 all time, checking if needed would take much time
                # get the sequence id
                seq_id = base_obj.read(cr, uid, foreign_id, [base_seq_field], context=context)[base_seq_field][0]
                # we reset the sequence to length+1
                self.reset_next_number(cr, uid, [seq_id], value=len(item_ids)+1, context=context)

        return True

    def reorder_sequence_number_from_unlink(self, cr, uid, ids, base_object, base_seq_field, dest_object, foreign_field, seq_field, context=None):
        '''
        receive a browse list corresponding to one2many lines
        recompute numbering corresponding to specified field
        compute next number of sequence

        for unlink, only items with id > min(deleted id) are resequenced + reset the sequence value

        we must make sure we reorder in conservative way according to original order

        this method is called from methods of **destination object**
        '''
        # Some verifications
        if context is None:
            context = {}
        # if no ids as parameter return Tru
        if not ids:
            return True

        # objects
        base_obj = self.pool.get(base_object)
        dest_obj = self.pool.get(dest_object)
        seq_obj = self.pool.get('ir.sequence')

        # find the corresponding base ids
        base_ids = [x[foreign_field][0] for x in dest_obj.read(cr, uid, ids, [foreign_field], context=context) if x[foreign_field]]
        # simulate unique sql
        foreign_ids = set(base_ids)

        for foreign_id in foreign_ids:
            # will be ordered by default according to db id, it's what we want according to user sequence
            # reorder only ids bigger than min deleted + do not select deleted ones
            item_ids = dest_obj.search(cr, uid, [('id', '>', min(ids)), (foreign_field, '=', foreign_id), ('id', 'not in', ids)], context=context)
            # start numbering sequence
            start_num = 0
            # if deleted object is not the first one, we find the numbering value of previous one
            before_ids = dest_obj.search(cr, uid, [('id', '<', min(ids)), (foreign_field, '=', foreign_id)], context=context)
            if before_ids:
                # we read the numbering value of previous value (biggest id)
                start_num = dest_obj.read(cr, uid, max(before_ids), [seq_field], context=context)[seq_field]
            if item_ids:
                # read line number and id from items
                item_data = dest_obj.read(cr, uid, item_ids, [seq_field], context=context)
                # check the line number: data are ordered according to db id, so line number must be equal to index+1
                for i in range(len(item_data)):
                    # numbering value
                    start_num = start_num+1
                    if item_data[i][seq_field] != start_num:
                        cr.execute("update "+dest_obj._table+" set "+seq_field+"=%s where id=%s", (start_num, item_data[i]['id']))
                        #dest_obj.write(cr, uid, [item_data[i]['id']], {seq_field: start_num}, context=context)

            # reset sequence to start_num + 1 all time, checking if needed would take much time
            # get the sequence id
            seq_id = base_obj.read(cr, uid, foreign_id, [base_seq_field], context=context)[base_seq_field][0]
            # we reset the sequence to length+1, whether or not items
            self.reset_next_number(cr, uid, [seq_id], value=start_num+1, context=context)

        return True

    def reset_next_number(self, cr, uid, seq_ids, value=1, context=None):
        '''
        reset the next number of the sequence to value, default value 1
        '''
        # Some verifications
        if context is None:
            context = {}
        if isinstance(seq_ids, (int, long)):
            seq_ids = [seq_ids]

        # objects
        seq_obj = self.pool.get('ir.sequence')
        seq_obj.write(cr, uid, seq_ids, {'number_next': value}, context=context)
        return True

    def create_sequence(self, cr, uid, vals, name, code, prefix='', padding=0, context=None):
        '''
        create a new sequence
        '''
        seq_pool = self.pool.get('ir.sequence')
        seq_typ_pool = self.pool.get('ir.sequence.type')

        assert name, 'create sequence: missing name'
        assert code, 'create sequence: missing code'

        types = {'name': name,
                 'code': code
                 }
        seq_typ_pool.create(cr, uid, types)

        seq = {'name': name,
               'code': code,
               'prefix': prefix,
               'padding': padding,
               }
        return seq_pool.create(cr, uid, seq)

sequence_tools()


class picking_tools(osv.osv):
    '''
    picking related tools
    '''
    _name = 'picking.tools'

    def confirm(self, cr, uid, ids, context=None):
        '''
        confirm the picking
        '''
        # Some verifications
        if context is None:
            context = {}
        if isinstance(ids, (int, long)):
            ids = [ids]

        # objects
        pick_obj = self.pool.get('stock.picking')
        pick_obj.draft_force_assign(cr, uid, ids, context)
        return True

    def check_assign(self, cr, uid, ids, context=None):
        '''
        check assign the picking
        '''
        # Some verifications
        if context is None:
            context = {}
        if isinstance(ids, (int, long)):
            ids = [ids]

        # objects
        pick_obj = self.pool.get('stock.picking')
        pick_obj.action_assign(cr, uid, ids, context)
        return True

    def force_assign(self, cr, uid, ids, context=None):
        '''
        force assign the picking
        '''
        # Some verifications
        if context is None:
            context = {}
        if isinstance(ids, (int, long)):
            ids = [ids]

        # objects
        pick_obj = self.pool.get('stock.picking')
        pick_obj.force_assign(cr, uid, ids, context)
        return True

    def validate(self, cr, uid, ids, context=None):
        '''
        validate the picking
        '''
        # Some verifications
        if context is None:
            context = {}
        if isinstance(ids, (int, long)):
            ids = [ids]

        # objects
        pick_obj = self.pool.get('stock.picking')
        wf_service = netsvc.LocalService("workflow")
        # trigger standard workflow for validated picking ticket
        for id in ids:
            pick_obj.action_move(cr, uid, [id])
            wf_service.trg_validate(uid, 'stock.picking', id, 'button_done', cr)
        return True

    def all(self, cr, uid, ids, context=None):
        '''
        confirm - check - validate
        '''
        self.confirm(cr, uid, ids, context=context)
        self.check_assign(cr, uid, ids, context=context)
        self.validate(cr, uid, ids, context=context)
        return True

picking_tools()


class ir_translation(osv.osv):
    _name = 'ir.translation'
    _inherit = 'ir.translation'

    def tr_view(self, cr, name, context):
        if not context or not context.get('lang'):
            return name
        tr = self._get_source(cr, 1, False, 'view', context['lang'], name, True)
        if not tr:
            # sometimes de view name is empty and so the action name is used as view name
            tr2 = self._get_source(cr, 1, 'ir.actions.act_window,name', 'model', context['lang'], name)
            if tr2:
                return tr2
            return name
        return tr

    @tools.cache(skiparg=3, multi='ids')
    def _get_ids(self, cr, uid, name, tt, lang, ids):
        res = dict.fromkeys(ids, False)
        if ids:
            cr.execute('select res_id,value ' +
                       'from ir_translation ' +
                       'where lang=%s ' +
                       'and type=%s ' +
                       'and name=%s ' +
                       'and res_id IN %s',
                       (lang, tt, name, tuple(ids)))
            for res_id, value in cr.fetchall():
                res[res_id] = value

            #print ids, name
            # US-394: If translation not found by res_id, search by xml_id
            for id in ids:
                if res[id] == False:
                    current_id = id
                    # Get the model name
                    if ',' in name:
                        model_name = name.split(",")[0]
                    else:
                        model_name = name
                    # product.template have not xml_id
                    if "product.template" in model_name:
                        model_name = 'product.product'
                        cr.execute('SELECT id ' +
                                   'FROM product_product ' +
                                   'WHERE product_tmpl_id=%s',
                                   ([current_id]))

                        for prod_id in cr.fetchall():
                            current_id = prod_id

                    # Search xml_id in ir_model_data
                    cr.execute('SELECT name ' +
                               'FROM ir_model_data ' +
                               'WHERE module=\'sd\' and model=%s and res_id=%s',
                               (model_name, current_id))

                    for xml_id in cr.fetchall():
                        # Search in translation by xml_id
                        cr.execute('select res_id, value ' +
                                   'from ir_translation ' +
                                   'where lang=%s ' +
                                   'and type=%s ' +
                                   'and name=%s ' +
                                   'and xml_id=%s',
                                   (lang, tt, name, xml_id))
                        for res_id, value in cr.fetchall():
                            res[id] = value
        return res

    def get_xml_id(self, cr, uid, vals, context=None):
        res = None

        if vals.get('name', False) and vals.get('res_id', False):
            name = vals['name']
            if ',' in name:
                model_name = name.split(",")[0]
            else:
                model_name = name

            if "ir.model.data" not in model_name:
                target_ids = vals['res_id']

                # product.template xml_id is not create, so we search the product.product xml_id
                if "product.template" in model_name:
                    target_ids = self.pool.get('product.product')\
                            .search(cr, uid, [('product_tmpl_id', '=', target_ids),
                                ('active', 'in', ('t', 'f'))], context=context)
                    model_name = 'product.product'

                if isinstance(target_ids, (int, long)):
                    target_ids = [target_ids]
                target = self.pool.get(model_name)
                if target:
                    if hasattr(target, "get_sd_ref"):
                        res = target.get_sd_ref(cr, uid, target_ids).values()[0]
        return res

    def _get_res_id(self, cr, uid, name, sdref, context=None):
        tr_split = name.split(',')
        res_id = self.pool.get('ir.model.data').find_sd_ref(cr, 1, sdref, field='res_id', context=context)
        if res_id and tr_split[0] == 'product.template':
            prod = self.pool.get('product.product').read(cr, 1, [res_id], ['product_tmpl_id'], context=context)[0]
            if prod['product_tmpl_id']:
                return prod['product_tmpl_id'][0]
        return res_id

    # US_394: Remove duplicate lines for ir.translation
    def create(self, cr, uid, vals, clear=True, context=None):
        if context is None:
            context = {}
        domain = []
        # Search xml_id
        if context.get('sync_update_execution') and vals.get('xml_id') and vals.get('name') and not vals.get('res_id'):
            vals['res_id'] = self._get_res_id(cr, uid, vals['name'], vals['xml_id'], context=context)

        if not vals.get('xml_id', False):
            vals['xml_id'] = self.get_xml_id(cr, uid, vals, context=context)

        if vals.get('xml_id') or vals.get('res_id'):
            domain.append('&')
            domain.append('&')

            if vals.get('type') != 'model' and vals.get('src'):
                domain.append(('src', '=', vals['src']))
            if vals.get('lang'):
                domain.append(('lang', '=', vals['lang']))
            if vals.get('name'):
                domain.append(('name', '=', vals['name']))
            if vals.get('xml_id') and vals.get('res_id'):
                domain.append('|')
                domain.append(('xml_id', '=', vals['xml_id']))
                domain.append(('res_id', '=', vals['res_id']))
            elif vals.get('res_id'):
                domain.append(('res_id', '=', vals['res_id']))
            elif vals.get('xml_id'):
                domain.append(('xml_id', '=', vals['xml_id']))

            existing_ids = self.search(cr, uid, domain)
            if existing_ids:
                if len(existing_ids) > 1:
                    ids = existing_ids[0:1]
                    del_ids = existing_ids[1:]
                    self.unlink(cr, uid, del_ids, context=context)
                else:
                    ids = existing_ids
                res = self.write(cr, uid, ids, vals, context=context)
                return ids[0]
        res = super(ir_translation, self).create(cr, uid, vals, clear=clear, context=context)
        return res

    # US_394: add xml_id for each lines
    def add_xml_ids(self, cr, uid, context=None):
        domain = [('type', '=', 'model'), ('xml_id', '=', False)]
        translation_ids = self.search(cr, uid, domain, context=context)
        translation_obj = self.browse(cr, uid, translation_ids, context=context)
        for translation in translation_obj:
            v = {'name': translation.name, 'res_id': translation.res_id}
            xml_id = self.get_xml_id(cr, uid, v, context=context)
            vals = {'xml_id': xml_id}
            self.write(cr, uid, translation['id'], vals, context=context)
        return

    # US_394: remove orphean ir.translation lines
    def clean_translation(self, cr, uid, context=None):
        unlink_ids = []
        domain = [('type', '=', 'model')]
        translation_ids = self.search(cr, uid, domain, context=context)
        translation_obj = self.browse(cr, uid, translation_ids, context=context)
        for translation in translation_obj:
            parent_name = translation.name.split(',')[0]

            obj = self.pool.get(parent_name)
            sql = "SELECT id FROM " + obj._table + \
                  " WHERE id=" + str(translation.res_id)
            cr.execute(sql)
            res = cr.fetchall()
            if not res:
                unlink_ids.append(translation.id)
        if unlink_ids:
            if self.pool.get('sync.client.entity'):
                self.purge(cr, uid, unlink_ids, context=context)
            else:
                self.unlink(cr, uid, unlink_ids, context=context)
        return

ir_translation()


class uom_tools(osv.osv_memory):
    """
    This osv_memory class helps to check certain consistency related to the UOM.
    """
    _name = 'uom.tools'

    def check_uom(self, cr, uid, product_id, uom_id, context=None):
        """
        Check the consistency between the category of the UOM of a product and the category of a UOM.
        Return a boolean value (if false, it will raise an error).
        :param cr: database cursor
        :param product_id: takes the id of a product
        :param product_id: takes the id of a uom
        Note that this method is not consistent with the onchange method that returns a dictionary.
        """
        if context is None:
            context = {}
        if product_id and uom_id:
            if isinstance(product_id, (int, long)):
                product_id = [product_id]
            if isinstance(uom_id, (int, long)):
                uom_id = [uom_id]
            cr.execute(
                """
                SELECT COUNT(*)
                FROM product_uom AS uom,
                    product_template AS pt,
                    product_product AS pp,
                    product_uom AS uom2
                WHERE uom.id = pt.uom_id
                AND pt.id = pp.product_tmpl_id
                AND pp.id = %s
                AND uom2.category_id = uom.category_id
                AND uom2.id = %s""",
                (product_id[0], uom_id[0]))
            count = cr.fetchall()[0][0]
            return count > 0
        return True

uom_tools()


class product_uom(osv.osv):
    _inherit = 'product.uom'

    def _compute_round_up_qty(self, cr, uid, uom_id, qty, context=None):
        '''
        Round up the qty according to the UoM
        '''
        uom = self.browse(cr, uid, uom_id, context=context)
        rounding_value = Decimal(str(uom.rounding).rstrip('0'))

        return float(Decimal(str(qty)).quantize(rounding_value, rounding=ROUND_UP))

    def _change_round_up_qty(self, cr, uid, uom_id, qty, fields=[], result=None, context=None):
        '''
        Returns the error message and the rounded value
        '''
        if not result:
            result = {'value': {}, 'warning': {}}

        if isinstance(fields, str):
            fields = [fields]

        message = {'title': _('Bad rounding'),
                   'message': _('The quantity entered is not valid according to the rounding value of the UoM. The product quantity has been rounded to the highest good value.')}

        if uom_id and qty:
            new_qty = self._compute_round_up_qty(cr, uid, uom_id, qty, context=context)
            if qty != new_qty:
                for f in fields:
                    result.setdefault('value', {}).update({f: new_qty})
                result.setdefault('warning', {}).update(message)

        return result

product_uom()


class finance_tools(osv.osv):
    """
    finance tools
    """
    _name = 'finance.tools'

    def get_orm_date(self, day, month, year=False):
        """
        get date in ORM format
        :type day: int
        :type month: int
        :type year: int (current FY if not provided)
        """
        return "%04d-%02d-%02d" % (year or datetime.now().year, month, day, )

    def check_document_date(self, cr, uid, document_date, posting_date,
        show_date=False, custom_msg=False, context=None):
        """
        US-192 document date check rules
        http://jira.unifield.org/browse/US-192?focusedCommentId=38911&page=com.atlassian.jira.plugin.system.issuetabpanels:comment-tabpanel#comment-38911

        Document date should be included within the fiscal year of
            the posting date it is tied with.
        01/01/FY <= document date <= 31/12/FY

        :type document_date: orm date
        :type posting_date: orm date
        :param show_date: True to display dates in message
        :param custom_msg: str for custom basic message (will cancel show_date)
        :type custom_msg: bool/str
        """
        if not document_date or not posting_date:
            return
        if custom_msg:
            show_date = False

        # initial check that not (posting_date < document_date)
        # like was until 1.0-5
        if posting_date < document_date:
            if custom_msg:
                msg = custom_msg  # optional custom message
            else:
                if show_date:
                    msg = _('Posting date (%s) should be later than' \
                        ' Document Date (%s).') % (posting_date, document_date,)
                else:
                    msg = _(
                        'Posting date should be later than Document Date.')
            raise osv.except_osv(_('Error'), msg)

        # US-192 check
        # 01/01/FY <= document date <= 31/12/FY
        posting_date_obj = self.pool.get('date.tools').orm2date(posting_date)
        check_range_start = self.get_orm_date(1, 1, year=posting_date_obj.year)
        check_range_end = posting_date
        if not (check_range_start <= document_date <= check_range_end):
            if show_date:
                msg = _('Document date (%s) should be in posting date FY') % (
                    document_date, )
            else:
                msg = _('Document date should be in posting date FY')
            raise osv.except_osv(_('Error'), msg)

finance_tools()

