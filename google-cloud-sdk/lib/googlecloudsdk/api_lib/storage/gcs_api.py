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
"""Client for interacting with Google Cloud Storage.

Implements CloudApi for the GCS JSON API. Example functions include listing
buckets, uploading objects, and setting lifecycle conditions.

TODO(b/160601969): Update class with remaining API methods for ls and cp.
                   Note, this class has not been tested against the GCS API yet.
"""

from __future__ import absolute_import
from __future__ import division
from __future__ import unicode_literals

from apitools.base.py import list_pager

from googlecloudsdk.api_lib.storage import cloud_api
from googlecloudsdk.api_lib.util import apis as core_apis
from googlecloudsdk.core import properties


# pylint: disable=abstract-method
class GcsApi(cloud_api.CloudApi):
  """Client for Google Cloud Storage API."""

  def __init__(self):
    self.client = core_apis.GetClientInstance('storage', 'v1')
    self.messages = core_apis.GetMessagesModule('storage', 'v1')

  def _GetGlobalParamsAndProjection(self, fields_scope, message_class):
    """Generate query projection and fields from fields_scope.

    Args:
      fields_scope (FieldsScope): Used to determine projection and fields to
          return.
      message_class (object): Apitools message object that contains a projection
          enum.

    Returns:
      global_params (object): API query parameters used across calls.
      projection (ProjectionValueValuesEnum): Determines if ACL properties
                                                should be returned.

    Raises:
      ValueError: The fields_scope isn't recognized.
    """
    if fields_scope not in cloud_api.FieldsScope:
      raise ValueError('Invalid fields_scope.')
    message_projection_enum = message_class.ProjectionValueValuesEnum

    global_params = self.messages.StandardQueryParameters()
    projection = None

    if fields_scope == cloud_api.FieldsScope.SHORT:
      global_params.fields = ','.join(['name', 'size'])
      projection = message_projection_enum.noAcl
    elif fields_scope == cloud_api.FieldsScope.NO_ACL:
      projection = message_projection_enum.noAcl
    elif fields_scope == cloud_api.FieldsScope.FULL:
      projection = message_projection_enum.full

    return (global_params, projection)

  def ListBuckets(self, fields_scope=cloud_api.FieldsScope.NO_ACL):
    """See super class."""
    global_params, projection = self._GetGlobalParamsAndProjection(
        fields_scope, self.messages.StorageBucketsListRequest)
    request = self.messages.StorageBucketsListRequest(
        project=properties.VALUES.core.project.GetOrFail(),
        projection=projection)

    # TODO(b/160238394) Decrypt metadata fields if necessary.
    bucket_iter = list_pager.YieldFromList(
        self.client.buckets,
        request,
        batch_size=cloud_api.NUM_ITEMS_PER_LIST_PAGE,
        global_params=global_params)
    for b in bucket_iter:
      yield b

  def ListObjects(self,
                  bucket_name,
                  prefix=None,
                  delimiter=None,
                  all_versions=None,
                  fields_scope=cloud_api.FieldsScope.NO_ACL):
    """See super class."""
    global_params, projection = self._GetGlobalParamsAndProjection(
        fields_scope, self.messages.StorageObjectsListRequest)
    request = self.messages.StorageObjectsListRequest(
        bucket=bucket_name, prefix=prefix, projection=projection)

    # TODO(b/160238394) Decrypt metadata fields if necessary.
    object_iter = list_pager.YieldFromList(
        self.client.objects,
        request,
        batch_size=cloud_api.NUM_ITEMS_PER_LIST_PAGE,
        global_params=global_params)
    for obj in object_iter:
      yield obj

  def GetObjectMetadata(self,
                        bucket_name,
                        object_name,
                        generation=None,
                        fields_scope=cloud_api.FieldsScope.NO_ACL):
    """See super class."""

    global_params, projection = self._GetGlobalParamsAndProjection(
        fields_scope, self.messages.StorageObjectsGetRequest)
    # TODO(b/160238394) Decrypt metadata fields if necessary.
    return self.client.objects.Get(
        self.messages.StorageObjectsGetRequest(
            bucket=bucket_name,
            object=object_name,
            generation=generation,
            projection=projection),
        global_params=global_params
    )
