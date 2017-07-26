# Copyright 2014 Google Inc. All Rights Reserved.
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

"""Helper methods for record-set transactions."""

import os
from dns import rdatatype
from googlecloudsdk.api_lib.dns import import_util
from googlecloudsdk.api_lib.dns import util
from googlecloudsdk.api_lib.util import apis
from googlecloudsdk.calliope import exceptions
from googlecloudsdk.core import exceptions as core_exceptions
from googlecloudsdk.core.resource import resource_printer
import yaml


DEFAULT_PATH = 'transaction.yaml'


class CorruptedTransactionFileError(core_exceptions.Error):

  def __init__(self):
    super(CorruptedTransactionFileError, self).__init__(
        'Corrupted transaction file.\n\n'
        'Please abort and start a new transaction.')


def WriteToYamlFile(yaml_file, change):
  """Writes the given change in yaml format to the given file.

  Args:
    yaml_file: file, File into which the change should be written.
    change: Change, Change to be written out.
  """
  resource_printer.Print([change], print_format='yaml', out=yaml_file)


def _RecordSetsFromDictionaries(messages, record_set_dictionaries):
  """Converts list of record-set dictionaries into list of ResourceRecordSets.

  Args:
    messages: Messages object for the API with Record Sets to be created.
    record_set_dictionaries: [{str:str}], list of record-sets as dictionaries.

  Returns:
    list of ResourceRecordSets equivalent to given list of yaml record-sets
  """
  record_sets = []
  for record_set_dict in record_set_dictionaries:
    record_set = messages.ResourceRecordSet()
    # Need to assign kind to default value for useful equals comparisons.
    record_set.kind = record_set.kind
    record_set.name = record_set_dict['name']
    record_set.ttl = record_set_dict['ttl']
    record_set.type = record_set_dict['type']
    record_set.rrdatas = record_set_dict['rrdatas']
    record_sets.append(record_set)
  return record_sets


def ChangeFromYamlFile(yaml_file, api_version='v1'):
  """Returns the change contained in the given yaml file.

  Args:
    yaml_file: file, A yaml file with change.
    api_version: [str], the api version to use for creating the change object.

  Returns:
    Change, the change contained in the given yaml file.

  Raises:
    CorruptedTransactionFileError: if the record_set_dictionaries are invalid
  """
  messages = apis.GetMessagesModule('dns', api_version)
  try:
    change_dict = yaml.safe_load(yaml_file) or {}
  except yaml.error.YAMLError:
    raise CorruptedTransactionFileError()
  if (change_dict.get('additions') is None or
      change_dict.get('deletions') is None):
    raise CorruptedTransactionFileError()
  change = messages.Change()
  change.additions = _RecordSetsFromDictionaries(
      messages, change_dict['additions'])
  change.deletions = _RecordSetsFromDictionaries(
      messages, change_dict['deletions'])
  return change


def CreateRecordSetFromArgs(args, api_version='v1'):
  """Creates and returns a record-set from the given args.

  Args:
    args: The arguments to use to create the record-set.
    api_version: [str], the api version to use for creating the RecordSet.

  Raises:
    ToolException: If given record-set type is not supported

  Returns:
    ResourceRecordSet, the record-set created from the given args.
  """
  messages = apis.GetMessagesModule('dns', api_version)
  rd_type = rdatatype.from_text(args.type)
  if import_util.GetRdataTranslation(rd_type) is None:
    raise exceptions.ToolException(
        'unsupported record-set type [{0}]'.format(args.type))

  record_set = messages.ResourceRecordSet()
  # Need to assign kind to default value for useful equals comparisons.
  record_set.kind = record_set.kind
  record_set.name = util.AppendTrailingDot(args.name)
  record_set.ttl = args.ttl
  record_set.type = args.type
  record_set.rrdatas = args.data
  if rd_type is rdatatype.TXT or rd_type is rdatatype.SPF:
    record_set.rrdatas = [import_util.QuotedText(datum) for datum in args.data]
  return record_set


class TransactionFile(object):
  """Context for reading/writing from/to a transaction file."""

  def __init__(self, trans_file_path, mode='r'):
    if not os.path.isfile(trans_file_path):
      raise exceptions.ToolException(
          'transaction not found at [{0}]'.format(trans_file_path))

    self.__trans_file_path = trans_file_path

    try:
      self.__trans_file = open(trans_file_path, mode)
    except IOError as exp:
      msg = 'unable to open transaction [{0}] because [{1}]'
      msg = msg.format(trans_file_path, exp)
      raise exceptions.ToolException(msg)

  def __enter__(self):
    return self.__trans_file

  def __exit__(self, typ, value, traceback):
    self.__trans_file.close()

    if typ is IOError or typ is yaml.YAMLError:
      msg = 'unable to read/write transaction [{0}] because [{1}]'
      msg = msg.format(self.__trans_file_path, value)
      raise exceptions.ToolException(msg)
