# -*- coding: utf-8 -*- #
# Copyright 2025 Google LLC. All Rights Reserved.
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

"""Helper class for generating Cloud Logging URLs for Dataproc resources."""

from __future__ import absolute_import
from __future__ import division
from __future__ import unicode_literals

import re

from googlecloudsdk.core import properties
from six.moves.urllib import parse


def get_plain_batch_logging_url():
  """Returns the base URL for the Cloud Logging console.

  This is used when parsing batch resource failed.
  """
  logging_base = 'https://console.cloud.google.com/logs/query'
  batch_resource_filter = 'resource.type="cloud_dataproc_batch"'

  return '{}?{}'.format(
      logging_base,
      parse.urlencode({
          'query': batch_resource_filter,
      }),
  )


def get_batch_logging_url(batch):
  """Returns a Cloud Logging URL for the given batch.

  Args:
    batch: The batch to get the Cloud Logging URL for.

  Returns:
    A Cloud Logging URL for the given batch or a plain url without batch info.
  """

  match = re.match(
      r'projects/(?P<project_id>[^/]+)/locations/[^/]+/batches/(?P<batch_id>[^/]+)',
      batch.name,
  )
  if not match:
    return get_plain_batch_logging_url()
  project_id = match.group('project_id')
  batch_id = match.group('batch_id')
  logging_base = 'https://console.cloud.google.com/logs/query'
  batch_resource_filter = 'resource.type="cloud_dataproc_batch"'
  project_query = f'project={project_id}'

  batch_id_filter = f'resource.labels.batch_id="{batch_id}"'
  universe_domain = properties.VALUES.core.universe_domain.Get()
  driver_output_filter = f'log_name="projects/{project_id}/logs/dataproc.{universe_domain}%2Foutput"'

  return '{}?{}&{}'.format(
      logging_base,
      parse.urlencode({
          'query': (
              batch_resource_filter
              + '\n'
              + batch_id_filter
              + '\n'
              + driver_output_filter
          ),
      }),
      project_query,
  )


def get_plain_batches_list_url():
  """Returns the base URL for the Dataproc Batches console.

  This is used when parsing batch resource failed.
  """
  dataproc_batches_base = 'https://console.cloud.google.com/dataproc/batches'
  return dataproc_batches_base


def get_dataproc_batch_url(batch):
  """Returns a Dataproc Batch URL for the given batch."""
  match = re.match(
      r'projects/(?P<project_id>[^/]+)/locations/(?P<location>[^/]+)/batches/(?P<batch_id>[^/]+)',
      batch.name,
  )
  if not match:
    return get_plain_batches_list_url()
  project_id = match.group('project_id')
  batch_id = match.group('batch_id')
  location = match.group('location')
  dataproc_batch_url = f'https://console.cloud.google.com/dataproc/batches/{location}/{batch_id}/summary'
  project_query = f'project={project_id}'
  return dataproc_batch_url + '?' + project_query
