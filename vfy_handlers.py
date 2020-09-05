#!/usr/bin/env python


def helloathena_func(input_data, service_registry, **kwargs):
    return "Hello from Athena!"


def ping_func(input_data, service_registry, **kwargs):
    return {
        'ok': True,
        'message': 'The verifier service is alive.'
    }
