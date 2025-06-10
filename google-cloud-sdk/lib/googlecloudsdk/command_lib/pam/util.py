# -*- coding: utf-8 -*- #
# Copyright 2024 Google LLC. All Rights Reserved.
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

"""Utility functions for `gcloud pam` commands."""

from __future__ import absolute_import
from __future__ import division
from __future__ import unicode_literals

import re

from googlecloudsdk.api_lib.util import apis
from googlecloudsdk.calliope import arg_parsers
from googlecloudsdk.calliope import base
from googlecloudsdk.core import log
from googlecloudsdk.core import yaml


def SetForceFieldInDeleteEntitlementRequest(unused_ref, unused_args, req):
  """Modify request hook to set the force field in delete entitlement requests to true."""
  req.force = True
  return req


def ParseEntitlementNameIntoCreateEntitlementRequest(unused_ref, args, req):
  """Modify request hook to parse the entitlement name into a CreateEntitlementRequest."""
  entitlement = args.CONCEPTS.entitlement.Parse()
  req.parent = entitlement.result.Parent().RelativeName()
  req.entitlementId = entitlement.result.Name()
  return req


def SetUpdateMaskInUpdateEntitlementRequest(unused_ref, unused_args, req):
  """Modify request hook to set the update mask field in update entitlement requests to '*'."""
  req.updateMask = '*'
  return req


def FormatWithdrawResponse(response, unused_args):
  """Formats the response of the withdraw command."""
  modified_response = {}
  if response.name:
    modified_response['name'] = response.name
  if not response.metadata:
    return modified_response
  modified_response['metadata'] = {}
  properties = response.metadata.additionalProperties
  for prop in properties:
    if prop.key in ('apiVersion', 'createTime', 'target'):
      modified_response['metadata'][prop.key] = prop.value.string_value

  log.status.Print(
      'Grant withdrawal initiated. The operation will complete in some time. To'
      ' track its status, run:\n`gcloud pam operations wait {}`\nNote that'
      ' the wait command requires you to have the'
      ' `privilegedaccessmanager.operations.get` permission on the resource.'
      .format(response.name)
  )
  return modified_response


def GetApiVersionFromArgs(args):
  """Return API version based on args.

  Args:
    args: The argparse namespace.

  Returns:
    API version (e.g. v1alpha or v1beta).
  """
  release_track = args.calliope_command.ReleaseTrack()
  if release_track == base.ReleaseTrack.ALPHA:
    return 'v1alpha'
  if release_track == base.ReleaseTrack.BETA:
    return 'v1beta'
  if release_track == base.ReleaseTrack.GA:
    return 'v1'


def SetRequestedPrivilegedAccessInCreateGrantRequest(unused_ref, args, req):
  """Modify request hook to populate the requestedPrivilegedAccess field in create grant requests."""
  if not args.requested_resources:
    return req
  messages = apis.GetMessagesModule(
      'privilegedaccessmanager', GetApiVersionFromArgs(args)
  )
  if len(args.requested_resources) > 1:
    raise arg_parsers.ArgumentTypeError(
        'Only one resource is supported for grant scope.'
    )
  for resource in args.requested_resources:
    resource = resource.strip()
    pattern = r'^(projects|organizations|folders)\/.+'
    components = resource.split('/')
    if not re.match(pattern, resource) or len(components) != 2:
      raise arg_parsers.ArgumentTypeError(
          'Invalid resource name: {}. Resource name must be of the form'
          ' (projects|organizations|folders)/<id>.'.format(resource)
      )
    resource_type = (
        'cloudresourcemanager.googleapis.com/' + components[0].capitalize()[:-1]
    )
    full_name = '//cloudresourcemanager.googleapis.com/' + resource
    requested_privileged_access = messages.RequestedPrivilegedAccess()
    requested_privileged_access.gcpIamAccess = (
        messages.RequestedPrivilegedAccessGcpIamAccess()
    )
    requested_privileged_access.gcpIamAccess.resourceType = resource_type
    requested_privileged_access.gcpIamAccess.resource = full_name
    req.grant.requestedPrivilegedAccess.append(requested_privileged_access)

  return req


def LoadGrantScopeFromYaml(stream):
  """Loads a YAML document from a stream.

  This function takes a stream (expected to be a list with a single string
  element) and parses it as a YAML document. It returns the loaded YAML data as
  a Python object (typically a list or dictionary).

  Args:
    stream: The stream to load from.

  Returns:
   The loaded YAML data.
  """
  if not stream or not stream[0]:
    # Return an empty list if no file is provided or the file is empty.
    return []
  return yaml.load(stream[0])


# TODO(b/261183749): Remove modify_request_hook when singleton resource args
# are enabled in declarative.
def UpdateSettingsResource(unused_ref, unused_args, req):
  """Modify request hook to update the resource field in settings requests."""
  req.name = req.name + '/settings'
  return req


def SetUpdateMaskInUpdateSettingsRequest(unused_ref, unused_args, req):
  """Modify request hook to set the update mask field in update settings requests to '*'."""
  req.updateMask = '*'
  return req
