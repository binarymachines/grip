#!/usr/bin/env python

import os, sys
import re
import json
import logging
from contextlib import contextmanager
import time
import boto3
import psycopg2


logging.basicConfig(level=logging.CRITICAL)
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

class SimpleAWSSecretService(object):
    def __init__(self, **kwargs):

        if not kwargs.get('aws_region'):
            raise Exception('"aws_region" is a required keyword argument for SimpleAWSSecretService.')

        region = kwargs['aws_region']
        profile = kwargs.get('profile', 'default')

        if profile == 'default':
            logger.debug('creating boto3 session with no profile spec...')
            b3session = boto3.session.Session()
        else:
            logger.debug('creating boto3 session with profile "%s"...' % profile)
            b3session = boto3.session.Session(profile_name=profile)

        self.asm_client = b3session.client('secretsmanager', region_name=region)


    def get_secret(self, secret_name):
        secret_value = self.asm_client.get_secret_value(SecretId=secret_name)
        return json.loads(secret_value['SecretString'])


class AWSAthenaQueryService(object):
    def __init__(self, **kwargs):
        
        self.database = kwargs['database']
        self.region = kwargs['aws_region']
        self.bucket = kwargs['s3_bucket']
        self.filepath = kwargs['bucket_path']

        profile = kwargs.get('aws_profile')

        if profile:
            print('creating boto3 session with profile "%s"...' % profile, file=sys.stderr)
            self.session = boto3.session.Session(profile_name=profile)
        else:
            # for example, if we get access via AssumeRole
            self.session = boto3.session.Session()

        self.client = self.session.client('athena', region_name=self.region)


    def _athena_query(self, query: str):
        response = client.start_query_execution(
            QueryString=query,
            QueryExecutionContext={
                'Database': self.database
            },
            ResultConfiguration={
                'OutputLocation': 's3://' + os.path.join(self.bucket, self.filepath)
            }
        )
        return response


    def athena_to_s3(self, query, max_execution=5):
        
        execution = self._athena_query(query)
        execution_id = execution['QueryExecutionId']
        state = 'RUNNING'

        print(f'### Query state: {state}')
        while (max_execution > 0 and state in ['RUNNING', 'QUEUED']):
            max_execution = max_execution - 1
            response = self.client.get_query_execution(QueryExecutionId = execution_id)
            print('### Query response:')
            print(response)

            if 'QueryExecution' in response and \
                    'Status' in response['QueryExecution'] and \
                    'State' in response['QueryExecution']['Status']:
                state = response['QueryExecution']['Status']['State']
                if state == 'FAILED':
                    print('### Athena query failed.')
                    return False
                elif state == 'SUCCEEDED':
                    print('### Athena query succeeded.')
                    s3_path = response['QueryExecution']['ResultConfiguration']['OutputLocation']
                    filename = re.findall('.*\/(.*)', s3_path)[0]
                    return filename
            time.sleep(1)
        
        return False


PSYCOPG_SVC_PARAM_NAMES = [
    'dbname',
    'user',
    'password',
    'host',
    'port'
]

class PostgresPsycopgService(object):
    def __init__(self, **kwargs):
        raw_params = kwargs

        self.db_connection_params = {}
        for name in PSYCOPG_SVC_PARAM_NAMES:
            self.db_connection_params[name] = raw_params[name]
        self.db_connection_params['connect_timeout'] = 3


    def open_connection(self):
        return psycopg2.connect(**self.db_connection_params)


    @contextmanager
    def connect(self):
        connection = None
        try:
            connection = psycopg2.connect(**self.db_connection_params)
            yield connection
            connection.commit()
        except:
            if connection is not None:
                connection.rollback()
            raise
        finally:
            if connection is not None:
                connection.close()
