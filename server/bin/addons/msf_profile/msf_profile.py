# -*- coding: utf-8 -*-
##############################################################################
#
#    OpenERP, Open Source Management Solution
#    Copyright (C) 2011 MSF, TeMPO consulting
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
import base64
from os.path import join as opj
from tools.translate import _
import tools
import os
import logging
from threading import Lock

class patch_scripts(osv.osv):
    _name = 'patch.scripts'
    _logger = logging.getLogger('patch_scripts')

    _columns = {
        'model': fields.text(string='Model', required=True),
        'method': fields.text(string='Method', required=True),
        'run': fields.boolean(string='Is ran ?'),
    }

    _defaults = {
        'model': lambda *a: 'patch.scripts',
    }

    def launch_patch_scripts(self, cr, uid, *a, **b):
        ps_obj = self.pool.get('patch.scripts')
        ps_ids = ps_obj.search(cr, uid, [('run', '=', False)])
        for ps in ps_obj.read(cr, uid, ps_ids, ['model', 'method']):
            method = ps['method']
            model_obj = self.pool.get(ps['model'])
            try:
                getattr(model_obj, method)(cr, uid, *a, **b)
                self.write(cr, uid, [ps['id']], {'run': True})
            except Exception as e:
                err_msg = 'Error with the patch scripts %s.%s :: %s' % (ps['model'], ps['method'], e)
                self._logger.error(err_msg)
                raise osv.except_osv(
                    'Error',
                    err_msg,
                )

    def us_993_patch(self, cr, uid, *a, **b):
        # set no_update to True on USB group_type not to delete it on
        # existing instances
        cr.execute("""
        UPDATE ir_model_data SET noupdate='t'
        WHERE model='sync.server.group_type' AND
        name='sync_remote_warehouse_rule_group_type'
        """)

    def us_918_patch(self, cr, uid, *a, **b):
        update_module = self.pool.get('sync.server.update')
        if update_module:
            # if this script is exucuted on server side, update the first delete
            # update of ZMK to be executed before the creation of ZMW (sequence
            # 4875). Then if ZMK is correctly deleted, ZMW can be added
            cr.execute("UPDATE sync_server_update "
                       "SET sequence=4874 "
                       "WHERE id=2222677")

            # change sdref ZMW to base_ZMW
            cr.execute("UPDATE sync_server_update "
                       "SET sdref='base_ZMW' "
                       "WHERE model='res.currency' AND sdref='ZMW'")

            # remove the ZMK creation update
            cr.execute("DELETE FROM sync_server_update WHERE id=52325;")
            cr.commit()

            # some update where refering to the old currency with sdref=sd.ZMW
            # as the reference changed, we need to modify all of this updates
            # pointing to a wrong reference (currency_rates, ...)
            updates_to_modify = update_module.search(
                cr, uid, [('values', 'like', '%sd.ZMW%')],)
            for update in update_module.browse(cr, uid, updates_to_modify):
                update_values = eval(update.values)
                if 'sd.ZMW' in update_values:
                    index = update_values.index('sd.ZMW')
                    update_values[index] = 'sd.base_ZMW'
                vals = {'values': update_values,}
                update_module.write(cr, uid, update.id, vals)

            # do the same for sdref=sd.base_ZMK
            updates_to_modify = update_module.search(
                cr, uid, [('values', 'like', '%sd.base_ZMK%')],)
            for update in update_module.browse(cr, uid, updates_to_modify):
                update_values = eval(update.values)
                if 'sd.base_ZMK' in update_values:
                    index = update_values.index('sd.base_ZMK')
                    update_values[index] = 'sd.base_ZMW'
                vals = {'values': update_values,}
                update_module.write(cr, uid, update.id, vals)
        else:
            # change the sdref on the client that use the wrong ZMK
            cr.execute("""UPDATE ir_model_data
            SET name='ZMW' WHERE name='ZMK'""")

            cr.execute("""UPDATE ir_model_data
            SET name='base_ZMW' WHERE name='base_ZMK'""")
            cr.commit()

            # check if the currency related to sd.base_ZMW exist, if not,
            # delete the ir_model_data base_ZMW entry and change the ZMW entry to base_ZMW
            cr.execute("""SELECT res_id FROM ir_model_data
            WHERE module='sd' and name='base_ZMW'""")
            res_id = cr.fetchone()
            if res_id and res_id[0]:
                cr.execute("""SELECT id FROM res_currency
                WHERE id=%s""", (res_id[0], ))
                currency_exists = cr.fetchone()
                if not currency_exists:
                    # delete the entry
                    cr.execute("""DELETE FROM ir_model_data
                    WHERE module='sd' AND name='base_ZMW'""")
                    cr.commit()

            # modify the ZMW to base_ZMW
            cr.execute("""UPDATE ir_model_data SET name='base_ZMW'
            WHERE module='sd' AND name='ZMW'""")

            # check if some updates with wrong sdref were ready to be sent and if yes, fix them
            update_module = self.pool.get('sync.client.update_to_send')
            if update_module:
                # change sdref ZMW to base_ZMW
                cr.execute("UPDATE sync_client_update_to_send "
                           "SET sdref='base_ZMW' "
                           "WHERE sdref='base_ZMK'")
                cr.execute("UPDATE sync_client_update_to_send "
                           "SET sdref='ZMW' "
                           "WHERE sdref='ZMK'")
    def us_1061_patch(self, cr, uid, *a, **b):
        '''setup the size on all attachment'''
        attachment_obj = self.pool.get('ir.attachment')
        attachment_ids = attachment_obj.search(cr, uid, [])
        vals = {}
        for attachment in attachment_obj.browse(cr, uid, attachment_ids):
            if attachment.datas and not attachment.size:
                vals['size'] = attachment_obj.get_size(attachment.datas)
                attachment_obj.write(cr, uid, attachment.id, vals)

    def us_898_patch(self, cr, uid, *a, **b):
        context = {}
        # remove period state from upper levels as an instance should be able
        # to see only the children account.period.state's
        period_state_obj = self.pool.get('account.period.state')
        period_obj = self.pool.get('account.period')
        msf_instance_obj = self.pool.get('msf.instance')

        # get the current instance id
        instance_ids = []
        user = self.pool.get('res.users').browse(cr, uid, uid, context=context)
        if user.company_id and user.company_id.instance_id:
            instance_ids = [user.company_id.instance_id.id]

        # get all the children of this instance
        children_ids = msf_instance_obj.get_child_ids(cr, uid)

        # remove period_state that are not concerning current instance or his
        # children
        period_state_ids = []
        period_state_ids = period_state_obj.search(cr, uid,
                            [('instance_id', 'not in', children_ids + instance_ids)])
        if period_state_ids:
            period_state_obj.unlink(cr, uid, period_state_ids)

        # delete ir.model.data related to deleted account.period.state
        model_data = self.pool.get('ir.model.data')
        ids_to_delete = []
        for period_state_id in period_state_ids:
            period_state_xml_id = period_state_obj.get_sd_ref(cr, uid, period_state_id)
            ids_to_delete.append(model_data._get_id(cr, uid, 'sd',
                                                   period_state_xml_id))
        model_data.unlink(cr, uid, ids_to_delete)

        # touch all ir.model.data object related to the curent
        # instance periods
        # this permit to fix incorrect period state on upper level
        # by re-sending state and create the missing period_states
        period_ids = period_obj.search(cr, uid, [('active', 'in', ('t', 'f'))])
        period_state_obj.update_state(cr, uid, period_ids)

    def us_332_patch(self, cr, uid, *a, **b):
        context = {}
        user_obj = self.pool.get('res.users')
        usr = user_obj.browse(cr, uid, [uid], context=context)[0]
        level_current = False

        if usr and usr.company_id and usr.company_id.instance_id:
            level_current = usr.company_id.instance_id.level

        if level_current == 'section':
            # create MSFID for product.nomenclature
            nomen_obj = self.pool.get('product.nomenclature')
            nomen_ids = nomen_obj.search(cr, uid, [('msfid', '=', False)], order='level asc, id')

            for nomen_id in nomen_ids:
                nomen = nomen_obj.browse(cr, uid, nomen_id, context={})
                msfid = ""
                if not nomen.msfid:
                    nomen_parent = nomen.parent_id
                    if nomen_parent and nomen_parent.msfid:
                        msfid = nomen_parent.msfid + "-"
                    name_first_word = nomen.name.split(' ')[0]
                    msfid += name_first_word
                    # Search same msfid
                    ids = nomen_obj.search(cr, uid, [('msfid', '=', msfid)])
                    if ids:
                        msfid += str(nomen.id)
                    nomen_obj.write(cr, uid, nomen.id, {'msfid': msfid})

            # create MSFID for product.category
            categ_obj = self.pool.get('product.category')
            categ_ids = categ_obj.search(cr, uid, [('msfid', '=', False), ('family_id', '!=', False)], order='id')

            for categ in categ_obj.browse(cr, uid, categ_ids, context={}):
                msfid = ""
                if not categ.msfid and categ.family_id and categ.family_id.name:
                    msfid = categ.family_id.name[0:4]
                    ids = categ_obj.search(cr, uid, [('msfid', '=', msfid)])
                    if ids:
                        msfid += str(categ.id)
                    categ_obj.write(cr, uid, categ.id, {'msfid': msfid})

    def update_parent_budget_us_489(self, cr, uid, *a, **b):
        logger = logging.getLogger('update')
        c = self.pool.get('res.users').browse(cr, uid, uid).company_id
        instance_name = c and c.instance_id and c.instance_id.name
        if instance_name == 'BD_DHK_OCA':
            budget_obj = self.pool.get('msf.budget')
            parent_id = budget_obj.search(cr, uid, [('type', '=', 'view'), ('id', '=', 2)])
            child_id = budget_obj.search(cr, uid, [('type', '=', 'normal'), ('id', '=', 4)])
            if not parent_id or not child_id:
                logger.warn('US-489: budget not found, parent: %s, child: %s' % (parent_id, child_id))
                return False
            budget_obj.write(cr, uid, parent_id, {'state': 'draft'})
            budget_obj.unlink(cr, uid, parent_id)
            fields = ['cost_center_id', 'fiscalyear_id', 'decision_moment_id']
            data = budget_obj.read(cr, uid, child_id[0], fields)
            vals = {}
            for f in fields:
                vals[f] = data[f] and data[f][0]
            budget_obj._check_parent(cr, uid, vals)
            budget_obj.update_parent_budgets(cr, uid, child_id)
            logger.warn('US-489: parent budget %s updated' % (parent_id,))

    def us_394_2_patch(self, cr, uid, *a, **b):
        obj = self.pool.get('ir.translation')
        obj.clean_translation(cr, uid, context={})
        obj.add_xml_ids(cr, uid, context={})

    def us_394_3_patch(self, cr, uid, *a, **b):
        self.us_394_2_patch(cr, uid, *a, **b)

    def update_us_435_2(self, cr, uid, *a, **b):
        period_obj = self.pool.get('account.period')
        period_state_obj = self.pool.get('account.period.state')
        periods = period_obj.search(cr, uid, [])
        for period in periods:
            period_state_obj.update_state(cr, uid, period)

        return True

    def update_us_133(self, cr, uid, *a, **b):
        p_obj = self.pool.get('res.partner')
        po_obj = self.pool.get('purchase.order')
        pl_obj = self.pool.get('product.pricelist')

        # Take good pricelist on existing partners
        p_ids = p_obj.search(cr, uid, [])
        fields = [
            'property_product_pricelist_purchase',
            'property_product_pricelist',
        ]
        for p in p_obj.read(cr, uid, p_ids, fields):
            p_obj.write(cr, uid, [p['id']], {
                'property_product_pricelist_purchase': p['property_product_pricelist_purchase'][0],
                'property_product_pricelist': p['property_product_pricelist'][0],
            })

        # Take good pricelist on existing POs
        pl_dict = {}
        po_ids = po_obj.search(cr, uid, [
            ('pricelist_id.type', '=', 'sale'),
        ])
        for po in po_obj.read(cr, uid, po_ids, ['pricelist_id']):
            vals = {}
            if po['pricelist_id'][0] in pl_dict:
                vals['pricelist_id'] = pl_dict[po['pricelist_id'][0]]
            else:
                pl_currency = pl_obj.read(cr, uid, po['pricelist_id'][0], ['currency_id'])
                p_pl_ids = pl_obj.search(cr, uid, [
                    ('currency_id', '=', pl_currency['currency_id'][0]),
                    ('type', '=', 'purchase'),
                ])
                if p_pl_ids:
                    pl_dict[po['pricelist_id'][0]] = p_pl_ids[0]
                    vals['pricelist_id'] = p_pl_ids[0]

            if vals:
                po_obj.write(cr, uid, [po['id']], vals)

    def us_822_patch(self, cr, uid, *a, **b):
        fy_obj = self.pool.get('account.fiscalyear')
        level = self.pool.get('res.users').browse(cr, uid,
            [uid])[0].company_id.instance_id.level

        # create FY15 /FY16 'system' periods (number 0 and 16)
        if level == 'section':
            fy_ids = self.pool.get('account.fiscalyear').search(cr, uid, [
                ('date_start', 'in', ('2015-01-01', '2016-01-01', ))
            ])
            if fy_ids:
                for fy_rec in fy_obj.browse(cr, uid, fy_ids):
                    year = int(fy_rec['date_start'][0:4])
                    periods_to_create = [16, ]
                    if year != 2015:
                        # for FY15 period 0 not needed as no initial balance for
                        # the first FY of UF start
                        periods_to_create.insert(0, 0)

                    self.pool.get('account.year.end.closing').create_periods(cr,
                        uid, fy_rec.id, periods_to_create=periods_to_create)

        # update fiscal year state (new model behaviour-like period state)
        fy_ids = self.pool.get('account.fiscalyear').search(cr, uid, [])
        if fy_ids:
            self.pool.get('account.fiscalyear.state').update_state(cr, uid,
                fy_ids)

        return True

    def us_908_patch(self, cr, uid, *a, **b):
        # add the version to unifield-version.txt as the code which
        # automatically add this version name is contained in the patch itself.
        from updater import re_version, md5hex_size
        import re
        from tools import config
        file_path = os.path.join(config['root_path'], 'unifield-version.txt')
        # get the last known patch line
        # 16679c0321623dd7e13fdd5fad6f677c 2015-12-22 14:30:00 UF2.0-0p1
        with open(file_path, 'r') as f:
            lines = f.readlines()
        #if last_version don't have any name
        # and the previous is UF2.0-0p1
        last_line = lines[-1]
        last_line = last_line.rstrip()
        if not last_line: #  the last is an empty line, no new patch was installed
            return True
        result = re_version.findall(last_line)
        md5sum, date, version_name = result[0]
        if not version_name:
            # check that the previous patch was UF2.1
            previous_line = lines[-2].rstrip() or lines[-3].rstrip() #  may be
                                                # there is a blank line between
            previous_line_res = re_version.findall(previous_line)
            p_md5sum, p_date, p_version_name = previous_line_res[0]
            if p_md5sum == '16679c0321623dd7e13fdd5fad6f677c':
                last_line = '%s %s %s' % (md5sum, date, 'UF2.1-0') + os.linesep
                lines[-1] = last_line
                with open(file_path, 'w') as file:
                        file.writelines(lines)

    def uftp_144_patch(self, cr, uid, *a, **b):
        """
        Sorting Fix in AJI: ref and partner_txt mustn't be empty strings
        """
        cr.execute("UPDATE account_analytic_line SET ref=NULL WHERE ref='';")
        cr.execute("UPDATE account_analytic_line SET partner_txt=NULL WHERE partner_txt='';")

    def disable_crondoall(self, cr, uid, *a, **b):
        cron_obj = self.pool.get('ir.cron')
        cron_ids = cron_obj.search(cr, uid, [('doall', '=', True), ('active', 'in', ['t', 'f'])])
        if cron_ids:
            cron_obj.write(cr, uid, cron_ids, {'doall': False})

    def bar_action_patch(self, cr, uid, *a, **b):
        rules_obj = self.pool.get('msf_button_access_rights.button_access_rule')
        data_obj = self.pool.get('ir.model.data')
        view_obj = self.pool.get('ir.ui.view')
        rule_ids = rules_obj.search(cr, uid, [('xmlname', '=', False), ('type', '=', 'action'), ('view_id', '!=', False), ('active', 'in', ['t', 'f'])])
        view_to_gen = {}
        for rule in rules_obj.read(cr, uid, rule_ids, ['view_id']):
            view_to_gen[rule['view_id'][0]] = True
            rules_obj.unlink(cr, uid, rule['id'])
            d_ids = data_obj.search(cr, uid, [
                ('module', '=', 'sd'),
                ('model', '=', 'msf_button_access_rights.button_access_rule'),
                ('res_id', '=', rule['id'])
                ])
            if d_ids:
                data_obj.unlink(cr, uid, d_ids)
        for view in view_to_gen:
            view_obj.generate_button_access_rules(cr, uid, view)

    def us_1024_send_bar_patch(self, cr, uid, *a, **b):
        context = {}
        user_obj = self.pool.get('res.users')
        ir_ui_obj = self.pool.get('ir.ui.view')
        data_obj = self.pool.get('ir.model.data')
        rules_obj = self.pool.get('msf_button_access_rights.button_access_rule')

        usr = user_obj.browse(cr, uid, [uid], context=context)[0]
        level_current = False

        rule_ids = rules_obj.search(cr, uid, [('xmlname', '=', False), ('type', '=', 'action'), ('view_id', '!=', False), ('active', 'in', ['t', 'f'])])
        if rule_ids:
            data_ids = data_obj.search(cr, uid, [
                ('module', '=', 'sd'),
                ('model', '=', 'msf_button_access_rights.button_access_rule'),
                ('res_id', 'in', rule_ids)
                ])
            if rule_ids:
                data_obj.unlink(cr, uid, data_ids)
            for rule in rules_obj.read(cr, uid, rule_ids, ['type', 'name']):
                xmlname = ir_ui_obj._get_xmlname(cr, uid, rule['type'], rule['name'])
                rules_obj.write(cr, uid, rule['id'], {'xmlname': xmlname})

        if usr and usr.company_id and usr.company_id.instance_id and usr.company_id.instance_id.level == 'section':
            cr.execute('''update ir_model_data
                set touched='[''active'']', last_modification=NOW()
                where module='sd' and model='msf_button_access_rights.button_access_rule'
            ''')

    def update_volume_patch(self, cr, uid, *a, **b):
        """
        Update the volume from dm³ to m³ for OCB databases
        :param cr: Cursor to the database
        :param uid: ID of the res.users that calls the method
        :param a: Unnamed parameters
        :param b: Named parameters
        :return: True
        """
        instance = self.pool.get('res.users').browse(cr, uid, uid).company_id.instance_id
        if instance:
            while instance.level != 'section':
                if not instance.parent_id:
                    break
                instance = instance.parent_id

        if instance and instance.name != 'OCBHQ':
            cr.execute("""
                UPDATE product_template
                SET volume_updated = True
                WHERE volume_updated = False
            """)
        else:
            cr.execute("""
                UPDATE product_template
                SET volume = volume*1000,
                    volume_updated = True
                WHERE volume_updated = False
            """)

    def us_750_patch(self, cr, uid, *a, **b):
        """
        Update the heat_sensitive_item field of product.product
        to 'Yes' if there is a value already defined by de-activated.
        :param cr: Cursor to the database
        :param uid: ID of the res.users that calls this method
        :param a: Non-named parameters
        :param b: Named parameters
        :return: True
        """
        prd_obj = self.pool.get('product.product')
        phs_obj = self.pool.get('product.heat_sensitive')
        data_obj = self.pool.get('ir.model.data')

        heat_id = data_obj.get_object_reference(cr, uid, 'product_attributes', 'heat_yes')[1]
        no_heat_id = data_obj.get_object_reference(cr, uid, 'product_attributes', 'heat_no')[1]

        phs_ids = phs_obj.search(cr, uid, [('active', '=', False)])
        prd_ids = prd_obj.search(cr, uid, [('heat_sensitive_item', '!=', False), ('active', 'in', ['t', 'f'])])
        if prd_ids:
            cr.execute("""
                UPDATE product_product SET heat_sensitive_item = %s, is_kc = True, kc_txt = 'X', show_cold_chain = True WHERE id IN %s
            """, (heat_id, tuple(prd_ids),))

        no_prd_ids = prd_obj.search(cr, uid, [('heat_sensitive_item', '=', False), ('active', 'in', ['t', 'f'])])
        if no_prd_ids:
            cr.execute("""
                UPDATE product_product SET heat_sensitive_item = %s, is_kc = False, kc_txt = '', show_cold_chain = False WHERE id IN %s
            """, (no_heat_id, tuple(no_prd_ids),))

        cr.execute('ALTER TABLE product_product ALTER COLUMN heat_sensitive_item SET NOT NULL')

        return True

    def update_us_963_negative_rule_seq(self, cr, uid, *a, **b):
        if self.pool.get('sync.client.update_received'):
            cr.execute("update sync_client_update_received set rule_sequence=-rule_sequence where is_deleted='t'")

    def another_translation_fix(self, cr, uid, *a, **b):
        if self.pool.get('sync.client.update_received'):
            ir_trans = self.pool.get('ir.translation')
            cr.execute('''select id, xml_id, name from ir_translation where
                xml_id is not null and
                res_id is null and
                type='model'
            ''')
            for x in cr.fetchall():
                res_id = ir_trans._get_res_id(cr, uid, name=x[2], sdref=x[1])
                if res_id:
                    cr.execute('update ir_translation set res_id=%s where id=%s', (res_id, x[0]))
        return True

    def another_other_translation_fix_bis(self, cr, uid, *a, **b):
        c = self.pool.get('res.users').browse(cr, uid, uid).company_id
        instance_name = c and c.instance_id and c.instance_id.name or ''
        logger = logging.getLogger('update')
        if instance_name.startswith('OCG'):
            logger.warn('Execute US-1527 script')
            self.another_other_translation_fix(cr, uid, *a, **b)
        else:
            logger.warn('Do not execute US-1527 script')
        return True

    def another_other_translation_fix(self, cr, uid, *a, **b):
        cr.execute('''
            DELETE FROM ir_model_data WHERE model = 'ir.translation'
            AND res_id IN (SELECT id FROM ir_translation WHERE res_id = 0 AND name = 'product.template,name')
        ''')
        cr.execute('''
            DELETE FROM ir_translation WHERE res_id = 0 AND name = 'product.template,name'
        ''')
        return True

    def clean_far_updates(self, cr, uid, *a, **b):
        '''
        US-1148: is_keep_cool has been removed on product
        delete FAR line update related to this old fields
        '''
        if self.pool.get('sync.server.update'):
            cr.execute("delete from sync_server_update where values like '%msf_outgoing.field_product_product_is_keep_cool%' and model='msf_field_access_rights.field_access_rule_line'")

    def us_1185_patch(self, cr, uid, *a, **b):
        # AT HQ level: untick 8/9 top accounts for display in BS/PL report
        user_rec = self.pool.get('res.users').browse(cr, uid, [uid])[0]
        if user_rec.company_id and user_rec.company_id.instance_id \
            and user_rec.company_id.instance_id.level == 'section':
            account_obj = self.pool.get('account.account')
            codes = ['8', '9', ]

            ids = account_obj.search(cr, uid, [
                ('type', '=', 'view'),
                ('code', 'in', codes),
            ])
            if ids and len(ids) == len(codes):
                account_obj.write(cr, uid, ids, {
                    'display_in_reports': False,
                })

    def us_1263_patch(self, cr, uid, *a, **b):
        ms_obj = self.pool.get('stock.mission.report')
        msl_obj = self.pool.get('stock.mission.report.line')

        ms_touched = "['name']"
        msl_touched = "['internal_qty']"

        ms_ids = ms_obj.search(cr, uid, [('local_report', '=', True)])
        if not ms_ids:
            return True

        # Touched Mission stock reports
        cr.execute('''UPDATE ir_model_data
                      SET touched = %s, last_modification = now()
                      WHERE model =  'stock.mission.report' AND res_id in %s''', (ms_touched, tuple(ms_ids),))
        # Touched Mission stock report lines
        cr.execute('''UPDATE ir_model_data
                      SET touched = %s, last_modification = now()
                      WHERE
                          model = 'stock.mission.report.line'
                          AND
                          res_id IN (SELECT l.id
                                     FROM stock_mission_report_line l
                                     WHERE
                                       l.mission_report_id IN %s
                                       AND (l.internal_qty != 0.00
                                       OR l.stock_qty != 0.00
                                       OR l.central_qty != 0.00
                                       OR l.cross_qty != 0.00
                                       OR l.secondary_qty != 0.00
                                       OR l.cu_qty != 0.00
                                       OR l.in_pipe_qty != 0.00
                                       OR l.in_pipe_coor_qty != 0.00))''', (msl_touched, tuple(ms_ids)))
        return True

    def us_1273_patch(self, cr, uid, *a, **b):
        # Put all internal requests import_in_progress field to False
        ir_obj = self.pool.get('sale.order')
        context = {'procurement_request': True}
        ir_ids = ir_obj.search(cr, uid, [('import_in_progress', '=', True)], context=context)
        if ir_ids:
            ir_obj.write(cr, uid, ir_ids, {'import_in_progress': False})
        return True

    def us_1297_patch(self, cr, uid, *a, **b):
        """
        Correct budgets with View Type Cost Center (consolidation)
        """
        budget_obj = self.pool.get('msf.budget')
        # apply the patch only if there are budgets on several fiscal years
        sql_count_fy = "SELECT COUNT(DISTINCT(fiscalyear_id)) FROM msf_budget;"
        cr.execute(sql_count_fy)
        count_fy = cr.fetchone()[0]
        if count_fy > 1:
            # get only budgets already validated
            sql_budgets = "SELECT id FROM msf_budget WHERE type != 'view' AND state != 'draft';"
            cr.execute(sql_budgets)
            budgets = cr.fetchall()
            if budgets:
                budget_to_correct_ids = [x and x[0] for x in budgets]
                # update the parent budgets
                budget_obj.update_parent_budgets(cr, uid, budget_to_correct_ids)
        return True

    def us_1427_patch(self, cr, uid, *a, **b):
        """
        Put active all inactive products with stock quantities in internal locations
        """
        sql = """
        UPDATE product_product SET active = 't' WHERE id IN (
            SELECT DISTINCT(q.product_id) FROM (
            SELECT location_id, product_id, sum(sm.product_qty) AS qty
                FROM (
                    (
                        SELECT location_id, product_id, sum(-product_qty) AS product_qty
                        FROM stock_move
                        WHERE location_id IN (SELECT id FROM stock_location WHERE usage = 'internal') AND state = 'done'
                        GROUP BY location_id, product_id
                    )
                    UNION
                    (
                        SELECT location_dest_id, product_id, sum(product_qty) AS product_qty
                        FROM stock_move
                        WHERE location_dest_id IN (SELECT id FROM stock_location WHERE usage = 'internal') AND state = 'done'
                        GROUP BY location_dest_id, product_id
                    )
                ) AS sm GROUP BY location_id, product_id) AS q
            LEFT JOIN product_product pp ON q.product_id = pp.id WHERE q.qty > 0 AND pp.active = 'f' ORDER BY q.product_id)
        """
        cr.execute(sql)
        return True

    def us_1452_patch(self, cr, uid, *a, **b):
        """
        Put 1.00 as cost price for all product with cost price = 0.00
        """
        setup_obj = self.pool.get('unifield.setup.configuration')
        setup_br = setup_obj.get_config(cr, uid)
        sale_percent = 1.00
        if setup_br:
            sale_percent = 1 + (setup_br.sale_price/100.00)


        sql = """UPDATE product_template SET standard_price = 1.00, list_price = %s WHERE standard_price = 0.00"""
        cr.execute(sql, (sale_percent, ))
        return True

patch_scripts()


class ir_model_data(osv.osv):
    _inherit = 'ir.model.data'
    _name = 'ir.model.data'

    def _update(self,cr, uid, model, module, values, xml_id=False, store=True, noupdate=False, mode='init', res_id=False, context=None):
        """
            Store in context that we came from _update
        """
        if not context:
            context = {}
        ctx = context.copy()
        ctx['update_mode'] = mode
        return super(ir_model_data, self)._update(cr, uid, model, module, values, xml_id, store, noupdate, mode, res_id, ctx)

    def patch13_install_export_import_lang(self, cr, uid, *a, **b):
        mod_obj = self.pool.get('ir.module.module')
        mod_ids = mod_obj.search(cr, uid, [('name', '=', 'export_import_lang')])
        if mod_ids and mod_obj.read(cr, uid, mod_ids, ['state'])[0]['state'] == 'uninstalled':
            mod_obj.write(cr, uid, mod_ids[0], {'state': 'to install'})

    def us_254_fix_reconcile(self, cr, uid, *a, **b):
        c = self.pool.get('res.users').browse(cr, uid, uid).company_id
        sql_file = opj('msf_profile', 'data', 'us_254.sql')
        instance_name = c and c.instance_id and c.instance_id.name
        if instance_name in ['OCBHT101', 'OCBHT143', 'OCBHQ']:
            logger = logging.getLogger('update')
            try:
                fp = tools.file_open(sql_file, 'r')
                logger.warn('Execute us-254 sql')
                cr.execute(fp.read())
                fp.close()
                logger.warn('Sql done')
                os.rename(fp.name, "%sold" % fp.name)
                logger.warn('Sql file renamed')
            except IOError, e:
                # file does not exist
                pass

    def _us_268_gen_message(self, cr, uid, obj, id, fields, values):
        msg_obj = self.pool.get("sync.client.message_to_send")
        xmlid = obj.get_sd_ref(cr, uid, id)
        data = {
            'identifier': 'us_268_fix_%s_%s' % (obj._name, id),
            'sent': False,
            'generate_message': True,
            'remote_call': "ir.model.data._query_from_sync",
            'arguments':"['%s', '%s', %r, %r]" % (obj._name, xmlid, fields, values),
            'destination_name': 'OCBHQ',
        }
        msg_obj.create(cr, uid, data)

    def us_268_fix_seq(self, cr, uid, *a, **b):
        msg_obj = self.pool.get("sync.client.message_to_send")
        if not msg_obj:
            return True
        c = self.pool.get('res.users').browse(cr, uid, uid).company_id
        instance_name = c and c.instance_id and c.instance_id.name
        touch_file = opj('msf_profile', 'data', 'us_268.sql')
        # TODO: set as done
        if instance_name == 'OCBHT143':
            logger = logging.getLogger('update')
            try:
                fp = tools.file_open(touch_file, 'r')
                logger.warn('Execute us-268 sql')
                cr.execute(fp.read())
                fp.close()
                logger.warn('Sql done')
                os.rename(fp.name, "%sold" % fp.name)
                logger.warn('Sql file renamed')
            except IOError, e:
                # file does not exist
                pass

        elif instance_name == 'OCBHT101' and msg_obj:
            logger = logging.getLogger('update')
            try:
                fp = tools.file_open(touch_file, 'r')
                fp.close()
            except IOError, e:
                return True
            logger.warn('Execute US-268 queries')
            journal_obj = self.pool.get('account.journal')
            instance_id = c.instance_id.id
            account_move_obj = self.pool.get('account.move')
            analytic_obj = self.pool.get('account.analytic.line')
            invoice_obj = self.pool.get('account.invoice')

            journal_id = journal_obj.search(cr, uid, [('type', '=', 'purchase'), ('is_current_instance', '=', True)])[0]
            journal = journal_obj.browse(cr, uid, journal_id)

            analytic_journal_id = journal.analytic_journal_id.id

            move_ids_to_fix = [453, 1122, 1303]

            instance_xml_id = self.pool.get('msf.instance').get_sd_ref(cr, uid, instance_id)
            journal_xml_id = journal_obj.get_sd_ref(cr, uid, journal_id)
            analytic_journal_xml_id = self.pool.get('account.analytic.journal').get_sd_ref(cr, uid, analytic_journal_id)

            move_prefix = c.instance_id.move_prefix

            for move in account_move_obj.browse(cr, uid, move_ids_to_fix):
                if move.instance_id.id == instance_id:
                    # fix already applied
                    continue

                seq_name = self.pool.get('ir.sequence').get_id(cr, uid, journal.sequence_id.id, context={'fiscalyear_id': move.period_id.fiscalyear_id.id})
                reference = '%s-%s-%s' % (move_prefix, journal.code, seq_name)

                cr.execute('update account_move set instance_id=%s, journal_id=%s, name=%s where id=%s', (instance_id, journal_id, reference, move.id))
                invoice_ids = invoice_obj.search(cr, uid, [('move_id', '=', move.id)])
                if invoice_ids:
                    cr.execute('update account_invoice set journal_id=%s, number=%s where id=%s', (journal_id, reference, invoice_ids[0]))

                self._us_268_gen_message(cr, uid, account_move_obj, move.id,
                    ['instance_id', 'journal_id', 'name'], [instance_xml_id, journal_xml_id, reference]
                )
                for line in move.line_id:
                    cr.execute('update account_move_line set instance_id=%s, journal_id=%s where id=%s', (instance_id, journal_id, line.id))
                    self._us_268_gen_message(cr, uid, self.pool.get('account.move.line'), line.id,
                        ['instance_id', 'journal_id'], [instance_xml_id, journal_xml_id]
                    )

                    analytic_ids = analytic_obj.search(cr, uid, [('move_id', '=', line.id)])

                    for analytic_id in analytic_ids:
                        cr.execute('update account_analytic_line set instance_id=%s, entry_sequence=%s, journal_id=%s where id=%s', (instance_id, reference, analytic_journal_id, analytic_id))
                        self._us_268_gen_message(cr, uid, analytic_obj, analytic_id,
                            ['instance_id', 'entry_sequence', 'journal_id'], [instance_xml_id, reference, analytic_journal_xml_id]
                        )
            os.rename(fp.name, "%sold" % fp.name)
            logger.warn('Set US-268 as executed')


ir_model_data()

class account_installer(osv.osv_memory):
    _inherit = 'account.installer'
    _name = 'account.installer'

    _defaults = {
        'charts': 'msf_chart_of_account',
    }

    # Fix for UF-768: correcting fiscal year and name
    def execute(self, cr, uid, ids, context=None):
        super(account_installer, self).execute(cr, uid, ids, context=context)
        # Retrieve created fiscal year
        fy_obj = self.pool.get('account.fiscalyear')
        for res in self.read(cr, uid, ids, context=context):
            if 'date_start' in res and 'date_stop' in res:
                f_ids = fy_obj.search(cr, uid, [('date_start', '<=', res['date_start']), ('date_stop', '>=', res['date_stop']), ('company_id', '=', res['company_id'])], context=context)
                if len(f_ids) > 0:
                    # we have one
                    new_name = "FY " + res['date_start'][:4]
                    new_code = "FY" + res['date_start'][:4]
                    if int(res['date_start'][:4]) != int(res['date_stop'][:4]):
                        new_name = "FY " + res['date_start'][:4] +'-'+ res['date_stop'][:4]
                        new_code = "FY" + res['date_start'][2:4] +'-'+ res['date_stop'][2:4]
                    vals = {
                        'name': new_name,
                        'code': new_code,
                    }
                    fy_obj.write(cr, uid, f_ids, vals, context=context)
        return

account_installer()

class res_config_view(osv.osv_memory):
    _inherit = 'res.config.view'
    _name = 'res.config.view'
    _defaults={
        'view': 'extended',
    }
res_config_view()

class base_setup_company(osv.osv_memory):
    _inherit = 'base.setup.company'
    _name = 'base.setup.company'

    def default_get(self, cr, uid, fields_list=None, context=None):
        ret = super(base_setup_company, self).default_get(cr, uid, fields_list, context)
        if not ret.get('name'):
            ret.update({'name': 'MSF', 'street': 'Rue de Lausanne 78', 'street2': 'CP 116', 'city': 'Geneva', 'zip': '1211', 'phone': '+41 (22) 849.84.00'})
            company = self.pool.get('res.users').browse(cr, uid, uid, context=context).company_id
            ret['name'] = company.name
            addresses = self.pool.get('res.partner').address_get(cr, uid, company.id, ['default'])
            default_id = addresses.get('default', False)
            # Default address
            if default_id:
                address = self.pool.get('res.partner.address').browse(cr, uid, default_id, context=context)
                for field in ['street','street2','zip','city','email','phone']:
                    ret[field] = address[field]
                for field in ['country_id','state_id']:
                    if address[field]:
                        ret[field] = address[field].id
            # Currency
            cur = self.pool.get('res.currency').search(cr, uid, [('name','=','EUR')])
            if company.currency_id:
                ret['currency'] = company.currency_id.id
            elif cur:
                ret['currency'] = cur[0]

            fp = tools.file_open(opj('msf_profile', 'data', 'msf.jpg'), 'rb')
            ret['logo'] = base64.encodestring(fp.read())
            fp.close()
        return ret

base_setup_company()

class res_users(osv.osv):
    _inherit = 'res.users'
    _name = 'res.users'

    def _get_default_ctx_lang(self, cr, uid, context=None):
        config_lang = self.pool.get('unifield.setup.configuration').get_config(cr, uid).lang_id
        if config_lang:
            return config_lang
        if self.pool.get('res.lang').search(cr, uid, [('translatable','=',True), ('code', '=', 'en_MF')]):
            return 'en_MF'
        return 'en_US'

    _defaults = {
        'context_lang': _get_default_ctx_lang,
    }
res_users()

class email_configuration(osv.osv):
    _name = 'email.configuration'
    _description = 'Email configuration'

    _columns = {
        'smtp_server': fields.char('SMTP Server', size=512, required=True),
        'email_from': fields.char('Email From', size=512, required=True),
        'smtp_port': fields.integer('SMTP Port', required=True),
        'smtp_ssl': fields.boolean('Use SSL'),
        'smtp_user': fields.char('SMTP User', size=512),
        'smtp_password': fields.char('SMTP Password', size=512),
        'destination_test': fields.char('Email Destination Test', size=512),
    }
    _defaults = {
        'smtp_port': 25,
        'smtp_ssl': False,
    }

    def set_config(self, cr):
        data = ['smtp_server', 'email_from', 'smtp_port', 'smtp_ssl', 'smtp_user', 'smtp_password']
        cr.execute("""select """+','.join(data)+"""
            from email_configuration
            limit 1
        """)
        res = cr.fetchone()
        if res:
            for i, key in enumerate(data):
                tools.config[key] = res[i] or False
        return True

    def __init__(self, pool, cr):
        super(email_configuration, self).__init__(pool, cr)
        cr.execute("SELECT relname FROM pg_class WHERE relkind IN ('r','v') AND relname=%s", (self._table,))
        if cr.rowcount:
            self.set_config(cr)

    def _update_email_config(self, cr, uid, ids, context=None):
        self.set_config(cr)
        return True

    def test_email(self, cr, uid, ids, context=None):
        cr.execute('select destination_test from email_configuration limit 1')
        res = cr.fetchone()
        if not res or not res[0]:
            raise osv.except_osv(_('Warning !'), _('No destination email given!'))
        if not tools.email_send(False, [res[0]], 'Test email from UniField', 'This is a test.'):
            raise osv.except_osv(_('Warning !'), _('Could not deliver email'))
        return True

    _constraints = [
        (_update_email_config, 'Always true: update email configuration', [])
    ]
email_configuration()

class ir_cron_linux(osv.osv_memory):
    _name = 'ir.cron.linux'
    _description = 'Start memory cleaning cron job from linux crontab'
    _columns = {
    }

    def __init__(self, *a, **b):
        self._logger = logging.getLogger('ir.cron.linux')
        self._jobs = {
            'memory_clean': ('osv_memory.autovacuum', 'power_on', ()),
            'save_puller': ('sync.server.update', '_save_puller', ())
        }
        self.running = {}
        for job in self._jobs:
            self.running[job] = Lock()

        super(ir_cron_linux, self).__init__(*a, **b)

    def execute_job(self, cr, uid, job, context=None):
        if job not in self._jobs:
            raise osv.except_osv(_('Warning !'), _('Job does not exists'))
        if uid != 1:
            raise osv.except_osv(_('Warning !'), _('Permission denied'))
        if not self.running[job].acquire(False):
            self._logger.info("Linux cron: job %s already running" % (job, ))
            return False
        try:
            self._logger.info("Linux cron: starting job %s" % (job, ))
            obj = self.pool.get(self._jobs[job][0])
            fct = getattr(obj, self._jobs[job][1])
            args = self._jobs[job][2]
            fct(cr, uid, *args)
            self._logger.info("Linux cron: job %s done" % (job, ))
        except Exception, e:
            self._logger.warning('Linux cron: job %s failed' % (job, ), exc_info=1)
        finally:
            self.running[job].release()
        return True

ir_cron_linux()
