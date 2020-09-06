#!/usr/bin/env python

from snap import common


def helloathena_func(input_data, service_registry, **kwargs):

    athenasvc = service_registry.lookup('athena')
    response = athenasvc.athena_to_s3('select * from firmware_prod.augeas limit 1')

    if not response:
        return 'No result from query.'

    s3_svc = service_registry.lookup('s3')

    print('###')
    print(f'###_______s3 object path is: {response}')
    print('###')

    querydata = s3_svc.download_data(response)

    # This is CSV data, so the first line will be the header
    if querydata.find('\n') > -1:
        query_output_header = querydata.split('\n')[0]
    else:
        query_output_header = querydata
    
    query_fields = [token.strip('"') for token in query_output_header.split(',')]


    print('###___________Downloaded S3 data FIELDS:')
    print(common.jsonpretty(query_fields))

    

    return response


def ping_func(input_data, service_registry, **kwargs):
    return {
        'ok': True,
        'message': 'The verifier service is alive.'
    }
