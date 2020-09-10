#!/usr/bin/env python

import os, sys
import re
import json
import logging

from contextlib import contextmanager
import time

from snap import common
import sqlalchemy as sqla
from sqlalchemy.ext.automap import automap_base
from sqlalchemy import Column, ForeignKey, Integer, String
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship
from sqlalchemy.orm.session import sessionmaker
from sqlalchemy import create_engine
from sqlalchemy import MetaData
from sqlalchemy_utils import UUIDType
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
        self.filepath = kwargs['bucket_path'].lstrip('/')
        self.output_path = f'{self.bucket}/{self.filepath}'

        profile = kwargs.get('aws_profile')
        if profile:
            print('creating boto3 session with profile "%s"...' % profile, file=sys.stderr)
            self.session = boto3.session.Session(profile_name=profile)
        else:
            # for example, if we get access via AssumeRole
            self.session = boto3.session.Session()

        self.client = self.session.client('athena', region_name=self.region)


    def _athena_query(self, query: str):
        response = self.client.start_query_execution(
            QueryString=query,
            QueryExecutionContext={
                'Database': self.database
            },
            ResultConfiguration={
                'OutputLocation': 's3://' + self.output_path
            }
        )

        print(f'###____________initial exec response: {response}')
        return response


    def athena_to_s3(self, query, max_execution=7):
        
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

                    s3_result_path = self.output_path.rstrip('/') + '/' + filename 
                    return s3_result_path
            time.sleep(2)
        
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


POSTGRESQL_SVC_PARAM_NAMES = [
    'host',
    'port',
    'dbname',
    'username',
    'password'
]

class PostgreSQLService(object):
    def __init__(self, **kwargs):
        #kwreader = common.KeywordArgReader(*POSTGRESQL_SVC_PARAM_NAMES)
        #kwreader.read(**kwargs)

        init_params = { 'db_type': 'postgresql+psycopg2' }
        

        if kwargs.get('init_secret'):

            # for staging, the secret_name is knowledgebase/stage/system_rw_static_creds
            #
            if kwargs.get('profile'):
                secret_mgr = SimpleAWSSecretService(aws_region='us-east-1', profile=kwargs['profile'])
                secret_name = kwargs['init_secret']
            
            else:
                secret_mgr = SimpleAWSSecretService(aws_region='us-east-1')
                secret_name = kwargs['init_secret']
            
            credentials = secret_mgr.get_secret(secret_name)            
            init_params['user'] = credentials.pop('username')            
            init_params.update(credentials)

        else:
            init_params['dbname'] = kwargs['dbname']
            init_params['host'] = kwargs['host']
            init_params['port'] = int(kwargs.get('port', 5432))
            init_params['user'] = kwargs['username']
            init_params['password'] = kwargs['password']        

        self.schema = kwargs.get('schema', 'public')
        self.metadata = None
        self.engine = None
        self.session_factory = None
        self.Base = None
        self.url = None

        url_template = '{db_type}://{user}:{password}@{host}:{port}/{dbname}'
        db_url = url_template.format(**init_params)
        
        retries = 0
        connected = False
        while not connected and retries < 3:
            try:
                self.engine = sqla.create_engine(db_url, echo=False)
                self.metadata = MetaData(schema=self.schema)
                self.Base = automap_base(bind=self.engine, metadata=self.metadata)
                self.Base.prepare(self.engine, reflect=True)
                self.metadata.reflect(bind=self.engine)
                self.session_factory = sessionmaker(bind=self.engine, autoflush=False, autocommit=False)

                # this is required. See comment in SimpleRedshiftService 
                connection = self.engine.connect()                
                connection.close()
                connected = True
                print('### Connected to PostgreSQL DB.', file=sys.stderr)
                self.url = db_url

            except Exception as err:
                print(err, file=sys.stderr)
                print(err.__class__.__name__, file=sys.stderr)
                print(err.__dict__, file=sys.stderr)
                time.sleep(1)
                retries += 1
            
        if not connected:
            raise Exception('!!! Unable to connect to PostgreSQL db on host %s at port %s.' % 
                            (self.host, self.port))

    @contextmanager
    def txn_scope(self):
        session = self.session_factory()
        try:
            yield session
            session.commit()
        except:
            session.rollback()
            raise
        finally:
            session.close()


    @contextmanager    
    def connect(self):
        connection = self.engine.connect()
        try:
            yield connection
        finally:
            connection.close()



class S3Service(object):
    def __init__(self, **kwargs):
                
        self.region = kwargs['aws_region']
        self.s3session = None
        
        profile = kwargs.get('aws_profile')
        if profile:
            print('creating boto3 session with profile "%s"...' % profile, file=sys.stderr)
            self.session = boto3.session.Session(profile_name=profile)
        else:
            # for example, if we get access via AssumeRole
            self.session = boto3.session.Session()

        self.s3client = boto3.client('s3', region_name=self.region)
 

    def download_data(self, s3path):

        separator_index = s3path.find('/')
        bucket_name = s3path[0:separator_index]
        object_key = s3path[separator_index:].strip('/')

        print(f'###__________Calling get_object() with bucket: {bucket_name} and key: {object_key}')

        obj = self.s3client.get_object(Bucket=bucket_name, Key=object_key)
        return obj['Body'].read().decode('utf-8')
