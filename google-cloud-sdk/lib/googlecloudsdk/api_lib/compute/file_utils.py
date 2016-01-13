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
"""Convenience functions for dealing with files."""

from googlecloudsdk.calliope import exceptions


def ReadFile(file_path, data_name):
  try:
    return open(file_path).read()
  except IOError as e:
    raise exceptions.ToolException(
        'Could not read {0} from file [{1}]: {2}'.format(
            data_name, file_path, e.strerror))
