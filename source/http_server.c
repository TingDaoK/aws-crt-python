/*
 * Copyright 2010-2019 Amazon.com, Inc. or its affiliates. All Rights Reserved.
 *
 * Licensed under the Apache License, Version 2.0 (the "License").
 * You may not use this file except in compliance with the License.
 * A copy of the License is located at
 *
 *  http://aws.amazon.com/apache2.0
 *
 * or in the "license" file accompanying this file. This file is distributed
 * on an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either
 * express or implied. See the License for the specific language governing
 * permissions and limitations under the License.
 */
#include "http_server.h"

#include "io.h"

#include <aws/common/array_list.h>
#include <aws/http/request_response.h>
#include <aws/http/server.h>
#include <aws/io/socket.h>
#include <aws/io/stream.h>

const char *s_capsule_name_http_server = "aws_http_server";

struct py_http_server {
    struct aws_allocator *allocator;
    struct aws_http_server *server;
    PyObject *capsule;
    PyObject *on_incoming_connection;
    PyObject *on_destroy_complete;
    bool destructor_called;
    bool destroy_called;
    bool destroy_complete;
};

static void s_http_server_destructor(PyObject *http_server_capsule) {
    struct py_http_server *py_server = PyCapsule_GetPointer(http_server_capsule, s_capsule_name_http_server);
    py_server->destructor_called = true;
    if (py_server->server) {
        if (!py_server->destroy_called) {
            aws_http_server_release(py_server->server);
            py_server->destroy_called = true;
        }
    }
    /* the incoming callback is not freed until now */
    Py_XDECREF(py_server->on_incoming_connection);
    if (py_server->destroy_complete) {
         
        aws_mem_release(py_server->allocator, py_server);
    }
}

static void s_on_destroy_complete(void *user_data) {
    struct py_http_server *py_server = user_data;
    
    py_server->destroy_complete = true;
    PyObject *on_destroy_complete_cb = py_server->on_destroy_complete;
    py_server->server = NULL;
    PyGILState_STATE state = PyGILState_Ensure();
    if (!py_server->destructor_called) {    
        PyObject *result = PyObject_CallFunction(on_destroy_complete_cb, "(O)", py_server->capsule);
        if(result){
            Py_XDECREF(result);
        }
        else{
            PyErr_WriteUnraisable(PyErr_Occurred());
        }   
        Py_XDECREF(py_server->on_destroy_complete); 
    } else {
        Py_XDECREF(py_server->on_destroy_complete);
        aws_mem_release(py_server->allocator, py_server);
    }
    PyGILState_Release(state);
}

static void s_on_incoming_connection(
    struct aws_http_server *server,
    struct aws_http_connection *connection,
    int error_code,
    void *user_data) {
    (void)server;
    (void)connection;
    (void)error_code;
    (void)user_data;
    /* fake one */
}

PyObject *aws_py_http_server_create(PyObject *self, PyObject *args) {
    (void)self;

    struct py_http_server *py_server = NULL;
    struct aws_allocator *allocator = aws_crt_python_get_allocator();

    PyObject *bootstrap_capsule = NULL;
    PyObject *on_incoming_connection = NULL;
    PyObject *on_destroy_complete = NULL;
    const char *host_name = NULL;
    Py_ssize_t host_name_len = 0;
    uint16_t port_number = 0;
    PyObject *py_socket_options = NULL;
    PyObject *tls_conn_options_capsule = NULL;

    if (!PyArg_ParseTuple(
            args,
            "OOOs#HOO",
            &bootstrap_capsule,
            &on_incoming_connection,
            &on_destroy_complete,
            &host_name,
            &host_name_len,
            &port_number,
            &py_socket_options,
            &tls_conn_options_capsule)) {
        PyErr_SetNone(PyExc_ValueError);
        goto error;
    }

    if (host_name_len >= (signed int)AWS_ADDRESS_MAX_LEN || host_name_len == 0) {
        PyErr_SetString(PyExc_ValueError, "host_name is not valid");
        goto error;
    }

    if (py_socket_options == Py_None) {
        PyErr_SetString(PyExc_ValueError, "socket_options is a required argument");
        goto error;
    }

    if (!PyCallable_Check(on_incoming_connection)) {
        PyErr_SetString(PyExc_ValueError, "on_incoming_connection callback is required");
        goto error;
    }

    if (!PyCallable_Check(on_destroy_complete)) {
        PyErr_SetString(PyExc_TypeError, "on_destroy_complete is invalid");
        goto error;
    }

    struct aws_server_bootstrap *bootstrap = PyCapsule_GetPointer(bootstrap_capsule, s_capsule_name_server_bootstrap);
    if (!bootstrap) {
        goto error;
    }

    struct aws_tls_connection_options *connection_options = NULL;

    if (tls_conn_options_capsule != Py_None) {
        connection_options = PyCapsule_GetPointer(tls_conn_options_capsule, s_capsule_name_tls_conn_options);
        if(!connection_options){
            goto error;
        }
    }

    py_server = aws_mem_calloc(allocator, 1, sizeof(struct py_http_server));
    if (!py_server) {
        PyErr_SetAwsLastError();
        goto error;
    }

    struct aws_socket_options socket_options;
    if (!aws_socket_options_init_from_py(&socket_options, py_socket_options)) {
        goto error;
    }

    py_server->on_incoming_connection = on_incoming_connection;

    
    py_server->on_destroy_complete = on_destroy_complete;
    
    py_server->allocator = allocator;

    struct aws_http_server_options options;
    AWS_ZERO_STRUCT(options);
    options.self_size = sizeof(options);
    options.bootstrap = bootstrap;
    options.tls_options = connection_options;
    options.allocator = allocator;
    options.server_user_data = py_server;
    struct aws_socket_endpoint endpoint;
    AWS_ZERO_STRUCT(endpoint);

    snprintf(endpoint.address, host_name_len, "%s", host_name);
    endpoint.port = port_number;
    options.socket_options = &socket_options;
    options.endpoint = &endpoint;
    options.on_incoming_connection = s_on_incoming_connection;
    options.on_destroy_complete = s_on_destroy_complete;
    PyObject *capsule = NULL;
    py_server->server = aws_http_server_new(&options);
    
    if (py_server->server) {
        /* success */
        capsule = PyCapsule_New(py_server, s_capsule_name_http_server, s_http_server_destructor);
        if(!capsule){
            goto error;
        }
        py_server->capsule = capsule;
        Py_INCREF(on_incoming_connection);
        Py_INCREF(on_destroy_complete);
        return capsule;
    }

error:
    if (py_server) {
        aws_mem_release(py_server->allocator, py_server);
    }
    return NULL;
}

PyObject *aws_py_http_server_release(PyObject *self, PyObject *args) {
    (void)self;

    PyObject *server_capsule = NULL;

    if (PyArg_ParseTuple(args, "O", &server_capsule)) {
        if (server_capsule != Py_None) {
            struct py_http_server *py_server = PyCapsule_GetPointer(server_capsule, s_capsule_name_http_server);
            if(!py_server){
                return NULL;
            }
            if (py_server->server) {
                if (!py_server->destroy_called) {
                    py_server->destroy_called = true;
                    aws_http_server_release(py_server->server);
                }
            }
        }
    }
    Py_RETURN_NONE;
}
