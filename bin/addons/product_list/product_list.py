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

import time
import logging


class product_list(osv.osv):
    _name = 'product.list'
    _description = 'Products list'

    def _get_nb_products(self, cr, uid, ids, field_name, arg, context=None):
        '''
        Returns the number of products on the list
        '''
        res = {}

        for list in self.browse(cr, uid, ids, context=context):
            res[list.id] = len(list.product_ids)

        return res

    def write(self, cr, uid, ids, vals, context=None):
        '''
        Adds update date and user information
        '''
        vals.update({
            'reviewer_id': uid,
            'last_update_date': time.strftime('%Y-%m-%d'),
        })

        if vals.get('type') == 'list':
            vals['parent_id'] = False

        return super(product_list, self).\
            write(cr, uid, ids, vals, context=context)

    def copy(self, cr, uid, id, default=None, context=None):
        '''
        Remove the last update date and the reviewer on the new list
        '''
        if not context:
            context = {}

        name = self.browse(cr, uid, id, context=context).name + ' (copy)'

        return super(product_list, self).copy(cr, uid, id, {
            'last_update_date': False,
            'name': name,
            'reviewer_id': False,
        }, context=context)

    _columns = {
        'name': fields.char(
            size=128,
            string='Name',
            required=True,
        ),
        'ref': fields.char(
            size=128,
            string='Ref.',
        ),
        'type': fields.selection(
            selection=[
                ('list', 'List'),
                ('sublist', 'Sublist'),
            ],
            string='Type',
            required=True,
        ),
        'creator': fields.selection(
            selection=[
                ('hq', 'HQ'),
                ('coordo', 'Coordination'),
                ('project', 'Project'),
                ('temp', 'Temporary'),
            ],
            string='Creator',
            required=True,
        ),
        'description': fields.char(
            size=256,
            string='Description',
        ),
        'creation_date': fields.date(
            string='Creation date',
            readonly=True,
        ),
        'last_update_date': fields.date(
            string='Last update date',
            readonly=True,
        ),
        'standard_list_ok': fields.boolean(
            string='Standard List',
        ),
        'order_list_print_ok': fields.boolean(
            string='Order list print',
        ),
        'reviewer_id': fields.many2one(
            'res.users',
            string='Reviewed by',
            readonly=True,
        ),
        'parent_id': fields.many2one(
            'product.list',
            string='Parent list',
        ),
        'warehouse_id': fields.many2one(
            'stock.warehouse',
            string='Warehouse',
        ),
        'location_id': fields.many2one(
            'stock.location',
            string='Stock Location',
        ),
        'product_ids': fields.one2many(
            'product.list.line',
            'list_id',
            string='Products',
        ),
        'old_product_ids': fields.one2many(
            'old.product.list.line',
            'list_id',
            string='Old Products',
        ),
        'nb_products': fields.function(
            _get_nb_products,
            method=True,
            type='integer',
            string='# of products',
        ),

    }

    _defaults = {
        'creation_date': lambda *a: time.strftime('%Y-%m-%d'),
        'creator': lambda *a: 'temp',
    }

    _sql_constraints = [
        ('name_uniq', 'unique (name)', 'A list or sublist with the same name already exists in the system!')
    ]

    def change_parent_list(self, cr, uid, ids, list_id, product_ids, context=None):
        '''
        Check if all products are in the parent list
        '''
        if not list_id:
            return {}

        parent_product_ids = []
        list_brw = self.browse(cr, uid, list_id, context=context)
        for list_line in list_brw.product_ids:
            parent_product_ids.append(list_line.name.id)

        for product in product_ids:
            if product[2]['name'][0] not in parent_product_ids:
                return {
                    'value': {
                        'parent_id': False,
                    },
                    'warning': {
                        'title': _('Not consistent parent list'),
                        'message': _('The selected parent list is not consistent with the products in the list. Please select another parent list or remove the products of the list that are not in the selected parent list before select the parent list.'),
                    }
                }

        return {}


    def change_product_line(self, cr, uid, ids, product_ids, context=None):
        '''
        Refresh the old product list
        '''
        res = {}
        old_products = []
        for list in self.browse(cr, uid, ids, context=context):
            for old_line in list.old_product_ids:
                old_products.append(old_line.id)

            res.update({'old_product_ids': old_products})

        if product_ids:
            res.update({'nb_products': len(product_ids[0][2])})
        else:
            res.update({'nb_products': 0})

        return {'value': res}

    def call_add_products(self, cr, uid, ids, context=None):
        '''
        Call the add multiple products wizard
        '''
        if not context:
            context = {}

        if isinstance(ids, (int, long)):
            ids = [ids]

        for list in self.browse(cr, uid, ids, context=context):
            wiz_id = self.pool.get('product.list.add.products').\
                create(cr, uid, {'list_id': list.id}, context=context)

        return {
            'type': 'ir.actions.act_window',
            'res_model': 'product.list.add.products',
            'res_id': wiz_id,
            'view_type': 'form',
            'view_mode': 'form',
            'target': 'new',
            'context': context,
        }

product_list()


class product_list_line(osv.osv):
    _name = 'product.list.line'
    _description = 'Line of product list'
    _order = 'ref'

    def _get_product(self, cr, uid, ids, context=None):
        return self.pool.get('product.list.line').\
            search(cr, uid, [('name', 'in', ids)], context=context)

    _columns = {
        'name': fields.many2one(
            'product.product',
            string='Product Description',
            required=True,
        ),
        'list_id': fields.many2one(
            'product.list',
            string='List',
            ondelete='cascade',
        ),
        'ref': fields.related(
            'name',
            'default_code',
            string='Product Code',
            readonly=True,
            type='char',
            size=64,
            store={
                'product.product': (
                    _get_product, ['default_code'], 10,
                ),
                'product.list.line': (
                    lambda self, cr, uid, ids, c=None: ids, ['name'], 20,
                ),
            },
        ),
        'comment': fields.char(
            size=256,
            string='Comment',
        ),
    }

    def unlink(self, cr, uid, ids, context=None):
        '''
        Create old product list line on product list line deletion
        '''
        opll = self.pool.get('old.product.list.line')

        if not context:
            context = {}

        if isinstance(ids, (int, long)):
            ids = [ids]

        if not context.get('import_error', False):
            for line in self.read(cr, uid, ids, context=context):
                opll.create(cr, uid, {
                    'removal_date': time.strftime('%Y-%m-%d'),
                    'comment': 'comment' in line and line['comment'] or '',
                    'name': line['name'][0],
                    'list_id': line['list_id'][0],
                }, context=context)

        return super(product_list_line, self).\
            unlink(cr, uid, ids, context=context)

product_list_line()


class old_product_list_line(osv.osv):
    _name = 'old.product.list.line'
    _inherit = 'product.list.line'
    _order = 'removal_date'

    def _get_product(self, cr, uid, ids, context=None):
        opll = self.pool.get('old.product.list.line')
        return opll.search(cr, uid, [('name', 'in', ids)], context=context)

    _columns = {
        'removal_date': fields.date(
            string='Removal date',
            readonly=True,
        ),
        'ref': fields.related(
            'name',
            'default_code',
            string='Product Code',
            readonly=True,
            type='char',
            size=64,
            store={
                'product.product': (
                    _get_product, ['default_code'], 10,
                ),
                'old.product.list.line': (
                    lambda self, cr, uid, ids, c=None: ids, ['name'], 20,
                ),
            },
        ),
    }

    _defaults = {
        'removal_date': lambda *a: time.strftime('%Y-%m-%d'),
    }

old_product_list_line()


class product_product(osv.osv):
    _name = 'product.product'
    _inherit = 'product.product'

    def unlink(self, cr, uid, ids, context=None):
        """
        Check if the unlinked product is not the 'To be defined' product
        """
        try:
            prd_tbd = self.pool.get('ir.model.data').get_object_reference(
                cr, uid, 'msf_doc_import', 'product_tbd')[1]
            if prd_tbd in ids:
                raise osv.except_osv(
                    _('Error'),
                    _("""The product 'To be defined' is an Unifield internal
product and can't be deleted"""),
                )
        except ValueError:
            pass

        return super(product_product, self).unlink(cr, uid, ids, context=context)

    def _get_list_sublist(self, cr, uid, ids, field_name, arg, context=None):
        '''
        Returns all lists/sublists where the product is in
        '''
        pll_obj = self.pool.get('product.list.line')

        if not context:
            context = {}

        if isinstance(ids, (long, int)):
            ids = [ids]

        res = {}

        for product in self.browse(cr, uid, ids, context=context):
            res[product.id] = []
            line_ids = pll_obj.search(cr, uid, [
                ('name', '=', product.id),
            ], context=context)
            for line in pll_obj.browse(cr, uid, line_ids, context=context):
                if line.list_id and line.list_id.id not in res[product.id]:
                    res[product.id].append(line.list_id.id)

        return res

    def _search_list_sublist(self, cr, uid, obj, name, args, context=None):
        '''
        Filter the search according to the args parameter
        '''
        pl_obj = self.pool.get('product.list')

        if not context:
            context = {}

        ids = []

        for arg in args:
            if arg[0] == 'list_ids' and arg[1] == '=' and arg[2]:
                list = pl_obj.browse(cr, uid, int(arg[2]), context=context)
                for line in list.product_ids:
                    ids.append(line.name.id)
            elif arg[0] == 'list_ids' and arg[1] == 'in' and arg[2]:
                for list in pl_obj.browse(cr, uid, arg[2], context=context):
                    for line in list.product_ids:
                        ids.append(line.name.id)
            else:
                return []

        return [('id', 'in', ids)]

    _columns = {
        'list_ids': fields.function(
            _get_list_sublist,
            fnct_search=_search_list_sublist,
            type='many2many',
            relation='product.list',
            method=True,
            string='Lists',
        ),
        # we can't write the default_code required because it is used in the product addons
        # UFTP-327 default_code passed from size 14 to 18
        # http://jira.unifield.org/browse/UFTP-327?focusedCommentId=36173&page=com.atlassian.jira.plugin.system.issuetabpanels:comment-tabpanel#comment-36173
        'default_code': fields.char(
            string='CODE',
            size=18,
            select=True,
        ),
        'msfid': fields.integer(
            string='Hidden field for UniData',
        ),  # US-45: Added this field but hidden, for UniData to be able to import the Id
        'xmlid_code': fields.char(
            'Hidden xmlid code',
            size=18,
        ),  # UF-2254: this code is only used for xml_id purpose, added ONLY when creating the product
    }

    _sql_constraints = [
        (
            'default_code',
            "unique(default_code)",
            'The "Product Code" must be unique',
        ),
        (
            'xmlid_code',
            "unique(xmlid_code)",
            'The xmlid_code must be unique',
        ),
    ]

    def search(self, cr, uid, args, offset=0, limit=None, order=None, context=None, count=False):
        """
        Customize the search() method to include the search of products in a specific list
        """
        pl_obj = self.pool.get('product.list')
        pll_obj = self.pool.get('product.list.line')

        iargs = -1
        for a in args:
            iargs += 1
            if a[0] == 'sublist':
                prd_domain = set()
                pl_ids = pl_obj.search(cr, uid, [
                    ('name', a[1], a[2])
                ], order='NO_ORDER', context=context)
                pll_ids = pll_obj.search(cr, uid, [
                    ('list_id', 'in', pl_ids),
                ], order='NO_ORDER', context=context)
                for line in pll_obj.browse(cr, uid, pll_ids, context=context):
                    prd_domain.add(line.name.id)

                del args[iargs]
                args.append(('id', 'in', list(prd_domain)))

                # In case of no list found or no line in lists, empty list
                if not prd_domain:
                    return []

        return super(product_product, self).search(cr, uid, args, offset,
                limit, order, context, count)

    def write(self, cr, uid, ids, value, context=None):
        single = False
        if isinstance(ids, (long, int)):
            ids = [ids]
            single = True
        if value.get('default_code') and value['default_code'] != 'XXX':
            # do we have any ids with default_code set to 'XXX'
            xxx_ids = self.search(cr, uid, [
                ('id', 'in', ids),
                ('default_code', '=', 'XXX'),
            ], order='NO_ORDER', context=context)
            if xxx_ids:
                self.write(cr, uid, xxx_ids, {
                    'xmlid_code': value['default_code'],
                }, context=context)
        return super(product_product, self).\
            write(cr, uid, single and ids[0] or ids, value, context=context)

product_product()


class product_template(osv.osv):
    _name = 'product.template'
    _inherit = 'product.template'

    # SP-193 : Change field size 60 to 128 digits
    _columns = {
        'name': fields.char(
            size=128,
            string='DESCRIPTION',
            required=True,
            translate=True,
        ),
    }
product_template()

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
