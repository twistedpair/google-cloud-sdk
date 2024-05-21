# -*- coding: utf-8 -*- #
# Copyright 2024 Google Inc. All Rights Reserved.
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
"""Client for interaction with AspectType API CRUD DATAPLEX."""

from __future__ import absolute_import
from __future__ import division
from __future__ import unicode_literals

import os

from apitools.base.py import encoding
from googlecloudsdk.api_lib.dataplex import util as dataplex_api
from googlecloudsdk.calliope import exceptions
from googlecloudsdk.command_lib.iam import iam_util
from googlecloudsdk.core import yaml
from googlecloudsdk.core.util import files
import six


def GenerateAspectTypeForCreateRequest(args):
  """Create Aspect Type Request."""
  module = dataplex_api.GetMessageModule()
  request = module.GoogleCloudDataplexV1AspectType(
      description=args.description,
      displayName=args.display_name,
      labels=dataplex_api.CreateLabels(
          module.GoogleCloudDataplexV1AspectType, args
      ),
      metadataTemplate=GenerateAspectTypeMetadataTemplate(
          args.metadata_template_file_name
      ),
  )

  return request


def GenerateAspectTypeForUpdateRequest(args):
  """Update Aspect Type Request."""
  module = dataplex_api.GetMessageModule()
  return module.GoogleCloudDataplexV1AspectType(
      description=args.description,
      displayName=args.display_name,
      etag=args.etag,
      labels=dataplex_api.CreateLabels(
          module.GoogleCloudDataplexV1AspectType, args
      ),
      metadataTemplate=GenerateUpdateAspectTypeMetadataTemplate(
          args.metadata_template_file_name
      ),
  )


def GenerateAspectTypeUpdateMask(args):
  """Create Update Mask for AspectType."""
  update_mask = []
  if args.IsSpecified('description'):
    update_mask.append('description')
  if args.IsSpecified('display_name'):
    update_mask.append('displayName')
  if args.IsSpecified('labels'):
    update_mask.append('labels')
  if args.IsSpecified('metadata_template_file_name'):
    update_mask.append('metadataTemplate')
  return update_mask


def GenerateUpdateAspectTypeMetadataTemplate(metadata_template_file_name):
  """Update Metadata Template for AspectType."""
  if metadata_template_file_name is None:
    return None

  return GenerateAspectTypeMetadataTemplate(metadata_template_file_name)


def GenerateAspectTypeMetadataTemplate(metadata_template_file_name):
  """Create Metadata Template from specified file."""
  if not os.path.exists(metadata_template_file_name):
    raise exceptions.BadFileException('No such file [{0}]'.format(
        metadata_template_file_name))
  if os.path.isdir(metadata_template_file_name):
    raise exceptions.BadFileException('[{0}] is a directory'.format(
        metadata_template_file_name))
  try:
    with files.FileReader(metadata_template_file_name) as import_file:
      return ConvertMetadataTemplateFileToProto(import_file)
  except Exception as exp:
    exp_msg = getattr(exp, 'message', six.text_type(exp))
    msg = ('Unable to read Metadata Template config from specified file '
           '[{0}] because [{1}]'.format(metadata_template_file_name, exp_msg))
    raise exceptions.BadFileException(msg)


def ConvertMetadataTemplateFileToProto(metadata_template_file_path):
  """Construct an AspectTypeMetadataTemplate from a JSON/YAML formatted file.

  Args:
    metadata_template_file_path: Path to the JSON or YAML file.

  Returns:
    a protorpc.Message of type GoogleCloudDataplexV1AspectTypeMetadataTemplate
    filled in from the JSON or YAML metadata template file.

  Raises:
    BadFileException if the JSON or YAML file is malformed.
  """

  try:
    parsed_metadata_template = yaml.load(metadata_template_file_path)
  except ValueError as e:
    raise exceptions.BadFileException(
        'Error parsing metadata template file: {0}'.format(six.text_type(e)))

  metadata_template_message = dataplex_api.GetMessageModule(
      ).GoogleCloudDataplexV1AspectTypeMetadataTemplate
  metadata_template = encoding.PyValueToMessage(metadata_template_message,
                                                parsed_metadata_template)
  return metadata_template


def WaitForOperation(operation):
  """Waits for the given google.longrunning.Operation to complete."""
  return dataplex_api.WaitForOperation(
      operation,
      dataplex_api.GetClientInstance().projects_locations_aspectTypes)


def AspectTypeSetIamPolicy(aspect_type_ref, policy):
  """Set Iam Policy request."""
  set_iam_policy_req = dataplex_api.GetMessageModule(
  ).DataplexProjectsLocationsAspectTypesSetIamPolicyRequest(
      resource=aspect_type_ref.RelativeName(),
      googleIamV1SetIamPolicyRequest=dataplex_api.GetMessageModule()
      .GoogleIamV1SetIamPolicyRequest(policy=policy))
  return dataplex_api.GetClientInstance(
  ).projects_locations_aspectTypes.SetIamPolicy(set_iam_policy_req)


def AspectTypeGetIamPolicy(aspect_type_ref):
  """Get Iam Policy request."""
  get_iam_policy_req = dataplex_api.GetMessageModule(
  ).DataplexProjectsLocationsAspectTypesGetIamPolicyRequest(
      resource=aspect_type_ref.RelativeName())
  return dataplex_api.GetClientInstance(
  ).projects_locations_aspectTypes.GetIamPolicy(get_iam_policy_req)


def AspectTypeAddIamPolicyBinding(aspect_type_ref, member, role):
  """Add IAM policy binding request."""
  policy = AspectTypeGetIamPolicy(aspect_type_ref)
  iam_util.AddBindingToIamPolicy(
      dataplex_api.GetMessageModule().GoogleIamV1Binding, policy, member, role)
  return AspectTypeSetIamPolicy(aspect_type_ref, policy)


def AspectTypeRemoveIamPolicyBinding(aspect_type_ref, member, role):
  """Remove IAM policy binding request."""
  policy = AspectTypeGetIamPolicy(aspect_type_ref)
  iam_util.RemoveBindingFromIamPolicy(policy, member, role)
  return AspectTypeSetIamPolicy(aspect_type_ref, policy)


def AspectTypeSetIamPolicyFromFile(aspect_type_ref, policy_file):
  """Set IAM policy binding request from file."""
  policy = iam_util.ParsePolicyFile(
      policy_file,
      dataplex_api.GetMessageModule().GoogleIamV1Policy)
  return AspectTypeSetIamPolicy(aspect_type_ref, policy)

