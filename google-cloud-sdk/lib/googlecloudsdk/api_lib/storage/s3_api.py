# Lint as: python3
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
"""Implementation of CloudApi for s3 using boto3."""

from __future__ import absolute_import
from __future__ import division
from __future__ import unicode_literals

import boto3
from googlecloudsdk.api_lib.storage import cloud_api
from googlecloudsdk.api_lib.util import apis
from googlecloudsdk.command_lib.storage import resource_reference
from googlecloudsdk.command_lib.storage import storage_url


class S3Api(cloud_api.CloudApi):
  """S3 Api client."""

  def __init__(self):
    self.scheme = cloud_api.ProviderPrefix.S3.value
    self.client = boto3.client(self.scheme)
    self.messages = apis.GetMessagesModule('storage', 'v1')

  def _TranslateListBucketsResponse(self, bucket_dict, owner_dict):
    bucket_message = self.messages.Bucket(
        name=bucket_dict['Name'],
        timeCreated=bucket_dict['CreationDate'],
        owner=self.messages.Bucket.OwnerValue(
            entity=owner_dict['DisplayName'], entityId=owner_dict['ID']))

    return resource_reference.BucketResource.from_gcs_metadata_object(
        self.scheme, bucket_message)

  def ListBuckets(self, fields_scope=None):
    """See super class."""
    response = self.client.list_buckets()
    for s3_bucket in response['Buckets']:
      yield self._TranslateListBucketsResponse(s3_bucket, response['Owner'])

  def _TranslateListObjectsResponse(self, object_dict, bucket_name):
    object_message = self.messages.Object(
        name=object_dict['Key'],
        updated=object_dict['LastModified'],
        etag=object_dict['ETag'],
        size=object_dict['Size'],
        storageClass=object_dict['StorageClass'],
        bucket=bucket_name)

    cloud_url = storage_url.CloudUrl(
        scheme=self.scheme,
        bucket_name=bucket_name,
        object_name=object_message.name)

    return resource_reference.ObjectResource(cloud_url, object_message)

  def ListObjects(self,
                  bucket_name,
                  prefix=None,
                  delimiter=None,
                  all_versions=None,
                  fields_scope=None):
    """See super class."""
    paginator = self.client.get_paginator('list_objects_v2')
    page_iterator = paginator.paginate(Bucket=bucket_name)
    for page in page_iterator:
      for obj in page['Contents']:
        yield self._TranslateListObjectsResponse(obj, bucket_name)
