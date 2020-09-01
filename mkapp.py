#!/usr/bin/env python


'''
Usage:
    mkapp --config <configfile> --project-name <name> [--force]
    mkapp --config <configfile> --load-schema <gql_schemafile>

Options:
    -f --force      Force overwrite of generated graphql schema file
'''


import os, sys
from collections import namedtuple
import docopt
import yaml
import jinja2
from snap import common
from griputil import create_gql_schema
from templates import MAIN_APP_TEMPLATE



class GripProjectConfig(object):

    def __init__(self, **kwargs):
        self.home_dir = ''
        self.schema_file = ''
        self.resolver_module = ''
        self.handler_module = ''
        self.object_types = []

    def set_home_dir(self, home_dir):
        if home_dir[0] == '/':
            self.home_dir = home_dir
        else:
            self.home_dir = os.path.join(os.getcwd(), home_dir)


    def set_schema_file(self, filename):
        self.schema_file = os.path.join(self.home_dir, filename)

    def add_object_type(self, obj_type: str):
        self.object_types.append(obj_type)
    
    def set_resolver_module(self, module: str):
        self.resolver_module = module

    def set_handler_module(self, module: str):
        self.handler_module = module


def generate_gql_source(schema_filename: str, yaml_config: dict) -> str:

    project_conf = GripProjectConfig()
    project_conf.set_home_dir(common.load_config_var(yaml_config['globals']['project_home']))
    project_conf.set_schema_file(schema_filename)
    project_conf.set_resolver_module(yaml_config['globals']['resolver_module'])
    project_conf.set_handler_module(yaml_config['globals']['handler_module'])

    j2env = jinja2.Environment()
    template_mgr = common.JinjaTemplateManager(j2env)
    template = j2env.from_string(MAIN_APP_TEMPLATE)
    
    return template.render(project=project_conf)


def main(args):
    print(common.jsonpretty(args))

    configfile_name = args['<configfile>']
    yaml_config = common.read_config_file(configfile_name)
    project_home = common.load_config_var(yaml_config['globals']['project_home'])
    schema_filename = args['<gql_schemafile>']

    # add the project home to our PYTHONPATH
    sys.path.append(os.path.join(os.getcwd(), project_home))

    if args['--project-name']:
        schema = create_gql_schema(yaml_config)
        # TODO: account for file paths relative to current dir

        project_name = args['<name>']
        schema_filename = f'{project_name}.graphql'
        schema_outfile = os.path.join(project_home,
                                      schema_filename)

        if os.path.isfile(schema_outfile):
            if args['--force'] == False:
                print(f'schema file {schema_outfile} already exists. Use -f to force overwrite.')
                return
        
        with open(schema_outfile, 'a') as f:
            f.write(schema)
        
    elif args['--load-schema']:
        schema_infile = os.path.join(project_home,
                                     schema_filename)

        with open(schema_infile) as f:
            schema_data = f.read()

    print(generate_gql_source(schema_filename, yaml_config))


if __name__ == '__main__':
    args = docopt.docopt(__doc__)
    main(args)