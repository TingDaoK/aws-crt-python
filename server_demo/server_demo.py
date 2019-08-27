import argparse
import sys
import os
from io import BytesIO
import random
from concurrent.futures import Future
import cgi
import psutil
sys.path.append("..")
from awscrt import io, http
from urllib.parse import urlparse
from requests_toolbelt.multipart import decoder

log_level = io.LogLevel.NoLogs
log_level = io.LogLevel.Error
log_output = 'stderr'
io.init_logging(log_level, log_output)

Server_dir = "./server_data"
received_dir = "./received_data"


def print_header_list(headers):
    for key, value in headers.items():
        print('{}: {}'.format(key, value))


def get_body_format(headers):
    postfix = ".unknown"
    for key, val in headers.items():
        if key.lower() == "content-type":
            types = val.split("/")
            if types[0] == "text":
                if types[1] == 'plain':
                    postfix = '.txt'
                elif types[1] == 'html':
                    postfix = '.html'
                else:
                    return postfix
            elif types[0] == 'image':
                postfix = '.' + types[1]
            return postfix
    return postfix

def has_handle(path):
    """
    Return True means this file is opened by someone else
    """
    path = os.path.abspath(path)
    for proc in psutil.process_iter():
        try:
            for item in proc.open_files():
                if path == item.path:
                    return True
        except Exception:
            pass

    return False

def put_path_check(url):
    return os.path.abspath(url).split("/")[-2] == received_dir.split("/")[-1]

def create_html(body):
    html = "<!DOCTYPE html>\n<html>\n<head>\n" + "<!-- Required meta tags -->\n" + "<meta charset=\"utf-8\">\n" + "<meta name=\"viewport\" content=\"width=device-width, initial-scale=1, shrink-to-fit=no\">\n" + "<title>Server Demo</title>\n" + "<link rel=\"icon\" href=\"img/favicon.png\">\n" + "<!-- Bootstrap CSS -->\n" + "<link rel=\"stylesheet\" href=\"css/bootstrap.min.css\">\n" + "<!-- animate CSS -->\n" + "<link rel=\"stylesheet\" href=\"css/animate.css\">\n" + "<!-- owl carousel CSS -->\n" + "<link rel=\"stylesheet\" href=\"css/owl.carousel.min.css\">\n" + "<!-- themify CSS -->\n" + "<link rel=\"stylesheet\" href=\"css/themify-icons.css\">\n" + "<!-- flaticon CSS -->\n" + "<link rel=\"stylesheet\" href=\"css/liner_icon.css\">\n" + "<link rel=\"stylesheet\" href=\"css/search.css\">\n" + "<!-- style CSS -->\n" + "<link rel=\"stylesheet\" href=\"css/style.css\">\n" + "</head>\n" + "<body>\n" + body + "</body>\n</html>\n "
    return html


def create_html_put_block(url):
    body = "<h1>Your put request is blocked, because {} is already there!</h1>\n".format(url)
    body = body + "<h2>To revise it, try POST</h2>\n"
    return create_html(body)

def create_html_put_path_invalid(url):
    body = "<h1>Your put request is blocked, because {} is invalid!</h1>\n".format(url)
    return create_html(body)

def create_html_put_success(url):
    body = "<h1>Your put request to {} succeed!</h1>\n".format(url)
    return create_html(body)

def create_binary_html(body):
    html = b'<!DOCTYPE html>\n<html>\n<body>\n' + body + b'</body>\n</html>\n'
    return html

def create_form_demo_body(request_handler, request_body):
    '''
    Byte type request_body
    '''
    if request_handler.method == "POST":
        body = "<h1>Your POST request succeed!</h1>\n"
        body = body + "<h1>Your POST request body is:</h1>\n<p>"
    else:
        body = "<h1>Your GET request succeed!</h1>\n"
        body = body + "<h1>Your GET request query is:</h1>\n<p>"
    body = body.encode(encoding='utf-8')
    body = body+request_body
    body = body + b'</p>'
    return create_binary_html(body)

def _set_html_response(response_data_file = None, response_string = None, response_binary = None):
    data_file = response_data_file

    response_status = 200
    response_headers = {}
    response_body_stream = None
    response_body_len = 0

    if data_file != None:
        response_body_len = os.stat(data_file).st_size
        response_body_stream = open(data_file, 'rb')

    elif response_string != None:
        response_body_len = len(response_string)
        response_body = response_string.encode(encoding='utf-8')
        response_body_stream = BytesIO(response_body)

    elif response_binary != None:
        response_body_len = len(response_binary)
        response_body_stream = BytesIO(response_binary)

    if response_body_len != 0:
        response_headers['content-length'] = str(response_body_len)
    response = http.HttpResponse(response_status, response_headers, response_body_stream)
    return response


def _set_notfound_response():
    data_file = Server_dir + "/not_found.html"
    response_body_len = os.stat(data_file).st_size
    response_body_stream = open(data_file, 'rb')
    response_headers = {}
    if response_body_len != 0:
        response_headers['content-length'] = str(response_body_len)
    response_status = 404
    response_headers['Content-type'] = 'text/html'
    response = http.HttpResponse(response_status, response_headers, response_body_stream)
    return response

def parse_query(query):
    queries = query.split("&")
    query_dic = {}
    for i in queries:
        key_val = i.split('=')
        query_dic[key_val[0]] = key_val[1]
    return query_dic


class ServerRequest(object):

    def __init__(self, request_handler):
        self.output = None
        self.request_handler = request_handler
        self.get_method_body_file = received_dir + "/get_body.txt"
        self.save_file_name = 0
        self.write_block = False
        self.path_invalid = False
        self.form_demo = False
        self.body_buffer = b''

    def _do_GET(self, request_handler):
        response = None
        urlparse_output = urlparse(request_handler.path_and_query)
        try:
            if urlparse_output.path == "/":
                response = _set_html_response(Server_dir + "/new_test.html")
            elif urlparse_output.path == "/form_demo":
                response_body = create_form_demo_body(request_handler, urlparse_output.query.encode(encoding='utf-8'))
                response = _set_html_response(None, None, response_body)
                response.outgoing_headers['Content-Type'] = 'text/html'    
            elif  urlparse_output.path.endswith('.html'):
                response = _set_html_response(Server_dir + urlparse_output.path)
                response.outgoing_headers['Content-Type'] = 'text/html'
            elif urlparse_output.path.endswith('.png'):
                response = _set_html_response(Server_dir + urlparse_output.path)
                response.outgoing_headers['Content-Type'] = 'img/png'
            elif urlparse_output.path.endswith('.css'):
                response = _set_html_response(Server_dir + urlparse_output.path)
                response.outgoing_headers['Content-Type'] = 'text/css'
            elif urlparse_output.path.endswith('.js'):
                response = _set_html_response(Server_dir + urlparse_output.path)
                response.outgoing_headers['Content-Type'] = 'text/js'
            else:
                response = _set_html_response(Server_dir + urlparse_output.path + '.html')
        except IOError:
            response = _set_notfound_response()

        request_handler.send_response(response)

    def _do_POST(self, request_handler):
        urlparse_output = urlparse(request_handler.path_and_query)
        if urlparse_output.path == "/form_demo":
            self.form_demo = True
            #send response when the incoming body done else send response now
        else:
            response_body = create_html_put_block(request_handler.path_and_query)
            response = _set_html_response(None, response_body)
            response.outgoing_headers['Content-Type'] = 'text/html'
            request_handler.send_response(response)

    def _do_PUT(self, request_handler):
        if self.write_block:
            if self.path_invalid:
                response_body = create_html_put_path_invalid(request_handler.path_and_query)
                response = _set_html_response(None, response_body)
            else:
                response_body = create_html_put_block(request_handler.path_and_query)
                response = _set_html_response(None, response_body)
        else:
            response_body = create_html_put_success(request_handler.path_and_query)
            response = _set_html_response(None, response_body)
        response.outgoing_headers['Content-Type'] = 'text/html'
        request_handler.send_response(response)


    def on_incoming_body(self, body_data):
        if self.form_demo:
            '''
            parse incoming body and do some awesome thing? No, just left this to backend developer...
            '''
            self.body_buffer = self.body_buffer + body_data
            return 
        if self.output == None:
            return
        elif self.output.closed:
            return

        self.output.write(body_data)


    def server_request_done(self, request_handler):

        if self.output != None:
            self.output.close()
            self.output = None
        if self.form_demo:
            response_body = create_form_demo_body(request_handler, self.body_buffer)
            response = _set_html_response(None, None, response_body)
            response.outgoing_headers['Content-Type'] = 'text/html'
            request_handler.send_response(response)
        Error = False
        return Error

    def on_request_header_received(self, request_handler, headers, method, uri, has_body):
        request_handler.request_headers = headers
        request_handler.method = method
        request_handler.path_and_query = uri
        request_handler.has_incoming_body = has_body
        request_handler.request_header_received.set_result(True)
        print(request_handler.method)
        print(request_handler.path_and_query)
        print_header_list(headers)
        if has_body:
            save_file_dir = self.get_method_body_file
            if method == "POST":
                save_file_dir = received_dir + '/' + str(self.save_file_name)
                self.save_file_name = self.save_file_name + 1
                save_file_dir = save_file_dir + get_body_format(headers)
               
            elif method == "GET":
                save_file_dir = self.get_method_body_file
                
            elif method == "PUT":
                urlparse_output = urlparse(request_handler.path_and_query)
                save_file_dir = received_dir + urlparse_output.path
                if os.path.isfile(save_file_dir):
                    self.write_block = True
                if not put_path_check(save_file_dir):
                    self.path_invalid = True
                    self.write_block = True

            if not self.write_block:
                try:
                    self.output = open(save_file_dir, mode='wb')
                except IOError:
                    self.output = None
                    self.path_invalid = True
                    self.write_block = True
            else:
                self.output = None

        if method == "POST":
            self._do_POST(request_handler)
        elif method == "GET":
            self._do_GET(request_handler)
        elif method == "PUT":
            self._do_PUT(request_handler)
        else:
            raise NotImplementedError("Demon: not implemented method!{}".format(request_handler.method))

class ServerDemo(object):
    def __init__(self):
        self.server_conn_future = Future()
        self.server = None
        self.server_connection = []

    def _on_incoming_request(self, connection):
        request = ServerRequest(None)
        request_handler = http.HttpRequestHandler(connection, request.on_request_header_received, request.on_incoming_body,
                                                  request.server_request_done)
        request.request_handler = request_handler
        return request_handler

    def _on_server_conn_shutdown(self, connection, error_code):
        print("----shutdown server connection with error_code: {}----".format(error_code))

    def _on_incoming_connection(self, connection, error_code):
        print("connetion received!")
        # configure the connection here!
        if error_code:
            print("----server connection fail with error_code: {}----".format(error_code))
        self.server_connection.append(http.ServerConnection.new_server_connection(connection, self._on_incoming_request,
                                                                                  self._on_server_conn_shutdown))

    def help(self, msg):
        print("\"help\": for help,\n\"create\": create a new server in general,\n\"create local\": create a local server of random host name,\n\"create ipv4\": create an ipv4 server, binding with 127.0.0.2:8127\n\"shutdown\": shutdown the server and all existing connections, and exit the program after the shutdown process succeed \n\"connection num\": print out the number of existing connections")

    def create(self, msg):
        print("Now create a server")
        if self.server != None:
            print("server already created")
            return 
        hostname = input("Please input the host name\n")
        port = input("Please input the port num\n")
        socket_domain = input("Please input the options for socket_domain: (local/ ipv4/ ipv6)\n")
        event_loop_group = io.EventLoopGroup(1)
        server_bootstrap = io.ServerBootstrap(event_loop_group)
        socket_options = io.SocketOptions()
        if socket_domain == "local":
            if sys.platform == 'win32':
                # win32
                hostname = "\\\\.\\pipe\\testsock-" + hostname
            else:
                hostname = "testsock-{}.sock".format(hostname)
            socket_options.domain = io.SocketDomain.Local
        elif socket_domain == "ipv4":
            socket_options.domain = io.SocketDomain.IPv4
        elif socket_domain == "ipv6":
            socket_options.domain = io.SocketDomain.IPv6
        else:
            print("invalid input for socket domain {}".format(socket_domain))
            exit(-1)
        self.server = http.HttpServer(server_bootstrap, hostname, port, socket_options,
                                      self._on_incoming_connection)

    def create_local(self, msg):
        print("Now create a local server")
        if self.server != None:
            print("server already created")
            return 
        random.seed()
        hostname = str(random.random())
        port = 0
        event_loop_group = io.EventLoopGroup(1)
        server_bootstrap = io.ServerBootstrap(event_loop_group)
        socket_options = io.SocketOptions()
        if sys.platform == 'win32':
            # win32
            hostname = "\\\\.\\pipe\\testsock-" + hostname
        else:
            hostname = "testsock-{}.sock".format(hostname)
        socket_options.domain = io.SocketDomain.Local
        self.server = http.HttpServer(server_bootstrap, hostname, port, socket_options,
                                      self._on_incoming_connection)
        print("server create success on {}:{}".format(hostname, port))

    def create_ipv4(self, msg):
        print("Now create a ipv4 server")
        if self.server != None:
            print("server already created")
            return 
        hostname = "127.0.0.2"
        port = 8127
        event_loop_group = io.EventLoopGroup(1)
        server_bootstrap = io.ServerBootstrap(event_loop_group)
        socket_options = io.SocketOptions()
        socket_options.domain = io.SocketDomain.IPv4
        self.server = http.HttpServer(server_bootstrap, hostname, port, socket_options,
                                      self._on_incoming_connection)
        print("server create success on {}:{}".format(hostname, port))

    def create_ipv6(self, msg):
        raise NotImplementedError("Demon: not implemented method")

    def shutdown(self, msg):
        print("Now shutdown the server")
        future = http.HttpServer.close(self.server)
        if future.result():
            print("Shutdown the server success, exiting demo!")
            exit(0)

    def connection_num(self, msg):
        print(len(self.server_connection))


server_demo = ServerDemo()


def commands_result(command, msg):
    commands = {
        "help": server_demo.help,
        "create": server_demo.create,
        "create local": server_demo.create_local,
        "create ipv4": server_demo.create_ipv4,
        "create ipv6": server_demo.create_ipv6,
        "shutdown": server_demo.shutdown,
        "connection num": server_demo.connection_num
    }
    method = commands.get(command)
    if method:
        method(msg)


while True:
    command = input("~:")
    commands_result(command, None)
