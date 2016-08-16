# -*- coding: utf-8 -*-
##############################################################################
#
#    OpenERP, Open Source Management Solution
#    Copyright (C) 2015 MSF, TeMPO consulting
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
import types
import functools
from osv import osv
from osv import fields
from osv import orm

class deleted_object(osv.osv):
    """Keep track of deleted objects"""
    _name = 'deleted.object'
    _auto = True
    _log_access = False
    _order = 'deletion_date desc, model, deleted_obj_id'

    _columns={
        'model': fields.char('Object Model', size=64, readonly=True),
        'deleted_obj_id': fields.integer('Deleted Object ID', readonly=True),
        'deleted_obj_sd_ref': fields.char('Deleted Object SD Ref', size=128,
            read_only=True),
        'deletion_date': fields.datetime('Deletion Date', read_only=True),
        'user_id': fields.many2one('res.users', 'User who delete',
            read_only=True),
        'deleted_in_sync': fields.boolean(string='Deleted by sync',
            help='This object has been deleted during a synchronization'),
    }

deleted_object()


class extended_delete_orm(osv.osv):
    """Extend orm methods"""
    _auto = False
    _name = 'deleted_object.orm_extended'
    _description = "Flag that certify presence of extended ORM methods"

extended_delete_orm()

def orm_delete_method_overload(method):
    """
    Wrapper method to override orm.orm classic methods
    """
    original_method = getattr(orm.orm, method.func_name)
    @functools.wraps(method)
    def wrapper(self, *args, **kwargs):
        if self.pool.get(extended_delete_orm._name) is not None:
            return method(self, original_method, *args, **kwargs)
        else:
            return original_method(self, *args, **kwargs)
    return wrapper

class extended_orm_delete_method:
    @orm_delete_method_overload
    def unlink(self, original_unlink, cr, uid, ids, context=None):
        """Create a delete_object in case the current object is not blacklisted
        to keep track of deleted objects"""
        if context is None:
            context = {}
        res = original_unlink(self, cr, uid, ids, context=context)
        if not res:
            return res
        if not ids:
            return True
        if isinstance(ids, (int, long)):
            ids = [ids]

        # we don't need to keep a track of all deleted objects
        model_deleted_black_list = ['funding.pool.distribution.line',
                                    ]
        if self._name in model_deleted_black_list or\
                self._name.startswith('ir.') or\
                isinstance(self, orm.orm_memory): # don't track object from
                                                  # orm.orm_memory class
            return res
        deletion_date = time.strftime('%Y-%m-%d %H:%M:%S')
        model_obj = self.pool.get(self._name)
        if not self.pool.get('sync.client.entity'):
            # sync client not installed
            return res
        obj_sd_ref = model_obj.get_sd_ref(cr, uid, ids)
        is_sync_context = context.get('sync_update_execution', False) or context.get('sync_message_execution', False)
        deleted_obj_module = self.pool.get('deleted.object')
        for sub_ids in cr.split_for_in_conditions(ids):
            # keep a track of deleted object if there are not blacklisted
            # by creating a deleted.object
            for obj_id in sub_ids:
                vals = {'model': self._name,
                        'deleted_obj_id': obj_id,
                        'deleted_obj_sd_ref': obj_sd_ref[obj_id],
                        'deletion_date': deletion_date,
                        'user_id': uid,
                        'deleted_in_sync': is_sync_context,}
                del_obj = deleted_obj_module.create(cr, uid, vals)
        return res

for symbol in filter(lambda sym: isinstance(sym, types.MethodType),
                     map(lambda label: getattr(extended_orm_delete_method, label),
                         dir(extended_orm_delete_method))):
    setattr(orm.orm, symbol.func_name, symbol.im_func)
