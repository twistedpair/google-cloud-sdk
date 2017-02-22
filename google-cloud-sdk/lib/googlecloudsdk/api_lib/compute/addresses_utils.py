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
from googlecloudsdk.api_lib.compute import base_classes
from googlecloudsdk.api_lib.compute import name_generator
from googlecloudsdk.calliope import exceptions
from googlecloudsdk.command_lib.compute import flags as compute_flags


class AddressesMutator(base_classes.BaseAsyncMutator):
  """Base class for modifying addresses."""

  @property
  def service(self):
    if self.global_request:
      return self.compute.globalAddresses
    else:
      return self.compute.addresses

  @property
  def resource_type(self):
    return 'addresses'

  @property
  def method(self):
    return 'Insert'

  def GetAddress(self, args, address, address_ref):
    return self.messages.Address(
        address=address,
        description=args.description,
        name=address_ref.Name())

  def CreateRequests(self, args):
    """Overrides."""
    names, addresses = self._GetNamesAndAddresses(args)
    if not args.name:
      args.name = names

    address_refs = self.ADDRESSES_ARG.ResolveAsResource(
        args, self.resources,
        scope_lister=compute_flags.GetDefaultScopeLister(
            self.compute_client, self.project))

    self.global_request = getattr(address_refs[0], 'region', None) is None

    requests = []
    for address, address_ref in zip(addresses, address_refs):
      address_msg = self.GetAddress(
          args,
          address,
          address_ref)

      if self.global_request:
        requests.append(self.messages.ComputeGlobalAddressesInsertRequest(
            address=address_msg, project=address_ref.project))
      else:
        requests.append(self.messages.ComputeAddressesInsertRequest(
            address=address_msg,
            region=address_ref.region,
            project=address_ref.project))
    return requests

  def _GetNamesAndAddresses(self, args):
    """Returns names and addresses provided in args."""
    if not args.addresses and not args.name:
      raise exceptions.ToolException(
          'At least one name or address must be provided.')

    if args.name:
      names = args.name
    else:
      # If we dont have any names then we must some addresses.
      names = [name_generator.GenerateRandomName() for _ in args.addresses]

    if args.addresses:
      addresses = args.addresses
    else:
      # If we dont have any addresses then we must some names.
      addresses = [None] * len(args.name)

    if len(addresses) != len(names):
      raise exceptions.ToolException(
          'If providing both, you must specify the same number of names as '
          'addresses.')

    return names, addresses
