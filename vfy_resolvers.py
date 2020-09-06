
#!/usr/bin/env python

from typing import Any
import json
from graphql.type import GraphQLResolveInfo
from ariadne import graphql_sync, make_executable_schema, load_schema_from_path, ObjectType, QueryType, MutationType

query = QueryType()
mutation = MutationType()




@query.field("helloathena")
def resolve_helloathena(obj: Any, info: GraphQLResolveInfo, **kwargs):
    grip_context = info.context # GRequestContext object

    request = grip_context.request
    service_registry = grip_context.service_registry
    forwarder = grip_context.forwarder

    handler_func = forwarder.lookup_query_handler('helloathena')
    return handler_func(kwargs, service_registry)


@query.field("ping")
def resolve_ping(obj: Any, info: GraphQLResolveInfo, **kwargs):
    grip_context = info.context # GRequestContext object

    request = grip_context.request
    service_registry = grip_context.service_registry
    forwarder = grip_context.forwarder

    handler_func = forwarder.lookup_query_handler('ping')
    return handler_func(kwargs, service_registry)



@mutation.field("mutx")
def resolve_mutx(obj: Any, info: GraphQLResolveInfo, **kwargs):
    grip_context = info.context # GRequestContext object

    request = grip_context.request
    service_registry = grip_context.service_registry
    forwarder = grip_context.forwarder

    handler_func = forwarder.lookup_query_handler('mutx')
    return handler_func(kwargs, service_registry)

