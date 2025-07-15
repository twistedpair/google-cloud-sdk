# -*- coding: utf-8 -*- #
# Copyright 2021 Google LLC. All Rights Reserved.
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
"""Networsecurity resource completers for the completion_cache module."""

from __future__ import absolute_import
from __future__ import division
from __future__ import unicode_literals

from googlecloudsdk.command_lib.util import completers
from googlecloudsdk.core import exceptions


class Error(exceptions.Error):
  """Exceptions for this module."""


class ServerTlsPoliciesCompleter(completers.MultiResourceCompleter):
  """Completer for ServerTlsPolicies."""

  def __init__(self, **kwargs):
    super(ServerTlsPoliciesCompleter, self).__init__(
        completers=[
            GlobalServerTlsPoliciesCompleter,
            RegionServerTlsPoliciesCompleter,
        ],
        **kwargs
    )


class GlobalServerTlsPoliciesCompleter(completers.ListCommandCompleter):
  """Completer for Global ServerTlsPolicies."""

  def __init__(self, **kwargs):
    super(GlobalServerTlsPoliciesCompleter, self).__init__(
        collection='networksecurity.projects.locations.serverTlsPolicies',
        api_version='v1alpha1',
        list_command=(
            'network-security server-tls-policies list --location=global --uri'
        ),
        **kwargs
    )


class RegionServerTlsPoliciesCompleter(completers.ListCommandCompleter):
  """Completer for Regional ServerTlsPolicies."""

  def __init__(self, **kwargs):
    super(RegionServerTlsPoliciesCompleter, self).__init__(
        collection='networksecurity.projects.locations.serverTlsPolicies',
        api_version='v1alpha1',
        list_command=(
            'network-security server-tls-policies list --filter=region:* --uri'
        ),
        **kwargs
    )


class BackendAuthenticationConfigsCompleter(completers.MultiResourceCompleter):
  """Completer for BackendAuthenticationConfigs.

  This is used to automatically complete the backend authentication
  config name in the tls-settings flag.
  """

  def __init__(self, **kwargs):
    super(BackendAuthenticationConfigsCompleter, self).__init__(
        completers=[
            GlobalBackendAuthenticationConfigsCompleter,
            RegionBackendAuthenticationConfigsCompleter,
        ],
        **kwargs
    )


class GlobalBackendAuthenticationConfigsCompleter(
    completers.ListCommandCompleter
):
  """Completer for Global BackendAuthenticationConfigs."""

  def __init__(self, **kwargs):
    super(GlobalBackendAuthenticationConfigsCompleter, self).__init__(
        collection=(
            'networksecurity.projects.locations.backendAuthenticationConfigs'
        ),
        list_command=(
            'network-security backend-authentication-configs list'
            ' --location=global --uri'
        ),
        **kwargs
    )


class RegionBackendAuthenticationConfigsCompleter(
    completers.ListCommandCompleter
):
  """Completer for Regional BackendAuthenticationConfigs."""

  def __init__(self, **kwargs):
    super(RegionBackendAuthenticationConfigsCompleter, self).__init__(
        collection=(
            'networksecurity.projects.locations.backendAuthenticationConfigs'
        ),
        list_command=(
            'network-security backend-authentication-configs list'
            ' --filter=region:* --uri'
        ),
        **kwargs
    )
