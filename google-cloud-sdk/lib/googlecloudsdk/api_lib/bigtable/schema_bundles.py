# -*- coding: utf-8 -*- #
# Copyright 2025 Google LLC. All Rights Reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#    http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""Bigtable schema bundles API helper."""

from __future__ import absolute_import
from __future__ import division
from __future__ import unicode_literals

from cloudsdk.google.protobuf import descriptor_pb2
from cloudsdk.google.protobuf import text_format
from googlecloudsdk.core import log
from googlecloudsdk.core.util import files


def ModifyCreateSchemaBundleRequest(unused_ref, args, req):
  """Parse argument and construct create schema bundle request.

  Args:
    unused_ref: the gcloud resource (unused).
    args: input arguments.
    req: the real request to be sent to backend service.

  Returns:
    The modified request to be sent to backend service.
  """
  if args.proto_descriptors_file:
    proto_desc_content = files.ReadBinaryFileContents(
        args.proto_descriptors_file
    )
    # Validates that the file contains a valid/parsable FileDescriptorSet.
    descriptor_pb2.FileDescriptorSet.FromString(proto_desc_content)
    req.schemaBundle.protoSchema.protoDescriptors = proto_desc_content

  # By specifying the request_id_field for the schema bundle resource in the
  # declarative yaml file, the req.schemaBundleId and the req.parent will be
  # automatically mapped, therefore no change regarding them is needed here.
  return req


def PrintParsedProtoDescriptorsInGetResponse(response, _):
  """Parse the proto descriptors in the Get response and print it.

  Args:
    response: the response from the backend service.
    _: unused.

  Returns:
    The original response.
  """
  if (
      response.protoSchema is not None
      and response.protoSchema.protoDescriptors is not None
  ):
    descriptors = descriptor_pb2.FileDescriptorSet.FromString(
        response.protoSchema.protoDescriptors
    )
    log.status.Print(text_format.MessageToString(descriptors))
  return response
