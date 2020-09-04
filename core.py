#!/usr/bin/env python

import os, sys
from typing import Callable
import argparse
from snap import snap, common


class UnregisteredQueryHandler(Exception):
    def __init__(self, query_field):
        super().__init__(f'No handler has been registered for the query field {query_field}')


class UnregisteredMutationHandler(Exception):
    def __init__(self, mutation_field):
        super().__init__(f'No handler has been registered for the mutation field {mutation_field}')


class NoSuchHandlerError(Exception):
    def __init__(self, handler_funcname, handler_module_name):
        super().__init__(f'No handler {handler_funcname}() exists in module {handler_module_name}')


class GRequestForwarder(object):
    def __init__(self):
        self.query_handlers = {}
        self.mutation_handlers = {}

    def register_query_handler(self, query_field:str, handler: Callable):
        self.query_handlers[query_field] = handler

    def register_mutation_handler(self, mutation_field:str, handler: Callable):
        self.mutation_handlers[mutation_field] = handler

    def lookup_query_handler(self, query_field: str) -> Callable:
        handler = self.query_handlers.get(query_field)
        if not handler:
            raise UnregisteredQueryHandler(query_field)

        return handler

    def lookup_mutation_handler(self, mutation_field: str) -> Callable:
        handler = self.mutation_handlers.get(mutation_field)
        if not handler:
            raise UnregisteredMutationHandler(mutation_field)
    
        return handler


class GRequestContext(object):
    def __init__(self,
                 http_request,
                 forwarder: GRequestForwarder,
                 services: common.ServiceObjectRegistry):

        self.request = http_request
        self.forwarder = forwarder
        self.service_registry = services


def load_grip_config(mode, app):
    config_file_path = None
    if mode == 'standalone':
        parser = argparse.ArgumentParser()
        parser.add_argument("--config",
                            metavar='<configfile>',
                            required=True,
                            nargs=1,
                            help='YAML config file for grip endpoints')

        args = parser.parse_args()        
        config_file_path = common.full_path(args.config[0])

    elif mode == 'server':
        config_file_path=os.getenv('GRIP_CONFIG')
        filename = os.path.join(app.instance_path, 'application.cfg')
        print('generated config path is %s' % filename)

    else:
        print('valid setup modes are "standalone" and "server".')
        exit(1)
        
    if not config_file_path:
        print('please set the "configfile" environment variable in the WSGI command string.')
        exit(1)
        
    return common.read_config_file(config_file_path)


def init_request_forwarder(yaml_config):

    forwarder = GRequestForwarder()
    handler_module_name = yaml_config['globals']['handler_module']
    handler_module = __import__(handler_module_name)

    for query_name in yaml_config['query_defs']:
        handler_funcname = f'{query_name}_func'
        if not hasattr(handler_module, handler_funcname):
            raise NoSuchHandlerError(handler_funcname, handler_module_name)
        
        handler_function = getattr(handler_module, handler_funcname)                
        forwarder.register_query_handler(query_name, handler_function)

    return forwarder


def setup(flask_runtime):
    if flask_runtime.config.get('initialized'):
        return flask_runtime

    mode = flask_runtime.config.get('startup_mode')
    yaml_config = load_grip_config(mode, flask_runtime)
    flask_runtime.debug = yaml_config['globals'].get('debug_mode', False)
    #configure_logging(yaml_config)

    service_object_tbl = snap.initialize_services(yaml_config)
    flask_runtime.config['services'] = common.ServiceObjectRegistry(service_object_tbl)
    flask_runtime.config['forwarder'] = init_request_forwarder(yaml_config)
    flask_runtime.config['initialized'] = True
    return flask_runtime