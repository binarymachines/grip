#!/usr/bin/env python


GQL_QUERY_TEMPLATE = """
type Query {
    {% for qspec in query_specs -%}
    {% if qspec.has_args -%}
    {{ qspec.name }}({{ qspec.arg_string }}): {{ qspec.return_type }} 
    {% else -%}
    {{ qspec.name }}: {{ qspec.return_type }}
    {% endif -%}
    {%- endfor -%}
}
"""

GQL_TYPE_TEMPLATE = """
{% for typespec in type_specs %}

type {{ typespec.name }} {
    {% for field in typespec.fields -%}
    {{ field.name }}: {{ field.datatype }}
    {% endfor -%}
}
{% endfor %}

"""

HANDLER_FUNCTION_TEMPLATE = """
def {{ handler_name }}(input_data, service_registry, **kwargs):
    return None
"""

HANDLER_MODULE_TEMPLATE = """
#!/usr/bin/env python

from typing import Any
import json


{% for query_spec in query_specs %}
def {{ query_spec.name }}_func(input_data, service_registry, **kwargs):
    return "placeholder data"

{% endfor -%}

"""

RESOLVER_MODULE_TEMPLATE = """
#!/usr/bin/env python

from typing import Any
import json
from graphql.type import GraphQLResolveInfo
from ariadne import graphql_sync, make_executable_schema, load_schema_from_path, ObjectType, QueryType

query = QueryType()

{% for query_spec in query_specs %}
@query.field("{{ query_spec.name }}")
def resolve_{{ query_spec.name }}(obj: Any, info: GraphQLResolveInfo, **kwargs):
    grip_context = info.context # GRequestContext object

    request = grip_context.request
    service_registry = grip_context.service_registry
    forwarder = grip_context.forwarder

    handler_func = forwarder.lookup_query_handler('{{ query_spec.name }}')
    return handler_func(kwargs, service_registry)

{% endfor %}

"""

RESOLVER_FUNCTION_TEMPLATE = """
@query.field("{{ query_spec.name }}")
def resolve_{{ query_spec.name }}(obj: Any, info: GraphQLResolveInfo, **kwargs):
    grip_context = info.context # GRequestContext object

    request = grip_context.request
    service_registry = grip_context.service_registry
    forwarder = grip_context.forwarder

    handler_func = forwarder.lookup_query_handler('{{ query_spec.name }}')
    return handler_func(kwargs, service_registry)

"""

MAIN_APP_TEMPLATE = """
#!/usr/bin/env python

import os, sys

from ariadne import graphql_sync, make_executable_schema, load_schema_from_path, ObjectType, QueryType
from ariadne.constants import PLAYGROUND_HTML
from flask import Flask, request, jsonify
import core

sys.path.append('{{ project.home_dir }}')

import {{ project.resolver_module }} as r
import {{ project.handler_module }} 

flask_runtime = Flask(__name__)


if __name__ == '__main__':
    print('starting GRIP graphql service in standalone (debug) mode...')
    flask_runtime.config['startup_mode'] = 'standalone'
else:
    print('starting GRIP graphql service in wsgi mode...')
    flask_runtime.config['startup_mode'] = 'server'

app = core.setup(flask_runtime)
service_registry = app.config.get('services')
forwarder = app.config.get('forwarder')

typedefs = load_schema_from_path('{{ project.schema_file }}')

bindables = []
bindables.append(r.query)
{% for typename in project.object_types -%}
bindables.append(ObjectType('{{ typename }}'))
{% endfor %}
schema = make_executable_schema(typedefs, bindables)

@app.route('/graphql', methods=['GET'])
def playground():
    return PLAYGROUND_HTML, 200


@app.route('/graphql', methods=['POST'])
def graphql_server():
    data = request.get_json()
    request_context = core.GRequestContext(request, forwarder, service_registry)
    success, result = graphql_sync(schema,
                                   data,
                                   context_value=request_context,
                                   debug=app.debug)

    status_code = 200 if success else 400
    return jsonify(result), status_code
    

if __name__ == '__main__':
    app.run(debug=True)

"""