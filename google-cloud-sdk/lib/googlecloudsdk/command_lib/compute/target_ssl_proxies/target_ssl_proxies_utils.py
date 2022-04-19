# -*- coding: utf-8 -*- #
# Copyright 2022 Google LLC. All Rights Reserved.
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
"""Code that's shared between multiple target-ssl-proxies subcommands."""

from __future__ import absolute_import
from __future__ import division
from __future__ import unicode_literals


def ResolveSslPolicy(args, ssl_policy_arg, target_ssl_proxy_ref, resources):
  """Parses the SSL policies that are pointed to by a Target SSL Proxy from args.

  This function handles parsing regional/global SSL policies that are
  pointed to by a regional/global Target SSL Proxy.

  Args:
    args: The arguments provided to the target_ssl_proxies command.
    ssl_policy_arg: The ResourceArgument specification for the ssl_policies
      argument.
    target_ssl_proxy_ref: The resource reference to the Target SSL Proxy. This
      is obtained by parsing the Target SSL Proxy arguments provided.
    resources: ComputeApiHolder resources.

  Returns:
    Returns the SSL policy resource
  """

  if IsRegionalTargetSslProxiesRef(target_ssl_proxy_ref):
    if not getattr(args, 'ssl_policy_region', None):
      args.ssl_policy_region = target_ssl_proxy_ref.region
  else:
    if not getattr(args, 'global_ssl_policy', None):
      args.global_ssl_policy = bool(args.ssl_policy)
  return ssl_policy_arg.ResolveAsResource(args, resources)


def IsRegionalTargetSslProxiesRef(target_ssl_proxy_ref):
  """Returns True if the Target SSL Proxy reference is regional."""

  return target_ssl_proxy_ref.Collection() == 'compute.regionTargetSslProxies'
