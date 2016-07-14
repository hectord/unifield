import os
import sys
from optparse import OptionParser

import babel.localedata

import cherrypy
try:
    from cherrypy.lib.reprconf import as_dict
except ImportError:
    from cherrypy._cpconfig import as_dict

import openobject
import openobject.release
import openobject.paths

class ConfigurationError(Exception):
    pass

DISTRIBUTION_CONFIG = os.path.join('doc', 'openerp-web.cfg')
FROZEN_DISTRIBUTION_CONFIG = os.path.join('conf', 'openerp-web.cfg')
OVERRIDE_CONFIG = os.path.join('conf', 'openerp-web-oc.cfg')
def get_config_override_file():
    if hasattr(sys, 'frozen'):
        configfile = os.path.join(openobject.paths.root(), OVERRIDE_CONFIG)
        if os.path.exists(configfile):
            return configfile

    return False

def get_config_file():
    if hasattr(sys, 'frozen'):
        configfile = os.path.join(openobject.paths.root(), FROZEN_DISTRIBUTION_CONFIG)
        if not os.path.exists(configfile):
            configfile = os.path.join(openobject.paths.root(), DISTRIBUTION_CONFIG)
    else:
        setupdir = os.path.dirname(os.path.dirname(__file__))
        isdevdir = os.path.isfile(os.path.join(setupdir, 'setup.py'))
        configfile = '/etc/openerp-web.cfg'
        if isdevdir or not os.path.exists(configfile):
            configfile = os.path.join(setupdir, DISTRIBUTION_CONFIG)
    return configfile

def start():

    parser = OptionParser(version="%s" % (openobject.release.version))
    parser.add_option("-c", "--config", metavar="FILE", dest="config",
                      help="configuration file", default=get_config_file())
    parser.add_option("--config-override", metavar="FILE", dest="config_override",
                      help="override configuration file", default=get_config_override_file())
    parser.add_option("-a", "--address", help="host address, overrides server.socket_host")
    parser.add_option("-p", "--port", help="port number, overrides server.socket_port")
    parser.add_option("--openerp-host", dest="openerp_host", help="overrides openerp.server.host")
    parser.add_option("--openerp-port", dest="openerp_port", help="overrides openerp.server.port")
    parser.add_option("--openerp-protocol", dest="openerp_protocol", help="overrides openerp.server.protocol")
    parser.add_option("--no-static", dest="static",
                      action="store_false", default=True,
                      help="Disables serving static files through CherryPy")
    options, args = parser.parse_args(sys.argv)

    if not os.path.exists(options.config):
        raise ConfigurationError(_("Could not find configuration file: %s") %
                                 options.config)

    error_config = False
    app_config = as_dict(options.config)
    if options.config_override:
        try:
            over_config = as_dict(options.config_override)
            for section, value in over_config.iteritems():
                app_config.setdefault(section, {}).update(value)
        except Exception, error_config:
            pass
    openobject.configure(app_config)

    if error_config:
        cherrypy.log('Unable to parse %s\nError: %s' % (options.config_override, error_config), "ERROR")
        raise ConfigurationError(_("Unable to parse: %s") %
                                 options.config_override)

    if options.static:
        openobject.enable_static_paths()

    if options.address:
        cherrypy.config['server.socket_host'] = options.address
    if options.port:
        try:
            cherrypy.config['server.socket_port'] = int(options.port)
        except:
            pass
    port = cherrypy.config.get('server.socket_port')
    if not isinstance(port, (int, long)) or port < 1 or port > 65535:
        cherrypy.log('Wrong configuration socket_port: %s' % (port,), "ERROR")
        raise ConfigurationError(_("Wrong configuration socket_port: %s") %
                                 port)
    if options.openerp_host:
        cherrypy.config['openerp.server.host'] = options.openerp_host
    if options.openerp_port:
        try:
            cherrypy.config['openerp.server.port'] = int(options.openerp_port)
        except:
            pass
    if options.openerp_protocol in ['http', 'https', 'socket']:
        cherrypy.config['openerp.server.protocol'] = options.openerp_protocol

    if sys.platform == 'win32':
        from cherrypy.process.win32 import ConsoleCtrlHandler
        class ConsoleCtrlHandlerWeb(ConsoleCtrlHandler):
            def handle(self, event):
                """Handle console control events (like Ctrl-C)."""
                # 'First to return True stops the calls'
                return 1
        cherrypy.engine.console_control_handler = ConsoleCtrlHandlerWeb(cherrypy.engine)

    if hasattr(cherrypy.engine, "signal_handler"):
        cherrypy.engine.signal_handler.subscribe()
    if hasattr(cherrypy.engine, "console_control_handler"):
        cherrypy.engine.console_control_handler.subscribe()

    cherrypy.engine.start()
    cherrypy.engine.block()

def stop():
    cherrypy.engine.exit()
