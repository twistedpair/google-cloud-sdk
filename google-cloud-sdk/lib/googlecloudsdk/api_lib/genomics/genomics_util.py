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

"""Common helper methods for Genomics commands."""

import json
import sys
import tempfile

from apitools.base.protorpclite.messages import DecodeError
from apitools.base.py import encoding
from apitools.base.py import exceptions as apitools_exceptions
from apitools.base.py import extra_types
from apitools.base.py import transfer

from googlecloudsdk.api_lib.genomics import exceptions as genomics_exceptions
from googlecloudsdk.calliope import exceptions as calliope_exceptions
from googlecloudsdk.core import apis as core_apis
from googlecloudsdk.core import log
from googlecloudsdk.core import properties
from googlecloudsdk.core.resource import resource_printer
from googlecloudsdk.core.util import files

import yaml

GCS_PREFIX = 'gs://'


def InfoValuesToAPI(values):
  """Converts a list of strings to the API JsonValue equivalent.

  Args:
    values: the string values to be converted
  Returns:
    An equivalent list of JsonValue strings
  """
  return [extra_types.JsonValue(string_value=v) for v in values]


def InfoValuesFromAPI(values):
  """Converts a list of strings to an API JsonValue equivalent.

  Args:
    values: the list of JsonValue strings to be converted
  Returns:
    An equivalent list of strings
  """
  return [v.string_value for v in values]


def PrettyPrint(resource, print_format='json'):
  """Prints the given resource."""
  resource_printer.Print(
      resources=[resource],
      print_format=print_format,
      out=log.out)


def GetError(error, verbose=False):
  """Returns a ready-to-print string representation from the http response.

  Args:
    error: A string representing the raw json of the Http error response.
    verbose: Whether or not to print verbose messages [default false]

  Returns:
    A ready-to-print string representation of the error.
  """
  data = json.loads(error.content)
  if verbose:
    PrettyPrint(data)
  code = data['error']['code']
  message = data['error']['message']
  return 'ResponseError: code={0}, message={1}'.format(code, message)


def GetErrorMessage(error):
  content_obj = json.loads(error.content)
  return content_obj.get('error', {}).get('message', '')


def GetGenomicsClient(version='v1'):
  return core_apis.GetClientInstance('genomics', version)


def GetGenomicsMessages(version='v1'):
  return core_apis.GetMessagesModule('genomics', version)


def ReraiseHttpExceptionPager(pager, rewrite_fn=None):
  """Wraps an HTTP paginator and converts errors to be gcloud-friendly.

  Args:
    pager: A list or generator of a response type.
    rewrite_fn: A function that rewrites the returned message.
        If 'None', no rewriting will occur.

  Yields:
    A generator which raises gcloud-friendly errors, if any.
  """

  try:
    for result in pager:
      yield result
  except apitools_exceptions.HttpError as error:
    msg = GetErrorMessage(error)
    if rewrite_fn:
      msg = rewrite_fn(msg)
    unused_type, unused_value, traceback = sys.exc_info()
    raise calliope_exceptions.HttpException, msg, traceback


def ReraiseHttpException(foo):
  def Func(*args, **kwargs):
    try:
      return foo(*args, **kwargs)
    except apitools_exceptions.HttpError as error:
      msg = GetErrorMessage(error)
      unused_type, unused_value, traceback = sys.exc_info()
      raise calliope_exceptions.HttpException, msg, traceback
  return Func


@ReraiseHttpException
def GetDataset(dataset_id):
  apitools_client = GetGenomicsClient()
  genomics_messages = GetGenomicsMessages()

  request = genomics_messages.GenomicsDatasetsGetRequest(
      datasetId=str(dataset_id),
  )

  return apitools_client.datasets.Get(request)


@ReraiseHttpException
def GetCallSet(call_set_id):
  apitools_client = GetGenomicsClient()
  genomics_messages = GetGenomicsMessages()

  request = genomics_messages.GenomicsCallsetsGetRequest(
      callSetId=str(call_set_id),
  )

  return apitools_client.callsets.Get(request)


def GetProjectId():
  return properties.VALUES.core.project.Get(required=True)


def GetFileAsMessage(path, message, client):
  """Reads a YAML or JSON object of type message from path (local or GCS).

  Args:
    path: A local or GCS path to an object specification in YAML or JSON format.
    message: The message type to be parsed from the file.
    client: The storage_v1 client to use.

  Returns:
    Object of type message, if successful.
  Raises:
    files.Error, genomics_exceptions.GenomicsInputFileError
  """
  if path.startswith(GCS_PREFIX):
    # Download remote file to a local temp file
    tf = tempfile.NamedTemporaryFile(delete=False)
    tf.close()

    bucket, obj = _SplitBucketAndObject(path)
    storage_messages = core_apis.GetMessagesModule('storage', 'v1')
    get_request = storage_messages.StorageObjectsGetRequest(
        bucket=bucket, object=obj)
    try:
      download = transfer.Download.FromFile(tf.name, overwrite=True)
      client.objects.Get(get_request, download=download)
      del download  # Explicitly close the stream so the results are there
    except apitools_exceptions.HttpError as e:
      raise genomics_exceptions.GenomicsInputFileError(
          'Unable to read remote file [{0}] due to [{1}]'.format(path, str(e)))
    path = tf.name

  # Read the file.
  in_text = files.GetFileContents(path)
  if not in_text:
    raise genomics_exceptions.GenomicsInputFileError(
        'Empty file [{0}]'.format(path))

  # Parse it, first trying YAML then JSON.
  try:
    result = encoding.PyValueToMessage(message, yaml.load(in_text))
  except (ValueError, AttributeError, yaml.YAMLError) as e:
    try:
      result = encoding.JsonToMessage(message, in_text)
    except (ValueError, DecodeError) as e:
      # ValueError is raised when JSON is badly formatted
      # DecodeError is raised when a tag is badly formatted (not Base64)
      raise genomics_exceptions.GenomicsInputFileError(
          'Pipeline file [{0}] is not properly formatted YAML or JSON '
          'due to [{1}]'.format(path, str(e)))
  return result


def ArgDictToAdditionalPropertiesList(argdict, message):
  result = []
  if argdict is None:
    return result
  # For consistent results (especially for deterministic testing), make
  # the return list ordered by key
  for k, v in sorted(argdict.iteritems()):
    result.append(message(key=k, value=v))
  return result


def _SplitBucketAndObject(gcs_path):
  """Split a GCS path into bucket & object tokens, or raise BadFileException."""
  tokens = gcs_path[len(GCS_PREFIX):].strip('/').split('/', 1)
  if len(tokens) != 2:
    raise calliope_exceptions.BadFileException(
        '[{0}] is not a valid Google Cloud Storage path'.format(gcs_path))
  return tokens


def GetQueryFields(referenced_fields, prefix):
  """Returns the comma separated list of field names referenced by the command.

  Args:
    referenced_fields: A list of field names referenced by the format and filter
      expressions.
    prefix: The referenced field name resource prefix.

  Returns:
    The comma separated list of field names referenced by the command.
  """
  if not referenced_fields:
    return None
  return ','.join(['nextPageToken'] +
                  ['.'.join([prefix, field]) for field in referenced_fields])
