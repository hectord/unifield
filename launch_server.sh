#!/bin/bash

set -e

if [[ ! -e myenv ]]
then
    virtualenv -p python2.6 myenv
fi
source myenv/bin/activate
pip install -r requirements.txt

. config.sh

cat <<HERE > openerp-server.conf
[options]
additional_xml = False
addons_path = 
admin_bkpdb_passwd = YWRtaW4=
admin_dropdb_passwd = YWRtaW4=
admin_passwd = YWRtaW4=
admin_restoredb_passwd = YWRtaW4=
assert_exit_level = error
cache_timeout = 100000
csv_internal_sep = ,
db_host = localhost
db_maxconn = 64
db_name = False
db_password = False
db_port = False
db_user = sblanc
debug_mode = False
demo = {}
email_from = noreply.gva@gogo.org
gzipxmlrpc = False
gzipxmlrpcs = False
import_partial = 
lang = en_US
list_db = True
log_level = info
logfile = None
login_message = False
logrotate = True
netrpc = $NETRPC_PORT
netrpc_gzip = False
netrpc_interface = 
netrpc_port = 8001
osv_memory_age_limit = 1.0
osv_memory_count_limit = False
pg_path = None
pidfile = None
reportgz = False
root_path = $PWD/server/bin
secure_cert_file = server.cert
secure_pkey_file = server.pkey
smtp_password = aCQxMjM0NTY3OCQk
smtp_port = 25
smtp_server = smtp.gogo.org
smtp_ssl = False
smtp_user = noreply.gva
soap = False
static_http_document_root = /var/www/html
static_http_enable = False
static_http_url_prefix = /
stop_after_init = False
syslog = False
test_commit = False
test_disable = False
test_file = False
test_report_directory = False
timezone = False
translate_modules = ['all']
upgrade = False
verbose = False
without_demo = False
xmlrpc = True
xmlrpc_interface = 
xmlrpc_port = 8000
xmlrpcs = True
xmlrpcs_interface = 
xmlrpcs_port = 8002
HERE

python2.6 server/bin/openerp-server.py --db_user=$DB_USERNAME --db_password=$DB_PASSWORD --db_port=$DB_PORT --db_host=$DB_ADDRESS -c openerp-server.conf $@

