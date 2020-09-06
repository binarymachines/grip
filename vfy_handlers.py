#!/usr/bin/env python

from snap import common
from vfy_services import PostgresPsycopgService



def get_kb_database_svc(service_object_registry):
    secret_mgr = service_object_registry.lookup('secrets')
    secret_name = os.getenv('FS_SECRET_NAME')
    if not secret_name:
        raise Exception('the environment variable FS_SECRET_NAME has not been set.')

    # for staging, the secret_name is knowledgebase/stage/system_rw_static_creds
    #
    credentials = secret_mgr.get_secret(secret_name)
    connection_params = copy.deepcopy(credentials)        
    connection_params['user'] = credentials.pop('username')
    return PostgresPsycopgService(**connection_params)


def lookup_kb_test_definition(cursor, schema, tablename):
    # TODO: get actual query
    lookup_query_template = '''
        SET SEARCH_PATH = {schema};
        SELECT id from {table}
    '''

    query = lookup_query_template.format(schema=schema, table=tablename)

    try:
        return None
    except Exception as e:
        l#ogger.error('Error fetching ID for test type "%s": %s' % (type_name, str(e)))
        raise


def helloathena_func(input_data, service_registry, **kwargs):

    athenasvc = service_registry.lookup('athena')
    response = athenasvc.athena_to_s3('select * from firmware_prod.augeas limit 1')

    if not response:
        return 'No result from query.'

    s3_svc = service_registry.lookup('s3')

    querydata = s3_svc.download_data(response)

    # This is CSV data, so the first line will be the header
    if querydata.find('\n') > -1:
        query_output_header = querydata.split('\n')[0]
    else:
        query_output_header = querydata
    
    query_fields = [token.strip('"') for token in query_output_header.split(',')]
    #print('###___________Downloaded S3 data FIELDS:')
    #print(common.jsonpretty(query_fields))

    # query the knowledgebase to get the fields in the test definition
    db_service = get_kb_database_svc(service_registry)
    with db_service.connect() as db_connection:
        cursor = db_connection.cursor()


    return response


def ping_func(input_data, service_registry, **kwargs):
    return {
        'ok': True,
        'message': 'The verifier service is alive.'
    }
