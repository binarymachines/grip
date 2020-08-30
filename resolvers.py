#!/usr/bin/env python

from typing import Any
import json
from graphql.type import GraphQLResolveInfo
from ariadne import graphql_sync, make_executable_schema, load_schema_from_path, ObjectType, QueryType


query = QueryType()

@query.field("hello")
def resolve_hello(obj: Any, info: GraphQLResolveInfo, **kwargs):
    request = info.context
    #user_agent = request.headers.get("User-Agent", "Guest")
    return "Hello from GRIP!"


@query.field('helloperson')
def resolve_helloperson(obj: Any, info: GraphQLResolveInfo, **kwargs):
    #request = info.context
    return {
        'id': 2,
        'word': 'Hey',
        'person': 'Joe'
    }


@query.field('sum')
def resolve_sum(obj: Any, info: GraphQLResolveInfo, **kwargs):
    return kwargs['a'] + kwargs['b']

