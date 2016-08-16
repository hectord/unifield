#!/usr/bin/env python
# -*- coding: utf-8 -*-
##############################################################################
#
#    OpenERP, Open Source Management Solution
#    Copyright (C) 2012 TeMPO Consulting, MSF. All Rights Reserved
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

from zipfile import ZipFile as zf
from zipfile import is_zipfile
import py7zlib
from osv import osv
from osv import fields
from tempfile import NamedTemporaryFile,mkdtemp
import csv
from base64 import decodestring
from time import strftime
from tools.misc import ustr
from addons import get_module_resource
from tools.which import which
from tools.translate import _
from lxml import etree
import subprocess
import os
import shutil

try:
    from io import BytesIO
except ImportError:
    from cStringIO import StringIO as BytesIO


def get_7z():
    if os.name == 'nt':
        return get_module_resource('msf_homere_interface', 'wizard', '7za.exe')
    try:
        return which('7z')
    except:
        raise osv.except_osv(_('Error'), _('7z is not installed on the server. Please install the package p7zip-full'))



class hr_payroll_import_confirmation(osv.osv_memory):
    _name = 'hr.payroll.import.confirmation'
    _description = 'Import Confirmation'

    _columns = {
        'updated': fields.integer(string="Updated", size=64, readonly=True),
        'created': fields.integer(string="Created", size=64, readonly=True),
        'total': fields.integer(string="Processed", size=64, readonly=True),
        'state': fields.selection([('none', 'None'), ('employee', 'From Employee'), ('payroll', 'From Payroll'), ('hq', 'From HQ Entries')],
            string="State", required=True, readonly=True),
        'error_line_ids': fields.many2many("hr.payroll.employee.import.errors", "employee_import_error_relation", "wizard_id", "error_id", "Error list",
            readonly=True),
        'errors': fields.text(string="Errors", readonly=True),
        'nberrors': fields.integer(string="Errors", readonly=True),
        'filename': fields.char(string="Filename", size=256, readonly=True),
    }

    _defaults = {
        'updated': lambda *a: 0,
        'created': lambda *a: 0,
        'total': lambda *a: 0,
        'state': lambda *a: 'none',
        'nberrors': lambda *a: 0,
    }

    def create(self, cr, uid, vals, context=None):
        """
        Attach errors if context contents "employee_import_wizard_ids"
        """
        if not context:
            context={}
        if context.get('employee_import_wizard_ids', False):
            wiz_ids = context.get('employee_import_wizard_ids')
            if isinstance(wiz_ids, (int, long)):
                wiz_ids = [wiz_ids]
            line_ids = self.pool.get('hr.payroll.employee.import.errors').search(cr, uid, [('wizard_id', 'in', wiz_ids)])
            if line_ids:
                vals.update({'error_line_ids': [(6, 0, line_ids)], 'nberrors': len(line_ids) or 0})
        return super(hr_payroll_import_confirmation, self).create(cr, uid, vals, context)

    def fields_view_get(self, cr, uid, view_id=None, view_type='form', context=None, toolbar=False, submenu=False):
        """
        Change message field
        """
        if not context:
            context = {}
        view = super(hr_payroll_import_confirmation, self).fields_view_get(cr, uid, view_id, view_type, context, toolbar, submenu)
        if view_type=='form' and context.get('message', False):
            message = context.get('message')
            tree = etree.fromstring(view['arch'])
            labels = tree.xpath('/form/label[@string="Nothing"]')
            for label in labels:
                label.set('string', "%s" % message)
            view['arch'] = etree.tostring(tree)
        return view

    def button_validate(self, cr, uid, ids, context=None):
        """
        Return rigth view
        """
        if not context:
            return {'type': 'ir.actions.act_window_close'}
        # Clean up error table
        if context.get('employee_import_wizard_ids', False):
            wiz_ids = context.get('employee_import_wizard_ids')
            if isinstance(wiz_ids, (int, long)):
                wiz_ids = [wiz_ids]
            line_ids = self.pool.get('hr.payroll.employee.import.errors').search(cr, uid, [('wizard_id', 'in', wiz_ids)])
            if line_ids:
                self.pool.get('hr.payroll.employee.import.errors').unlink(cr, uid, line_ids)
        if context.get('from', False):
            result = False
            domain = False
            if context.get('from') == 'employee_import':
                result = ('editable_view_employee_tree', 'hr.employee')
                context.update({'search_default_active': 1})
                domain = "[('employee_type', '=', 'local')]"
            if context.get('from') == 'payroll_import':
                result = ('view_hr_payroll_msf_tree', 'hr.payroll.msf')
                domain = "[('state', '=', 'draft'), ('account_id.is_analytic_addicted', '=', True)]"
            if context.get('from') == 'hq_entries_import':
                result = ('hq_entries_tree', 'hq.entries', 'account_hq_entries')
                domain = ""
                context.update({'search_default_non_validated': 1})
            if context.get('from') == 'expat_employee_import':
                context.update({'search_default_employee_type_expatriate': 1})
                action = self.pool.get('ir.actions.act_window').for_xml_id(cr,
                    uid, 'hr', 'open_view_employee_list_my', context=context)
                action['target'] = 'same'
                action['context'] = context
                return action
            if context.get('from') == 'nat_staff_import':
                result = ('inherit_view_employee_tree', 'hr.employee')
                context.update({'search_default_employee_type_local': 1, 'search_default_active': 1})
            if result:
                module_name = 'msf_homere_interface'
                if result and len(result) > 2:
                    module_name = result[2]
                view_id = self.pool.get('ir.model.data').get_object_reference(cr, uid, module_name, result[0])
                if view_id:
                    view_id = view_id and view_id[1] or False
                return {
                    'type': 'ir.actions.act_window',
                    'res_model': result[1],
                    'view_type': 'form',
                    'view_mode': 'tree,form',
                    'view_id': [view_id],
                    'target': 'crush',
                    'context': context,
                    'domain': domain,
                }
        return {'type': 'ir.actions.act_window_close', 'context': context}

hr_payroll_import_confirmation()

class hr_payroll_employee_import_errors(osv.osv):
    _name = 'hr.payroll.employee.import.errors'
    _rec_name = 'wizard_id'
    _description = 'Employee Import Errors'

    _columns = {
        'wizard_id': fields.integer("Payroll employee import wizard", readonly=True, required=True),
        'msg': fields.text("Message", readonly=True, required=True),
    }

hr_payroll_employee_import_errors()

class hr_payroll_employee_import(osv.osv_memory):
    _name = 'hr.payroll.employee.import'
    _description = 'Employee Import'

    _columns = {
        'file': fields.binary(string="File", filters='*.zip', required=True),
        'filename': fields.char(string="Imported filename", size=256),
    }

    def update_employee_check(self, cr, uid,
        staffcode=False, missioncode=False, staff_id=False, uniq_id=False,
        wizard_id=None, employee_name=False, registered_keys=None):
        """
        Check that:
        - no more than 1 employee exist for "missioncode + staff_id + uniq_id"
        - only one employee have this staffcode
        :return (ok, what_changed)
        :rtype tuple
        """
        def changed(mission1, mission2, staff1, staff2, unique1, unique2):
            res = None
            if mission1 != mission2:
                res = 'mission'
            elif staff1 != staff2:
                res = 'staff'
            elif unique1 != unique2:
                res = 'unique'
            return res

        res = False
        what_changed = None

        # Checks
        if not staffcode or not missioncode or not staff_id or not uniq_id:
            name = employee_name or _('Nonamed Employee')
            message = _('Unknown error for employee %s') % name
            if not staffcode:
                message = _('No "code_staff" found for employee %s!') % (name,)
            elif not missioncode:
                message = _('No "code_terrain" found for employee %s!') % (name,)
            elif not staff_id:
                message = _('No "id_staff" found for employee %s!') % (name,)
            elif not uniq_id:
                message = _('No "id_unique" found for employee %s!') % (name,)
            self.pool.get('hr.payroll.employee.import.errors').create(cr, uid, {'wizard_id': wizard_id, 'msg': message})
            return (res, what_changed)

        # Check employees

        # US-1404: check duplicates on the import files itself
        # => as not already in db
        check_key = missioncode + staff_id + uniq_id
        if check_key in registered_keys:
            self.pool.get('hr.payroll.employee.import.errors').create(cr, uid, {
                'wizard_id': wizard_id,
                'msg': _("Import file have more than one employee with the combination key codeterrain/id_staff(/id_unique) of this employee: %s") % (employee_name,)
                })
            return (res, what_changed)

        # check duplicates already in db
        search_ids = self.pool.get('hr.employee').search(cr, uid, [('homere_codeterrain', '=', missioncode), ('homere_id_staff', '=', staff_id), ('homere_id_unique', '=', uniq_id)])
        if search_ids and len(search_ids) > 1:
            self.pool.get('hr.payroll.employee.import.errors').create(cr, uid, {
                'wizard_id': wizard_id,
                'msg': _("Database have more than one employee with the unique code of this employee: %s") % (employee_name,)
                })
            return (res, what_changed)

        # Check staffcode
        staffcode_ids = self.pool.get('hr.employee').search(cr, uid, [('identification_id', '=', staffcode)])
        if staffcode_ids:
            message = "Several employee have the same ID code: "
            employee_error_list = []
            # UTP-1098: Do not make an error if the employee have the same code staff and the same name
            for employee in self.pool.get('hr.employee').browse(cr, uid, staffcode_ids):
                what_changed = changed(employee.homere_codeterrain, missioncode, str(employee.homere_id_staff), staff_id, employee.homere_id_unique, uniq_id)
                if employee.name == employee_name:
                    continue
                if what_changed != None:
                    employee_error_list.append(employee.name)
            if employee_error_list:
                message += ' ; '.join([employee_name] + employee_error_list)
                self.pool.get('hr.payroll.employee.import.errors').create(cr, uid, {'wizard_id': wizard_id, 'msg': message})
                return (res, what_changed)

        res = True
        return (res, what_changed)

    def read_employee_infos(self, cr, uid, line='', context=None):
        """
        Read each line to extract infos (code, name and surname)
        """
        res = False
        code_staff = line.get('code_staff', False)
        nom = line.get('nom', False)
        prenom = line.get('prenom', False)
        if code_staff:
            res = (code_staff, nom, prenom)
        return res

    def update_employee_infos(self, cr, uid, employee_data='', wizard_id=None,
        line_number=None, registered_keys=None):
        """
        Get employee infos and set them to DB.
        """
        # Some verifications
        created = 0
        updated = 0
        if not employee_data or not wizard_id:
            message = _('No data found for this line: %s.') % line_number
            self.pool.get('hr.payroll.employee.import.errors').create(cr, uid, {'wizard_id': wizard_id, 'msg': message})
            return False, created, updated
        # Prepare some values
        vals = {}
        current_date = strftime('%Y-%m-%d')
        # Extract information
        try:
            code_staff = employee_data.get('code_staff', False)
            codeterrain = employee_data.get('codeterrain', False)
            commentaire = employee_data.get('commentaire', False)
            datenaissance = employee_data.get('datenaissance', False)
            decede = employee_data.get('decede', False)
            email = employee_data.get('email', False)
            id_staff = employee_data.get('id_staff', False)
            id_unique = employee_data.get('id_unique', False)
            nation = employee_data.get('nation', False)
            nom = employee_data.get('nom', False)
            num_soc = employee_data.get('num_soc', False)
            portable = employee_data.get('portable', False)
            prenom = employee_data.get('prenom', False)
            sexe = employee_data.get('sexe', False)
            statutfamilial = employee_data.get('statutfamilial', False)
            tel_bureau = employee_data.get('tel_bureau', False)
            tel_prive = employee_data.get('tel_prive', False)
        except ValueError, e:
            raise osv.except_osv(_('Error'), _('The given file is probably corrupted!\n%s') % (e))
        # Process data
        # Due to UF-1742, if no id_unique, we fill it with "empty"
        uniq_id = id_unique or False
        if not id_unique:
            uniq_id = 'empty'
        if codeterrain and id_staff and code_staff:
            # Employee name
            employee_name = (nom and prenom and ustr(nom) + ', ' + ustr(prenom)) or (nom and ustr(nom)) or (prenom and ustr(prenom)) or False

            # Do some check
            employee_check, what_changed = self.update_employee_check(cr, uid,
                staffcode=ustr(code_staff), missioncode=ustr(codeterrain),
                staff_id=id_staff, uniq_id=ustr(uniq_id),
                wizard_id=wizard_id, employee_name=employee_name,
                registered_keys=registered_keys)
            if not employee_check and not what_changed:
                return False, created, updated

            # Search employee regarding a unique trio: codeterrain, id_staff, id_unique
            e_ids = self.pool.get('hr.employee').search(cr, uid, [('homere_codeterrain', '=', codeterrain), ('homere_id_staff', '=', id_staff), ('homere_id_unique', '=', uniq_id)])
            # UTP-1098: If what_changed is not None, we should search the employee only on code_staff
            if what_changed:
                e_ids = self.pool.get('hr.employee').search(cr, uid, [('identification_id', '=', ustr(code_staff)), ('name', '=', employee_name)])
            # Prepare vals
            res = False
            vals = {
                'active': True,
                'employee_type': 'local',
                'homere_codeterrain': codeterrain,
                'homere_id_staff': id_staff,
                'homere_id_unique': uniq_id,
                'photo': False,
                'identification_id': code_staff or False,
                'notes': commentaire and ustr(commentaire) or '',
                'birthday': datenaissance or False,
                'work_email': email or False,
                # Do "NOM, Prenom"
                'name': employee_name,
                'ssnid': num_soc or False,
                'mobile_phone': portable or False,
                'work_phone': tel_bureau or False,
                'private_phone': tel_prive or False,
            }
            # Update Birthday if equal to 0000-00-00
            if datenaissance and datenaissance == '0000-00-00':
                vals.update({'birthday': False,})
            # Update Nationality
            if nation:
                n_ids = self.pool.get('res.country').search(cr, uid, [('code', '=', ustr(nation))])
                res_nation = False
                # Only get nationality if one result
                if n_ids:
                    if len(n_ids) == 1:
                        res_nation = n_ids[0]
                    else:
                        raise osv.except_osv(_('Error'), _('An error occured on nationality. Please verify all nationalities.'))
                vals.update({'country_id': res_nation})
            # Update gender
            if sexe:
                gender = 'unknown'
                if sexe == 'M':
                    gender = 'male'
                elif sexe == 'F':
                    gender = 'female'
                vals.update({'gender': gender})
            # Update Marital Status
            if statutfamilial:
                statusname = False
                status = False
                if statutfamilial == 'MA':
                    statusname = 'Married'
                elif statutfamilial == 'VE':
                    statusname = 'Widower'
                elif statutfamilial == 'CE':
                    statusname = 'Single'
                if statusname:
                    s_ids = self.pool.get('hr.employee.marital.status').search(cr, uid, [('name', '=', statusname)])
                    if s_ids and len(s_ids) == 1:
                        status = s_ids[0]
                vals.update({'marital': status})
            # In case of death, desactivate employee
            if decede and decede == 'Y':
                vals.update({'active': False})
            # Desactivate employee if:
            # - no contract line found
            # - end of current contract exists and is inferior to current date
            # - no contract line found with current = True
            contract_ids = self.pool.get('hr.contract.msf').search(cr, uid, [('homere_codeterrain', '=', codeterrain), ('homere_id_staff', '=', id_staff)])
            if not contract_ids:
                vals.update({'active': False})
            current_contract = False
            for contract in self.pool.get('hr.contract.msf').browse(cr, uid, contract_ids):
                # Check current contract
                if contract.current:
                    current_contract = True
                    if contract.date_end and contract.date_end < strftime('%Y-%m-%d'):
                        vals.update({'active': False})
                # Check job
                if contract.job_id:
                    vals.update({'job_id': contract.job_id.id})
            # Desactivate employee if no current contract
            if not current_contract:
                vals.update({'active': False})
            if not e_ids:
                res = self.pool.get('hr.employee').create(cr, uid, vals, {'from': 'import'})
                if res:
                    created += 1
            else:
                res = self.pool.get('hr.employee').write(cr, uid, e_ids, vals, {'from': 'import'})
                if res:
                    updated += 1
            registered_keys[codeterrain + id_staff + uniq_id] = True
        else:
            message = _('Line %s. One of this column is missing: code_terrain, id_unique or id_staff. This often happens when the line is empty.') % (line_number)
            self.pool.get('hr.payroll.employee.import.errors').create(cr, uid, {'wizard_id': wizard_id, 'msg': message})
            return False, created, updated

        return True, created, updated

    def update_contract(self, cr, uid, ids, reader, context=None):
        """
        Read lines from reader and update database
        """
        res = []
        if not reader:
            return res
        for line in reader:
            if not line.get('contratencours'): #or not line.get('contratencours') == 'O':
                continue
            vals = {
                'homere_codeterrain': line.get('codeterrain') or False,
                'homere_id_staff': line.get('id_staff') or False,
                'homere_id_unique': line.get('id_unique') or 'empty',
                'current': False,
            }
            # Update values for current field
            if line.get('contratencours'):
                if line.get('contratencours') == 'O':
                    vals.update({'current': True})
            # Update values for datedeb and datefin fields
            for field in [('datedeb', 'date_start'), ('datefin', 'date_end')]:
                if line.get(field[0]):
                    if line.get(field[0]) == '0000-00-00':
                        vals.update({field[1]: False})
                    else:
                        vals.update({field[1]: line.get(field[0])})
            # Update values for job
            if line.get('fonction'):
                job_ids = self.pool.get('hr.job').search(cr, uid, [('code', '=', line.get('fonction'))])
                if job_ids:
                    vals.update({'job_id': job_ids[0]})
            # Add entry to database
            new_line = self.pool.get('hr.contract.msf').create(cr, uid, vals)
            if new_line:
                res.append(new_line)
        return res

    def update_job(self, cr, uid, ids, reader, context=None):
        """
        Read lines from reader and update database
        """
        res = []
        if not reader:
            return res
        for line in reader:
            # Check that no line with same code exist
            if line.get('code', False):
                search_ids = self.pool.get('hr.job').search(cr, uid, [('code', '=', line.get('code'))])
                if search_ids:
                    continue
                vals = {
                    'homere_codeterrain': line.get('codeterrain') or False,
                    'homere_id_unique': line.get('id_unique') or False,
                    'code': line.get('code') or '',
                    'name': line.get('libelle') or '',
                }
                # Add entry to database
                new_line = self.pool.get('hr.job').create(cr, uid, vals)
                if new_line:
                    res.append(new_line)
        return res

    def _extract_7z(self, cr, uid, filename):
        tmp_dir = mkdtemp()
        passwd = self.pool.get('hr.payroll.import')._get_homere_password(cr, uid, pass_type='permois')
        szexe = get_7z()
        devnull = open(os.devnull, 'w')
        szret = subprocess.call([szexe, 'x', '-p%s' % passwd, '-o%s' % tmp_dir, '-y', filename], stdout=devnull)
        devnull.close()
        if szret != 0:
            raise osv.except_osv(_('Error'), _('Error when extracting the file with 7-zip'))
        return tmp_dir

    def read_files(self, cr, uid, filename):
        staff_file = 'staff.csv'
        contract_file = 'contrat.csv'
        job_file = 'fonction.csv'
        job_reader =False
        contract_reader = False
        staff_reader = False
        desc_to_close = []
        tmpdir = False
        if is_zipfile(filename):
            zipobj = zf(filename)
            if zipobj.namelist() and job_file in zipobj.namelist():
                job_reader = csv.DictReader(zipobj.open(job_file), quotechar='"', delimiter=',', doublequote=False, escapechar='\\')
                # Do not raise error for job file because it's just a useful piece of data, but not more.
        # read the contract file
            if zipobj.namelist() and contract_file in zipobj.namelist():
                contract_reader = csv.DictReader(zipobj.open(contract_file), quotechar='"', delimiter=',', doublequote=False, escapechar='\\')
        # read the staff file
            if zipobj.namelist() and staff_file in zipobj.namelist():
                # Doublequote and escapechar avoid some problems
                staff_reader = csv.DictReader(zipobj.open(staff_file), quotechar='"', delimiter=',', doublequote=False, escapechar='\\')
        else:
            tmpdir = self._extract_7z(cr, uid, filename)
            job_file_name = os.path.join(tmpdir, job_file)
            if os.path.isfile(job_file_name):
                job_file_desc = open(job_file_name, 'rb')
                desc_to_close.append(job_file_desc)
                job_reader = csv.DictReader(job_file_desc, quotechar='"', delimiter=',', doublequote=False, escapechar='\\')

            contract_file_name = os.path.join(tmpdir, contract_file)
            if os.path.isfile(contract_file_name):
                contract_file_desc = open(contract_file_name, 'rb')
                desc_to_close.append(contract_file_desc)
                contract_reader = csv.DictReader(contract_file_desc, quotechar='"', delimiter=',', doublequote=False, escapechar='\\')

            staff_file_name = os.path.join(tmpdir, staff_file)
            if os.path.isfile(staff_file_name):
                staff_file_desc = open(staff_file_name, 'rb')
                desc_to_close.append(staff_file_desc)
                staff_reader = csv.DictReader(staff_file_desc, quotechar='"', delimiter=',', doublequote=False, escapechar='\\')

        if not contract_reader:
            raise osv.except_osv(_('Error'), _('%s not found in given zip file!') % (contract_file,))
        if not staff_reader:
            raise osv.except_osv(_('Error'), _('%s not found in given zip file!') % (staff_file,))
        return (job_reader, contract_reader, staff_reader, desc_to_close, tmpdir)

    def button_validate(self, cr, uid, ids, context=None):
        """
        Open ZIP file and search staff.csv
        """
        if not context:
            context = {}
        # Prepare some values
        staff_file = 'staff.csv'
        contract_file = 'contrat.csv'
        job_file = 'fonction.csv'
        res = False
        message = _("Employee import FAILED.")
        created = 0
        updated = 0
        processed = 0
        filename = ""
        registered_keys = {}
        # Delete old errors
        error_ids = self.pool.get('hr.payroll.employee.import.errors').search(cr, uid, [])
        if error_ids:
            self.pool.get('hr.payroll.employee.import.errors').unlink(cr, uid, error_ids)
        for wiz in self.browse(cr, uid, ids):
            if not wiz.file:
                raise osv.except_osv(_('Error'), _('Nothing to import.'))
            fileobj = NamedTemporaryFile('w+b', delete=False)
            fileobj.write(decodestring(wiz.file))
            # now we determine the file format
            filename = fileobj.name
            fileobj.close()
            job_reader, contract_reader, staff_reader, desc_to_close, tmpdir = self.read_files(cr, uid, filename)
            filename = wiz.filename or ""

            job_ids = False
            if job_reader:
                job_ids = self.update_job(cr, uid, ids, job_reader, context=context)
            # Do not raise error for job file because it's just a useful piece of data, but not more.
            # read the contract file
            contract_ids = False
            if contract_reader:
                contract_ids = self.update_contract(cr, uid, ids, contract_reader, context=context)
            # UF-2472: Read all lines to check employee's code before importing
            staff_data = []
            staff_codes = []
            duplicates = []
            staff_seen = []
            for line in staff_reader:
                staff_seen.append(line)
                data = self.read_employee_infos(cr, uid, line)
                processed += 1
                if data: # to avoid False value in staff_data list
                    staff_data.append(data)
                    code = data[0]
                    if code in staff_codes:
                        duplicates.append(code)
                    staff_codes.append(code)
            # Delete duplicates of… duplicates!
            duplicates = list(set(duplicates))
            details = []
            for employee_infos in staff_data:
                employee_code = employee_infos[0]
                if employee_code in duplicates:
                    details.append(','.join([ustr(employee_infos[1]), ustr(employee_infos[2])]))
            res = True
            if not details:
                created = 0
                processed = 0
                updated = 0
                # UF-2504 read staff file again for next enumeration
                # (because already read/looped above for staff codes)
                for i, employee_data in enumerate(staff_seen):
                    update, nb_created, nb_updated = self.update_employee_infos(
                        cr, uid, employee_data, wiz.id, i,
                        registered_keys=registered_keys)
                    if not update:
                        res = False
                    created += nb_created
                    updated += nb_updated
                    processed += 1
            else:
                res = False
                message = _('Several employees have the same unique code: %s.') % (';'.join(details))
                self.pool.get('hr.payroll.employee.import.errors').create(cr, uid, {'wizard_id': wiz.id, 'msg': message})
            # Close Temporary File
            # Delete previous created lines for employee's contracts
            if contract_ids:
                self.pool.get('hr.contract.msf').unlink(cr, uid, contract_ids)
            for to_close in desc_to_close:
                to_close.close()
            if tmpdir:
                shutil.rmtree(tmpdir)
        del registered_keys
        if res:
            message = _("Employee import successful.")
        else:
            context.update({'employee_import_wizard_ids': ids})
        context.update({'message': message})

        view_id = self.pool.get('ir.model.data').get_object_reference(cr, uid, 'msf_homere_interface', 'payroll_import_confirmation')
        view_id = view_id and view_id[1] or False

        # This is to redirect to Employee Tree View
        context.update({'from': 'employee_import'})

        res_id = self.pool.get('hr.payroll.import.confirmation').create(cr, uid, {'filename': filename, 'created': created, 'updated': updated, 'total': processed, 'state': 'employee'}, context)

        return {
            'name': 'Employee Import Confirmation',
            'type': 'ir.actions.act_window',
            'res_model': 'hr.payroll.import.confirmation',
            'view_mode': 'form',
            'view_type': 'form',
            'view_id': [view_id],
            'res_id': res_id,
            'target': 'new',
            'context': context,
        }

hr_payroll_employee_import()
# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
