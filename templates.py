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


MAIN_APP_TEMPLATE = """
#!/usr/bin/env python


from ariadne import graphql_sync, make_executable_schema, load_schema_from_path, ObjectType, QueryType
from ariadne.constants import PLAYGROUND_HTML
from flask import Flask, request, jsonify

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


app = grip.setup(flask_runtime)
service_registry = app.config.get('services')
forwarder = core.Forwarder(app.config.get('services'))


typedefs = load_schema_from_path('{{ project.schema_file }}')
bindables = []
bindables.append(r.query)

{% for typename in project.object_types %}
bindables.append(ObjectType('{{ typename }}'))
{% endfor %}

schema = make_executable_schema(typedefs, bindables)


@app.route('/graphql', methods=['GET'])
def playground():
    return PLAYGROUND_HTML, 200


@app.route('/graphql', methods=['POST'])
def graphql_server():
    data = request.get_json()
    success, result = graphql_sync(schema,
                                   data,
                                   context_value=None,
                                   debug=app.debug)

    status_code = 200 if success else 400
    return jsonify(result), status_code
    

if __name__ == '__main__':
    app.run(debug=True)

"""