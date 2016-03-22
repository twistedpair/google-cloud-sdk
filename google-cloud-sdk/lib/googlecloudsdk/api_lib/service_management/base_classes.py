# Copyright 2016 Google Inc. All Rights Reserved.
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

"""Base commands for service management command classes."""

import abc

from googlecloudsdk.core import properties


# TODO(b/27358815): Remove the dependency on these base classes
class BaseServiceManagementCommand():
  """Base class for all service-management subcommands."""

  __metaclass__ = abc.ABCMeta

  @property
  def project(self):
    return properties.VALUES.core.project.Get()

  @property
  def services_client(self):
    return self.context['servicemanagement-v1']

  @property
  def services_messages(self):
    return self.context['servicemanagement-v1-messages']

  @property
  def apikeys_client(self):
    return self.context['apikeys-v1']

  @property
  def apikeys_messages(self):
    return self.context['apikeys-v1-messages']


class AccessCommand(BaseServiceManagementCommand):
  """A helper class with fields and methods related to principals."""

  # The key is how the user enters the type in the command-line
  # The value is what we prepend to the principal when talking to Inception
  # (e.g., "user:foo@bar.com")
  _PRINCIPAL_TYPES = {
      'user': 'user',
      'group': 'group',
  }

  def _BuildPrincipalString(self, principal, principal_type):
    return '%s:%s' % (self._PRINCIPAL_TYPES[principal_type], principal)
