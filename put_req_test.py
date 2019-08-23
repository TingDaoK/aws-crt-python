import argparse
import sys
import os
from io import BytesIO
from awscrt import io, http
import unittest
import random
from concurrent.futures import Future

parser = argparse.ArgumentParser()
parser.add_argument('date_file', help='FILE: File to read from file and POST or PUT')
args = parser.parse_args()

def print_header_list(headers):
    for key, value in headers.items():
        print('{}: {}'.format(key, value))
# invoked up on the connection closing
client_conn_shutdown_future = Future()
def on_connection_shutdown(err_code):
    client_conn_shutdown_future.set_result(
        '----client connection close with error code {}----'.format(err_code))

def on_incoming_body(body_data):
        print(str(body_data, encoding='utf-8'))

def response_received_cb(ftr):
    print('Response Code: {}'.format(request.response_code))
    print_header_list(request.response_headers)

print("Now create a client to connect to the server")
hostname = "127.0.0.2"
port = 8127
event_loop_group = io.EventLoopGroup(1)
client_bootstrap = io.ClientBootstrap(event_loop_group)
socket_options = io.SocketOptions()
socket_options.domain = io.SocketDomain.IPv4
connect_future = http.HttpClientConnection.new_connection(client_bootstrap, hostname, port,
                                                                  socket_options,
                                                                  on_connection_shutdown, None)
connection = connect_future.result()
data_file = args.date_file
method = 'PUT'
uri_str = '/'+data_file.split("/")[-1]
request_headers = {'host': hostname,
                   'user-agent': 'elasticurl.py 1.0, Powered by the AWS Common Runtime.'}

request_data_len = os.stat(data_file).st_size
request_data_stream = open(data_file, 'rb')
if request_data_len != 0:
        request_headers['content-length'] = str(request_data_len)
        print_header_list(request_headers)

# make request
print("----MAKE REQUEST NOW-----")
request = connection.make_request(method, uri_str, request_headers, request_data_stream,
                                                on_incoming_body)
request.response_headers_received.add_done_callback(response_received_cb)

# wait client side connection to shutdown
print(client_conn_shutdown_future.result())
