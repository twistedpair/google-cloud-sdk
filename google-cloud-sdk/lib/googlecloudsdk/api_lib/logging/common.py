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

from googlecloudsdk.api_lib.logging import util
from googlecloudsdk.core import apis
from googlecloudsdk.core import properties
from googlecloudsdk.third_party.apitools.base.py import list_pager


def FetchLogs(log_filter=None, log_ids=None, order_by='DESC', limit=None):
  """Fetches log entries.

  This method uses Cloud Logging V2 api.
  https://cloud.google.com/logging/docs/api/introduction_v2

  Entries are sorted on the timestamp field, and afterwards filter is applied.
  If limit is passed, returns only up to that many matching entries.

  It is recommended to provide a filter with resource.type, and log_ids.

  Args:
    log_filter: filter expression used in the request.
    log_ids: if present, contructs full log names and passes it in filter.
    order_by: the sort order, either DESC or ASC.
    limit: how many entries to return.

  Returns:
    A generator that returns matching log entries.
    Callers are responsible for handling any http exceptions.
  """
  client = apis.GetClientInstance('logging', 'v2beta1')
  messages = apis.GetMessagesModule('logging', 'v2beta1')
  project = properties.VALUES.core.project.Get(required=True)

  if order_by.upper() == 'DESC':
    order_by = 'timestamp desc'
  else:
    order_by = 'timestamp asc'

  if log_ids is not None:
    log_names = ['"%s"' %  util.CreateLogResourceName(project, log_id)
                 for log_id in log_ids]
    log_names = ' OR '.join(log_names)
    # TODO(b/27930464): Always use parentheses when resolved
    if len(log_ids) > 1:
      log_names = '(%s)' % log_names
    if log_filter:
      log_filter = 'logName=%s AND (%s)' % (log_names, log_filter)
    else:
      log_filter = 'logName=%s' % log_names

  request = messages.ListLogEntriesRequest(
      projectIds=[project], filter=log_filter, orderBy=order_by)

  # The backend has an upper limit of 1000 for page_size.
  # However, there is no need to retrieve more entries if limit is specified.
  page_size = min(limit, 1000) or 1000

  return list_pager.YieldFromList(
      client.entries, request, field='entries', limit=limit,
      batch_size=page_size, batch_size_attribute='pageSize')

