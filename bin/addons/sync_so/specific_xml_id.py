'''
Created on 15 mai 2012

@author: openerp
'''

from osv import osv
from osv import fields

# Note:
#
#     * Only the required fields need a " or 'no...' " next to their use.
#     * Beware to check that many2one fields exists before using their property
#

# !! Please always use this method before returning an xml_name
#    It will automatically convert arguments to strings, remove False args
#    and finally remove all dots (unexpected dots appears when the system
#    language is not english)
def get_valid_xml_name(*args):
    return u"_".join(map(lambda x: unicode(x), filter(None, args))).replace('.', '').replace(',', '_')

class fiscal_year(osv.osv):

    _inherit = 'account.fiscalyear'

    def get_unique_xml_name(self, cr, uid, uuid, table_name, res_id):
        fiscalyear = self.browse(cr, uid, res_id)
        return get_valid_xml_name(fiscalyear.code)

fiscal_year()

class account_journal(osv.osv):

    _inherit = 'account.journal'

    def get_unique_xml_name(self, cr, uid, uuid, table_name, res_id):
        journal = self.browse(cr, uid, res_id)
        return get_valid_xml_name('journal', (journal.instance_id.code or 'noinstance'), (journal.code or 'nocode'), (journal.name or 'noname'))

account_journal()


class ir_actions_act_window(osv.osv):
    _inherit = 'ir.actions.act_window'

    def get_unique_xml_name(self, cr, uid, uuid, table_name, res_id):
        model_data_obj = self.pool.get('ir.model.data')
        sdref_ids = model_data_obj.search(cr, uid, [('model','=',self._name),('res_id','=',res_id),('module','!=','sd')])
        if not sdref_ids:
            return super(ir_actions_act_window, self).get_unique_xml_name(cr, uid, uuid, table_name, res_id)
        origin_xmlid = model_data_obj.read(cr, uid, sdref_ids[0], ['module', 'name'])
        return get_valid_xml_name(origin_xmlid['module'], origin_xmlid['name'])

    def _get_is_remote_wh(self, cr, uid, ids, field_name, args, context=None):
        return {}.fromkeys(ids, False)

    def _search_is_remote_wh(self, cr, uid, obj, name, args, context=None):
        if not args:
            return []
        rarg = []
        for arg in args:
            if arg[1] != '=':
                raise osv.except_osv('Error', 'Filter on is_remote_wh not implemented')
            model_data_obj = self.pool.get('ir.model.data')
            mod_ids = model_data_obj.search(cr, uid, [('model', '=', obj._name), ('module', '=', 'sync_remote_warehouse')])
            ids = []
            for m in model_data_obj.read(cr, uid, mod_ids, ['res_id']):
                ids.append(m['res_id'])
            value = arg[2] not in (False, 'f', 'False')
            rarg.append(('id', value and 'in' or 'not in', ids))
        return rarg

    _columns = {
        'is_remote_wh': fields.function(_get_is_remote_wh, type='boolean', string="From RW module", fnct_search=_search_is_remote_wh, method=True),
    }
ir_actions_act_window()


class bank_statement(osv.osv):

    _inherit = 'account.bank.statement'

    def get_unique_xml_name(self, cr, uid, uuid, table_name, res_id):
        bank = self.browse(cr, uid, res_id)
        # to be unique, the journal xml_id must include also the period, otherwise no same name journal cannot be inserted for different periods!
        unique_journal = (bank.journal_id.code or 'nojournal') + '_' + (bank.period_id.name or 'noperiod')
        return get_valid_xml_name('bank_statement', (bank.instance_id.code or 'noinstance'), (bank.name or 'nobank'), unique_journal)

    def update_xml_id_register(self, cr, uid, res_id, context):
        """
        Reupdate the xml_id of the register once the button Open got clicked. Because in draft state the period can be modified,
        the xml_id is no more relevant to the register. After openning the register, the period is readonly, xml_id is thus safe
        """
        bank = self.browse(cr, uid, res_id) # search the fake xml_id
        model_data_obj = self.pool.get('ir.model.data')

        # This one is to get the prefix of the bank_statement for retrieval of the correct xml_id
        prefix = get_valid_xml_name('bank_statement', (bank.instance_id.code or 'noinstance'), (bank.name or 'nobank'))

        data_ids = model_data_obj.search(cr, uid, [('model', '=', self._name), ('res_id', '=', res_id), ('name', 'like', prefix), ('module', '=', 'sd')], limit=1, context=context)
        xml_id = self.get_unique_xml_name(cr, uid, False, self._table, res_id)

        existing_xml_id = False
        if data_ids:
            existing_xml_id = model_data_obj.read(cr, uid, data_ids[0], ['name'])['name']
        if xml_id != existing_xml_id:
            model_data_obj.write(cr, uid, data_ids, {'name': xml_id}, context=context)
        return True

    def button_open_bank(self, cr, uid, ids, context=None):
        res = super(bank_statement, self).button_open_bank(cr, uid, ids, context=context)
        self.update_xml_id_register(cr, uid, ids[0], context)
        return res

    def button_open_cheque(self, cr, uid, ids, context=None):
        res = super(bank_statement, self).button_open_cheque(cr, uid, ids, context=context)
        self.update_xml_id_register(cr, uid, ids[0], context)
        return res

    def button_open_cash(self, cr, uid, ids, context=None):
        """
        The update of xml_id may be done when opening the register
        --> set the value of xml_id based on the period as period is no more modifiable
        """
        res = super(bank_statement, self).button_open_cash(cr, uid, ids, context=context)
        self.update_xml_id_register(cr, uid, ids[0], context)
        return res

bank_statement()

class account_period_sync(osv.osv):

    _inherit = "account.period"

    def get_unique_xml_name(self, cr, uid, uuid, table_name, res_id):
        period = self.browse(cr, uid, res_id)
        return get_valid_xml_name(period.fiscalyear_id.code+"/"+period.name, period.date_start)

account_period_sync()

class res_currency_sync(osv.osv):

    _inherit = 'res.currency'

    def get_unique_xml_name(self, cr, uid, uuid, table_name, res_id):
        currency = self.browse(cr, uid, res_id)
        return get_valid_xml_name(currency.name, (currency.currency_table_id and currency.currency_table_id.name))

res_currency_sync()

class product_pricelist(osv.osv):

    _inherit = 'product.pricelist'

    def get_unique_xml_name(self, cr, uid, uuid, table_name, res_id):
        pricelist = self.browse(cr, uid, res_id)
        return get_valid_xml_name(pricelist.name, pricelist.type)

product_pricelist()

class hq_entries(osv.osv):

    _inherit = 'hq.entries'

    def get_destination_name(self, cr, uid, ids, dest_field, context=None):
        if dest_field == 'cost_center_id':
            res = dict.fromkeys(ids, False)
            for line_data in self.browse(cr, uid, ids, context=context):
                if line_data.cost_center_id:
                    cost_center_name = line_data.cost_center_id and \
                                       line_data.cost_center_id.code and \
                                       line_data.cost_center_id.code[:3] or ""
                    cost_center_ids = self.pool.get('account.analytic.account').search(cr, uid, [('category', '=', 'OC'),
                                                                                                 ('code', '=', cost_center_name)], context=context)
                    if len(cost_center_ids) > 0:
                        target_ids = self.pool.get('account.target.costcenter').search(cr, uid, [('cost_center_id', '=', cost_center_ids[0]),
                                                                                                 ('is_target', '=', True)])
                        if len(target_ids) > 0:
                            target = self.pool.get('account.target.costcenter').browse(cr, uid, target_ids[0], context=context)
                            if target.instance_id and target.instance_id.instance:
                                res[line_data.id] = target.instance_id.instance
            return res
        return super(hq_entries, self).get_destination_name(cr, uid, ids, dest_field, context=context)

hq_entries()


class account_target_costcenter(osv.osv):

    _inherit = 'account.target.costcenter'

    def get_destination_name(self, cr, uid, ids, dest_field, context=None):
        if dest_field == 'instance_id':
            res = dict.fromkeys(ids, False)
            for target_line in self.browse(cr, uid, ids, context=context):
                if target_line.instance_id:
                    instance = target_line.instance_id
                    if instance.state == 'active':
                        res_data = [instance.instance]
                        # if it is a coordo instance, send it to its active projects as well
                        if instance.level == 'coordo':
                            for project in instance.child_ids:
                                if project.state == 'active':
                                    res_data.append(project.instance)
                        # if it is a project instance, send it to its active siblings as well
                        elif instance.level == 'project' and instance.parent_id:
                            for project in instance.parent_id.child_ids:
                                if project != instance and project.state == 'active':
                                    res_data.append(project.instance)
                        res[target_line.id] = res_data
            return res
        return super(account_target_costcenter, self).get_destination_name(cr, uid, ids, dest_field, context=context)

    def create(self, cr, uid, vals, context={}):
        res_id = super(account_target_costcenter, self).create(cr, uid, vals, context=context)
        # create lines in instance's children
        if 'instance_id' in vals:
            instance = self.pool.get('msf.instance').browse(cr, uid, vals['instance_id'], context=context)
            current_instance = self.pool.get('res.users').browse(cr, uid, uid, context=context).company_id.instance_id
            if instance.state == 'active' and current_instance.level == 'section':
                # "touch" cost center if instance is active (to sync to new targets)
                self.pool.get('account.analytic.account').synchronize(cr, uid, [vals['cost_center_id']], context=context)
        return res_id

account_target_costcenter()

class account_analytic_account(osv.osv):

    _inherit = 'account.analytic.account'

    def get_destination_name(self, cr, uid, ids, dest_field, context=None):
        # get all active project instance with the cost center in one of its target lines
        if dest_field == 'category':
            if isinstance(ids, (long, int)):
                ids = [ids]
            res = dict.fromkeys(ids, False)
            for id in ids:
                cr.execute("select instance_id from account_target_costcenter where cost_center_id = %s" % (id))
                instance_ids = [x[0] for x in cr.fetchall()]
                if len(instance_ids) > 0:
                    res_temp = []
                    for instance_id in instance_ids:
                        cr.execute("select instance from msf_instance where id = %s and state = 'active'" % (instance_id))
                        result = cr.fetchone()
                        if result:
                            res_temp.append(result[0])
                    res[id] = res_temp
            return res

        # UFTP-2: Get the children of the given instance and create manually sync updates for them, only when it is Coordo
        if dest_field == 'instance_id':
            ## Check if it is *funding pool* and created at HQ
            res = dict.fromkeys(ids, False)
            for target_line in self.browse(cr, uid, ids, context=context):
                if target_line.instance_id:
                    instance = target_line.instance_id
                    if instance.state == 'active':
                        res_data = [instance.instance]
                        # if it is a coordo instance, send it to its active projects as well
                        if instance.level == 'coordo':
                            for project in instance.child_ids:
                                if project.state == 'active':
                                    res_data.append(project.instance)
                        res[target_line.id] = res_data
            return res
        return super(account_analytic_account, self).get_destination_name(cr, uid, ids, dest_field, context=context)

    def get_unique_xml_name(self, cr, uid, uuid, table_name, res_id):
        account = self.read(cr, uid, res_id, ['code', 'name', 'category'])
        if account and account['code'] in ('OC', 'cc-intermission', 'FUNDING',
                                           'FREE1', 'FREE2', 'PF', 'DEST',
                                           'OPS', 'SUP', 'NAT', 'EXP'):
            # specific account created on each instances by xml data file, should have the same xmlid
            return get_valid_xml_name(account['category'], account['code'], account['name'])
        return super(account_analytic_account, self).get_unique_xml_name(cr, uid, uuid, table_name, res_id)

account_analytic_account()


#US-113: Sync only to the mission with attached prop instance
class financing_contract_contract(osv.osv):
    _inherit = 'financing.contract.contract'

    def get_destination_name(self, cr, uid, ids, dest_field, context=None):
        # BKLG-34: Get the children of the given instance and create manually sync updates for them, only when it is Coordo
        if dest_field == 'instance_id':
            ## Check if it is *financing contract* created at HQ
            res = dict.fromkeys(ids, False)
            for target_line in self.browse(cr, uid, ids, context=context):
                if target_line.instance_id:
                    instance = target_line.instance_id
                    if instance.state == 'active':
                        res_data = [instance.instance]
                        # if it is a coordo instance, send it to its active projects as well
                        if instance.level == 'coordo':
                            for project in instance.child_ids:
                                if project.state == 'active':
                                    res_data.append(project.instance)
                        res[target_line.id] = res_data
            return res
        return super(financing_contract_contract, self).get_destination_name(cr, uid, ids, dest_field, context=context)

financing_contract_contract()

#US-113: Sync only to the mission with attached prop instance
class financing_contract_funding_pool_line(osv.osv):

    _inherit = 'financing.contract.funding.pool.line'

    def get_destination_name(self, cr, uid, ids, dest_field, context=None):
        # BKLG-34: Get the children of the given instance and create manually sync updates for them, only when it is Coordo
        if dest_field == 'instance_id':
            ## Check if it is *financing contract* created at HQ
            res = dict.fromkeys(ids, False)
            for target_line in self.browse(cr, uid, ids, context=context):
                if target_line.instance_id:
                    instance = target_line.instance_id
                    if instance.state == 'active':
                        res_data = [instance.instance]
                        # if it is a coordo instance, send it to its active projects as well
                        if instance.level == 'coordo':
                            for project in instance.child_ids:
                                if project.state == 'active':
                                    res_data.append(project.instance)
                        res[target_line.id] = res_data
            return res
        return super(financing_contract_funding_pool_line, self).get_destination_name(cr, uid, ids, dest_field, context=context)

financing_contract_funding_pool_line()

#US-113: Sync only to the mission with attached prop instance
class financing_contract_format(osv.osv):

    _inherit = 'financing.contract.format'

    def get_destination_name(self, cr, uid, ids, dest_field, context=None):
        # BKLG-34: Get the children of the given instance and create manually sync updates for them, only when it is Coordo
        if dest_field == 'hidden_instance_id':
            ## Check if it is *financing contract* created at HQ
            res = dict.fromkeys(ids, False)
            for target_line in self.browse(cr, uid, ids, context=context):
                if target_line.hidden_instance_id:
                    instance = target_line.hidden_instance_id
                    if instance.state == 'active':
                        res_data = [instance.instance]
                        # if it is a coordo instance, send it to its active projects as well
                        if instance.level == 'coordo':
                            for project in instance.child_ids:
                                if project.state == 'active':
                                    res_data.append(project.instance)
                        res[target_line.id] = res_data
            return res
        return super(financing_contract_format, self).get_destination_name(cr, uid, ids, dest_field, context=context)

financing_contract_format()

#US-113: Sync only to the mission with attached prop instance
class financing_contract_format_line(osv.osv):
    _inherit = 'financing.contract.format.line'
    def get_destination_name(self, cr, uid, ids, dest_field, context=None):
        # BKLG-34: Get the children of the given instance and create manually sync updates for them, only when it is Coordo
        if dest_field == 'instance_id':
            ## Check if it is *financing contract* created at HQ
            res = dict.fromkeys(ids, False)
            for target_line in self.browse(cr, uid, ids, context=context):
                if target_line.instance_id:
                    instance = target_line.instance_id
                    if instance.state == 'active':
                        res_data = [instance.instance]
                        # if it is a coordo instance, send it to its active projects as well
                        if instance.level == 'coordo':
                            for project in instance.child_ids:
                                if project.state == 'active':
                                    res_data.append(project.instance)
                        res[target_line.id] = res_data
            return res
        return super(financing_contract_format_line, self).get_destination_name(cr, uid, ids, dest_field, context=context)

financing_contract_format_line()

class msf_instance(osv.osv):

    _inherit = 'msf.instance'

    def create(self, cr, uid, vals, context=None):
        res_id = super(msf_instance, self).create(cr, uid, vals, context=context)
        current_instance = self.pool.get('res.users').browse(cr, uid, uid, context=context).company_id.instance_id
        if 'state' in vals and 'parent_id' in vals and vals['state'] == 'active' and current_instance.level == 'section':
            instance = self.browse(cr, uid, res_id, context=context)
            # touch cost centers and account_Target_cc lines in order to sync them
            target_ids = [x.id for x in instance.target_cost_center_ids]
            self.pool.get('account.target.costcenter').synchronize(cr, uid, target_ids, context=context)

            cost_center_ids = [x.cost_center_id.id for x in instance.target_cost_center_ids]
            self.pool.get('account.analytic.account').synchronize(cr, uid, cost_center_ids, context=context)

            # also touch parent instance and lines from parent, since those were already sent to other instances
            if instance.parent_id and instance.parent_id.target_cost_center_ids and instance.level == 'project':
                parent_target_ids = [x.id for x in instance.parent_id.target_cost_center_ids]
                self.pool.get('account.target.costcenter').synchronize(cr, uid, parent_target_ids, context=context)
                # also also, re-send other projects' lines
                if instance.parent_id.child_ids:
                    sibling_target_ids = []
                    for sibling in instance.parent_id.child_ids:
                        if sibling != instance and sibling.state == 'active':
                            sibling_target_ids += [x.id for x in sibling.target_cost_center_ids]
                    self.pool.get('account.target.costcenter').synchronize(cr, uid, sibling_target_ids, context=context)

        return res_id

    def write(self, cr, uid, ids, vals, context=None):
        if isinstance(ids, (int, long)):
            ids = [ids]
        current_instance = self.pool.get('res.users').browse(cr, uid, uid, context=context).company_id.instance_id
        if 'state' in vals and vals['state'] == 'active' and current_instance.level == 'section':
            for instance in self.browse(cr, uid, ids, context=context):
                if instance.state != 'active':
                    # only for now-activated instances (first push)
                    # touch cost centers and account_Target_cc lines in order to sync them
                    target_ids = [x.id for x in instance.target_cost_center_ids]
                    self.pool.get('account.target.costcenter').synchronize(cr, uid, target_ids, context=context)

                    cost_center_ids = [x.cost_center_id.id for x in instance.target_cost_center_ids]
                    self.pool.get('account.analytic.account').synchronize(cr, uid, cost_center_ids, context=context)

                    # also touch parent instance and lines from parent, since those were already sent to other instances
                    if instance.parent_id and instance.parent_id.target_cost_center_ids and instance.level == 'project':
                        parent_target_ids = [x.id for x in instance.parent_id.target_cost_center_ids]
                        self.pool.get('account.target.costcenter').synchronize(cr, uid, parent_target_ids, context=context)
                        # also also, re-send other projects' lines
                        if instance.parent_id.child_ids:
                            sibling_target_ids = []
                            for sibling in instance.parent_id.child_ids:
                                if sibling != instance and sibling.state == 'active':
                                    sibling_target_ids += [x.id for x in sibling.target_cost_center_ids]
                            self.pool.get('account.target.costcenter').synchronize(cr, uid, sibling_target_ids, context=context)

        return super(msf_instance, self).write(cr, uid, ids, vals, context=context)

msf_instance()

class account_analytic_line(osv.osv):

    _inherit = 'account.analytic.line'

    _columns = {
        'correction_date': fields.datetime('Correction Date'), # UF-2343: Add timestamp when making the correction, to be synced
    }

    def get_browse_instance_name_from_cost_center(self, cr, uid, cost_center_id, context=None):
        if cost_center_id:
            target_ids = self.pool.get('account.target.costcenter').search(cr, uid, [('cost_center_id', '=', cost_center_id),
                                                                                     ('is_target', '=', True)])
            current_instance = self.pool.get('res.users').browse(cr, uid, uid).company_id.instance_id
            if len(target_ids) > 0:
                target = self.pool.get('account.target.costcenter').browse(cr, uid, target_ids[0], context=context)
                if target.instance_id and target.instance_id.instance:
                    return target.instance_id

            if current_instance.parent_id and current_instance.parent_id.instance:
                # Instance has a parent
                return current_instance.parent_id
            else:
                return False
        else:
            return False

    def get_instance_name_from_cost_center(self, cr, uid, cost_center_id, context=None):
        browse_instance = self.get_browse_instance_name_from_cost_center(cr, uid, cost_center_id, context=context)
        if browse_instance:
            return browse_instance.instance
        return browse_instance

    def get_lower_instance_name(self, cr, uid, browse_inst1, browse_inst2, context=None):
        if browse_inst1.id == browse_inst2.id:
            return browse_inst1.instance
        if browse_inst1.level == browse_inst2.level:
            # same level so no parentality
            return [browse_inst1.instance, browse_inst2.instance]
        if browse_inst1.level == 'project' and browse_inst2.level in ('coordo', 'mission') or \
                browse_inst1.level == 'coordo' and browse_inst2.level == 'mission':
            lower = browse_inst1
            upper = browse_inst2
        else:
            lower = browse_inst2
            upper = browse_inst1

        if lower.parent_id and lower.parent_id.id == upper.id or lower.parent_id.parent_id and lower.parent_id.parent_id.id == upper.id:
            return lower.instance
        return [browse_inst1.instance, browse_inst2.instance]
    def get_instance_level_from_cost_center(self, cr, uid, cost_center_id, context=None):
        if cost_center_id:
            target_ids = self.pool.get('account.target.costcenter').search(cr, uid, [('cost_center_id', '=', cost_center_id),
                                                                                     ('is_target', '=', True)])
            current_instance = self.pool.get('res.users').browse(cr, uid, uid).company_id.instance_id
            if len(target_ids) > 0:
                target = self.pool.get('account.target.costcenter').browse(cr, uid, target_ids[0], context=context)
                if target.instance_id and target.instance_id.level:
                    return target.instance_id.level

            if current_instance.parent_id and current_instance.parent_id.level:
                # Instance has a parent
                return current_instance.parent_id.level
            else:
                return False
        else:
            return False

    def get_destination_name(self, cr, uid, ids, dest_field, context=None):
        if not dest_field == 'cost_center_id':
            return super(account_analytic_line, self).get_destination_name(cr, uid, ids, dest_field, context=context)

        current_instance = self.pool.get('res.users').browse(cr, uid, uid).company_id.instance_id
        res = dict.fromkeys(ids, False)
        for line_data in self.browse(cr, uid, ids, context=context):
            browse_instance = False
            if line_data.cost_center_id:
                browse_instance = self.get_browse_instance_name_from_cost_center(cr, uid, line_data.cost_center_id.id, context)
                if browse_instance:
                    res[line_data.id] = browse_instance.instance
            elif current_instance.parent_id and current_instance.parent_id.instance:
                # Instance has a parent
                browse_instance = current_instance.parent_id
                res[line_data.id] = current_instance.parent_id.instance
            # UFTP-382/BKLG-24: sync the line associated to a register line to the register owner and to the target CC
            # UF-450: send also the AJI to the journal owner
            if line_data and line_data.move_id and line_data.move_id.journal_id and line_data.move_id.journal_id.instance_id and line_data.move_id.journal_id.instance_id.id != current_instance.id:
                if res[line_data.id]:
                    res[line_data.id] = self.get_lower_instance_name(cr, uid, browse_instance, line_data.move_id.journal_id.instance_id, context=context)
                else:
                    res[line_data.id] = line_data.move_id.journal_id.instance_id.instance
        return res

    # Generate delete message for AJI at Project
    def generate_delete_message_at_project(self, cr, uid, ids, vals, context):
        if context is None:
            context = {}

        if context.get('sync_update_execution'):
            # US-450: no delete msg on a sync context
            return False

        # NEED REFACTORING FOR THIS METHOD, if the action write on Analytic.line happens often!
        msf_instance_obj = self.pool.get('msf.instance')
        msg_to_send_obj = self.pool.get("sync.client.message_to_send")
        instance = self.pool.get("sync.client.entity").get_entity(cr, uid, context=context)
        instance_name = instance.name
        instance_identifier = instance.identifier
        msf_instance = self.pool.get('res.users').browse(cr, uid, uid).company_id.instance_id
        instance_level = msf_instance.level
        line_data = self.read(cr, uid, ids, ['cost_center_id'], context=context)
        line_data = dict((data['id'], data) for data in line_data)
        now = fields.datetime.now()

        for id in ids:
            old_cost_center_id = line_data[id]['cost_center_id'] and line_data[id]['cost_center_id'][0] or False
            new_cost_center_id = False
            xml_id = self.get_sd_ref(cr, uid, id, context=context)
            if 'cost_center_id' in vals:
                new_cost_center_id = vals['cost_center_id']
            else:
                new_cost_center_id = old_cost_center_id

            ''' UTP-1128: If the correction is made with the following usecase, do not generate anything:
                If the correction is to replace the cost center of the current instance, say P1 to the cc of P2, the deletion
                must not be generated for P1, because if it got generated, this deletion will be spread up to Coordo, then resync
                back to P1 making that P1 deletes also the line with cost center of P2 <--- this is wrong as stated in the ticket
            '''

            if new_cost_center_id != old_cost_center_id:
                old_destination_name = self.get_instance_name_from_cost_center(cr, uid, old_cost_center_id, context=context)
                new_destination_name = self.get_instance_name_from_cost_center(cr, uid, new_cost_center_id, context=context)
                if old_destination_name != new_destination_name and old_destination_name != instance.name:
                    is_parent = False
                    parent = msf_instance.parent_id
                    while parent:
                        if parent.instance == old_destination_name:
                            is_parent = True
                            break
                        parent = parent.parent_id

                    if not is_parent:
                        this = self.browse(cr, uid, id, context=context)
                        journal_instance = this.move_id and this.move_id.journal_id and this.move_id.journal_id.instance_id and this.move_id.journal_id.instance_id.instance
                        if journal_instance and journal_instance != old_destination_name:
                            # we have sent a orphean AJI to old_destination_name: delete it
                            message_data = {'identifier':'delete_%s_to_%s' % (xml_id, old_destination_name),
                                'sent':False,
                                'generate_message':True,
                                'remote_call':self._name + ".message_unlink_analytic_line",
                                'arguments':"[{'model' :  '%s', 'xml_id' : '%s', 'correction_date' : '%s'}]" % (self._name, xml_id, now),
                                'destination_name':old_destination_name}
                            msg_to_send_obj.create(cr, uid, message_data)



                # Check if the new code center belongs to a project that has *previously* a delete message for the same AJI created but not sent
                # -> remove that delete message from the queue
                new_destination_level = self.get_instance_level_from_cost_center(cr, uid, new_cost_center_id, context=context)
                if new_destination_level == 'project': # Only concern Project (other level has no delete message)
                    new_destination_name = self.get_instance_name_from_cost_center(cr, uid, new_cost_center_id, context=context)
                    if new_destination_name and xml_id:
                        identifier = 'delete_%s_to_%s' % (xml_id, new_destination_name)
                        exist_ids = msg_to_send_obj.search(cr, uid,
                                [('identifier', '=', identifier), ('sent', '=',
                                    False)], order='NO_ORDER')
                        if exist_ids:
                            msg_to_send_obj.unlink(cr, uid, exist_ids, context=context) # delete this unsent delete-message


    def write(self, cr, uid, ids, vals, context=None):
        if context is None:
            context = {}
        if not 'cost_center_id' in vals:
            return super(account_analytic_line, self).write(cr, uid, ids, vals, context=context)

        if isinstance(ids, (long, int)):
            ids = [ids]

        # Only set the correction date if data not come from sync
        if not context.get('sync_update_execution', False):
            vals['correction_date'] = fields.datetime.now() # This timestamp is used for the write, but need to set BEFORE
        # call to generate delete message if the cost center is removed from a project
        self.generate_delete_message_at_project(cr, uid, ids, vals, context)
        return super(account_analytic_line, self).write(cr, uid, ids, vals, context=context)

account_analytic_line()

class account_move_line(osv.osv):
    _inherit = 'account.move.line'

    def write(self, cr, uid, ids, vals, context=None, check=True, update_check=True):
        if context is None:
            context = {}
        res = super(account_move_line, self).write(cr, uid, ids, vals, context=context, check=check, update_check=update_check)
        # Do workflow if line is coming from sync, is now reconciled and it has an unpaid invoice
        if context.get('sync_update_execution', False) and 'reconcile_id' in vals and vals['reconcile_id']:
            invoice_ids = []
            line_list = self.browse(cr, uid, ids, context=context)
            invoice_ids = [line.invoice.id for line in line_list if
                    line.invoice and line.invoice.state != 'paid']
            if self.pool.get('account.invoice').test_paid(cr, uid, invoice_ids):
                self.pool.get('account.invoice').confirm_paid(cr, uid, invoice_ids)
        return res

account_move_line()

class funding_pool_distribution_line(osv.osv):
    _inherit = 'funding.pool.distribution.line'

    def get_destination_name(self, cr, uid, ids, dest_field, context=None):
        if not dest_field == 'cost_center_id':
            return super(funding_pool_distribution_line, self).get_destination_name(cr, uid, ids, dest_field, context=context)

        current_instance = self.pool.get('res.users').browse(cr, uid, uid).company_id.instance_id
        ana_obj = self.pool.get('account.analytic.line')
        res = dict.fromkeys(ids, False)
        for line_id in ids:
            line_data = self.browse(cr, uid, line_id, context=context)
            browse_instance = False
            if line_data.cost_center_id:
                browse_instance = ana_obj.get_browse_instance_name_from_cost_center(cr, uid, line_data.cost_center_id.id, context)
                if browse_instance:
                    res[line_id] = browse_instance.instance
            elif current_instance.parent_id and current_instance.parent_id.instance:
                # Instance has a parent
                browse_instance = current_instance.parent_id
                res[line_id] = current_instance.parent_id.instance
            # UFTP-382: sync down the distrib line associated to the register line
            if line_data.distribution_id and line_data.distribution_id.register_line_ids:
                for stat_line in line_data.distribution_id.register_line_ids:
                    if current_instance.id != stat_line.statement_id.instance_id.id:
                        res[line_id] = stat_line.statement_id.instance_id.instance
            # UFTP-382: sync down the distrib line associated to the project register move line
            elif line_data.distribution_id and line_data.distribution_id.move_line_ids:
                for move_line in line_data.distribution_id.move_line_ids:
                    if move_line.statement_id and move_line.statement_id.instance_id.id != current_instance.id:
                        res[line_id] = move_line.statement_id.instance_id.instance

            # US-450: also sent fp.line to related G/L journal instance
            if line_data.distribution_id and line_data.distribution_id.move_line_ids:
                for move_line in line_data.distribution_id.move_line_ids:
                    if move_line.journal_id:
                        inst = move_line.journal_id and move_line.journal_id.instance_id
                        if inst and inst.id != current_instance.id and inst.instance != res[line_id]:
                            res[line_id] = ana_obj.get_lower_instance_name(cr, uid, browse_instance, inst, context=context)
                        break
        return res

funding_pool_distribution_line()

class cost_center_distribution_line(osv.osv):
    _inherit = 'cost.center.distribution.line'

    def get_destination_name(self, cr, uid, ids, dest_field, context=None):
        if not dest_field == 'analytic_id':
            return super(cost_center_distribution_line, self).get_destination_name(cr, uid, ids, dest_field, context=context)

        current_instance = self.pool.get('res.users').browse(cr, uid, uid).company_id.instance_id
        res = dict.fromkeys(ids, False)
        for line_id in ids:
            line_data = self.browse(cr, uid, line_id, context=context)
            if line_data.analytic_id:
                res[line_id] = self.pool.get('account.analytic.line').get_instance_name_from_cost_center(cr, uid, line_data.analytic_id.id, context)
            elif current_instance.parent_id and current_instance.parent_id.instance:
                # Instance has a parent
                res[line_id] = current_instance.parent_id.instance
        return res

cost_center_distribution_line()

class product_product(osv.osv):
    _inherit = 'product.product'

    def get_unique_xml_name(self, cr, uid, uuid, table_name, res_id):
        product = self.browse(cr, uid, res_id)
        return get_valid_xml_name('product', product.xmlid_code) if product.xmlid_code else \
               super(product_product, self).get_unique_xml_name(cr, uid, uuid, table_name, res_id)

    # UF-2254: Treat the case of product with empty or XXX for default_code
    def write(self, cr, uid, ids, vals, context=None):
        res = super(product_product, self).write(cr, uid, ids, vals, context=context)
        if isinstance(ids, (long, int)):
            ids = [ids]
        res_id = ids[0]

        prod = self.read(cr, uid, res_id, ['default_code'], context=context)['default_code']
        if prod is not None and prod != 'XXX': # normal case, do nothing
            return res

        # if the default_code is empty or XXX, rebuild the xmlid
        model_data_obj = self.pool.get('ir.model.data')
        sdref_ids = model_data_obj.search(cr, uid,
                [('model','=',self._name),('res_id','=',res_id),('module','=','sd')],
                order='NO_ORDER')
        if not sdref_ids: # xmlid not exist in ir model data -> create new
            identifier = self.pool.get('sync.client.entity')._get_entity(cr).identifier
            name = xmlids.get(res_id, self.get_unique_xml_name(cr, uid, identifier, self._table, res_id))
            new_data_id = model_data_obj.create(cr, uid, {
                'noupdate' : False, # don't set to True otherwise import won't work
                'module' : 'sd',
                'last_modification' : now,
                'model' : self._name,
                'res_id' : res_id,
                'version' : 1,
                'name' : name,
            }, context=context)
        else:
            if prod == 'XXX': # if the system created automatically the xmlid in ir_model_data, just delete it!
                model_data_obj.unlink(cr, uid, sdref_ids,context=context)

        return res

    def unlink(self, cr, uid, ids, context=None):
        try:
            res = super(product_product, self).unlink(cr, uid, ids, context=context)
        except AttributeError, e:
            """
            UFTP-208: when deleting a Temporary product (default_code 'XXX')
            comming from GUI duplication, we dive into get_unique_xml_name
            an AttributeError is raised:
                AttributeError: 'Field xmlid_code not found in browse_record(product.product, ID)'

            => browse does not cache for a 'Temporary' Product in get_unique_xml_name...
            => so we intercept this exception
            """
            tolerated_error = "'Field xmlid_code not found in browse_record(product.product,"
            if str(e).startswith(tolerated_error):
                """
                this exception is not raised when deleting a 'regular' product
                """
                return True
            raise e  # default behavior: raise any other AttributeError exception
        return res

product_product()

class product_asset(osv.osv):

    _inherit = "product.asset"

    def get_unique_xml_name(self, cr, uid, uuid, table_name, res_id):
        asset = self.browse(cr, uid, res_id)
        #UF-2148: use the xmlid_name for building the xml for this object
        return get_valid_xml_name('product_asset', (asset.partner_name or 'no_partner'), (asset.product_id.code or 'noprod'), (asset.xmlid_name or 'noname'))

product_asset()


class ir_model_access(osv.osv):
    """
    UF-2146 To allow synchronisation of ir.model.access, must have same sd ref across all instances
    """
    _inherit = "ir.model.access"

    def get_unique_xml_name(self, cr, uid, uuid, table_name, res_id):
        ima = self.browse(cr, uid, res_id)
        return get_valid_xml_name(
                  'ir_model_access',
                  self.pool.get('ir.model').get_sd_ref(cr, uid, ima.model_id.id),
                  ima.name
                )

ir_model_access()

class ir_model(osv.osv):
    """
    UF-2146 sd ref for ir.model to be included in sd ref of ir.model.access
    """
    _inherit = 'ir.model'

    def get_unique_xml_name(self, cr, uid, uuid, table_name, res_id):
        model = self.browse(cr, uid, res_id)
        return get_valid_xml_name('ir_model', model.model)

ir_model()

class button_access_rule(osv.osv):
    """
    Generate an xml ID like BAR_$view-xml-id_$button-name
    so rules can be synchronized between instances after being generated at each instance
    """
    _inherit = 'msf_button_access_rights.button_access_rule'

    def get_unique_xml_name(self, cr, uid, uuid, table_name, res_id):
        bar = self.browse(cr, uid, res_id)
        view_xml_id = self.pool.get('ir.ui.view').get_xml_id(cr, 1, [bar.view_id.id])
        if bar.type == 'action' and bar.xmlname:
            button_name = bar.xmlname
        else:
            button_name = bar.name
        return get_valid_xml_name('BAR', view_xml_id[bar.view_id.id], button_name)

    def _get_is_remote_wh(self, cr, uid, ids, field_name, args, context=None):
        return {}.fromkeys(ids, False)

    def _search_is_remote_wh(self, cr, uid, obj, name, args, context=None):
        if not args:
            return []
        rarg = []
        for arg in args:
            if arg[1] != '=':
                raise osv.except_osv('Error', 'Filter on is_remote_wh not implemented')
            model_data_obj = self.pool.get('ir.model.data')
            mod_ids = model_data_obj.search(cr, uid, [('model', '=', obj._name), ('name', '=like', 'BAR_sync_remote_warehouse%')])
            ids = []
            for m in model_data_obj.read(cr, uid, mod_ids, ['res_id']):
                ids.append(m['res_id'])
            value = arg[2] not in (False, 'f', 'False')
            rarg.append(('id', value and 'in' or 'not in', ids))
        return rarg

    _columns = {
        'is_remote_wh': fields.function(_get_is_remote_wh, type='boolean', string="From RW module", fnct_search=_search_is_remote_wh, method=True),
    }

button_access_rule()

class hr_employee(osv.osv):
    _inherit = 'hr.employee'

    def get_unique_xml_name(self, cr, uid, uuid, table_name, res_id):
        r = self.read(cr, uid, [res_id],
            ['employee_type', 'identification_id'])[0]
        if r['employee_type'] and r['employee_type'] == 'ex' and \
            r['identification_id']:
            return get_valid_xml_name('employee', r['identification_id'])
        else:
            return super(hr_employee, self).get_unique_xml_name(cr, uid, uuid,
                table_name, res_id)

    def unlink(self, cr, uid, ids, context=None):
        super(hr_employee, self).unlink(cr, uid, ids, context)
        if isinstance(ids, (int, long)):
            ids = [ids]
        cr.execute("delete from ir_model_data where model=%s and res_id in %s", (self._name, tuple(ids)))
        return True

hr_employee()
