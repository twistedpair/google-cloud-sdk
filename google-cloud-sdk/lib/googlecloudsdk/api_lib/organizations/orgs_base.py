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

"""Base class for Organization commands."""

from googlecloudsdk.calliope import base
from googlecloudsdk.core import apis
from googlecloudsdk.core import resources


ORGS_COLLECTION = 'cloudresourcemanager.organizations'


class OrganizationCommand(base.Command):
  """Common methods for an organization command."""

  @staticmethod
  def IdArg(parser, help_text):
    parser.add_argument(
        'id',
        metavar='ORGANIZATION_ID',
        completion_resource=ORGS_COLLECTION,
        list_command_path='organizations',
        help=help_text)

  def Collection(self):
    return ORGS_COLLECTION

  def OrganizationsClient(self):
    client = apis.GetClientInstance('cloudresourcemanager', 'v1beta1')
    return client.organizations

  def OrganizationsMessages(self):
    return apis.GetMessagesModule('cloudresourcemanager', 'v1beta1')

  def GetOrganizationRef(self, organization_id):
    return resources.Parse(organization_id, collection=self.Collection())

  def GetUriFunc(self):
    def _GetUri(resource):
      return self.GetOrganizationRef(resource.organizationId).SelfLink()
    return _GetUri
