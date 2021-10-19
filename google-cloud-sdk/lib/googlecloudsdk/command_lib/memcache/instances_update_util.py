# -*- coding: utf-8 -*- #
# Copyright 2021 Google Inc. All Rights Reserved.
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
"""Utilities for `gcloud memcache instances update` commands."""

from __future__ import absolute_import
from __future__ import division
from __future__ import unicode_literals

from apitools.base.py import encoding
from googlecloudsdk.api_lib import memcache


def ChooseUpdateMethod(unused_ref, args):
  if args.IsSpecified('parameters'):
    return 'updateParameters'
  return 'patch'


def CreateUpdateRequest(ref, args):
  """Returns an Update or UpdateParameters request depending on the args given."""
  messages = memcache.Messages(ref.GetCollectionInfo().api_version)
  if args.IsSpecified('parameters'):
    params = encoding.DictToMessage(args.parameters,
                                    messages.MemcacheParameters.ParamsValue)
    parameters = messages.MemcacheParameters(params=params)
    param_req = messages.UpdateParametersRequest(
        updateMask='params', parameters=parameters)
    request = (
        messages.MemcacheProjectsLocationsInstancesUpdateParametersRequest(
            name=ref.RelativeName(), updateParametersRequest=param_req))
  else:
    mask = []
    instance = messages.Instance()
    if args.IsSpecified('display_name'):
      mask.append('displayName')
      instance.displayName = args.display_name
    if args.IsSpecified('node_count'):
      mask.append('nodeCount')
      instance.nodeCount = args.node_count
    if args.IsSpecified('labels'):
      mask.append('labels')
      instance.labels = messages.Instance.LabelsValue(
          additionalProperties=args.labels)
    # TODO(b/181810566): add maintenance policy update support to gcloud
    update_mask = ','.join(mask)
    request = (
        messages.MemcacheProjectsLocationsInstancesPatchRequest(
            name=ref.RelativeName(), instance=instance, updateMask=update_mask))

  return request
