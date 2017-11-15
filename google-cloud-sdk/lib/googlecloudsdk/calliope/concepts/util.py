# Copyright 2017 Google Inc. All Rights Reserved.
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
"""Utilities for resource args."""


PREFIX = '--'


def NormalizeFormat(arg_name):
  """Converts arg name to lower snake case, no '--' prefix."""
  if arg_name.startswith(PREFIX):
    return arg_name[len(PREFIX):].lower().replace('-', '_')
  return arg_name.lower()


def IsPositional(arg_name):
  """Confirms if an arg name is for a positional or a flag."""
  return not arg_name.startswith(PREFIX)


def NamespaceFormat(arg_name):
  if IsPositional(arg_name):
    return arg_name
  return NormalizeFormat(arg_name)


def MetavarFormat(arg_name):
  """Gets arg name in upper snake case."""
  return arg_name.lstrip('-').replace('-', '_').upper()
