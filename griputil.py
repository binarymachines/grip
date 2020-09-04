#!/usr/bin/env python


import os, sys
from collections import namedtuple
import yaml
import jinja2
from snap import common

from templates import GQL_QUERY_TEMPLATE
from templates import GQL_MUTATION_TEMPLATE
from templates import GQL_TYPE_TEMPLATE
from templates import MAIN_APP_TEMPLATE
from templates import RESOLVER_MODULE_TEMPLATE
from templates import HANDLER_MODULE_TEMPLATE
from templates import HANDLER_FUNCTION_TEMPLATE
from templates import QUERY_RESOLVER_FUNCTION_TEMPLATE
from templates import MUTATION_RESOLVER_FUNCTION_TEMPLATE


GQLArg = namedtuple('GQLArg', 'name datatype')
GQLTypespecField = namedtuple('GQLTypespecField', 'name datatype')


class GQLQuerySpec(object):
    def __init__(self, name: str, return_type: str, *gql_query_args: GQLArg):
        # TODO: check for trailing '!' in type names
        self.name = name
        self.return_type = return_type
        self.query_args = gql_query_args
        

    @property
    def has_args(self):
        return len(self.query_args) > 0


    @property
    def arg_string(self):
        arg_strings = [f'{qarg.name}: {qarg.datatype}' for qarg in self.query_args]        
        return ', '.join(arg_strings)
        #return(f'({args})')


class GQLMutationSpec(object):
    def __init__(self, name: str, return_type: str, *gql_mutation_args: GQLArg):
        self.name = name
        self.return_type = return_type
        self.mutation_args = gql_mutation_args

    @property
    def has_args(self):
        return len(self.mutation_args) > 0

    @property
    def arg_string(self):        
        arg_strings = [f'{arg.name}: {arg.datatype}' for arg in self.mutation_args]        
        return ', '.join(arg_strings)


class GQLTypespec(object):
    def __init__(self, name: str, fields: dict):
        self.name = name
        self.fields = [GQLTypespecField(name=fname, datatype=ftype) for fname, ftype in fields.items()]


class GProjectConfig(object):

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


class GProjectBuilder(object):
    @staticmethod
    def build_project(schema_filename: str, yaml_config: dict) -> GProjectConfig:
        project_conf = GProjectConfig()
        project_conf.set_home_dir(common.load_config_var(yaml_config['globals']['project_home']))
        project_conf.set_schema_file(schema_filename)
        project_conf.set_resolver_module(yaml_config['globals']['resolver_module'])
        project_conf.set_handler_module(yaml_config['globals']['handler_module'])

        for typespec in load_type_specs(yaml_config):
            project_conf.add_object_type(typespec.name)

        return project_conf


def generate_handler_source(yaml_config: dict) -> str:

    j2env = jinja2.Environment()
    template_mgr = common.JinjaTemplateManager(j2env)
    template = j2env.from_string(HANDLER_MODULE_TEMPLATE)
    
    qspecs = load_query_specs(yaml_config)
    return template.render(query_specs=qspecs)


def generate_handler_function(name: str) -> str:

    j2env = jinja2.Environment()
    template_mgr = common.JinjaTemplateManager(j2env)
    template = j2env.from_string(HANDLER_FUNCTION_TEMPLATE)
    return template.render(handler_name=name)


def generate_app_source(schema_filename: str, yaml_config: dict) -> str:

    project_conf = GProjectBuilder.build_project(schema_filename, yaml_config)

    j2env = jinja2.Environment()
    template_mgr = common.JinjaTemplateManager(j2env)
    template = j2env.from_string(MAIN_APP_TEMPLATE)
    
    return template.render(project=project_conf)


def generate_resolver_source(yaml_config: dict) -> str:

    j2env = jinja2.Environment()
    template_mgr = common.JinjaTemplateManager(j2env)
    template = j2env.from_string(RESOLVER_MODULE_TEMPLATE)

    qspecs = load_query_specs(yaml_config)
    mspecs = load_mutation_specs(yaml_config)

    return template.render(query_specs=qspecs, mutation_specs=mspecs)


def generate_query_resolver_function(qspec: GQLQuerySpec) -> str:

    j2env = jinja2.Environment()
    template_mgr = common.JinjaTemplateManager(j2env)
    template = j2env.from_string(QUERY_RESOLVER_FUNCTION_TEMPLATE)

    return template.render(query_spec=qspec)


def generate_mutation_resolver_function(mspec: GQLMutationSpec) -> str:

    j2env = jinja2.Environment()
    template_mgr = common.JinjaTemplateManager(j2env)
    template = j2env.from_string(MUTATION_RESOLVER_FUNCTION_TEMPLATE)

    return template.render(mutation_spec=mspec)


def input_param_to_args(param):
    args = []
    for p_tuple in param.items():
        args.append(GQLArg(name=p_tuple[0], datatype=p_tuple[1]))

    return args


def load_query_specs(yaml_config: dict) -> list:
    query_specs = []
    query_segment = yaml_config.get('query_defs')
    for name, query_config  in query_segment.items():
        query_name = name
        query_args = []
        input_params = query_segment[name].get('inputs')

        if input_params:
            for ip in input_params:
                query_args.extend(input_param_to_args(ip))
                
        return_type = query_segment[name]['output']
        query_specs.append(GQLQuerySpec(query_name, return_type, *query_args))
    
    return query_specs


def load_mutation_specs(yaml_config: dict) -> list:
    mutation_specs = []
    mutation_segment = yaml_config.get('mutation_defs')
    for name, mutation_config in mutation_segment.items():
        mutation_name = name
        mutation_args = []
        input_params = mutation_segment[name].get('inputs')

        if input_params:
            for ip in input_params:
                mutation_args.extend(input_param_to_args(ip))

        return_type = mutation_segment[name]['output']
        mutation_specs.append(GQLMutationSpec(mutation_name, return_type, *mutation_args))

    return mutation_specs


def load_type_specs(yaml_config: dict) -> list:
    type_specs = []
    type_segment = yaml_config.get('type_defs')

    for name, raw_field_dict in type_segment.items():

        field_dict = {}
        for field_name, field_value in raw_field_dict.items():
            if field_value.__class__ == list:
                field_dict[field_name] = f'[{field_value[0]}]'
            else:
                field_dict[field_name] = field_value

        type_specs.append(GQLTypespec(name, field_dict))

    return type_specs


def create_gql_schema(yaml_config: dict) -> str:
    
    j2env = jinja2.Environment()
    template_mgr = common.JinjaTemplateManager(j2env)

    query_template = j2env.from_string(GQL_QUERY_TEMPLATE)
    query_schema = query_template.render(query_specs=load_query_specs(yaml_config))

    mutation_template = j2env.from_string(GQL_MUTATION_TEMPLATE)
    mutation_schema = mutation_template.render(mutation_specs=load_mutation_specs(yaml_config))

    types_template = j2env.from_string(GQL_TYPE_TEMPLATE)
    types_schema = types_template.render(type_specs=load_type_specs(yaml_config))

    return ''.join([query_schema, mutation_schema, types_schema])

