# -*- coding: utf-8 -*- #
# Copyright 2020 Google LLC. All Rights Reserved.
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
"""Essential Contacts API."""

from __future__ import absolute_import
from __future__ import division
from __future__ import unicode_literals

from googlecloudsdk.api_lib.util import apis


class ContactsClient():
  """Client for Essential Contacts API."""

  def __init__(self, version='v1beta1'):
    self.client = apis.GetClientInstance(
        api_name='essentialcontacts', api_version=version, no_http=False)

    self._messages = self.client.MESSAGES_MODULE

    self._projects_service = self.client.projects_contacts

    self._folders_service = self.client.folders_contacts

    self._organizations_service = self.client.organizations_contacts

  def Delete(self, contact_name):
    """Deletes an Essential Contact.

    Args:
      contact_name: the full id of the contact to delete in the form of
        [projects|folders|organizations]/{resourceId}/contacts/{contactId}

    Returns:
      Empty response message.
    """
    if contact_name.startswith('folders'):
      delete_req = self._messages.EssentialcontactsFoldersContactsDeleteRequest(
          name=contact_name)
      return self._folders_service.Delete(delete_req)

    if contact_name.startswith('organizations'):
      delete_req = self._messages.EssentialcontactsOrganizationsContactsDeleteRequest(
          name=contact_name)
      return self._organizations_service.Delete(delete_req)

    delete_req = self._messages.EssentialcontactsProjectsContactsDeleteRequest(
        name=contact_name)
    return self._projects_service.Delete(delete_req)
