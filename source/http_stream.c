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
#include "http_stream.h"

#include "io.h"

#include <aws/common/array_list.h>
#include <aws/io/socket.h>
#include <aws/io/stream.h>

const char *s_capsule_name_http_stream = "aws_http_client_stream";


int native_on_incoming_headers(
    struct aws_http_stream *internal_stream,
    const struct aws_http_header *header_array,
    size_t num_headers,
    void *user_data) {
    (void)internal_stream;
    struct py_http_stream *stream = user_data;

    PyGILState_STATE state = PyGILState_Ensure();

    for (size_t i = 0; i < num_headers; ++i) {
        PyObject *key = PyString_FromStringAndSize((const char *)header_array[i].name.ptr, header_array[i].name.len);
        PyObject *value =
            PyString_FromStringAndSize((const char *)header_array[i].value.ptr, header_array[i].value.len);

        PyDict_SetItem(stream->received_headers, key, value);
    }
    PyGILState_Release(state);

    return AWS_OP_SUCCESS;
}

int native_on_incoming_body(
    struct aws_http_stream *internal_stream,
    const struct aws_byte_cursor *data,
    void *user_data) {
    (void)internal_stream;

    int err = AWS_OP_SUCCESS;

    struct py_http_stream *stream = user_data;

    PyGILState_STATE state = PyGILState_Ensure();

    Py_ssize_t data_len = (Py_ssize_t)data->len;
    PyObject *result =
        PyObject_CallFunction(stream->on_incoming_body, "(" BYTE_BUF_FORMAT_STR ")", (const char *)data->ptr, data_len);
    if (!result) {
        PyErr_WriteUnraisable(PyErr_Occurred());
        err = AWS_OP_ERR;
    }
    Py_XDECREF(result);
    PyGILState_Release(state);

    return err;
}

void native_on_stream_complete(struct aws_http_stream *internal_stream, int error_code, void *user_data) {
    (void)internal_stream;
    struct py_http_stream *stream = user_data;

    PyGILState_STATE state = PyGILState_Ensure();

    PyObject *result = PyObject_CallFunction(stream->on_stream_completed, "(i)", error_code);
    Py_XDECREF(result);
    Py_XDECREF(stream->on_stream_completed);
    Py_XDECREF(stream->on_incoming_body);
    Py_XDECREF(stream->outgoing_body);

    PyGILState_Release(state);
}

void native_http_stream_destructor(PyObject *http_stream_capsule) {
    struct py_http_stream *stream = PyCapsule_GetPointer(http_stream_capsule, s_capsule_name_http_stream);
    assert(stream);

    aws_http_stream_release(stream->stream);
    aws_mem_release(stream->allocator, stream);
}