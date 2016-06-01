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

"""A library for diagnosing common network and proxy problems."""

import httplib
import socket
import ssl

from googlecloudsdk.core.credentials import http
import httplib2


class Failure(object):
  """Result of a failed network diagnostic check."""

  def __init__(self, message=None, exception=None, response=None):
    self.message = message
    self.exception = exception
    self.response = response

  def __eq__(self, other):
    if dir(self) != dir(other):
      return False
    if self.message != other.message:
      return False
    if not isinstance(self.exception, type(other.exception)):
      return False
    if self.response != other.response:
      return False
    return True


def CheckReachability(urls, http_client=None):
  """Check whether the hosts of given urls are reachable.

  Args:
    urls: iterable(str), The list of urls to check connection to.
    http_client: httplib2.Http, an object used by gcloud to make http and https
      connections. Defaults to an non-authenticated Http object from the
      googlecloudsdk.core.credentials.http module.

  Returns:
    list(Failure): Reasons for why any urls were unreachable. The list will be
    empty if all urls are reachable.
  """
  if not http_client:
    http_client = http.Http(auth=False)

  failures = []
  for url in urls:
    try:
      response, _ = http_client.request(url, method='HEAD')
    # TODO(user): Investigate other possible exceptions that might be thrown.
    except (httplib.HTTPException, socket.error, ssl.SSLError,
            httplib2.HttpLib2Error) as err:
      message = 'Cannot reach {0} ({1})'.format(url, type(err).__name__)
      failures.append(Failure(message=message, exception=err))
    else:
      if response.status != httplib.OK:
        message = 'Cannot reach {0} ([{1}] {2})'.format(url, response.status,
                                                        response.reason)
        failures.append(Failure(message=message, response=response))
  return failures
