#!/usr/bin/env python


import os, sys
from collections import namedtuple
import yaml
import jinja2
from snap import common

from templates import GQL_QUERY_TEMPLATE


GQLQueryArg = namedtuple('GQLQueryArg', 'name datatype')

class GQLQuerySpec(object):
    def __init__(self, name: str, return_type: str, *gql_query_args: GQLQueryArg):
        # TODO: check for trailing '!' in type names
        self.name = name
        self.return_type = return_type
        self.query_args = gql_query_args
        

    @property
    def has_args(self):
        return len(self.query_args) > 0


    @property
    def arg_string(self):
        arg_strings = []
        #for qarg in self.query_args:
            #arg_strings.append(f'{qarg.name}: {qarg.datatype}')
        arg_strings = [f'{qarg.name}: {qarg.datatype}' for qarg in self.query_args]
        
        return ', '.join(arg_strings)
        #return(f'({args})')


def load_gql_type_configs(yaml_config):
    pass


def input_param_to_args(param):
    args = []
    for p_tuple in param.items():
        args.append(GQLQueryArg(name=p_tuple[0], datatype=p_tuple[1]))

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


def create_gql_schema(yaml_config: dict) -> str:
    
    type_config = load_gql_type_configs(yaml_config)
    query_spec = load_query_specs(yaml_config)

    j2env = jinja2.Environment()
    template_mgr = common.JinjaTemplateManager(j2env)
    template = j2env.from_string(GQL_QUERY_TEMPLATE)

    return template.render(query_specs=load_query_specs(yaml_config))
