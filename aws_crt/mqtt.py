# Copyright 2010-2017 Amazon.com, Inc. or its affiliates. All Rights Reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License").
# You may not use this file except in compliance with the License.
# A copy of the License is located at
#
#  http://aws.amazon.com/apache2.0
#
# or in the "license" file accompanying this file. This file is distributed
# on an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either
# express or implied. See the License for the specific language governing
# permissions and limitations under the License.

import _aws_crt_python
from aws_crt.io import ClientBootstrap, ClientTlsContext
from concurrent.futures import Future
from enum import Enum

class QoS(Enum):
    """Quality of Service"""
    AT_MOST_ONCE = 0
    AT_LEAST_ONCE = 1
    AtLeastOnce=1 # DELETEME
    EXACTLY_ONCE = 2

class ConnectReturnCode(Enum):
    ACCEPTED = 0
    UNACCEPTABLE_PROTOCOL_VERSION = 1
    IDENTIFIER_REJECTED = 2
    SERVER_UNAVAILABLE = 3
    BAD_USERNAME_OR_PASSWORD = 4
    NOT_AUTHORIZED = 5

class Will(object):
    __slots__ = ('topic', 'qos', 'payload', 'retain')

    def __init__(self, topic, qos, payload, retain):
        self.topic = topic
        self.qos = qos
        self.payload = payload
        self.retain = retain

class Client(object):
    __slots__ = ('_internal_client', 'bootstrap', 'tls_ctx')

    def __init__(self, bootstrap, tls_ctx = None):
        assert isinstance(bootstrap, ClientBootstrap)
        assert tls_ctx is None or isinstance(tls_ctx, ClientTlsContext)

        self.bootstrap = bootstrap
        self.tls_ctx = tls_ctx
        self._internal_client = _aws_crt_python.aws_py_mqtt_client_new(self.bootstrap._internal_bootstrap)

class ConnAck(object):
    __slots__ = ('session_present') # Not passing return code because non-zero results in exception

class SubAck(object):
    __slots__ = ('packet_id', 'topic', 'qos')

class UnsubAck(object):
    __slots__ = ('packet_id', 'topic')

class PubAck(object):
    __slots__ = ('packet_id') # topic?

class OperationError(Exception):
    __slots__ = ('packet_id')

class ConnectionRejectedError(Exception):
    __slots__ = ('return_code')

class SubscriptionRejectedError(Exception):
    __slots__ = ('packet_id') # UGHHHH how to transmit packet_id to unexpected failures

class Connection(object):

    def __init__(self,
            client, client_id,
            host_name, port,
            on_connection_interrupted=None,
            on_connection_resumed=None,
            use_websocket=False, alpn=None,
            clean_session=True, keep_alive=0,
            will=None,
            username=None, password=None,
            connect_timeout_sec=5.0,
            reconnect_min_timeout_sec=5.0,
            reconnect_max_timeout_sec=60.0,
            ):
        # connection is created, but we don't call connect() on it yet.
        # We do this so that connect() can return a future which is awaitable
        # And also so users can set up subscriptions before initiating a persistent connect()
        pass

    def connect(self): # we're still debating the params for this vs constructor
        return Future() # Future will have a Connack result, or an exception such as ConnectionRejectedError

    def reconnect(self, respect_backoff=True):
        pass # like connect but uses same params as last time

    def disconnect(self, is_final=True):
         # This is treated like a kill() command, doing anything else with the
         # Connection after this results in exceptions

        return Future() # Not sure if Future should contain anything?

    def subscribe(self, topic, qos, callback):
        packet_id = 1234
        return Future(), packet_id # Future will contain Suback

    def unsubscribe(self, topic):
        packet_id = 1234
        return Future(), packet_id # Future will contain UnsubAck

    def publish(self, topic, payload, qos, retain=False):
        packet_id = 1234
        return Future(), packet_id # Future wil contain PubAck

    def ping(self):
        pass