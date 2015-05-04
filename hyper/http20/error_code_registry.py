# -*- coding: utf-8 -*-
"""
hyper/http20/error_code_registry
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Global error code registry containing the established HTTP/2 error codes.
The registry is based on a 32-bit space so we use the error code to index into
the array.

The current registry is available at:
https://tools.ietf.org/html/draft-ietf-httpbis-http2-17#section-11.4
"""

NO_ERROR =            {'Name': 'NO_ERROR',
                       'Description': 'Graceful shutdown'}
PROTOCOL_ERROR =      {'Name': 'PROTOCOL_ERROR',
                       'Description': 'Protocol error detected'}
INTERNAL_ERROR =      {'Name': 'INTERNAL_ERROR',
                       'Description': 'Implementation fault'}
FLOW_CONTROL_ERROR =  {'Name': 'FLOW_CONTROL_ERROR',
                       'Description': 'Flow control limits exceeded'}
SETTINGS_TIMEOUT =    {'Name': 'SETTINGS_TIMEOUT',
                       'Description': 'Settings not acknowledged'}
STREAM_CLOSED =       {'Name': 'STREAM_CLOSED',
                       'Description': 'Frame received for closed stream'}
FRAME_SIZE_ERROR =    {'Name': 'FRAME_SIZE_ERROR',
                       'Description': 'Frame size incorrect'}
REFUSED_STREAM =      {'Name': 'REFUSED_STREAM ',
                       'Description': 'Stream not processed'}
CANCEL =              {'Name': 'CANCEL',
                       'Description': 'Stream cancelled'}
COMPRESSION_ERROR =   {'Name': 'COMPRESSION_ERROR',
                       'Description': 'Compression state not updated'}
CONNECT_ERROR =       {'Name': 'CONNECT_ERROR',
                       'Description': 
                       'TCP connection error for CONNECT method'}
ENHANCE_YOUR_CALM =   {'Name': 'ENHANCE_YOUR_CALM',
                       'Description': 'Processing capacity exceeded'}
INADEQUATE_SECURITY = {'Name': 'INADEQUATE_SECURITY',
                       'Description': 
                       'Negotiated TLS parameters not acceptable'}
HTTP_1_1_REQUIRED =   {'Name': 'HTTP_1_1_REQUIRED', 
                       'Description': 'Use HTTP/1.1 for the request'}

H2_ERROR_CODE_REGISTRY = [NO_ERROR, PROTOCOL_ERROR, INTERNAL_ERROR,
                          FLOW_CONTROL_ERROR, SETTINGS_TIMEOUT, STREAM_CLOSED,
                          FRAME_SIZE_ERROR, REFUSED_STREAM, CANCEL,
                          COMPRESSION_ERROR, CONNECT_ERROR, ENHANCE_YOUR_CALM,
                          INADEQUATE_SECURITY, HTTP_1_1_REQUIRED]
