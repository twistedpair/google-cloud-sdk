# -*- coding: utf-8 -*- #
# Copyright 2022 Google LLC. All Rights Reserved.
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
"""Tools for converting metadata fields to S3 formats."""

from __future__ import absolute_import
from __future__ import division
from __future__ import unicode_literals

from googlecloudsdk.api_lib.storage import metadata_util


def process_cors(file_path):
  """Converts CORS file to S3 metadata dict."""
  # Expect CORS file to already be in correct format for S3.
  # { "CORSRules": [...] }
  # https://boto3.amazonaws.com/v1/documentation/api/latest/reference
  # /services/s3.html#S3.Client.put_bucket_cors
  return metadata_util.cached_read_json_file(file_path)


def process_labels(file_path):
  """Converts labels file to S3 metadata dict."""
  labels_pair_list = metadata_util.get_label_pairs_from_file(file_path)
  s3_tag_set_list = []
  for key, value in labels_pair_list:
    s3_tag_set_list.append({'Key': key, 'Value': value})

  return {'TagSet': s3_tag_set_list}


def process_lifecycle(file_path):
  """Converts lifecycle file to S3 metadata dict."""
  # Expect lifecycle file to already be in correct format for S3.
  # { "Rules": [...] }
  # https://boto3.amazonaws.com/v1/documentation/api/latest/reference
  # /services/s3.html#S3.Client.put_bucket_lifecycle_configuration
  return metadata_util.cached_read_json_file(file_path)


def process_versioning(versioning):
  """Converts versioning bool to S3 metadata dict."""
  versioning_string = 'Enabled' if versioning else 'Suspended'
  return {'Status': versioning_string}


def process_website(web_error_page, web_main_page_suffix):
  """Converts website strings to S3 metadata dict."""
  metadata_dict = {}
  if web_error_page:
    metadata_dict['ErrorDocument'] = {'Key': web_error_page}
  if web_main_page_suffix:
    metadata_dict['IndexDocument'] = {'Suffix': web_main_page_suffix}
  return metadata_dict
