###############################################################################
#
#  Copyright (C) 2007-TODAY OpenERP SA. All Rights Reserved.
#
#  $Id$
#
#  Developed by OpenERP (http://openerp.com) and Axelor (http://axelor.com).
#
#  The OpenERP web client is distributed under the "OpenERP Public License".
#  It's based on Mozilla Public License Version (MPL) 1.1 with following 
#  restrictions:
#
#  -   All names, links and logos of OpenERP must be kept as in original
#      distribution without any changes in all software screens, especially
#      in start-up page and the software header, even if the application
#      source code has been changed or updated or code has been added.
#
#  You can see the MPL licence at: http://www.mozilla.org/MPL/MPL-1.1.html
#
###############################################################################
import StringIO
import csv
import xml.dom.minidom
import cherrypy

from openerp.controllers import SecuredController
from openerp.utils import rpc, common, TinyDict, node_attributes
from openerp.widgets import treegrid

from openobject import tools
from openobject.tools import expose, redirect, ast
import simplejson
import time
from openobject.i18n import format
import re


product_remove_fields = ['qty_available', 'virtual_available', 'product_amc', 'reviewed_consumption', 'monthly_consumption']
def datas_read(ids, model, flds, context=None):
    ctx = dict((context or {}), **rpc.session.context)
    return rpc.RPCProxy(model).export_data(ids, flds, ctx)

def export_csv(fields, result):
    try:
        fp = StringIO.StringIO()
        writer = csv.writer(fp, quoting=csv.QUOTE_ALL)

        writer.writerow(fields)

        for data in result:
            row = []
            for d in data:
                if isinstance(d, basestring):
                    d = d.replace('\n',' ').replace('\t',' ')
                    try:
                        d = d.encode('utf-8')
                    except:
                        pass
                if d is False: d = None
                row.append(d)

            writer.writerow(row)

        fp.seek(0)
        data = fp.read()
        fp.close()

        return data
    except IOError, (errno, strerror):
        raise common.message(_("Operation failed\nI/O error")+"(%s)" % (errno,))

def _fields_get_all(model, views, context=None):

    context = context or {}

    def parse(root, fields):

        for node in root.childNodes:

            if node.nodeName in ('form', 'notebook', 'page', 'group', 'tree', 'hpaned', 'vpaned'):
                parse(node, fields)

            elif node.nodeName=='field':
                attrs = node_attributes(node)
                name = attrs['name']

                fields[name].update(attrs)

        return fields

    def get_view_fields(view):
        return parse(
            xml.dom.minidom.parseString(view['arch'].encode('utf-8')).documentElement,
            view['fields'])

    proxy = rpc.RPCProxy(model)

    tree_view = proxy.fields_view_get(views.get('tree', False), 'tree', context)
    form_view = proxy.fields_view_get(views.get('form', False), 'form', context)

    fields = {}
    fields.update(get_view_fields(tree_view))
    fields.update(get_view_fields(form_view))

    return fields


class ImpEx(SecuredController):

    _cp_path = "/openerp/impex"

    @expose(template="/openerp/controllers/templates/exp.mako")
    def exp(self, import_compat="0", **kw):

        params, data = TinyDict.split(kw)
        ctx = dict((params.context or {}), **rpc.session.context)
        views = {}
        if params.view_mode and params.view_ids:
            for i, view in enumerate(params.view_mode):
                views[view] = params.view_ids[i]

        export_format = data.get('export_format', 'excel')
        all_records = data.get('all_records', '0')

        if not params.ids:
            all_records = '1'
        exports = rpc.RPCProxy('ir.exports')

        headers = [{'string' : 'Name', 'name' : 'name', 'type' : 'char'}]
        tree = treegrid.TreeGrid('export_fields',
                                 model=params.model,
                                 headers=headers,
                                 url=tools.url('/openerp/impex/get_fields'),
                                 field_parent='relation',
                                 context=ctx,
                                 views=views,
                                 import_compat=int(import_compat))

        tree.show_headers = False

        existing_exports = exports.read(
            exports.search([('resource', '=', params.model)], context=ctx),
            [], ctx)

        default = []
        if params._terp_listheaders:
            default = [x.split(',',1) for x in params._terp_listheaders]
        elif kw.get('_terp_fields2') and kw.get('fields') and params.fields2:
            default = []
            for i in range(0, len(kw.get('fields'))):
                if import_compat=='1' and '/' in kw.get('fields')[i] and kw.get('fields')[i].split('/')[-1] not in ('id', '.id'):
                    continue
                default.append([kw['fields'][i], params.fields2[i]])

        export_id = False
        if '_export_id' in kw and kw['_export_id']:
            export_id = int(kw['_export_id'])

        if params.model:
            proxy = rpc.RPCProxy(params.model)
            default = proxy.update_exported_fields(default)

        if params.model == 'product.product':
            default = [x for x in default if x[0] not in product_remove_fields]
        default = simplejson.dumps(default)
        group_by_no_leaf = ctx and  ctx.get('group_by_no_leaf', False)
        if params.search_data and ctx and not ctx.get('group_by') and params.search_data.get('group_by_ctx'):
            ctx['group_by'] = params.search_data['group_by_ctx']
        return dict(existing_exports=existing_exports, model=params.model, ids=params.ids, ctx=ctx,
                    search_domain=params.search_domain, source=params.source, group_by_no_leaf=group_by_no_leaf,
                    tree=tree, import_compat=import_compat, default=default, export_format=export_format, all_records=all_records, export_id=export_id)

    @expose()
    def save_exp(self, **kw):
        params, data = TinyDict.split(kw)

        selected_list = data.get('fields')
        name = data.get('savelist_name')

        proxy = rpc.RPCProxy('ir.exports')

        if selected_list and name:
            if isinstance(selected_list, basestring):
                selected_list = [selected_list]
            exp_id = proxy.create({'name' : name, 'resource' : params.model, 'export_fields' : [(0, 0, {'name' : f}) for f in selected_list]})
            kw['_export_id'] = exp_id
        return self.exp(**kw)
        #raise redirect('/openerp/impex/exp', **kw)

    @expose()
    def delete_listname(self, **kw):

        params, data = TinyDict.split(kw)
        proxy = rpc.RPCProxy('ir.exports')

        proxy.unlink(params.id)

        raise redirect('/openerp/impex/exp', **kw)


    @expose('json')
    def get_fields(self, model, prefix='', name='', field_parent=None, **kw):

        parent_field = kw.get('ids').split(',')[0].split('/')
        if len(parent_field) == 1:
            parent_field = parent_field[0]
        else:
            parent_field = parent_field[-2]

        is_importing = kw.get('is_importing', False)
        import_compat= bool(int(kw.get('import_compat', True)))

        try:
            ctx = ast.literal_eval(kw['context'])
        except:
            ctx = {}

        ctx.update(**rpc.session.context)

        try:
            views = ast.literal_eval(kw['views'])
        except:
            views = {}

        fields = _fields_get_all(model, views, ctx)
        m2ofields = cherrypy.session.get('fld')
        if m2ofields:
            for i in m2ofields:
                if i == parent_field:
                    fields = {}
        else:
            m2ofields = []

        fields.update({'id': {'string': 'ID'}, '.id': {'string': 'Database ID'}})

        fields_order = fields.keys()
        fields_order.sort(lambda x,y: -cmp(fields[x].get('string', ''), fields[y].get('string', '')))
        records = []


        for i, field in enumerate(fields_order):
            value = fields[field]
            record = {}

            if import_compat and value.get('readonly', False):
                ok = False
                for sl in value.get('states', {}).values():
                    for s in sl:
                        ok = ok or (s==('readonly',False))
                if not ok: continue
                
            id = prefix + (prefix and '/' or '') + field
            nm = name + (name and '/' or '') + value['string']

            if is_importing and (value.get('type') not in ('reference',)) and (not value.get('readonly') \
                        or not dict(value.get('states', {}).get('draft', [('readonly', True)])).get('readonly', True)):

                record.update(id=id, items={'name': nm},
                              action='javascript: void(0)', target=None,
                              icon=None, children=[],
                              required=value.get('required', False))

                records.append(record)

            elif not is_importing:

                record.update(id=id, items={'name': nm},
                              action='javascript: void(0)', target=None,
                              icon=None, children=[])
                records.append(record)


            if len(nm.split('/')) < 3 and value.get('relation', False):

                if import_compat or is_importing:
                    ref = value.pop('relation')
                    proxy = rpc.RPCProxy(ref)
                    cfields = proxy.fields_get(False, rpc.session.context)
                    if (value['type'] == 'many2many') and not is_importing:
                        record['children'] = None
                        record['params'] = {'model': ref, 'prefix': id, 'name': nm}

                    elif (value['type'] == 'many2one') or (value['type'] == 'many2many' and is_importing):
                        m2ofields.append(field)
                        cfields_order = cfields.keys()
                        cfields_order.sort(lambda x,y: -cmp(cfields[x].get('string', ''), cfields[y].get('string', '')))
                        children = []
                        for j, fld in enumerate(cfields_order):
                            cid = id + '/' + fld
                            cid = cid.replace(' ', '_')
                            children.append(cid)
                        record['children'] = children or None
                        record['params'] = {'model': ref, 'prefix': id, 'name': nm}
                        cherrypy.session['fld'] = m2ofields

                    else:
                        cfields_order = cfields.keys()
                        cfields_order.sort(lambda x,y: -cmp(cfields[x].get('string', ''), cfields[y].get('string', '')))
                        children = []
                        for j, fld in enumerate(cfields_order):
                            cid = id + '/' + fld
                            cid = cid.replace(' ', '_')
                            children.append(cid)
                        record['children'] = children or None
                        record['params'] = {'model': ref, 'prefix': id, 'name': nm}

                else:
                    ref = value.pop('relation')
                    proxy = rpc.RPCProxy(ref)
                    cfields = proxy.fields_get(False, rpc.session.context)
                    cfields_order = cfields.keys()
                    cfields_order.sort(lambda x,y: -cmp(cfields[x].get('string', ''), cfields[y].get('string', '')))
                    children = []
                    for j, fld in enumerate(cfields_order):
                        cid = id + '/' + fld
                        cid = cid.replace(' ', '_')
                        children.append(cid)
                    record['children'] = children or None
                    record['params'] = {'model': ref, 'prefix': id, 'name': nm}
                    cherrypy.session['fld'] = []

        records.reverse()
        return dict(records=records)


    @expose('json')
    def namelist(self, **kw):

        params, data = TinyDict.split(kw)

        ctx = dict((params.context or {}), **rpc.session.context)

        id = params.id

        res = self.get_data(params.model, ctx)
        ir_export = rpc.RPCProxy('ir.exports')
        ir_export_line = rpc.RPCProxy('ir.exports.line')

        field = ir_export.read(id)
        fields = ir_export_line.read(field['export_fields'])

        name_list = [
                (f['name'], res.get(f['name']))
                for f in fields]

        return dict(name_list=name_list)

    def get_data(self, model, context=None):

        ids = []
        context = context or {}
        fields_data = {}
        proxy = rpc.RPCProxy(model)
        fields = proxy.fields_get(False, rpc.session.context)

        # XXX: in GTK client, top fields comes from Screen
        if not ids:
            f1 = proxy.fields_view_get(False, 'tree', context)['fields']
            f2 = proxy.fields_view_get(False, 'form', context)['fields']

            fields = dict(f1)
            fields.update(f2)

        def rec(fields):
            _fields = {'id': 'ID' , '.id': 'Database ID' }

            def model_populate(fields, prefix_node='', prefix=None, prefix_value='', level=2):
                fields_order = fields.keys()
                fields_order.sort(lambda x,y: -cmp(fields[x].get('string', ''), fields[y].get('string', '')))

                for field in fields_order:
                    fields_data[prefix_node+field] = fields[field]
                    if prefix_node:
                        fields_data[prefix_node + field]['string'] = '%s%s' % (prefix_value, fields_data[prefix_node + field]['string'])
                    st_name = fields[field]['string'] or field
                    _fields[prefix_node+field] = st_name
                    if fields[field].get('relation', False) and level>0:
                        fields2 = rpc.session.execute('object', 'execute', fields[field]['relation'], 'fields_get', False, rpc.session.context)
                        model_populate(fields2, prefix_node+field+'/', None, st_name+'/', level-1)
            model_populate(fields)

            return _fields

        return rec(fields)
    
    @expose(template="/openerp/controllers/templates/expxml.mako")
    def export_html(self, fields, result, view_name):
        cherrypy.response.headers['Content-Type'] = 'application/vnd.ms-excel'
        cherrypy.response.headers['Content-Disposition'] = 'attachment; filename="%s_%s.xls"'%(view_name, time.strftime('%Y%m%d'))
        return {'fields': fields, 'result': result, 'title': 'Export %s %s'%(view_name, time.strftime(format.get_datetime_format())), 're': re}

    def get_grp_data(self, result, flds):
        data = []
        for r in result:
            tmp_data = []
            for f in flds:
                value = r.get(f,'')
                if isinstance(value, tuple):
                    value = value and value[1] or ''
                tmp_data.append(value)
            data.append(tmp_data)
        return data

    @expose(content_type="application/octet-stream")
    def export_data(self, fname, fields, import_compat=False, export_format='csv', all_records=False, **kw):

        params, data_index = TinyDict.split(kw)
        proxy = rpc.RPCProxy(params.model)

        flds = []
        for item in fields:
            fld = item.replace('/.id','.id')
            flds.append(fld)

        if isinstance(fields, basestring):
            fields = fields.replace('/.id','.id')
            flds = [fields]

        if params.model == 'product.product':
            tmp_flds = flds
            flds = []
            fields_header = []
            for f in tmp_flds:
                header = ""
                if params.fields2 and len(params.fields2):
                    header = params.fields2.pop(0)
                if f not in product_remove_fields:
                    flds.append(f)
                    fields_header.append(header)

            params.fields2 = fields_header

        ctx = dict((params.context or {}), **rpc.session.context)
        ctx['import_comp'] = bool(int(import_compat))

        view_name = ctx.get('_terp_view_name', '')

        if ctx.get('group_by_no_leaf'):
            ctx['client_export_data'] = True  # UTP-580-582-697 client export flag

            rpc_obj = rpc.RPCProxy(params.model)
            domain = params.search_domain or []
            to_group = ctx.get('group_by', [])
            group_by = []
            for gr in to_group:
                gr = gr.replace('group_', '')
                group_by.append(gr)
                if gr not in flds:
                    flds.append(gr)
                    params.fields2.append(gr)

            fields_to_read = []
            for f in flds:
                if '/' not in f:
                    fields_to_read.append(f)

            flds = fields_to_read[:]
            params.fields2 = fields_to_read[:]

            data = rpc_obj.read_group(domain, flds, group_by, 0, 2000, ctx)

            result_tmp = []  # List of processed data lines (dictionaries)
            # Closure to recursively prepare and insert lines in 'result_tmp'
            # (as much as the number of 'group_by' levels)
            def process_data(line):
                domain_line = line.get('__domain', [])
                grp_by_line = line.get('__context', {}).get('group_by', [])
                # If there is a 'group_by', we fetch data one level deeper
                if grp_by_line:
                    data = rpc_obj.read_group(domain_line, flds, grp_by_line, 0, 0, ctx)
                    for line2 in data:
                        line_copy = line.copy()
                        line_copy.update(line2)
                        process_data(line_copy)
                # If 'group_by' is empty, this means we were at the last level
                # so we insert the line in the final result
                else:
                    result_tmp.append(line)
            # Prepare recursively the data to export (inserted in 'result_tmp')
            for data_line in data:
                process_data(data_line)
            result = self.get_grp_data(result_tmp, flds)

            result, params.fields2 = rpc_obj.filter_export_data_result(result, params.fields2)
            if export_format == "excel":
                return self.export_html(params.fields2, result, view_name)
            return export_csv(params.fields2, result)

        if not params.ids or all_records:
            domain = params.search_domain or []
            if params.model == 'product.product':
                ids = proxy.search(domain, 0, None, 0, ctx)
            else:
                ids = proxy.search(domain, 0, 2000, 0, ctx)
        else:
            ids = params.ids or []
        result = datas_read(ids, params.model, flds, context=ctx)
        if result.get('warning'):
            common.warning(unicode(result.get('warning', False)), _('Export Error'))
            return False
        result = result.get('datas',[])

        if import_compat == "1":
            params.fields2 = flds
        if export_format == "excel":
            return self.export_html(params.fields2, result, view_name)
        return export_csv(params.fields2, result)

    @expose(template="/openerp/controllers/templates/imp.mako")
    def imp(self, error=None, records=None, success=None, **kw):
        params, data = TinyDict.split(kw)

        ctx = dict((params.context or {}), **rpc.session.context)

        views = {}
        if params.view_mode and params.view_ids:
            for i, view in enumerate(params.view_mode):
                views[view] = params.view_ids[i]

        headers = [{'string' : 'Name', 'name' : 'name', 'type' : 'char'}]
        tree = treegrid.TreeGrid('import_fields',
                                    model=params.model,
                                    headers=headers,
                                    url=tools.url('/openerp/impex/get_fields'),
                                    field_parent='relation',
                                    views=views,
                                    context=ctx,
                                    is_importing=1)

        tree.show_headers = False
        return dict(error=error, records=records, success=success,
                    model=params.model, source=params.source,
                    tree=tree, fields=kw.get('fields', {}))

    @expose()
    def detect_data(self, csvfile, csvsep, csvdel, csvcode, csvskip, **kw):
        params, data = TinyDict.split(kw)

        _fields = {}
        _fields_invert = {}
        error = None

        fields = dict(rpc.RPCProxy(params.model).fields_get(False, rpc.session.context))
        fields.update({'id': {'string': 'ID'}, '.id': {'string': 'Database ID'}})

        def model_populate(fields, prefix_node='', prefix=None, prefix_value='', level=2):
            def str_comp(x,y):
                if x<y: return 1
                elif x>y: return -1
                else: return 0

            fields_order = fields.keys()
            fields_order.sort(lambda x,y: str_comp(fields[x].get('string', ''), fields[y].get('string', '')))
            for field in fields_order:
                if (not fields[field].get('readonly')\
                            or not dict(fields[field].get('states', {}).get(
                            'draft', [('readonly', True)])).get('readonly',True)):

                    st_name = prefix_value+fields[field]['string'] or field
                    _fields[prefix_node+field] = st_name
                    _fields_invert[st_name] = prefix_node+field

                    if fields[field].get('type','')=='one2many' and level>0:
                        fields2 = rpc.session.execute('object', 'execute', fields[field]['relation'], 'fields_get', False, rpc.session.context)
                        model_populate(fields2, prefix_node+field+'/', None, st_name+'/', level-1)

                    if fields[field].get('relation',False) and level>0:
                        model_populate({'/id': {'type': 'char', 'string': 'ID'}, '.id': {'type': 'char', 'string': 'Database ID'}},
                                       prefix_node+field, None, st_name+'/', level-1)
        fields.update({'id':{'string':'ID'},'.id':{'string':_('Database ID')}})
        model_populate(fields)


        try:
            data = csv.reader(csvfile.file, quotechar=str(csvdel), delimiter=str(csvsep))
        except:
            raise common.warning(_('Error opening .CSV file'), _('Input Error.'))


        records = []
        fields = []
        word=''
        limit = 3

        try:
            for i, row in enumerate(data):
                records.append(row)
                if i == limit:
                    break

            for line in records:
                for word in line:
                    word = ustr(word.decode(csvcode))
                    if word in _fields:
                        fields.append((word, _fields[word]))
                    elif word in _fields_invert.keys():
                        fields.append((_fields_invert[word], word))
                    else:
                        error = {'message':_("You cannot import the field '%s', because we cannot auto-detect it" % (word,))}
                break
        except:
            error = {'message':_('Error processing the first line of the file. Field "%s" is unknown') % (word,), 'title':_('Import Error.')}

        kw['fields'] = fields
        if error:
            csvfile.file.seek(0)
            return self.imp(error=dict(error, preview=csvfile.file.read(200)), **kw)
        return self.imp(records=records, **kw)

    @expose()
    def import_data(self, csvfile, csvsep, csvdel, csvcode, csvskip, fields=[], **kw):

        params, data = TinyDict.split(kw)
        res = None
        
        content = csvfile.file.read()
        input=StringIO.StringIO(content)
        limit = 0
        data = []

        if not (csvdel and len(csvdel) == 1):
            return self.imp(error={'message': _("The CSV delimiter must be a single character")}, **kw)

        try:
            for j, line in enumerate(csv.reader(input, quotechar=str(csvdel), delimiter=str(csvsep))):
                # If the line contains no data, we should skip it.
                if not line:
                    continue
                if j == limit:
                    fields = line
                else:
                    data.append(line)
        except csv.Error, e:
            return self.imp(
                error={
                    'message': ustr(e),
                    'title': _('File Format Error')
                },
                **kw)

        datas = []
        ctx = dict(rpc.session.context)

        if not isinstance(fields, list):
            fields = [fields]

        for line in data:
            try:
                datas.append(map(lambda x:x.decode(csvcode).encode('utf-8'), line))
            except:
                datas.append(map(lambda x:x.decode('latin').encode('utf-8'), line))
        
        # If the file contains nothing,
        if not datas:
            error = {'message': _('The file is empty !'), 'title': _('Importation !')}
            return self.imp(error=error, **kw)
        
        #Inverting the header into column names
        try:
            res = rpc.session.execute('object', 'execute', params.model, 'import_data', fields, datas, 'init', '', False, ctx)
        except Exception, e:
            error = {'message':ustr(e), 'title':_('XML-RPC error')}
            return self.imp(error=error, **kw)


        if res[0]>=0:
            return self.imp(success={'message':_('Imported %d objects') % (res[0],)}, **kw)

        d = ''
        for key,val in res[1].items():
            d+= ('%s: %s' % (ustr(key),ustr(val)))
        msg = _('Error trying to import this record:%s. ErrorMessage:%s %s') % (d,res[2],res[3])
        error = {'message':ustr(msg), 'title':_('ImportationError')}

        return self.imp(error=error, **kw)
