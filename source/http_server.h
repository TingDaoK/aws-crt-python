#ifndef AWS_CRT_PYTHON_HTTP_SERVER_H
#define AWS_CRT_PYTHON_HTTP_SERVER_H
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
#include "module.h"
#include <aws/http/connection.h>

extern const char *s_capsule_name_http_server;

/**
 * Create a new server. returns a server object.
 */
PyObject *aws_py_http_server_create(PyObject *self, PyObject *args);


/**
 * Release the server. It will close the listening socket and all the connections existing in the server.
 * The on_destroy_complete will be invoked when the destroy operation completes
 */
PyObject *aws_py_http_server_release(PyObject *self, PyObject *args);

#endif /* AWS_CRT_PYTHON_HTTP_CLIENT_CONNECTION_H */
