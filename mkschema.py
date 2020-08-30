#!/usr/bin/env python

'''
Usage:
    mkschema --config <configfile>
'''


import os, sys
from collections import namedtuple
import docopt
import yaml
import jinja2
from snap import common
from griputil import create_gql_schema



def main(args):

    configfile_name = args['<configfile>']
    yaml_config = common.read_config_file(configfile_name)
    project_home = common.load_config_var(yaml_config['globals']['project_home'])
    
    print(create_gql_schema(yaml_config))



if __name__ == '__main__':
    args = docopt.docopt(__doc__)
    main(args)