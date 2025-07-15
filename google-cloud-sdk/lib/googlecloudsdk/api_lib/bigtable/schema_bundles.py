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
from googlecloudsdk.calliope import parser_extensions
from googlecloudsdk.core import log
from googlecloudsdk.core import resources
from googlecloudsdk.core.util import files
from googlecloudsdk.generated_clients.apis.bigtableadmin.v2 import bigtableadmin_v2_messages


def ModifyCreateSchemaBundleRequest(
    unused_ref: resources.Resource,
    args: parser_extensions.Namespace,
    req: bigtableadmin_v2_messages.BigtableadminProjectsInstancesTablesSchemaBundlesCreateRequest,
) -> (
    bigtableadmin_v2_messages.BigtableadminProjectsInstancesTablesSchemaBundlesCreateRequest
):
  """Parse argument and construct create schema bundle request.

  This function is used to modify the create schema bundle request to include
  the proto descriptors file content if provided.

  Args:
    unused_ref: the gcloud resource (unused).
    args: input arguments.
    req: the real request to be sent to backend service.

  Returns:
    The modified request to be sent to backend service.

  Raises:
    ValueError: if the proto descriptors file is invalid.
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


def ModifyUpdateSchemaBundleRequest(
    unused_ref: resources.Resource,
    args: parser_extensions.Namespace,
    req: bigtableadmin_v2_messages.BigtableadminProjectsInstancesTablesSchemaBundlesPatchRequest,
) -> (
    bigtableadmin_v2_messages.BigtableadminProjectsInstancesTablesSchemaBundlesPatchRequest
):
  """Parse argument and construct update schema bundle request.

  This function is used to modify the update schema bundle request to include
  the proto descriptors file content if provided.

  Args:
    unused_ref: the gcloud resource (unused).
    args: input arguments.
    req: the real request to be sent to backend service.

  Returns:
    The modified request to be sent to backend service.

  Raises:
    ValueError: if the proto descriptors file is invalid.
  """
  if args.proto_descriptors_file:
    proto_desc_content = files.ReadBinaryFileContents(
        args.proto_descriptors_file
    )
    # Validates that the file contains a valid/parsable FileDescriptorSet.
    descriptor_pb2.FileDescriptorSet.FromString(proto_desc_content)
    req.schemaBundle.protoSchema.protoDescriptors = proto_desc_content
  if args.ignore_warnings:
    req.ignoreWarnings = True

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
