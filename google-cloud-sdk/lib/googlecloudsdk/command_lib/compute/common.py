# -*- coding: utf-8 -*- #
# Copyright 2025 Google LLC. All Rights Reserved.
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
"""Helpers for the compute related commands."""

from googlecloudsdk.calliope import arg_parsers


def ArgList(min_length=0, max_length=None):
  """Returns an ArgList type for health sources."""
  min_length = int(min_length)
  if max_length is not None:
    max_length = int(max_length)
  return arg_parsers.ArgList(min_length=min_length, max_length=max_length)
