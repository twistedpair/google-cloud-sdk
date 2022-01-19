# -*- coding: utf-8 -*- #
# Copyright 2022 Google Inc. All Rights Reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
"""Provider-neutral tools for manipulating metadata."""

from __future__ import absolute_import
from __future__ import division
from __future__ import unicode_literals

import json

from googlecloudsdk.core.cache import function_result_cache
from googlecloudsdk.core.util import files


@function_result_cache.lru(maxsize=None)
def cached_read_json_file(file_path):
  """Convert JSON file to an in-memory dict."""
  with files.FileReader(file_path) as file_reader:
    return json.load(file_reader)


def get_label_pairs_from_file(file_path):
  """Convert JSON file to a list of label keys and values."""
  # Expected JSON file format: Dict<str: str>
  labels_dict = cached_read_json_file(file_path)
  # {'key1': 'val1', 'key2': 'val2', ...} -> [('key1', 'val1'), ...]
  return list(labels_dict.items())
