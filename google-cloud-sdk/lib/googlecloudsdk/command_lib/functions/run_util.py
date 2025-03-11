# -*- coding: utf-8 -*- #
# Copyright 2023 Google LLC. All Rights Reserved.
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
"""Cloud Run utility library for GCF."""

from __future__ import absolute_import
from __future__ import division
from __future__ import unicode_literals

from googlecloudsdk.api_lib.functions.v2 import util as api_util
from googlecloudsdk.api_lib.run import global_methods
from googlecloudsdk.command_lib.run import connection_context
from googlecloudsdk.command_lib.run import serverless_operations
from googlecloudsdk.core import resources


_CLOUD_RUN_SERVICE_COLLECTION_K8S = 'run.namespaces.services'
_CLOUD_RUN_SERVICE_COLLECTION_ONE_PLATFORM = 'run.projects.locations.services'


def AddOrRemoveInvokerBinding(function, member, add_binding=True, is_gen2=True):
  """Add the IAM binding for the invoker role on the function's Cloud Run service.

  Args:
    function: cloudfunctions_v2_messages.Function, a GCF v2 function.
    member: str, The user to bind the Invoker role to.
    add_binding: bool, Whether to add to or remove from the IAM policy.
    is_gen2: bool, Whether the function is a 2nd gen function. If false, the
      function is a 1st gen function undergoing upgrade.

  Returns:
    A google.iam.v1.Policy
  """
  service_ref_one_platform = _GetOnePlatformServiceRef(function, is_gen2)

  run_connection_context = _GetRunRegionalConnectionContext(
      service_ref_one_platform.locationsId
  )

  with serverless_operations.Connect(run_connection_context) as operations:
    return operations.AddOrRemoveIamPolicyBinding(
        _GetK8sServiceRef(service_ref_one_platform.Name()),
        add_binding=add_binding,
        member=member,
        role=serverless_operations.ALLOW_UNAUTH_POLICY_BINDING_ROLE,
    )


def GetService(function):
  """Get the Cloud Run service for the given function."""
  service_ref_one_platform = _GetOnePlatformServiceRef(function)

  run_connection_context = _GetRunRegionalConnectionContext(
      service_ref_one_platform.locationsId
  )

  with serverless_operations.Connect(run_connection_context) as operations:
    return operations.GetService(
        _GetK8sServiceRef(service_ref_one_platform.Name())
    )


def _GetRunRegionalConnectionContext(location):
  return connection_context.RegionalConnectionContext(
      location,
      global_methods.SERVERLESS_API_NAME,
      global_methods.SERVERLESS_API_VERSION,
  )


def _GetOnePlatformServiceRef(function, is_gen2=True):
  service_name = (
      function.serviceConfig.service
      if is_gen2
      else function.upgradeInfo.serviceConfig.service
  )
  return resources.REGISTRY.ParseRelativeName(
      service_name, _CLOUD_RUN_SERVICE_COLLECTION_ONE_PLATFORM
  )


def _GetK8sServiceRef(service_name):
  return resources.REGISTRY.ParseRelativeName(
      'namespaces/{}/services/{}'.format(api_util.GetProject(), service_name),
      _CLOUD_RUN_SERVICE_COLLECTION_K8S,
  )
