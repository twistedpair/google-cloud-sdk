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
import botocore
from googlecloudsdk.api_lib.storage import cloud_api
from googlecloudsdk.api_lib.storage import errors
from googlecloudsdk.api_lib.util import apis
from googlecloudsdk.command_lib.storage import resource_reference
from googlecloudsdk.command_lib.storage import storage_url
from googlecloudsdk.core import exceptions as core_exceptions

# Head object response keys and their self.messages.Object attribute
# counterparts. Note: this does not include all of the keys that head_object
# can return, as some require additional processing or do not clearly
# correspond to a field in self.messages.Object.
_S3_HEAD_OBJECT_KEY_TRANSLATION = {
    'CacheControl': 'cacheControl',
    'PartsCount': 'componentCount',
    'ContentDisposition': 'contentDisposition',
    'ContentEncoding': 'contentEncoding',
    'ContentLanguage': 'contentLanguage',
    'ContentType': 'contentType',
    'ETag': 'etag',
    'ContentLength': 'size',
    'StorageClass': 'storageClass',
    'LastModified': 'updated',
    'SSEKMSKeyId': 'kmsKeyName',
    'ObjectLockRetainUntilDate': 'retentionExpirationTime',
}


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
    try:
      response = self.client.list_buckets()
      for s3_bucket in response['Buckets']:
        yield self._TranslateListBucketsResponse(
            s3_bucket, response['Owner'])
    except botocore.exceptions.ClientError as error:
      core_exceptions.reraise(errors.S3ApiError(error))

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
    try:
      paginator = self.client.get_paginator('list_objects_v2')
      page_iterator = paginator.paginate(Bucket=bucket_name)
      for page in page_iterator:
        for obj in page['Contents']:
          yield self._TranslateListObjectsResponse(obj, bucket_name)
    except botocore.exceptions.ClientError as error:
      core_exceptions.reraise(errors.S3ApiError(error))

  # pylint:disable=unused-argument
  def DownloadObject(self,
                     bucket_name,
                     object_name,
                     download_stream,
                     compressed_encoding=False,
                     decryption_wrapper=None,
                     digesters=None,
                     download_strategy=cloud_api.DownloadStrategy.ONE_SHOT,
                     generation=None,
                     object_size=None,
                     progress_callback=None,
                     serialization_data=None,
                     start_byte=0,
                     end_byte=None):
    """See super class."""
    kwargs = {'Bucket': bucket_name, 'Key': object_name}
    if generation:
      kwargs['VersionId'] = generation
    try:
      response = self.client.get_object(**kwargs)
      download_stream.write(response['Body'].read())
      return response['ContentEncoding']
    except botocore.exceptions.ClientError as error:
      core_exceptions.reraise(errors.S3ApiError(error))

    # TODO(b/161437901): Handle resumed download.
    # TODO(b/161460749): Handle download retries.
    # pylint:enable=unused-argument

  def _GetObjectMessageFromS3Response(self, object_dict, bucket_name,
                                      object_name):
    object_message = self.messages.Object(
        bucket=bucket_name,
        name=object_name,
    )

    for key, value in object_dict.items():
      if key in _S3_HEAD_OBJECT_KEY_TRANSLATION:
        message_class_field_name = _S3_HEAD_OBJECT_KEY_TRANSLATION[key]
        setattr(object_message, message_class_field_name, value)

    if 'Metadata' in object_dict:
      property_class = self.messages.Object.MetadataValue.AdditionalProperty
      object_message.metadata = self.messages.Object.MetadataValue(
          additionalProperties=[
              property_class(key=k, value=v)
              for k, v in object_dict['Metadata'].items()
          ])

    return object_message

  def _GetObjectUrlFromS3Response(self, object_dict, bucket_name, object_name):
    object_url = storage_url.CloudUrl(
        scheme=self.scheme, bucket_name=bucket_name, object_name=object_name)

    if 'VersionId' in object_dict:
      # botocore validates the type of the fields it returns, ensuring VersionId
      # is a string.
      object_url.generation = object_dict['VersionId']

    return object_url

  def _GetObjectResourceFromS3Response(self, object_dict, bucket_name,
                                       object_name):
    object_message = self._GetObjectMessageFromS3Response(
        object_dict, bucket_name, object_name)

    object_url = self._GetObjectUrlFromS3Response(
        object_dict, bucket_name, object_name)

    return resource_reference.ObjectResource(
        object_url, object_message, additional_metadata=object_dict)

  def GetObjectMetadata(self,
                        bucket_name,
                        object_name,
                        generation=None,
                        fields_scope=None):
    """See super class."""
    request = {'Bucket': bucket_name, 'Key': object_name}

    # The VersionId keyword argument to head_object is not nullable if it is
    # present, so only include it in the function call if it has a value.
    if generation is not None:
      request['VersionId'] = generation

    try:
      object_dict = self.client.head_object(**request)
    except botocore.exceptions.ClientError as error:
      core_exceptions.reraise(errors.S3ApiError(error))

    return self._GetObjectResourceFromS3Response(
        object_dict, bucket_name, object_name)
