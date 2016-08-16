#!/usr/bin/env python
# -*- coding: utf-8 -*-
##############################################################################
#
#    OpenERP, Open Source Management Solution
#    Copyright (C) 2013 TeMPO Consulting, MSF. All Rights Reserved
#    Developer: Olivier DOSSMANN
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
from tools.translate import _
import csv
from cStringIO import StringIO
import pooler
import zipfile
from tempfile import NamedTemporaryFile
import os
from hashlib import md5
from string import Template

class finance_archive():
    """
    SQLREQUESTS DICTIONNARY
     - key: name of the SQL request
     - value: the SQL request to use

    PROCESS REQUESTS LIST: list of dict containing info to process some SQL requests
    Dict:
     - [optional] headers: list of headers that should appears in the CSV file
     - filename: the name of the result filename in the future ZIP file
     - key: the name of the key in SQLREQUESTS DICTIONNARY to have the right SQL request
     - [optional] query_params: data to use to complete SQL requests
     - [optional] query_tpl_context: dict data to use to complete SQL requests with templating like $var
     - [optional] function: name of the function to postprocess data (example: to change selection field into a human readable text)
     - [optional] fnct_params: params that would used on the given function
     - [optional] delete_columns: list of columns to delete before writing files into result
     - [optional] id (need 'object'): number of the column that contains the ID of the element. Column number begin from 0. Note that you should adapt your SQL request to add the ID of lines.
     - [optional] object (need 'id'): name of the object in the system. For an example: 'account.bank.statement'.
    TIP & TRICKS:
     + More than 1 request in 1 file: just use same filename for each request you want to be in the same file.
     + If you cannot do a SQL request to create the content of the file, do a simple request (with key) and add a postprocess function that returns the result you want
     + Do not repeat headers if you use the same filename for more than 1 request. This avoid having multiple lines as headers.
    """

    def __init__(self, sql, process):
        self.sqlrequests = sql
        self.processrequests = process

    def line_to_utf8(self, line):
        """
        Change all elements of this line to UTF-8
        """
        newline = []
        if not line:
            return []
        for element in line:
            if type(element) == unicode:
                newline.append(element.encode('utf-8'))
            else:
                newline.append(element)
        return newline

    def delete_x_column(self, line, columns=[]):
        """
        Take numbers in 'columns' list and delete them from given line.
        Begin from 0.
        """
        if not line:
            return []
        if not columns:
            return line
        # Create a list of all elements from line except those given in columns
        newline = []
        for element in sorted([x for x in xrange(len(line)) if x not in columns]):
            newline.append(line[element])
        return newline

    def get_selection(self, cr, model, field):
        """
        Return a list of all selection from a field in a given model.
        """
        pool = pooler.get_pool(cr.dbname)
        data = pool.get(model).fields_get(cr, 1, [field])
        return dict(data[field]['selection'])

    def get_hash(self, cr, uid, ids, model):
        """
        Create a concatenation of:
          - dbname
          - ids
          - model
        Then create a md5
        """
        return self._get_hash(cr, uid, ids, model)

    @staticmethod
    def _get_hash(cr, uid, ids, model):
        """
        Create a concatenation of:
          - dbname
          - ids
          - model
        Then create a md5
        """
        # Prepare some values
        md5sum = md5()
        is_list = False
        if not ids or not model:
            return ''
        if not isinstance(ids, (str, unicode, list)):
            return ''
        if isinstance(ids, list):
            is_list = True
            res_ids = ids
        # preapre some values
        name = cr.dbname
        if not is_list:
            ids = sorted(ids.split(','))
            # We have this: [u'2', u'4', u'6', u'8']
            # And we want this: [2, 4, 6, 8]
            # So we do some process on this list
            res_ids = [int(x) for x in ids]
        md5sum.update(','.join([name, model, str(res_ids)]))
        return md5sum.hexdigest()

    def postprocess_selection_columns(self, cr, uid, data, changes, column_deletion=False):
        """
        This method takes each line from data and change some columns regarding "changes" variable.
        'changes' should be a list containing some tuples. A tuple is composed of:
         - a model (example: res.partner)
         - the selection field in which retrieve all real values (example: partner_type)
         - the column number in the data lines from which you want to change the value (begin from 0)
        """
        # Checks
        if not changes:
            return data
        # Prepare some values
        new_data = []
        # Fetch selections
        changes_values = {}
        for change in changes:
            model = change[0]
            field = change[1]
            changes_values[change] = self.get_selection(cr, model, field)
        # Browse each line to replace partner type by it's human readable value (selection)
        # partner_type is the 3rd column
        for line in data:
            tmp_line = list(line)
            # Delete some columns if needed
            if column_deletion:
                tmp_line = self.delete_x_column(list(line), column_deletion)
            for change in changes:
                column = change[2]
                # use line value to search into changes_values[change] (the list of selection) the right value
                tmp_line[column] = changes_values[change][tmp_line[column]]
            new_data.append(self.line_to_utf8(tmp_line))
        return new_data

    def archive(self, cr, uid):
        """
        Create an archive with sqlrequests params and processrequests params.
        """
        # open buffer for result zipfile
        zip_buffer = StringIO()
        # Prepare some values
        pool = pooler.get_pool(cr.dbname)

        # List is composed of a tuple containing:
        # - filename
        # - key of sqlrequests dict to fetch its SQL request
        files = {}
        for fileparams in self.processrequests:
            if not fileparams.get('filename', False):
                raise osv.except_osv(_('Error'), _('Filename param is missing!'))
            if not fileparams.get('key', False):
                raise osv.except_osv(_('Error'), _('Key param is missing!'))
            # temporary file (process filename to display datetime data instead of %(year)s chars)
            filename = pool.get('ir.sequence')._process(cr, uid, fileparams['filename'] or '') or fileparams['filename']
            if filename not in files:
                tmp_file = NamedTemporaryFile('w+b', delete=False)
            else:
                tmp_file = files[filename]

            # fetch data with given sql query
            sql = self.sqlrequests[fileparams['key']]
            if fileparams.get('query_tpl_context', False):
                sql = Template(sql).safe_substitute(
                    fileparams.get('query_tpl_context'))
            if fileparams.get('query_params', False):
                cr.execute(sql, fileparams['query_params'])
            else:
                cr.execute(sql)
            sqlres = cr.fetchall()
            # Fetch ID column and mark lines as exported
            if fileparams.get('id', None) != None:
                if not fileparams.get('object', False):
                    raise osv.except_osv(_('Error'), _('object param is missing to use ID one.'))
                # prepare needed values
                object_name = fileparams['object']
                pool = pooler.get_pool(cr.dbname)
                tablename = pool.get(object_name)._table
                if not tablename:
                    raise osv.except_osv(_('Error'), _("Table name not found for the given object: %s") % (fileparams['object'],))
                key_column_number = fileparams['id']
                # get ids from previous request
                ids = [x and x[key_column_number] or 0 for x in sqlres]
                # mark lines as exported
                if ids:
                    update_request = 'UPDATE ' + tablename + ' SET exported=\'t\' WHERE id in %s'
                    try:
                        cr.execute(update_request, (tuple(ids),))
                    except Exception, e:
                        raise osv.except_osv(_('Error'), _('An error occured: %s') % (e.message and e.message or '',))
            without_headers = []
            # Check if a function is given. If yes, use it.
            # If not, transform lines into UTF-8. Note that postprocess method should transform lines into UTF-8 ones.
            if fileparams.get('function', False):
                fnct = getattr(self, fileparams['function'], False)
                delete_columns = fileparams.get('delete_columns', False)
                # If the function has some params, use them.
                if fnct and fileparams.get('fnct_params', False):
                    without_headers = fnct(cr, uid, sqlres, fileparams['fnct_params'], column_deletion=delete_columns)
                elif fnct:
                    without_headers = fnct(cr, uid, sqlres, column_deletion=delete_columns)
            else:
                # Change to UTF-8 all unicode elements
                for line in sqlres:
                    # Delete useless columns if needed
                    if fileparams.get('delete_columns', False):
                        line = self.delete_x_column(line, fileparams['delete_columns'])
                    without_headers.append(self.line_to_utf8(line))
            result = without_headers
            if fileparams.get('headers', False):
                headers = [fileparams['headers']]
                for line in result:
                    headers.append(line)
                result = headers
            # Write result in a CSV writer then close it.
            writer = csv.writer(tmp_file, quoting=csv.QUOTE_ALL)
            writer.writerows(result)
            # Only add a link to the temporary file if not in "files" dict
            if filename not in files:
                files[filename] = tmp_file

        # WRITE RESULT INTO AN ARCHIVE
        # Create a ZIP file
        out_zipfile = zipfile.ZipFile(zip_buffer, "w")
        for filename in files:
            tmpfile = files[filename]
            # close temporary file
            tmpfile.close()
            # write content into zipfile
            out_zipfile.write(tmpfile.name, filename, zipfile.ZIP_DEFLATED)
            # unlink temporary file
            os.unlink(tmpfile.name)
        # close zip
        out_zipfile.close()
        out = zip_buffer.getvalue()
        # Return result
        return (out, 'zip')

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
