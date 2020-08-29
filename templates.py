#!/usr/bin/env python


from ariadne import graphql_sync, make_executable_schema, load_schema_from_path, ObjectType, QueryType
from ariadne.constants import PLAYGROUND_HTML
from flask import Flask, request, jsonify
import resolvers as r

#
'''
sys.path.append('{{ PROJECT_HOME }}')

import {{resolver_module}}
import {{handler_module}} 

flask_runtime = Flask(__name__)

if __name__ == '__main__':
    print('starting GRIP graphql service in standalone (debug) mode...')
    flask_runtime.config['startup_mode'] = 'standalone'
    
else:
    print('starting GRIP graphql service in wsgi mode...')
    flask_runtime.config['startup_mode'] = 'server'

app = grip.setup(flask_runtime)
service_registry = app.config.get('services')

delegator = core.Delegator(app.config.get('services'))
'''

app = Flask(__name__)

typedefs = load_schema_from_path('schema.graphql')
bindables = []
bindables.append(r.query)
bindables.append(ObjectType('Building'))
bindables.append(ObjectType('Resident'))

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