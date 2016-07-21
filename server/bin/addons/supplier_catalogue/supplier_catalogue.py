##############################################################################
# -*- coding: utf-8 -*-
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

from osv import osv
from osv import fields

from tools.translate import _

from mx.DateTime import DateFrom, now, RelativeDate
from datetime import date, datetime

import decimal_precision as dp

import time

import base64
from spreadsheet_xml.spreadsheet_xml import SpreadsheetXML
from spreadsheet_xml.spreadsheet_xml_write import SpreadsheetCreator

_HEADER_TYPE = {type('char'): 'string',
                type(1): 'number',
                type(1.00): 'number',
                type(long(1)): 'number',
                type(now()): 'datetime'}

class supplier_catalogue(osv.osv):
    _name = 'supplier.catalogue'
    _description = 'Supplier catalogue'
    _order = 'period_from, period_to'

    def copy(self, cr, uid, catalogue_id, default=None, context=None):
        '''
        Disallow the possibility to duplicate a catalogue.
        '''
        raise osv.except_osv(_('Error'), _('You cannot duplicate a catalogue because you musn\'t have ' \
                               'overlapped catalogue !'))

        default = default or {}
        default.update({'state': 'draft'})

        return False

    def _update_other_catalogue(self, cr, uid, cat_id, period_from, currency_id, partner_id, period_to=False, context=None):
        '''
        Check if other catalogues with the same partner/currency exist and are defined in the period of the
        new catalogue. If yes, update the period_to of the old catalogue with the period_from - 1 day of
        the new catalogue.
        '''
        if not context:
            context = {}

        if not context.get('cat_ids', False):
            context.update({'cat_ids': []})

        # Add catalogues already written to avoid
        # loops in the same product
        if cat_id:
            context['cat_ids'].append(cat_id)

        # Search other catalogues for the same partner/currency
        # which are overrided by the new catalogue
        equal_ids = self.search(cr, uid, [('id', 'not in', context.get('cat_ids', [])), ('period_from', '=', period_from),
                                                                                        ('currency_id', '=', currency_id),
                                                                                        ('partner_id', '=', partner_id)],
                                                                                        order='period_from asc',
                                                                                        limit=1,
                                                                                        context=context)
        if period_to:
            to_ids = self.search(cr, uid, [('id', 'not in', context.get('cat_ids', [])), ('period_from', '>', period_from),
                                                                                         ('period_from', '<', period_to),
                                                                                         ('currency_id', '=', currency_id),
                                                                                         ('partner_id', '=', partner_id)],
                                                                                         order='period_from asc',
                                                                                         limit=1,
                                                                                         context=context)
        else:
            to_ids = self.search(cr, uid, [('id', 'not in', context.get('cat_ids', [])), ('period_from', '>', period_from),
                                                                                         ('currency_id', '=', currency_id),
                                                                                         ('partner_id', '=', partner_id)],
                                                                                         order='period_from asc',
                                                                                         limit=1,
                                                                                         context=context)

        # If overrided catalogues exist, display an error message
        if equal_ids:
            cat = self.browse(cr, uid, cat_id, context=context)
            if cat and not cat.is_esc:
                # [utp-746] no message for an esc supplier catalogue
                # (no period for an esc supplier catalogue)
                over_cat = self.browse(cr, uid, equal_ids[0], context=context)
                over_cat_from = self.pool.get('date.tools').get_date_formatted(cr, uid, d_type='date', datetime=over_cat.period_from, context=context)
                over_cat_to = self.pool.get('date.tools').get_date_formatted(cr, uid, d_type='date', datetime=over_cat.period_to, context=context)
                raise osv.except_osv(_('Error'), _('This catalogue has the same \'From\' date than the following catalogue : %s (\'From\' : %s - \'To\' : %s) - ' \
                                                   'Please change the \'From\' date of this new catalogue or delete the other catalogue.') % (over_cat.name, over_cat_from, over_cat_to))

        # If overrided catalogues exist, display an error message
        if to_ids:
            over_cat = self.browse(cr, uid, to_ids[0], context=context)
            over_cat_from = self.pool.get('date.tools').get_date_formatted(cr, uid, d_type='date', datetime=over_cat.period_from, context=context)
            over_cat_to = self.pool.get('date.tools').get_date_formatted(cr, uid, d_type='date', datetime=over_cat.period_to, context=context)
            raise osv.except_osv(_('Error'), _('The \'To\' date of this catalogue is older than the \'From\' date of another catalogue - ' \
                                               'Please change the \'To\' date of this catalogue or the \'From\' date of the following ' \
                                               'catalogue : %s (\'From\' : %s - \'To\' : %s)') % (over_cat.name, over_cat_from, over_cat_to))

        # Search all catalogues with the same partner/currency which are done
        # after the beginning of the new catalogue
        from_update_ids = self.search(cr, uid, [('id', 'not in', context.get('cat_ids', [])), ('currency_id', '=', currency_id),
                                                                                              ('partner_id', '=', partner_id),
                                                                                              ('period_from', '<=', period_from),
                                                                                              '|',
                                                                                              ('period_to', '>=', period_from),
                                                                                              ('period_to', '=', False)],
                                                                                              order='NO_ORDER', context=context)

        # Update these catalogues with an end date which is the start date - 1 day of
        # the new catalogue
        if isinstance(period_from, date):
            period_from = period_from.strftime('%Y-%m-%d')
        period_from = DateFrom(period_from) + RelativeDate(days=-1)
        self.write(cr, uid, from_update_ids, {'period_to': period_from.strftime('%Y-%m-%d')}, context=context)

        return True

    def create(self, cr, uid, vals, context=None):
        '''
        Check if the new values override a catalogue
        '''
        if context is None:
            context = {}

        # Check if other catalogues need to be updated because they finished
        # after the starting date of the new catalogue.
        if vals.get('active', True):
            self._update_other_catalogue(cr, uid, None, vals.get('period_from', False),
                                                        vals.get('currency_id', False),
                                                        vals.get('partner_id', context.get('partner_id', False)),
                                                        vals.get('period_to', False), context=context)
        res = super(supplier_catalogue, self).create(cr, uid, vals, context=context)

        # UTP-746: now check if the partner is inactive, then set this catalogue also to become inactive
        catalogue = self.browse(cr, uid, [res], context=context)[0]
        if not catalogue.partner_id.active:
            self.write(cr, uid, [res], {'active': False}, context=context)

        return res

    def write(self, cr, uid, ids, vals, context=None):
        '''
        Update the supplierinfo and pricelist line according to the
        new values
        '''
        supinfo_obj = self.pool.get('product.supplierinfo')
        price_obj = self.pool.get('pricelist.partnerinfo')
        user_obj = self.pool.get('res.users')

        if context is None:
            context = {}

        to_be_confirmed = False
        for catalogue in self.browse(cr, uid, ids, context=context):

            # Check if other catalogues need to be updated because they finished
            # after the starting date of the updated catalogue.
            if vals.get('active', catalogue.active):
                self._update_other_catalogue(cr, uid, catalogue.id, vals.get('period_from', catalogue.period_from),
                                                                    vals.get('currency_id', catalogue.currency_id.id),
                                                                    vals.get('partner_id', catalogue.partner_id.id),
                                                                    vals.get('period_to', catalogue.period_to), context=context)

            current_partner_id = user_obj.browse(cr, uid, uid, context=context).company_id.partner_id.id
            if 'partner_id' in vals and vals['partner_id'] != catalogue.partner_id.id:
                if vals['partner_id'] == current_partner_id:
                    # If the new partner is the instance partner, remove the supplier info
                    supplierinfo_ids = supinfo_obj.search(cr, uid,
                            [('catalogue_id', 'in', ids)], order='NO_ORDER', context=context)
                    supinfo_obj.unlink(cr, uid, supplierinfo_ids, context=context)
                elif catalogue.partner_id.id == current_partner_id:
                    # If the catalogue was for teh instance partner, set it to False, then confirm it again
                    to_be_confirmed.append(catalogue.id)

            # Update product pricelists only if the catalogue is confirmed
            if vals.get('state', catalogue.state) == 'confirmed' and not to_be_confirmed:
                new_supinfo_vals = {}

                # Change the partner of all supplier info instances
                if 'partner_id' in vals and vals['partner_id'] != catalogue.partner_id.id:
                    delay = self.pool.get('res.partner').browse(cr, uid, vals['partner_id'], context=context).default_delay
                    new_supinfo_vals.update({'name': vals['partner_id'],
                                             'delay': delay})

                # Change pricelist data according to new data
                new_price_vals = {'valid_till': vals.get('period_to', None),
                                  'valid_from': vals.get('period_from', catalogue.period_from),
                                  'currency_id': vals.get('currency_id', catalogue.currency_id.id),
                                  'name': vals.get('name', catalogue.name),}

                # utp1033 optimisation
                pricelist_ids = []
                #for line in catalogue.line_ids:
                #    if line.partner_info_id:
                #        pricelist_ids.append(line.partner_info_id.id)
                cr.execute('''select partner_info_id from supplier_catalogue_line where catalogue_id = %s ''' % (ids[0]))
                pricelist_ids += [x[0] for x in cr.fetchall() if x[0] is not None]
                #pricelist_ids =  cr.fetchall()  returns tuples - may be a problem
                # Update the supplier info and price lines
                supplierinfo_ids = supinfo_obj.search(cr, uid,
                        [('catalogue_id', 'in', ids)], order='NO_ORDER', context=context)
                supinfo_obj.write(cr, uid, supplierinfo_ids, new_supinfo_vals, context=context)
                price_obj.write(cr, uid, pricelist_ids, new_price_vals, context=context)

        res = super(supplier_catalogue, self).write(cr, uid, ids, vals, context=context)

        # Confirm the catalogue in case of partner change from instance partner to other partner
        if to_be_confirmed:
            self.button_draft(cr, uid, to_be_confirmed, context=context)
            self.button_confirm(cr, uid, to_be_confirmed, context=context)

        return res

    def button_confirm(self, cr, uid, ids, context=None):
        '''
        Confirm the catalogue and all lines
        '''
        ids = isinstance(ids, (int, long)) and [ids] or ids
        line_obj = self.pool.get('supplier.catalogue.line')

        line_ids = line_obj.search(cr, uid, [('catalogue_id', 'in', ids)],
                order='NO_ORDER', context=context)

        if not all(x['state'] == 'draft' for x in self.read(cr, uid, ids, ['state'], context=context)):
            raise osv.except_osv(_('Error'), _('The catalogue you try to confirm is already confirmed. Please reload the page to update the status of this catalogue'))

        # Update catalogues
        self.write(cr, uid, ids, {'state': 'confirmed'}, context=context)
        # Update lines
        line_obj.write(cr, uid, line_ids, {}, context=context)

        return True

    def button_draft(self, cr, uid, ids, context=None):
        '''
        Reset to draft the catalogue
        '''
        ids = isinstance(ids, (int, long)) and [ids] or ids
        #line_obj = self.pool.get('supplier.catalogue.line')

        #line_ids = line_obj.search(cr, uid, [('catalogue_id', 'in', ids)], context=context)

        if not all(x['state'] == 'confirmed' for x in self.read(cr, uid, ids, ['state'], context=context)):
            raise osv.except_osv(_('Error'), _('The catalogue you try to confirm is already in draft state. Please reload the page to update the status of this catalogue'))

        # Update catalogues
        self.write(cr, uid, ids, {'state': 'draft'}, context=context)

        # Update lines
        #line_obj.write(cr, uid, line_ids, {}, context=context)
        #utp1033
        cr.execute('''delete from pricelist_partnerinfo
                      where id in (select partner_info_id
                                    from supplier_catalogue_line
                                    where catalogue_id = %s)''' % (ids[0]))
        cr.execute('''delete from product_supplierinfo
                        where id in (select supplier_info_id
                                    from supplier_catalogue_line
                                     where catalogue_id = %s)
                        and id not in (select suppinfo_id from
                                    pricelist_partnerinfo ) ''' % (ids[0]))


        return True

    def name_get(self, cr, uid, ids, context=None):
        '''
        Add currency to the name of the catalogue
        '''
        res = []

        for r in self.browse(cr, uid, ids, context=context):
            res.append((r.id, '%s (%s)' % (r.name, r.currency_id.name)))

        return res

    def _search(self, cr, uid, args, offset=0, limit=None, order=None, context=None, count=False, access_rights_uid=None):
        '''
        If the search is called from the catalogue line list view, returns only catalogues of the
        partner defined in the context
        '''
        if not context:
            context = {}

        if context.get('search_default_partner_id', False):
            args.append(('partner_id', '=', context.get('search_default_partner_id', False)))

        return super(supplier_catalogue, self)._search(cr, uid, args, offset,
                limit, order, context, count, access_rights_uid)

    def _get_active(self, cr, uid, ids, field_name, arg, context=None):
        '''
        Return True if today is into the period of the catalogue
        '''
        res = {}

        for catalogue in self.browse(cr, uid, ids, context=context):
            date_from = DateFrom(catalogue.period_from)
            date_to = DateFrom(catalogue.period_to)
            res[catalogue.id] = date_from < now() < date_to

        return res

    def _search_active(self, cr, uid, obj, name, args, context=None):
        '''
        Returns all active catalogues
        '''
        ids = []

        for arg in args:
            if arg[0] == 'current' and arg[1] == '=':
                ids = self.search(cr, uid, [('period_from', '<', date.today()),
                                            ('period_to', '>', date.today())], context=context)
                return [('id', 'in', ids)]
            elif arg[0] == 'current' and arg[1] == '!=':
                ids = self.search(cr, uid, ['|', ('period_from', '>', date.today()),
                                                 ('period_to', '<', date.today())], context=context)
                return [('id', 'in', ids)]

        return ids

    def _is_esc_from_partner_id(self, cr, uid, partner_id, context=None):
        """Is an ESC Supplier Catalog ? (from partner id)"""
        if not partner_id:
            return False
        rs = self.pool.get('res.partner').read(cr, uid, [partner_id],
                                               ['partner_type'],
                                               context=context)
        if rs and rs[0] and rs[0]['partner_type'] \
           and rs[0]['partner_type'] == 'esc':
                return True
        return False

    def _is_esc(self, cr, uid, ids, fieldname, args, context=None):
        """Is an ESC Supplier Catalog ?"""
        res = {}
        if not ids:
            return res
        if isinstance(ids, (int, long)):
            ids = [ids]
        for r in self.read(cr, uid, ids, ['partner_id'],
                            context=context):
            res[r['id']] = False
            if r['partner_id']:
                res[r['id']] = self._is_esc_from_partner_id(cr, uid,
                                                    r['partner_id'][0],
                                                    context=context)

        return res

    _columns = {
        'name': fields.char(size=64, string='Name', required=True),
        'partner_id': fields.many2one('res.partner', string='Partner', required=True,
                                      domain=[('supplier', '=', True)]),
        'period_from': fields.date(string='From',
                                   help='Starting date of the catalogue.'),
        'period_to': fields.date(string='To',
                                 help='End date of the catalogue'),
        'currency_id': fields.many2one('res.currency', string='Currency', required=True,
                                       help='Currency used in this catalogue.'),
        'comment': fields.text(string='Comment'),
        'line_ids': fields.one2many('supplier.catalogue.line', 'catalogue_id', string='Lines'),
        'supplierinfo_ids': fields.one2many('product.supplierinfo', 'catalogue_id', string='Supplier Info.'),
        'active': fields.boolean(string='Active'),
        'current': fields.function(_get_active, fnct_search=_search_active, method=True, string='Active', type='boolean', store=False,
                                   readonly=True, help='Indicate if the catalogue is currently active.'),
        'file_to_import': fields.binary(string='File to import', filters='*.xml',
                                        help="""The file should be in XML Spreadsheet 2003 format. The columns should be in this order :
                                        Product Code*, Product Description, Product UoM*, Min Quantity*, Unit Price*, SoQ Rounding, Min Order Qty, Comment."""),
        'data': fields.binary(string='File with errors',),
        'filename': fields.char(string='Lines not imported', size=256),
        'filename_template': fields.char(string='Template', size=256),
        'import_error_ok': fields.boolean('Display file with error'),
        'text_error': fields.text('Text Error', readonly=True),
        'esc_update_ts': fields.datetime('Last updated on', readonly=True),  # UTP-746 last update date for ESC Supplier
        'is_esc': fields.function(_is_esc, type='boolean', string='Is ESC Supplier', method=True),
        'state': fields.selection([('draft', 'Draft'), ('confirmed', 'Confirmed')], string='State', required=True, readonly=True),
    }

    _defaults = {
        # By default, use the currency of the user
        'currency_id': lambda obj, cr, uid, ctx: obj.pool.get('res.users').browse(cr, uid, uid, context=ctx).company_id.currency_id.id,
        'partner_id': lambda obj, cr, uid, ctx: ctx.get('partner_id', False),
        'period_from': lambda *a: time.strftime('%Y-%m-%d'),
        'active': lambda *a: True,
        'filename_template': 'template.xls',
        'state': lambda *a: 'draft',
    }

    def _check_period(self, cr, uid, ids):
        '''
        Check if the To date is older than the From date
        '''
        for catalogue in self.browse(cr, uid, ids):
            if catalogue.period_to and catalogue.period_to < catalogue.period_from:
                return False
        return True

    _constraints = [(_check_period, 'The \'To\' date mustn\'t be younger than the \'From\' date !', ['period_from', 'period_to'])]

    def open_lines(self, cr, uid, ids, context=None):
        '''
        Opens all lines of this catalogue
        '''
        if isinstance(ids, (int, long)):
            ids = [ids]
        if context is None:
            context = {}

        cat = self.browse(cr, uid, ids[0], context=context)
        name = '%s - %s' % (cat.partner_id.name, cat.name)

        context.update({'search_default_partner_id': cat.partner_id.id,})

        view_id = self.pool.get('ir.model.data').get_object_reference(cr, uid, 'supplier_catalogue', 'non_edit_supplier_catalogue_line_tree_view')[1]

        return {'type': 'ir.actions.act_window',
                'name': name,
                'res_model': 'supplier.catalogue.line',
                'view_type': 'form',
                'view_mode': 'tree,form',
                'view_id': [view_id],
                'domain': [('catalogue_id', '=', ids[0])],
                'context': context}

    def edit_catalogue(self, cr, uid, ids, context=None):
        '''
        Open an edit view of the selected catalogue
        '''
        if context is None:
            context = {}
        if isinstance(ids, (int, long)):
            ids = [ids]

        return {'type': 'ir.actions.act_window',
                'res_model': 'supplier.catalogue',
                'view_type': 'form',
                'view_mode': 'form',
                'res_id': ids[0],
                'context': context}

    def export_file_with_error(self, cr, uid, ids, *args, **kwargs):
        """
        Export lines with errors in a file.
        Warning: len(columns_header) == len(lines_not_imported)
        """
        columns_header = [('Product code*', 'string'), ('Product description', 'string'), ('Product UoM*', 'string'),
                          ('Min Quantity*', 'number'), ('Unit Price*', 'number'), ('SoQ Rounding', 'number'), ('Min Order Qty', 'number'),
                          ('Comment', 'string')]
        lines_not_imported = [] # list of list
        t_dt = type(now())
        for line in kwargs.get('line_with_error'):
            for f in line:
                if type(f) == t_dt:
                    new_f = f.strftime('%Y-%m-%dT%H:%M:%S.000')
                    line[line.index(f)] = (new_f, 'DateTime')
                elif isinstance(f, str) and 0 <= line.index(f) < len(columns_header) and columns_header[line.index(f)][1] != 'string':
                    try:
                        line[line.index(f)] = (float(f), 'Number')
                    except:
                        line[line.index(f)] = (f, 'String')

            if len(line) < len(columns_header):
                lines_not_imported.append(line + ['' for x in range(len(columns_header)-len(line))])
            else:
                lines_not_imported.append(line)

        files_with_error = SpreadsheetCreator('Lines with errors', columns_header, lines_not_imported)
        vals = {'data': base64.encodestring(files_with_error.get_xml(['decode.utf8'])),
                'filename': 'Lines_Not_Imported.xls',
                'import_error_ok': True}
        return vals

    def catalogue_import_lines(self, cr, uid, ids, context=None):
        '''
        Import the catalogue lines
        '''
        if not context:
            context = {}
        vals = {}
        vals['line_ids'], error_list, line_with_error = [], [], []
        msg_to_return = _("All lines successfully imported")
        ignore_lines = 0

        product_obj = self.pool.get('product.product')
        uom_obj = self.pool.get('product.uom')
        obj_data = self.pool.get('ir.model.data')
        wiz_common_import = self.pool.get('wiz.common.import')
        obj_catalog_line = self.pool.get('supplier.catalogue.line')

        date_format = self.pool.get('date.tools').get_db_date_format(cr, uid, context=context)

        for obj in self.browse(cr, uid, ids, context=context):
            if not obj.file_to_import:
                raise osv.except_osv(_('Error'), _('Nothing to import.'))

            fileobj = SpreadsheetXML(xmlstring=base64.decodestring(obj.file_to_import))
            rows,reader = fileobj.getRows(), fileobj.getRows() # because we got 2 iterations
            # take all the lines of the file in a list of dict
            file_values = wiz_common_import.get_file_values(cr, uid, ids, rows, False, error_list, False, context)

            reader.next()
            line_num = 1
            for row in reader:
                error_list_line = []
                to_correct_ok = False
                row_len = len(row)
                if row_len != 8:
                    error_list_line.append(_("You should have exactly 8 columns in this order: Product code*, Product description, Product UoM*, Min Quantity*, Unit Price*, SoQ Rounding, Min Order Qty, Comment."))
                comment = []
                p_comment = False
                #Product code
                try:
                    product_code = row.cells[0].data
                except TypeError:
                    product_code = row.cells[0].data
                except ValueError:
                    product_code = row.cells[0].data
                if not product_code or row.cells[0].type != 'str':
                    default_code = obj_data.get_object_reference(cr, uid, 'msf_doc_import','product_tbd')[1]
                    to_correct_ok = True
                    error_list_line.append(_("The product was not defined properly."))
                else:
                    try:
                        product_code = product_code.strip()
                        code_ids = product_obj.search(cr, uid, [('default_code', '=', product_code)])
                        if not code_ids:
                            default_code = obj_data.get_object_reference(cr, uid, 'msf_doc_import','product_tbd')[1]
                            to_correct_ok = True
                            error_list_line.append(_("The product '%s' was not found.") % product_code)
                        else:
                            default_code = code_ids[0]
                    except Exception:
                         default_code = obj_data.get_object_reference(cr, uid, 'msf_doc_import','product_tbd')[1]
                         to_correct_ok = True
                         error_list_line.append(_("The product '%s' was not found.") % product_code)

                #Product UoM
                p_uom = len(row.cells)>=3 and row.cells[2].data
                if not p_uom:
                    uom_id = obj_data.get_object_reference(cr, uid, 'msf_doc_import','uom_tbd')[1]
                    to_correct_ok = True
                    error_list_line.append(_("The UoM '%s' was not found.") % p_uom)
                else:
                    try:
                        uom_name = p_uom.strip()
                        uom_ids = uom_obj.search(cr, uid, [('name', '=', uom_name)], context=context)
                        if not uom_ids:
                            uom_id = obj_data.get_object_reference(cr, uid, 'msf_doc_import','uom_tbd')[1]
                            error_list_line.append(_("The UoM '%s' was not found.") % uom_name)
                            to_correct_ok = True
                        else:
                            uom_id = uom_ids[0]
                    except Exception:
                         uom_id = obj_data.get_object_reference(cr, uid, 'msf_doc_import','uom_tbd')[1]
                         error_list_line.append(_("The UoM '%s' was not found.") % p_uom)
                         to_correct_ok = True
                #[utp-129]: check consistency of uom
                # I made the check on uom_id according to the constraint _check_uom in unifield-addons/product/product.py (l.744) so that we keep the consistency even when we create a supplierinfo directly from the product
                if default_code != obj_data.get_object_reference(cr, uid, 'msf_doc_import','product_tbd')[1]:
                    if not self.pool.get('uom.tools').check_uom(cr, uid, default_code, uom_id, context):
                        browse_uom = uom_obj.browse(cr, uid, uom_id, context)
                        browse_product = product_obj.browse(cr, uid, default_code, context)
                        uom_id = browse_product.uom_id.id
                        to_correct_ok = True
                        error_list_line.append(_('The UoM "%s" was not consistent with the UoM\'s category ("%s") of the product "%s".'
                                            ) % (browse_uom.name, browse_product.uom_id.category_id.name, browse_product.default_code))

                #Product Min Qty
                if not len(row.cells)>=4 or not row.cells[3].data :
                    p_min_qty = 1.0
                else:
                    if row.cells[3].type in ['int', 'float']:
                        p_min_qty = row.cells[3].data
                    else:
                        error_list_line.append(_('Please, format the line number %s, column "Min Qty".') % (line_num,))

                #Product Unit Price
                if not len(row.cells)>=5 or not row.cells[4].data :
                    p_unit_price = 1.0
                    to_correct_ok = True
                    comment.append('Unit Price defined automatically as 1.00')
                else:
                    if row.cells[4].type in ['int', 'float']:
                        p_unit_price = row.cells[4].data
                    else:
                        error_list_line.append(_('Please, format the line number %s, column "Unit Price".') % (line_num,))

                #Product Rounding
                if not len(row.cells)>=6 or not row.cells[5].data:
                    p_rounding = False
                else:
                    if row.cells[5] and row.cells[5].type in ['int', 'float']:
                        p_rounding = row.cells[5].data
                    else:
                        error_list_line.append(_('Please, format the line number %s, column "SoQ rounding".') % (line_num,))

                #Product Min Order Qty
                if not len(row.cells)>=7 or not row.cells[6].data:
                    p_min_order_qty = 0
                else:
                    if row.cells[6].type in ['int', 'float']:
                        p_min_order_qty = row.cells[6].data
                    else:
                        error_list_line.append(_('Please, format the line number %s, column "Min Order Qty".') % (line_num,))

                #Product Comment
                if len(row.cells)>=8 and row.cells[7].data:
                    comment.append(str(row.cells[7].data))
                if comment:
                    p_comment = ', '.join(comment)

                if error_list_line:
                    error_list_line.insert(0, _('Line %s of the file was exported in the file of the lines not imported:') % (line_num,))
                    data = file_values[line_num].items()
                    line_with_error.append([v for k,v in sorted(data, key=lambda tup: tup[0])])
                    ignore_lines += 1
                    line_num += 1
                    error_list.append('\n -'.join(error_list_line) + '\n')
                    continue
                line_num += 1

               # [utp-746] update prices of an already product in catalog
                criteria = [
                    ('catalogue_id', '=', obj.id),
                    ('product_id', '=', default_code),
                ]
                catalog_line_id = obj_catalog_line.search(cr, uid, criteria, context=context)
                if catalog_line_id:
                    if isinstance(catalog_line_id, (int, long)):
                        catalog_line_id = [catalog_line_id]
                    # update product in catalog only if any modification
                    # and only modified fields (for sync)
                    cl_obj = obj_catalog_line.browse(cr, uid, catalog_line_id[0], context=context)
                    if cl_obj:
                        to_write = {}
                        if cl_obj.min_qty != p_min_qty:
                            to_write['min_qty'] = p_min_qty
                        if cl_obj.line_uom_id.id != uom_id:
                            to_write['line_uom_id'] = uom_id
                        if cl_obj.unit_price != p_unit_price:
                            to_write['unit_price'] = p_unit_price
                        if cl_obj.rounding != p_rounding:
                            to_write['rounding'] = p_rounding
                        if cl_obj.min_order_qty != p_min_order_qty:
                            to_write['min_order_qty'] = p_min_order_qty
                        if cl_obj.comment != p_comment:
                            to_write['comment'] = p_comment
                        if to_write:
                            vals['line_ids'].append((1, catalog_line_id[0], to_write))
                else:
                    to_write = {
                        'to_correct_ok': to_correct_ok,
                        'product_id': default_code,
                        'min_qty': p_min_qty,
                        'line_uom_id': uom_id,
                        'unit_price': p_unit_price,
                        'rounding': p_rounding,
                        'min_order_qty': p_min_order_qty,
                        'comment': p_comment,
                    }
                    vals['line_ids'].append((0, 0, to_write))

            # in case of lines ignored, we notify the user and create a file with the lines ignored
            vals.update({'text_error': _('Lines ignored: %s \n ----------------------\n') % (ignore_lines,) +
                         '\n'.join(error_list), 'data': False, 'import_error_ok': False,
                         'file_to_import': False})
            if line_with_error:
                file_to_export = self.export_file_with_error(cr, uid, ids, line_with_error=line_with_error)
                vals.update(file_to_export)
            vals['esc_update_ts'] = datetime.now().strftime(date_format)
            self.write(cr, uid, ids, vals, context=context)

            # TODO: To implement


            #res_id = self.pool.get('catalogue.import.lines').create(cr, uid, {'catalogue_id': ids[0]}, context=context)
            if any([line for line in obj.line_ids if line.to_correct_ok]) or line_with_error:
                msg_to_return = _("The import of lines had errors, please correct the red lines below")

        return self.log(cr, uid, obj.id, msg_to_return,)

    def clear_error(self, cr, uid, ids, context=None):
        '''
        Remove the error list and the file with lines in error
        '''
        vals = {'data': False, 'text_error': '', 'import_error_ok': False}
        return self.write(cr, uid, ids, vals, context=context)

    def check_lines_to_fix(self, cr, uid, ids, context=None):
        if isinstance(ids, (int, long)):
            ids = [ids]
        message = ''
        plural= ''
        for var in self.browse(cr, uid, ids, context=context):
            if var.line_ids:
                for var in var.line_ids:
                    if var.to_correct_ok:
                        line_num = var.line_number
                        if message:
                            message += ', '
                        message += str(line_num)
                        if len(message.split(',')) > 1:
                            plural = 's'
        if message:
            raise osv.except_osv(_('Warning !'), _('You need to correct the following line%s : %s')% (plural, message))
        return True

    def default_get(self, cr, uid, fields, context=None):
        """[utp-746] ESC supplier catalogue default value
        and catalogue create not allowed in a not HQ instance"""
        res = super(supplier_catalogue, self).default_get(cr, uid, fields, context=context)
        if 'partner_id' in context:
            res['is_esc'] = self._is_esc_from_partner_id(cr, uid,
                                                context['partner_id'],
                                                context=context)
            if res['is_esc']:
                supplier_r = self.pool.get('res.partner').read(cr, uid,
                                                    [context['partner_id']],
                                                    ['partner_type'],
                                                    context=context)
                if supplier_r and supplier_r[0] \
                   and supplier_r[0]['partner_type'] \
                   and supplier_r[0]['partner_type'] == 'esc':
                    users_obj = self.pool.get('res.users')
                    user_ids = users_obj.search(cr, uid, [('id','=', uid)],
                                                context=context)
                    if user_ids:
                        if isinstance(user_ids, (int, long)):
                            user_ids = [user_ids]
                        users = users_obj.browse(cr, uid, user_ids,
                                                 context=context)
                        if users:
                            user = users[0]
                            if user.company_id and user.company_id.instance_id:
                                if user.company_id.instance_id.level and \
                                    user.company_id.instance_id.level !=  'section':
                                        raise osv.except_osv(
                                            _('Error'),
                                            'For an ESC Supplier you must create the catalogue on a HQ instance.'
                                        )

                # ESC supplier catalogue: no period date
                res['period_from'] = False
                res['period_to'] = False
        return res

supplier_catalogue()


class supplier_catalogue_line(osv.osv):
    _name = 'supplier.catalogue.line'
    _rec_name = 'line_number'
    _description = 'Supplier catalogue line'
    _table = 'supplier_catalogue_line'
    # Inherits of product.product to an easier search of lines
    # with product attributes
    _inherits = {'product.product': 'product_id'}
    _order = 'product_id, line_uom_id, min_qty'

    def _create_supplier_info(self, cr, uid, vals, context=None):
        '''
        Create a pricelist line on product supplier information tab
        '''
        if context is None:
            context = {}
        supinfo_obj = self.pool.get('product.supplierinfo')
        cat_obj = self.pool.get('supplier.catalogue')
        price_obj = self.pool.get('pricelist.partnerinfo')
        prod_obj = self.pool.get('product.product')
        user_obj = self.pool.get('res.users')

        tmpl_id = prod_obj.browse(cr, uid, vals['product_id'], context=context).product_tmpl_id.id
        catalogue = cat_obj.browse(cr, uid, vals['catalogue_id'], context=context)

        if catalogue.partner_id.id == user_obj.browse(cr, uid, uid, context=context).company_id.partner_id.id:
            return vals

        # Search if a product_supplierinfo exists for the catalogue, if not, create it !
        sup_ids = supinfo_obj.search(cr, uid, [('product_id', '=', tmpl_id),
                                               ('catalogue_id', '=', vals['catalogue_id'])],
                                               context=context)
        sup_id = sup_ids and sup_ids[0] or False
        if not sup_id:
            sup_id = supinfo_obj.create(cr, uid, {'name': catalogue.partner_id.id,
                                                  'sequence': 0,
                                                  'delay': catalogue.partner_id.default_delay,
                                                  'product_id': tmpl_id,
                                                  'catalogue_id': vals['catalogue_id'],
                                                  },
                                                  context=context)

        # Pass 'no_store_function' to False to compute the sequence on the pricelist.partnerinfo object
        create_context = context.copy()
        if context.get('no_store_function'):
            create_context['no_store_function'] = False

        price_id = price_obj.create(cr, uid, {'name': catalogue.name,
                                              'suppinfo_id': sup_id,
                                              'min_quantity': vals.get('min_qty', 0.00),
                                              'uom_id': vals['line_uom_id'],
                                              'price': vals['unit_price'],
                                              'rounding': vals.get('rounding', 1.00),
                                              'min_order_qty': vals.get('min_order_qty', 0.00),
                                              'currency_id': catalogue.currency_id.id,
                                              'valid_from': catalogue.period_from,
                                              'valid_till': catalogue.period_to,},
                                              context=create_context)

        vals.update({'supplier_info_id': sup_id,
                     'partner_info_id': price_id})

        return vals

    def create(self, cr, uid, vals, context=None):
        '''
        Create a pricelist line on product supplier information tab
        '''
        cat_state = False
        if vals.get('catalogue_id'):
            cat_state = self.pool.get('supplier.catalogue').read(cr, uid, vals.get('catalogue_id'), ['state'], context=context)['state']

        if cat_state != 'draft':
            vals = self._create_supplier_info(cr, uid, vals, context=context)

        ids = super(supplier_catalogue_line, self).create(cr, uid, vals, context=context)

        self._check_min_quantity(cr, uid, ids, context=context)

        return ids

    def write(self, cr, uid, ids, vals, context=None):
        '''
        Update the pricelist line on product supplier information tab
        '''
        if context is None:
            context = {}

        #product_obj = self.pool.get('product.product')
        #uom_obj = self.pool.get('product.uom')
        cat_obj = self.pool.get('supplier.catalogue')
        obj_data = self.pool.get('ir.model.data')
        uom_id = obj_data.get_object_reference(cr, uid, 'msf_doc_import','uom_tbd')[1]
        prod_id = obj_data.get_object_reference(cr, uid, 'msf_doc_import','product_tbd')[1]

        for line in self.browse(cr, uid, ids, context=context):
            new_vals = vals.copy()
            cat_state = cat_obj.read(cr, uid, new_vals.get('catalogue_id', line.catalogue_id.id), ['state'], context=context)['state']
            if 'product_id' in new_vals and 'line_uom_id' in new_vals and new_vals['product_id'] != prod_id and new_vals['line_uom_id'] != uom_id:
                new_vals['to_correct_ok'] = False
            # If product is changed
            if cat_state != 'draft' and new_vals.get('product_id', line.product_id.id) != line.product_id.id:
                c = context.copy()
                c.update({'product_change': True})
                # Remove the old pricelist.partnerinfo and create a new one
                if line.partner_info_id:
                    self.pool.get('pricelist.partnerinfo').unlink(cr, uid, line.partner_info_id.id, context=c)

                # Check if the removed line wasn't the last line of the supplierinfo
                if line.supplier_info_id and len(line.supplier_info_id.pricelist_ids) == 0:
                    # Remove the supplier info
                    self.pool.get('product.supplierinfo').unlink(cr, uid, line.supplier_info_id.id, context=c)

                # Create new partnerinfo line
                new_vals.update({'catalogue_id': new_vals.get('catalogue_id', line.catalogue_id.id),
                                 'product_id': new_vals.get('product_id', line.product_id.id),
                                 'min_qty': new_vals.get('min_qty', line.min_qty),
                                 'line_uom_id': new_vals.get('line_uom_id', line.line_uom_id.id),
                                 'unit_price': new_vals.get('unit_price', line.unit_price),
                                 'rounding': new_vals.get('rounding', line.rounding),
                                 'min_order_qty': new_vals.get('min_order_qty', line.min_order_qty),
                                 'comment': new_vals.get('comment', line.comment),
                                 })
                new_vals = self._create_supplier_info(cr, uid, new_vals, context=context)
            elif cat_state != 'draft' and line.partner_info_id:
                pinfo_data = {'min_quantity': new_vals.get('min_qty', line.min_qty),
                          'price': new_vals.get('unit_price', line.unit_price),
                          'uom_id': new_vals.get('line_uom_id', line.line_uom_id.id),
                          'rounding': new_vals.get('rounding', line.rounding),
                          'min_order_qty': new_vals.get('min_order_qty', line.min_order_qty)
                          }
                # Update the pricelist line on product supplier information tab
                self.pool.get('pricelist.partnerinfo').write(cr, uid, [line.partner_info_id.id],
                                                         pinfo_data, context=context)
            elif cat_state != 'draft':
                new_vals.update({'catalogue_id': new_vals.get('catalogue_id', line.catalogue_id.id),
                                 'product_id': new_vals.get('product_id', line.product_id.id),
                                 'min_qty': new_vals.get('min_qty', line.min_qty),
                                 'line_uom_id': new_vals.get('line_uom_id', line.line_uom_id.id),
                                 'unit_price': new_vals.get('unit_price', line.unit_price),
                                 'rounding': new_vals.get('rounding', line.rounding),
                                 'min_order_qty': new_vals.get('min_order_qty', line.min_order_qty),})
                new_vals = self._create_supplier_info(cr, uid, new_vals, context=context)
            elif cat_state == 'draft':
                #utp1033
                cr.execute('''delete from pricelist_partnerinfo
                              where id in (select partner_info_id
                                          from supplier_catalogue_line
                                          where catalogue_id = %s)''' % (ids[0]))
                cr.execute('''delete from product_supplierinfo
                              where id in (select supplier_info_id
                                          from supplier_catalogue_line
                                          where catalogue_id = %s)
                              and id not in (select suppinfo_id from
                                            pricelist_partnerinfo ) ''' % (ids[0]))

            res = super(supplier_catalogue_line, self).write(cr, uid, [line.id], new_vals, context=context)

        self._check_min_quantity(cr, uid, ids, context=context)

        return res

    def unlink(self, cr, uid, line_id, context=None):
        '''
        Remove the pricelist line on product supplier information tab
        If the product supplier information has no line, remove it
        '''
        if isinstance(line_id, (int, long)):
            line_id = [line_id]

        for l in line_id:
            line = self.browse(cr, uid, l, context=context)
            c = context is not None and context.copy() or {}
            c.update({'product_change': True})
            # Remove the pricelist line in product tab
            if line.partner_info_id:
                self.pool.get('pricelist.partnerinfo').unlink(cr, uid, line.partner_info_id.id, context=c)

            # Check if the removed line wasn't the last line of the supplierinfo
            if line.supplier_info_id and len(line.supplier_info_id.pricelist_ids) == 0:
                # Remove the supplier info
                self.pool.get('product.supplierinfo').unlink(cr, uid, line.supplier_info_id.id, context=c)

        return super(supplier_catalogue_line, self).unlink(cr, uid, line_id, context=context)

    def _check_min_quantity(self, cr, uid, ids, context=None):
        '''
        Check if the min_qty field is set
        '''
        if context is None:
            context = {}

        if isinstance(ids, (int, long)):
            ids = [ids]

        if not context.get('noraise'):
            for line in self.browse(cr, uid, ids, context=context):
                if line.min_qty <= 0.00:
                    raise osv.except_osv(_('Error'), _('The line of product [%s] %s has a negative or zero min. qty !') % (line.product_id.default_code, line.product_id.name))
                    return False

        return True

    _columns = {
        'line_number': fields.integer(string='Line'),
        'catalogue_id': fields.many2one('supplier.catalogue', string='Catalogue', required=True, ondelete='cascade'),
        'product_id': fields.many2one('product.product', string='Product', required=True, ondelete='cascade'),
        'min_qty': fields.float(digits=(16,2), string='Min. Qty', required=True,
                                  help='Minimal order quantity to get this unit price.'),
        'line_uom_id': fields.many2one('product.uom', string='Product UoM', required=True,
                                  help='UoM of the product used to get this unit price.'),
        'unit_price': fields.float(string='Unit Price', required=True, digits_compute=dp.get_precision('Purchase Price Computation')),
        'rounding': fields.float(digits=(16,2), string='SoQ rounding',
                                   help='The ordered quantity must be a multiple of this rounding value.'),
        'min_order_qty': fields.float(digits=(16,2), string='Min. Order Qty'),
        'comment': fields.char(size=64, string='Comment'),
        'supplier_info_id': fields.many2one('product.supplierinfo', string='Linked Supplier Info'),
        'partner_info_id': fields.many2one('pricelist.partnerinfo', string='Linked Supplier Info line'),
        'to_correct_ok': fields.boolean('To correct'),
    }

    _defaults = {
        'rounding': 1.00,
    }


    def product_change(self, cr, uid, ids, product_id, min_qty, min_order_qty, context=None):
        '''
        When the product change, fill automatically the line_uom_id field of the
        catalogue line.
        @param product_id: ID of the selected product or False
        '''
        v = {'line_uom_id': False}
        res = {}

        if product_id:
            product = self.pool.get('product.product').browse(cr, uid, product_id, context=context)
            v.update({'line_uom_id': product.uom_id.id})
            res = self.change_uom_qty(cr, uid, ids, product.uom_id.id, min_qty, min_order_qty)
        else:
            return {}

        res.setdefault('value', {}).update(v)

        return res

    def change_uom_qty(self, cr, uid, ids, uom_id, min_qty, min_order_qty):
        '''
        Check round qty according to UoM
        '''
        res = {}
        uom_obj = self.pool.get('product.uom')

        if min_qty:
            res = uom_obj._change_round_up_qty(cr, uid, uom_id, min_qty, 'min_qty', result=res)

        if min_order_qty:
            res = uom_obj._change_round_up_qty(cr, uid, uom_id, min_order_qty, 'min_order_qty', result=res)

        res.setdefault('value', {})
        res['value']['rounding'] = 0.00

        return res

    def change_soq_quantity(self, cr, uid, ids, soq, uom_id, context=None):
        """
        When the SoQ quantity is changed, check if the new quantity is consistent
        with rounding value of the UoM of the catalogue line.
        :param cr: Cursor to the database
        :param uid: ID of the res.users that calls the method
        :param ids: List of ID of product.product on which the SoQ quantity is changed
        :param soq: New value for SoQ Quantity
        :param uom_id: ID of the product.uom linked to the product
        :param context: Context of the call
        :return: A dictionary that contains a warning message and the SoQ quantity
        rounded with the UoM rounding value
        """
        res = self.pool.get('product.product').change_soq_quantity(cr, uid, [], soq, uom_id, context=context)

        if res.get('value', {}).get('soq_quantity', False):
            res['value']['rounding'] = res['value'].pop('soq_quantity')

        return res

    def onChangeSearchNomenclature(self, cr, uid, line_id, position, line_type, nomen_manda_0, nomen_manda_1, nomen_manda_2, nomen_manda_3, num=True, context=None):
        '''
        Method to fill nomenclature fields in search view
        '''
        return self.pool.get('product.product').onChangeSearchNomenclature(cr, uid, [], position, line_type, nomen_manda_0, nomen_manda_1, nomen_manda_2, nomen_manda_3, num=num, context=context)

    def fields_view_get(self, cr, uid, view_id=None, view_type='form', context=None, toolbar=False, submenu=False):
        '''
        Override the tree view to display historical prices according to context
        '''
        if context is None:
            context = {}
        res = super(supplier_catalogue_line, self).fields_view_get(cr, uid, view_id, view_type, context, toolbar, submenu)

        # If the context is set to open historical view
        if context.get('catalogue_ids', False) and view_type == 'tree':
            catalogues = self.pool.get('supplier.catalogue').browse(cr, uid, context.get('catalogue_ids'), context=context)

            # Modify the tree view to add one column by pricelist
            line_view = """<tree string="Historical prices" editable="top" noteditable="1" notselectable="0"
                    hide_new_button="1" hide_delete_button="1">
                   <field name="product_id"/>
                   <field name="line_uom_id" />
                   <field name="min_qty" />"""

            for cat in catalogues:
                line_view += """<field name="%s" />""" % cat.period_from

            line_view += "</tree>"

            if res['type'] == 'tree':
                res['arch'] = line_view

        return res

    def fields_get(self, cr, uid, fields=None, context=None):
        '''
        Override the fields to display historical prices according to context
        '''
        if context is None:
            context = {}
        res = super(supplier_catalogue_line, self).fields_get(cr, uid, fields, context)

        if context.get('catalogue_ids', False):
            catalogues = self.pool.get('supplier.catalogue').browse(cr, uid, context.get('catalogue_ids'), context=context)
            for cat in catalogues:
                cat_from = self.pool.get('date.tools').get_date_formatted(cr, uid, d_type='date', datetime=cat.period_from, context=context)
                cat_to = ''
                if cat.period_to:
                    cat_to = self.pool.get('date.tools').get_date_formatted(cr, uid, d_type='date', datetime=cat.period_to, context=context)
                res.update({cat.period_from: {'size': 64,
                                              'selectable': True,
                                              'string': '%s-%s' % (cat_from, cat_to),
                                              'type': 'char',}})

        return res

    def read(self, cr, uid, ids, fields=None, context=None, load="_classic_write"):
        if context is None:
            context = {}
        if context.get('catalogue_ids', False):
            line_dict = {}
            new_context = context.copy()
            new_context.pop('catalogue_ids')
            catalogues = self.pool.get('supplier.catalogue').browse(cr, uid, context.get('catalogue_ids'), context=new_context)
            for cat in catalogues:
                period_name = '%s' % cat.period_from
                for line in cat.line_ids:
                    line_name = '%s_%s_%s' % (line.product_id.id, line.min_qty, line.line_uom_id.id)
                    if line_name not in line_dict:
                        line_dict.update({line_name: {}})

                    line_dict[line_name].update({period_name: '%s' % line.unit_price})

            res = super(supplier_catalogue_line, self).read(cr, uid, ids, fields, context=context)

            for r in res:
                line_name = '%s_%s_%s' % (r['product_id'][0], r['min_qty'], r['line_uom_id'][0])
                for period in line_dict[line_name]:
                    r.update({period: line_dict[line_name][period]})

        else:
            res = super(supplier_catalogue_line, self).read(cr, uid, ids, fields, context=context)

        return res

supplier_catalogue_line()


class supplier_historical_catalogue(osv.osv_memory):
    _name = 'supplier.historical.catalogue'

    _columns = {
        'partner_id': fields.many2one('res.partner', string='Supplier'),
        'currency_id': fields.many2one('res.currency', string='Currency', required=True),
        'from_date': fields.date(string='From', required=True),
        'to_date': fields.date(string='To', required=True),
    }

    _defaults = {
        'partner_id': lambda obj, uid, ids, ctx: ctx.get('active_id'),
        'to_date': lambda *a: time.strftime('%Y-%m-%d'),
    }

    def open_historical_prices(self, cr, uid, ids, context=None):
        '''
        Open the historical prices view
        '''
        if not context:
            context = {}

        for hist in self.browse(cr, uid, ids, context=context):
            catalogue_ids = self.pool.get('supplier.catalogue').search(cr, uid, [('partner_id', '=', hist.partner_id.id),
                                                                                 ('active', 'in', ['t', 'f']),
                                                                                 ('currency_id', '=', hist.currency_id.id),
                                                                                 ('period_from', '<=', hist.to_date),
                                                                                 '|', ('period_to', '=', False),
                                                                                 ('period_to', '>=', hist.from_date)])

            if not catalogue_ids:
                raise osv.except_osv(_('Error'), _('No catalogues found for this supplier and this currency in the period !'))

            line_dict = {}
            line_ids = []
            catalogues = self.pool.get('supplier.catalogue').browse(cr, uid, catalogue_ids, context=context)
            for cat in catalogues:
                for line in cat.line_ids:
                    line_name = '%s_%s_%s' % (line.product_id.id, line.min_qty, line.line_uom_id.id)
                    if line_name not in line_dict:
                        line_dict.update({line_name: {}})
                        line_ids.append(line.id)

            context.update({'from_date': hist.from_date,
                            'to_date': hist.to_date,
                            'partner_id': hist.partner_id.id,
                            'currency_id': hist.currency_id.id,
                            'catalogue_ids': catalogue_ids})

        from_str = self.pool.get('date.tools').get_date_formatted(cr, uid, d_type='date', datetime=context.get('from_date'), context=context)
        to_str = self.pool.get('date.tools').get_date_formatted(cr, uid, d_type='date', datetime=context.get('to_date'), context=context)

        view_id = self.pool.get('ir.model.data').get_object_reference(cr, uid, 'supplier_catalogue', 'non_edit_supplier_catalogue_line_tree_view')[1]

        return {'type': 'ir.actions.act_window',
                'name': '%s - Historical prices (%s) - from %s to %s' % (hist.partner_id.name, hist.currency_id.name, from_str, to_str),
                'res_model': 'supplier.catalogue.line',
                'view_type': 'form',
                'view_mode': 'tree,form',
                'domain': [('id', 'in', line_ids)],
                'view_id': [view_id],
                'context': context}

supplier_historical_catalogue()


class from_supplier_choose_catalogue(osv.osv_memory):
    _name = 'from.supplier.choose.catalogue'

    _columns = {
        'partner_id': fields.many2one('res.partner', string='Supplier', required=True),
        'catalogue_id': fields.many2one('supplier.catalogue', string='Catalogue', required=True),
    }

    def default_get(self, cr, uid, fields, context=None):
        '''
        Fill partner_id from context
        '''
        if context is None:
            context = {}
        if not context.get('active_id', False):
            raise osv.except_osv(_('Error'), _('No catalogue found !'))

        partner_id = context.get('active_id')

        if not self.pool.get('supplier.catalogue').search(cr, uid,
                [('partner_id', '=', partner_id)],
                limit=1, context=context, order='NO_ORDER'):
            raise osv.except_osv(_('Error'), _('No catalogue found !'))

        res = super(from_supplier_choose_catalogue, self).default_get(cr, uid, fields, context=context)

        res.update({'partner_id': partner_id})

        return res

    def open_catalogue(self, cr, uid, ids, context=None):
        '''
        Open catalogue lines
        '''
        wiz = self.browse(cr, uid, ids[0], context=context)

        return self.pool.get('supplier.catalogue').open_lines(cr, uid, wiz.catalogue_id.id, context=context)

from_supplier_choose_catalogue()

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
