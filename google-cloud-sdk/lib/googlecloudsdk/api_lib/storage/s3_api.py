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
from googlecloudsdk.command_lib.storage import resource_reference
from googlecloudsdk.command_lib.storage import storage_url
from googlecloudsdk.core import exceptions as core_exceptions


_GCS_TO_S3_PREDEFINED_ACL_TRANSLATION_DICT = {
    'authenticatedRead': 'authenticated-read',
    'bucketOwnerFullControl': 'bucket-owner-full-control',
    'bucketOwnerRead': 'bucket-owner-read',
    'private': 'private',
    'publicRead': 'public-read',
    'publicReadWrite': 'public-read-write'
}


def _TranslatePredefinedAclStringToS3(predefined_acl_string):
  """Translates Apitools predefined ACL enum key (as string) to S3 equivalent.

  Args:
    predefined_acl_string (str): Value representing user permissions.

  Returns:
    Translated ACL string.

  Raises:
    ValueError: Predefined ACL translation could not be found.
  """
  if predefined_acl_string not in _GCS_TO_S3_PREDEFINED_ACL_TRANSLATION_DICT:
    raise ValueError('Could not translate predefined_acl_string {} to'
                     ' AWS-accepted ACL.'.format(predefined_acl_string))
  return _GCS_TO_S3_PREDEFINED_ACL_TRANSLATION_DICT[predefined_acl_string]


# pylint:disable=abstract-method
class S3Api(cloud_api.CloudApi):
  """S3 Api client."""

  def __init__(self):
    self.scheme = storage_url.ProviderPrefix.S3
    self.client = boto3.client(self.scheme.value)

  def _GetObjectUrlFromS3Response(
      self, object_dict, bucket_name, object_name=None):
    """Creates storage_url.CloudUrl from S3 API response.

    Args:
      object_dict (dict): Dictionary representing S3 API response.
      bucket_name (str): Bucket to include in URL.
      object_name (str | None): Object to include in URL.

    Returns:
      storage_url.CloudUrl populated with data.
    """
    object_url = storage_url.CloudUrl(
        scheme=self.scheme, bucket_name=bucket_name, object_name=object_name)

    if 'VersionId' in object_dict:
      # botocore validates the type of the fields it returns, ensuring VersionId
      # is a string.
      object_url.generation = object_dict['VersionId']

    return object_url

  def _GetObjectResourceFromS3Response(self, object_dict, bucket_name,
                                       object_name=None):
    """Creates resource_reference.ObjectResource from S3 API response.

    Args:
      object_dict (dict): Dictionary representing S3 API response.
      bucket_name (str): Bucket response is relevant to.
      object_name (str | None): Object if relevant to query.

    Returns:
      resource_reference.ObjectResource populated with data.
    """
    object_url = self._GetObjectUrlFromS3Response(
        object_dict, bucket_name, object_name or object_dict['Key'])
    etag = None
    if 'ETag' in object_dict:
      etag = object_dict['ETag']
    elif 'CopyObjectResult' in object_dict:
      etag = object_dict['CopyObjectResult']['ETag']
    size = object_dict.get('Size', None)

    return resource_reference.ObjectResource(
        object_url, etag=etag, metadata=object_dict, size=size)

  def _GetPrefixResourceFromS3Response(self, prefix_dict, bucket_name):
    """Creates resource_reference.PrefixResource from S3 API response.

    Args:
      prefix_dict (dict): The S3 API response representing a prefix.
      bucket_name (str): Bucket for the prefix.

    Returns:
      A resource_reference.PrefixResource instance.
    """
    prefix = prefix_dict['Prefix']
    return resource_reference.PrefixResource(
        storage_url.CloudUrl(
            scheme=self.scheme, bucket_name=bucket_name, object_name=prefix),
        prefix=prefix)

  def GetBucket(self, bucket_name, fields_scope=cloud_api.FieldsScope.SHORT):
    """See super class."""
    metadata = {'Name': bucket_name}
    # TODO (b/168716392): As new commands are implemented, they may want
    # specific error handling for different methods.
    try:
      # Low-bandwidth way to determine if bucket exists for FieldsScope.SHORT.
      metadata.update(self.client.get_bucket_location(
          Bucket=bucket_name))
    except botocore.exceptions.ClientError as error:
      metadata['LocationConstraint'] = errors.S3ApiError(error)

    if fields_scope is not cloud_api.FieldsScope.SHORT:
      # Data for FieldsScope.NO_ACL.
      for key, api_call, result_has_key in [
          ('CORSRules', self.client.get_bucket_cors, True),
          ('LifecycleConfiguration',
           self.client.get_bucket_lifecycle_configuration, False),
          ('LoggingEnabled', self.client.get_bucket_logging, True),
          ('Payer', self.client.get_bucket_request_payment, True),
          ('Versioning', self.client.get_bucket_versioning, False),
          ('Website', self.client.get_bucket_website, False)]:
        try:
          api_result = api_call(Bucket=bucket_name)
          # Some results are wrapped in dictionaries with keys matching "key".
          metadata[key] = api_result[key] if result_has_key else api_result
        except botocore.exceptions.ClientError as error:
          metadata[key] = errors.S3ApiError(error)

      # User requested ACL's with FieldsScope.FULL.
      if fields_scope is cloud_api.FieldsScope.FULL:
        try:
          metadata['ACL'] = self.client.get_bucket_acl(Bucket=bucket_name)
        except botocore.exceptions.ClientError as error:
          metadata['ACL'] = errors.S3ApiError(error)

    return resource_reference.BucketResource(
        storage_url.CloudUrl(storage_url.ProviderPrefix.S3, bucket_name),
        metadata=metadata)

  def ListBuckets(self, fields_scope=None):
    """See super class."""
    try:
      response = self.client.list_buckets()
      for bucket in response['Buckets']:
        yield resource_reference.BucketResource(
            storage_url.CloudUrl(storage_url.ProviderPrefix.S3,
                                 bucket['Name']),
            metadata={'Bucket': bucket, 'Owner': response['Owner']})
    except botocore.exceptions.ClientError as error:
      core_exceptions.reraise(errors.S3ApiError(error))

  def ListObjects(self,
                  bucket_name,
                  prefix='',
                  delimiter='',
                  all_versions=None,
                  fields_scope=None):
    """See super class."""
    try:
      paginator = self.client.get_paginator('list_objects_v2')
      page_iterator = paginator.paginate(
          Bucket=bucket_name, Prefix=prefix, Delimiter=delimiter)
      for page in page_iterator:
        for object_dict in page.get('Contents', []):
          yield self._GetObjectResourceFromS3Response(object_dict, bucket_name)
        for prefix_dict in page.get('CommonPrefixes', []):
          prefix = prefix_dict['Prefix']
          yield self._GetPrefixResourceFromS3Response(prefix_dict, bucket_name)
    except botocore.exceptions.ClientError as error:
      core_exceptions.reraise(errors.S3ApiError(error))

  def CopyObject(self,
                 source_resource,
                 destination_resource,
                 progress_callback=None,
                 request_config=None):
    """See super class."""
    del progress_callback

    source_kwargs = {'Bucket': source_resource.storage_url.bucket_name,
                     'Key': source_resource.storage_url.object_name}
    if source_resource.storage_url.generation:
      source_kwargs['VersionId'] = source_resource.storage_url.generation

    kwargs = {'Bucket': destination_resource.storage_url.bucket_name,
              'Key': destination_resource.storage_url.object_name,
              'CopySource': source_kwargs}

    if request_config and request_config.predefined_acl_string:
      kwargs['ACL'] = _TranslatePredefinedAclStringToS3(
          request_config.predefined_acl_string)

    try:
      response = self.client.copy_object(**kwargs)
      return self._GetObjectResourceFromS3Response(
          response, kwargs['Bucket'], kwargs['Key'])
    except botocore.exceptions.ClientError as error:
      core_exceptions.reraise(errors.S3ApiError(error))

    # TODO(b/161900052): Implement resumable copies.

  # pylint: disable=unused-argument
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
      return response.get('ContentEncoding', None)
    except botocore.exceptions.ClientError as error:
      core_exceptions.reraise(errors.S3ApiError(error))

    # TODO(b/161437901): Handle resumed download.
    # TODO(b/161460749): Handle download retries.
    # pylint:enable=unused-argument

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

  def UploadObject(self,
                   upload_stream,
                   upload_resource,
                   progress_callback=None,
                   request_config=None):
    """See super class."""
    # TODO(b/160998556): Implement resumable upload.
    del progress_callback

    kwargs = {'Bucket': upload_resource.storage_url.bucket_name,
              'Key': upload_resource.storage_url.object_name,
              'Body': upload_stream.read()}
    if request_config and request_config.predefined_acl_string:
      kwargs['ACL'] = _TranslatePredefinedAclStringToS3(
          request_config.predefined_acl_string)

    try:
      response = self.client.put_object(**kwargs)
      return self._GetObjectResourceFromS3Response(
          response, upload_resource.storage_url.bucket_name,
          upload_resource.storage_url.object_name)
    except botocore.exceptions.ClientError as error:
      core_exceptions.reraise(errors.S3ApiError(error))
