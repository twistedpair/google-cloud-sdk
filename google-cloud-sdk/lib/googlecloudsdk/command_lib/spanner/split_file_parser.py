# -*- coding: utf-8 -*- #
# Copyright 2024 Google LLC. All Rights Reserved.
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
"""Provides split file preprocessing for adding splits to a database."""

from __future__ import absolute_import
from __future__ import division
from __future__ import unicode_literals

import csv
import io
import re

from apitools.base.py import extra_types
from googlecloudsdk.api_lib.util import apis
from googlecloudsdk.calliope import exceptions as c_exceptions
from googlecloudsdk.core.util import files


class SplitFileParser:
  r"""Parses a split file into a list of split points.

  The split file is expected to be in the format of:
  <ObjectType>[space]<ObjectName>[space](<Split Value>)
  <ObjectType>[space]<ObjectName>[space](<Split Value>)
  ...
  where ObjectType can be TABLE or INDEX.
  Each split point must be in a new line.
  Split value is expected to be a comma separated list of key parts.
    Split values should be surrounded by parenthesis like ()
    String values should be supplied in single quotes:'splitKeyPart'
    Boolean values should be one of: true/false
    INT64 and NUMERIC spanner datatype values should be supplied within
    single quotes values like string format: '123',
    '999999999999999999999999999.99'
    Other number values should be supplied without quotes: 1.287
    Timestamp values should be provided in the following format in single quote
    values: '2020-06-18T17:24:53Z'
    If the split value needs to have a comma, then that should be escaped by
    backslash.

    Examples:
    TABLE Singers ('c32ca57a-786c-2268-09d4-95182a9930be')
    INDEX Order (4.2)
    TABLE TableD  (0,'7ef9db22-d0e5-6041-8937-4bc6a7ef9db2')
    INDEX IndexXYZ ('8762203435012030000',NULL,NULL)
    INDEX IndexABC  (0, '2020-06-18T17:24:53Z') TableKey (123,'ab\,c')
    -- note that the above split value has a delimieter (comma) in it,
        hence escaped by a backslash.
  """

  def __init__(self, splits_file, split_expiration_date):
    self.splits_file = splits_file
    self.split_expiration_date = split_expiration_date
    self.split_line_pattern = re.compile(r'(\S+)\s+(\S+)\s+(.+)')
    self.incorrect_split_with_table_key_pattern = re.compile(
        r'\((.*?)\) TABLE (\S+)\s+\((.*?)\)$'
    )
    self.incorrect_split_with_index_key_pattern = re.compile(
        r'\((.*?)\) INDEX (\S+)\s+\((.*?)\)$'
    )
    self.index_full_key_pattern = re.compile(r'\((.*?)\) TableKey \((.*?)\)$')
    self.single_key_pattern = re.compile(r'\((.*?)\)$')

  def Process(self):
    """Gets the split points from the input file."""
    msgs = apis.GetMessagesModule('spanner', 'v1')
    split_points_list = []
    with files.FileReader(self.splits_file) as file:
      for single_split_string in file.read().splitlines():
        single_split = self.ParseSplitPointString(single_split_string)
        if (
            not single_split
            or not single_split['SplitValue']
            or not single_split['ObjectName']
            or not single_split['ObjectType']
            or single_split['ObjectType'].upper() not in ['TABLE', 'INDEX']
        ):
          raise c_exceptions.InvalidArgumentException(
              '--splits-file',
              'Invalid split point string: {}. Each split point must be in the'
              ' format of <ObjectType> <ObjectName> (<Split Value>) where'
              ' ObjectType can be TABLE or INDEX'.format(single_split_string),
          )
        split = msgs.SplitPoints()
        if single_split['ObjectType'].upper() == 'TABLE':
          split.table = single_split['ObjectName']
        elif single_split['ObjectType'].upper() == 'INDEX':
          split.index = single_split['ObjectName']

        if single_split['SplitValue']:
          split.keys = self.ParseSplitValue(single_split['SplitValue'])

        if self.split_expiration_date:
          split.expireTime = self.split_expiration_date
        split_points_list.append(split)
    return split_points_list

  def ParseSplitPointString(self, input_string):
    """Parses a string in the format "<ObjectType> <ObjectName> (<Split Value>)".

    and returns a dictionary with the extracted information.

    Args:
      input_string: The string to parse.

    Returns:
      A dictionary with keys "ObjectType", "ObjectName", and "SplitValue",
      or None if the input string is not in the expected format.
    """
    # Matches three groups of non-whitespace characters separated by spaces
    match = self.split_line_pattern.match(input_string)
    if match:
      return {
          'ObjectType': match.group(1),
          'ObjectName': match.group(2),
          'SplitValue': match.group(3)
      }
    else:
      raise c_exceptions.InvalidArgumentException(
          '--splits-file',
          'Invalid split point string: {}. Each split point must be in the'
          ' format of <ObjectType> <ObjectName> (<Split Value>) where'
          ' ObjectType can be TABLE or INDEX'.format(input_string),
      )

  def ParseSplitValue(self, input_string):
    """Parses a string in the format "(CommaSeparatedKeyParts) TableKey (CommaSeparatedKeyParts)".

    and returns a dictionary with the extracted information.

    Args:
      input_string: The string to parse.

    Returns:
      A split point key.
    """
    msgs = apis.GetMessagesModule('spanner', 'v1')
    keys_all = []
    input_string = input_string.strip()
    # Catches the case when single line contains multiple split points.
    if self.incorrect_split_with_table_key_pattern.match(
        input_string
    ) or self.incorrect_split_with_index_key_pattern.match(input_string):
      raise c_exceptions.InvalidArgumentException(
          '--splits-file',
          'Invalid split point string: {}. Each line must contain a single'
          ' split point for a table or index.'.format(input_string),
      )

    all_keys_strings = []
    match = self.index_full_key_pattern.match(input_string)
    if match:
      # Index split with full key
      all_keys_strings.append(match.group(1))
      all_keys_strings.append(match.group(2))
    else:
      match = self.single_key_pattern.match(input_string)
      if match:
        all_keys_strings.append(match.group(1))
      else:
        raise c_exceptions.InvalidArgumentException(
            '--splits-file',
            'The split value must be surrounded by parenthesis.',
        )
    for input_string_per_key in all_keys_strings:
      input_string_per_key = input_string_per_key.strip()
      input_string_per_key = input_string_per_key.strip('()')
      single_key = msgs.Key()
      for split_token in self.TokenizeWithCsv(input_string_per_key):
        key_parts = extra_types.JsonValue()
        if split_token == 'NULL':
          key_parts.is_null = True
        else:
          if (
              split_token == 'true'
              or split_token == 'false'
              or split_token == 'TRUE'
              or split_token == 'FALSE'
          ):
            key_parts.boolean_value = bool(split_token.lower())
          else:
            if split_token.find('\'') == -1:
              key_parts.double_value = float(split_token)
            else:
              key_parts.string_value = split_token.strip('\'')
        single_key.keyParts.append(key_parts)
      keys_all.append(single_key)
    return keys_all

  def TokenizeWithCsv(self, text):
    """Tokenizes text using commas as delimiters, ignoring commas within single quotes.

    Args:
      text: The text to tokenize.

    Returns:
      A list of tokens.
    """
    reader = csv.reader(
        io.StringIO(text),
        quotechar="'",
        skipinitialspace=True, quoting=csv.QUOTE_NONE,
        escapechar='\\'
    )
    return next(reader)


def ParseSplitPoints(args):
  """Gets the split points from the input file."""
  return SplitFileParser(args.splits_file, args.split_expiration_date).Process()

