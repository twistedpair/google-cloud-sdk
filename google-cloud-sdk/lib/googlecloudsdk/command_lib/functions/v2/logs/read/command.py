# -*- coding: utf-8 -*- #
# Copyright 2021 Google LLC. All Rights Reserved.
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
"""This file provides the implementation of the `functions logs read` command."""

from __future__ import absolute_import
from __future__ import division
from __future__ import unicode_literals

import datetime
from apitools.base.py.exceptions import HttpForbiddenError
from apitools.base.py.exceptions import HttpNotFoundError
from googlecloudsdk.api_lib.functions.v2 import exceptions
from googlecloudsdk.api_lib.functions.v2 import util as api_util
from googlecloudsdk.api_lib.logging import common as logging_common
from googlecloudsdk.api_lib.logging import util as logging_util
from googlecloudsdk.command_lib.functions import flags
from googlecloudsdk.core import log
from googlecloudsdk.core import properties
import six

DEFAULT_TABLE_FORMAT = 'table(level,name,time_utc,log)'
EXECUTION_ID_NOT_SUPPORTED = (
    '`execution_id` is not supported in Cloud Functions v2.')


def _Run(args, release_track):
  """Display log entries produced by Google Cloud Functions."""
  if args.execution_id:
    raise exceptions.FunctionsError(EXECUTION_ID_NOT_SUPPORTED)

  region = properties.VALUES.functions.region.GetOrFail()
  log_filter = [
      'resource.type="cloud_run_revision"',
      'resource.labels.location="%s"' % region, 'logName:"run.googleapis.com"'
  ]

  if args.name:
    log_filter.append('resource.labels.service_name="%s"' % args.name)
  if args.min_log_level:
    log_filter.append('severity>=%s' % args.min_log_level.upper())

  log_filter.append('timestamp>="%s"' % logging_util.FormatTimestamp(
      args.start_time or
      datetime.datetime.utcnow() - datetime.timedelta(days=7)))

  if args.end_time:
    log_filter.append('timestamp<="%s"' %
                      logging_util.FormatTimestamp(args.end_time))

  log_filter = ' '.join(log_filter)

  entries = list(
      logging_common.FetchLogs(log_filter, order_by='DESC', limit=args.limit))

  if args.name and not entries:
    # Check if the function even exists in the given region.
    try:
      client = api_util.GetClientInstance(release_track=release_track)
      messages = api_util.GetMessagesModule(release_track=release_track)
      client.projects_locations_functions.Get(
          messages.CloudfunctionsProjectsLocationsFunctionsGetRequest(
              name='projects/%s/locations/%s/functions/%s' %
              (properties.VALUES.core.project.GetOrFail(), region,
               args.name)))
    except (HttpForbiddenError, HttpNotFoundError):
      # The function doesn't exist in the given region.
      log.warning(
          'There is no function named `%s` in region `%s`. Perhaps you '
          'meant to specify `--region` or update the `functions/region` '
          'configuration property?' % (args.name, region))

  for entry in entries:
    message = entry.textPayload
    if entry.jsonPayload:
      props = [
          prop.value
          for prop in entry.jsonPayload.additionalProperties
          if prop.key == 'message'
      ]
      if len(props) == 1 and hasattr(props[0], 'string_value'):
        message = props[0].string_value
    row = {'log': message}
    if entry.severity:
      severity = six.text_type(entry.severity)
      if severity in flags.SEVERITIES:
        # Use short form (first letter) for expected severities.
        row['level'] = severity[0]
      else:
        # Print full form of unexpected severities.
        row['level'] = severity
    if entry.resource and entry.resource.labels:
      for label in entry.resource.labels.additionalProperties:
        if label.key == 'service_name':
          row['name'] = label.value
    if entry.timestamp:
      row['time_utc'] = api_util.FormatTimestamp(entry.timestamp)
    yield row


def Run(args, release_track):
  if not args.IsSpecified('format'):
    args.format = DEFAULT_TABLE_FORMAT

  return _Run(args, release_track)
