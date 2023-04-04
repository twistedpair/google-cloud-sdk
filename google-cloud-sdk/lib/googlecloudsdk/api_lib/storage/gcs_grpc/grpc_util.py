# -*- coding: utf-8 -*- #
# Copyright 2023 Google LLC. All Rights Reserved.
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
"""Helper functions for making gRPC API calls."""

# TODO(b/271932922): Move functions from here to its own client class.

from __future__ import absolute_import
from __future__ import division
from __future__ import unicode_literals

from googlecloudsdk.api_lib.storage.gcs_grpc import metadata_util
from googlecloudsdk.command_lib.storage import hash_util


def get_full_bucket_name(bucket_name):
  """Returns the bucket resource name as expected by gRPC API."""
  return 'projects/_/buckets/{}'.format(bucket_name)


def download_object(gapic_client,
                    cloud_resource,
                    download_stream,
                    digesters,
                    progress_callback,
                    start_byte,
                    end_byte):
  """Downloads the object using gRPC."""
  # Initialize request arguments.
  bucket_name = get_full_bucket_name(cloud_resource.storage_url.bucket_name)
  request = gapic_client.types.ReadObjectRequest(
      bucket=bucket_name,
      object_=cloud_resource.storage_url.object_name,
      read_offset=start_byte,
      read_limit=end_byte - start_byte + 1 if end_byte is not None else 0)

  # Make the request.
  stream = gapic_client.storage.read_object(request=request)

  # Handle the response.
  processed_bytes = start_byte
  for response in stream:
    data = response.checksummed_data.content
    if data:
      download_stream.write(data)
      if digesters:
        for hash_object in digesters.values():
          hash_object.update(data)

      processed_bytes += len(data)
      if progress_callback:
        progress_callback(processed_bytes)


def _get_write_object_spec(client, object_resource, size):
  destination_object = client.types.Object(
      name=object_resource.storage_url.object_name,
      bucket='projects/_/buckets/{}'.format(
          object_resource.storage_url.bucket_name),
      size=size)
  return client.types.WriteObjectSpec(
      resource=destination_object, object_size=size)


def _simple_upload_write_object_request_generator(
    client, stream, destination_resource, resource_args):
  """Yields the WriteObjectRequest for each chunk of the source stream."""
  first_request_done = False
  while True:
    data = stream.read(
        client.types.ServiceConstants.Values.MAX_WRITE_CHUNK_BYTES)
    if data:
      if not first_request_done:
        write_object_spec = _get_write_object_spec(
            client, destination_resource, resource_args.size)
        object_checksums = client.types.ObjectChecksums(
            md5_hash=(
                hash_util.get_bytes_from_base64_string(resource_args.md5_hash)
                if resource_args.md5_hash is not None else None))
        write_offset = 0
        first_request_done = True
      else:
        write_object_spec = None
        object_checksums = None
        write_offset = None

      yield client.types.WriteObjectRequest(
          write_object_spec=write_object_spec,
          write_offset=write_offset,
          checksummed_data=client.types.ChecksummedData(content=data),
          object_checksums=object_checksums)
    else:
      yield client.types.WriteObjectRequest(
          checksummed_data=client.types.ChecksummedData(content=b''),
          finish_write=True)
      break


def upload_object(gapic_client,
                  source_stream,
                  destination_resource,
                  request_config):
  """Uploads the object using gRPC."""
  response = gapic_client.storage.write_object(
      requests=_simple_upload_write_object_request_generator(
          gapic_client,
          source_stream,
          destination_resource,
          request_config.resource_args))
  return metadata_util.get_object_resource_from_grpc_object(
      response.resource)

