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

"""A library that contains common logging commands."""

from apitools.base.py import list_pager

from googlecloudsdk.api_lib.logging import util
from googlecloudsdk.calliope import exceptions
from googlecloudsdk.core import apis
from googlecloudsdk.core import properties


def FetchLogs(log_filter=None,
              log_ids=None,
              order_by='DESC',
              limit=None,
              parent=None):
  """Fetches log entries.

  This method uses Cloud Logging V2 api.
  https://cloud.google.com/logging/docs/api/introduction_v2

  Entries are sorted on the timestamp field, and afterwards filter is applied.
  If limit is passed, returns only up to that many matching entries.

  It is recommended to provide a filter with resource.type, and log_ids.

  If neither log_filter nor log_ids are passed, no filtering is done.

  Args:
    log_filter: filter expression used in the request.
    log_ids: if present, contructs full log names based on parent and filters
      only those logs in addition to filtering with log_filter.
    order_by: the sort order, either DESC or ASC.
    limit: how many entries to return.
    parent: the name of the log's parent resource, e.g. "projects/foo" or
      "organizations/123". Defaults to the current project.

  Returns:
    A generator that returns matching log entries.
    Callers are responsible for handling any http exceptions.
  """
  if parent:
    if not ('projects/' in parent or 'organizations/' in parent):
      raise exceptions.InvalidArgumentException(
          'parent', 'Unknown parent type in parent %s' % parent)
  else:
    parent = 'projects/%s' % properties.VALUES.core.project.Get(required=True)
  # The backend has an upper limit of 1000 for page_size.
  # However, there is no need to retrieve more entries if limit is specified.
  page_size = min(limit or 1000, 1000)
  id_filter = _LogFilterForIds(log_ids, parent)
  if id_filter and log_filter:
    combined_filter = '%s AND (%s)' % (id_filter, log_filter)
  else:
    combined_filter = id_filter or log_filter
  if order_by.upper() == 'DESC':
    order_by = 'timestamp desc'
  else:
    order_by = 'timestamp asc'

  client = apis.GetClientInstance('logging', 'v2beta1')
  messages = apis.GetMessagesModule('logging', 'v2beta1')
  request = messages.ListLogEntriesRequest(resourceNames=[parent],
                                           filter=combined_filter,
                                           orderBy=order_by)
  if 'projects/' in parent:
    request.projectIds = [parent[len('projects/'):]]
  return list_pager.YieldFromList(
      client.entries, request, field='entries', limit=limit,
      batch_size=page_size, batch_size_attribute='pageSize')


def _LogFilterForIds(log_ids, parent):
  """Constructs a log filter expression from the log_ids and parent name."""
  if not log_ids:
    return None
  log_names = ['"%s"' % util.CreateLogResourceName(parent, log_id)
               for log_id in log_ids]
  log_names = ' OR '.join(log_names)
  # TODO(b/27930464): Always use parentheses when resolved
  if len(log_ids) > 1:
    log_names = '(%s)' % log_names
  return 'logName=%s' % log_names
