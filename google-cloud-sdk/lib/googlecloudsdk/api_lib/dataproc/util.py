# Copyright 2015 Google Inc. All Rights Reserved.
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

"""Common utilities for the gcloud dataproc tool."""

import time
import uuid

from apitools.base.py import encoding
from apitools.base.py import exceptions as apitools_exceptions

from googlecloudsdk.api_lib.dataproc import exceptions
from googlecloudsdk.calliope import arg_parsers
from googlecloudsdk.core import log
from googlecloudsdk.core.console import progress_tracker


def FormatRpcError(error):
  """Returns a printable representation of a failed Google API's status.proto.

  Args:
    error: the failed Status to print.

  Returns:
    A ready-to-print string representation of the error.
  """
  log.debug('Error:\n' + encoding.MessageToJson(error))
  formatted_error = error.message
  # Only display details if the log level is INFO or finer.
  if error.details and log.GetVerbosity() <= log.info:
    formatted_error += (
        '\nDetails:\n' + encoding.MessageToJson(error.details))
  return formatted_error


def WaitForResourceDeletion(
    request_method,
    resource_ref,
    message,
    timeout_s=60,
    poll_period_s=5):
  """Poll Dataproc resource until it no longer exists."""
  with progress_tracker.ProgressTracker(message, autotick=True):
    start_time = time.time()
    while timeout_s > (time.time() - start_time):
      try:
        request_method(resource_ref)
      except apitools_exceptions.HttpError as error:
        if error.status_code == 404:
          # Object deleted
          return
        log.debug('Get request for [{0}] failed:\n{1}', resource_ref, error)
        # Keep trying until we timeout in case error is transient.
      time.sleep(poll_period_s)
  raise exceptions.OperationTimeoutError(
      'Deleting resource [{0}] timed out.'.format(resource_ref))


def GetJobId(job_id=None):
  if job_id:
    return job_id
  return str(uuid.uuid4())


class Bunch(object):
  """Class that converts a dictionary to javascript like object.

  For example:
      Bunch({'a': {'b': {'c': 0}}}).a.b.c == 0
  """

  def __init__(self, dictionary):
    for key, value in dictionary.iteritems():
      if isinstance(value, dict):
        value = Bunch(value)
      self.__dict__[key] = value


def AddJvmDriverFlags(parser):
  parser.add_argument(
      '--jar',
      dest='main_jar',
      help='The HCFS URI of jar file containing the driver jar.')
  parser.add_argument(
      '--class',
      dest='main_class',
      help=('The class containing the main method of the driver. Must be in a'
            ' provided jar or jar that is already on the classpath'))


def AddTimeoutFlag(parser, default='10m'):
  """Add hidden client side timeout flag to parser."""
  # This may be made visible or passed to the server in future.
  parser.add_argument(
      '--timeout',
      type=arg_parsers.Duration(),
      default=default,
      hidden=True)
