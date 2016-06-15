# Copyright 2014 Google Inc. All Rights Reserved.
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
"""Common classes and functions for addresses."""
import abc
from googlecloudsdk.api_lib.compute import base_classes
from googlecloudsdk.command_lib.compute import flags


class AddressesMutator(base_classes.BaseAsyncMutator):
  """Base class for modifying addresses."""

  @staticmethod
  def Args(parser):
    """Adds common flags for mutating addresses."""
    scope = parser.add_mutually_exclusive_group()

    flags.AddRegionFlag(
        scope,
        resource_type='address',
        operation_type='operate on')

    scope.add_argument(
        '--global',
        action='store_true',
        help='If provided, it is assumed the addresses are global.')

  @property
  def service(self):
    if self.global_request:
      return self.compute.globalAddresses
    else:
      return self.compute.addresses

  @property
  def resource_type(self):
    return 'addresses'

  @abc.abstractmethod
  def CreateGlobalRequests(self, args):
    """Return a list of one of more globally-scoped request."""

  @abc.abstractmethod
  def CreateRegionalRequests(self, args):
    """Return a list of one of more regionally-scoped request."""

  def CreateRequests(self, args):
    self.global_request = getattr(args, 'global')

    if self.global_request:
      return self.CreateGlobalRequests(args)
    else:
      return self.CreateRegionalRequests(args)
