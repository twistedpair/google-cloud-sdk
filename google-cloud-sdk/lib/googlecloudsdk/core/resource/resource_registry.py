# Copyright 2017 Google Inc. All Rights Reserved.
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
"""Resource info registry."""

from googlecloudsdk.core.resource import resource_exceptions
from googlecloudsdk.core.resource import resource_info

RESOURCE_REGISTRY = {

    # cloud billing
    'cloudbilling.billingAccounts':
        resource_info.ResourceInfo(
            cache_command='billing accounts list',
            # TODO(b/22402915) Delete this when OP resource completion is
            # supported.
            bypass_cache=True,
            list_format="""
          table(
            name.basename():label=ID,
            displayName:label=NAME,
            open
          )
        """,),

    # cloud key management system
    'cloudkms.projects.locations':
        resource_info.ResourceInfo(
            bypass_cache=True,
            list_command='kms locations list --format=value(location_id)',
            list_format="""
          table(
            locationId
          )
        """,),

    # Cloud SDK client side resources

    # compute

    # This entry is needed due to a bug in the resource parser. It will be
    # removable when the new completion code lands.
    'compute.instances':
        resource_info.ResourceInfo(
            async_collection='compute.operations',
            cache_command='compute instances list',
            list_format="""
          table(
            name,
            zone.basename(),
            machineType.machine_type().basename(),
            scheduling.preemptible.yesno(yes=true, no=''),
            networkInterfaces[].networkIP.notnull().list():label=INTERNAL_IP,
            networkInterfaces[].accessConfigs[0].natIP.notnull().list()\
            :label=EXTERNAL_IP,
            status
          )
        """,),

    # iam
    'iam.service_accounts':
        resource_info.ResourceInfo(
            list_command='iam service-accounts list --format=value(email)',
            bypass_cache=True,
            list_format="""
          table(
            displayName:label=NAME,
            email
          )
        """,),

    # special IAM roles completion case
    'iam.roles':
        resource_info.ResourceInfo(
            bypass_cache=True,),
}


def Get(collection, must_be_registered=False):
  """Returns the ResourceInfo for collection or None if not registered.

  Args:
    collection: The resource collection.
    must_be_registered: Raises exception if True, otherwise returns None.

  Raises:
    UnregisteredCollectionError: If collection is not registered and
      must_be_registered is True.

  Returns:
    The ResourceInfo for collection or an default ResourceInfo if not
      registered.
  """
  info = RESOURCE_REGISTRY.get(collection, None)
  if not info:
    if not must_be_registered:
      return resource_info.ResourceInfo()
    raise resource_exceptions.UnregisteredCollectionError(
        'Collection [{0}] is not registered.'.format(collection))
  info.collection = collection
  return info
