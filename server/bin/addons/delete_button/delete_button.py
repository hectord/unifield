# -*- coding: utf-8 -*-
##############################################################################
#
#    OpenERP, Open Source Management Solution
#    Copyright (C) 2004-2010 Tiny SPRL (<http://tiny.be>).
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

from osv import fields, osv
from tools.translate import _

class stock_picking(osv.osv):
    """
    Override the class stock_picking to replace the standard 
    delete button by a delete button of type "object"
    """
    _name = 'stock.picking'
    _inherit = 'stock.picking'
    
    def unlink(self, cr, uid, ids, context=None):
        """
        The deletion is possible only for draft document that are not generated by the system, 
        i.e. that doesn't come from a PO or a SO => the check is done in msf_outgoing>msf_outgoing.py
        """
        if isinstance(ids, (int, long)):
            ids = [ids]
        for sp  in self.read(cr, uid, ids,['state'], context=context):
            if sp['state'] == 'draft':
                return super(stock_picking, self).unlink(cr, uid, ids, context)
            else:
                raise osv.except_osv(_('Warning !'), _('You can only delete documents which are in "Draft" state.'))
    
    def delete_button(self, cr, uid, ids, context=None):
        """
        This method is called on the button of type object in tree view.
        The aim is to be able to display the delete button only in draft state, which is not possible with the standard delete button.
        """
        if isinstance(ids, (int, long)):
            ids = [ids]
        return self.unlink(cr, uid, ids, context)
    
stock_picking()

class purchase_order(osv.osv):
    """
    Override the class purchase_order to replace the standard 
    delete button by a delete button of type "object"
    """
    _name = 'purchase.order'
    _inherit = 'purchase.order'
    
    def unlink(self, cr, uid, ids, context=None):
        """
        Don't allow user to delete purchase order in draft state
        """
        if isinstance(ids, (int, long)):
            ids = [ids]
        for p  in self.read(cr, uid, ids,['state'], context=context):
            if p['state'] == 'draft':
                return super(purchase_order, self).unlink(cr, uid, ids, context)
            else:
                raise osv.except_osv(_('Warning !'), _('You can only delete documents which are in "Draft" state.'))
    
    def delete_button(self, cr, uid, ids, context=None):
        """
        This method is called on the button of type object in tree view.
        The aim is to be able to display the delete button only in draft state, which is not possible with the standard delete button.
        """
        if isinstance(ids, (int, long)):
            ids = [ids]
        return self.unlink(cr, uid, ids, context)
    
purchase_order()

class sale_order(osv.osv):
    """
    Override the class sale_order to replace the standard 
    delete button by a delete button of type "object"
    """
    _name = 'sale.order'
    _inherit = 'sale.order'
    
    def unlink(self, cr, uid, ids, context=None):
        """
        Do not allow user to delete sale order in draft state
        """
        if isinstance(ids, (int, long)):
            ids = [ids]
        for order in self.read(cr, uid, ids,['state'], context=context):
            if order['state'] == 'draft':
                return super(sale_order, self).unlink(cr, uid, ids, context)
            else:
                raise osv.except_osv(_('Warning !'), _('You can only delete documents which are in "Draft" state.'))
    
    def delete_button(self, cr, uid, ids, context=None):
        """
        This method is called on the button of type object in tree view.
        The aim is to be able to display the delete button only in draft state, which is not possible with the standard delete button.
        """
        if isinstance(ids, (int, long)):
            ids = [ids]
        return self.unlink(cr, uid, ids, context)
    
sale_order()

class tender(osv.osv):
    """
    Override the class tender to replace the standard 
    delete button by a delete button of type "object"
    """
    _name = 'tender'
    _inherit = 'tender'
    
    def unlink(self, cr, uid, ids, context=None):
        """
        Do not allow user to delete tender in draft state
        """
        if isinstance(ids, (int, long)):
            ids = [ids]
        for order in self.read(cr, uid, ids,['state'], context=context):
            if order['state'] == 'draft':
                return super(tender, self).unlink(cr, uid, ids, context)
            else:
                raise osv.except_osv(_('Warning !'), _('You can only delete documents which are in "Draft" state.'))
    
    def delete_button(self, cr, uid, ids, context=None):
        """
        This method is called on the button of type object in tree view.
        The aim is to be able to display the delete button only in draft state, which is not possible with the standard delete button.
        """
        if isinstance(ids, (int, long)):
            ids = [ids]
        return self.unlink(cr, uid, ids, context)
    
tender()

class composition_kit(osv.osv):
    """
    Override the class composition_kit to replace the standard 
    delete button by a delete button of type "object"
    """
    _name = 'composition.kit'
    _inherit = 'composition.kit'
    
    def unlink(self, cr, uid, ids, context=None):
        """
        Do not allow user to delete composition_kit in draft state
        """
        if isinstance(ids, (int, long)):
            ids = [ids]
        for order in self.read(cr, uid, ids,['state'], context=context):
            if order['state'] == 'draft':
                return super(composition_kit, self).unlink(cr, uid, ids, context)
            else:
                raise osv.except_osv(_('Warning !'), _('You can only delete documents which are in "Draft" state.'))
    
    def delete_button(self, cr, uid, ids, context=None):
        """
        This method is called on the button of type object in tree view.
        The aim is to be able to display the delete button only in draft state, which is not possible with the standard delete button.
        """
        if isinstance(ids, (int, long)):
            ids = [ids]
        return self.unlink(cr, uid, ids, context)
    
composition_kit()

class real_average_consumption(osv.osv):
    _name = 'real.average.consumption'
    _inherit = 'real.average.consumption'

    def delete_button(self, cr, uid, ids, context=None):
        """
        This method is called on the button of type object in tree view.
        The aim is to be able to display the delete button only in draft state, which is not possible with the standard delete button.
        """
        if isinstance(ids, (int, long)):
            ids = [ids]
        return self.unlink(cr, uid, ids, context)

real_average_consumption()

