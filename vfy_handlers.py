#!/usr/bin/env python

import os, sys
import copy
import base64
from snap import common
from vfy_services import PostgresPsycopgService
from vfy_services import PostgreSQLService
from sqlalchemy_utils import UUIDType



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
    #return PostgresPsycopgService(**connection_params)

    return PostgreSQLService(**connection_params)


def lookup_kb_test_verification(def_id, cursor, schema):
    #
    # 
    # Parent table: issue_mgmt_observationdefinition
    # child table: issue_mgmt_observationverification
    #

    lookup_query_template = """
        SET SEARCH_PATH = {schema};
        SELECT * FROM issue_mgmt_observationverification WHERE observation_definition_id = %(odid)s;
    """

    #lookup_query_template = """
    #    SET SEARCH_PATH = {schema};
    #    SELECT * FROM issue_mgmt_observationverification LIMIT 5;
    #"""

    query = lookup_query_template.format(schema=schema)
    
    print(f'>>>____________Fetching record with foreign key {def_id}...')

    try:
        cursor.execute(query, {'odid': def_id})
        return cursor.fetchall()
    except Exception as e:
        # logger.error('Error fetching ID for test type "%s": %s' % (type_name, str(e)))
        raise


def helloathena_func(input_data, service_registry, **kwargs):

    athenasvc = service_registry.lookup('athena')
    db_service = service_registry.lookup('postgres')
    encoded_input_query = input_data['input_query']

    input_query = base64.b64decode(encoded_input_query).decode('utf-8')
    s3_output_filename = athenasvc.athena_to_s3(input_query, 8)

    if not s3_output_filename:
        return 'No result from query.'

    s3_svc = service_registry.lookup('s3')
    querydata = s3_svc.download_data(s3_output_filename)

    # This is CSV data, so the first line will be the header
    if querydata.find('\n') > -1:
        query_output_header = querydata.split('\n')[0]
    else:
        query_output_header = querydata
    
    query_response_fields = [token.strip('"') for token in query_output_header.split(',')]

    # query the knowledgebase to get the fields in the test definition    
    
    definition_fields = {}
    obs_def_id = input_data['observation_def_id']

    with db_service.txn_scope() as session:

        print(f'########  OBSERVATION DEF ID: {obs_def_id}')
        ObservationVerification = db_service.Base.classes.issue_mgmt_observationverification
        verification_query = session.query(ObservationVerification).filter(ObservationVerification.observation_definition_id == obs_def_id)
        results = verification_query.all()

        for record in results:
            definition_fields[record.key_name] = record.data_type
 
        print(common.jsonpretty(definition_fields))
        
    errors = []
    for fieldname in query_response_fields:
        if fieldname not in definition_fields:
            errors.append({
                'error_type': 'undefined_field',
                'error_key': 'field_name',
                'error_value': fieldname
            })

    response = {
        'ok': True,
        'input_query': input_query
    }

    if len(errors):
        response['ok'] = False
        response['errors'] = errors
    
    return response


def ping_func(input_data, service_registry, **kwargs):
    return {
        'ok': True,
        'message': 'The verifier service is alive.'
    }
