# -*- coding: utf-8 -*- #
# Copyright 2019 Google LLC. All Rights Reserved.
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
"""Provides common methods for the Events command surface."""

from __future__ import absolute_import
from __future__ import division
from __future__ import print_function
from __future__ import unicode_literals

from googlecloudsdk.command_lib.events import exceptions


def EventTypeFromTypeString(source_crds, type_string):
  """Returns the matching event type object given a list of source crds."""
  for crd in source_crds:
    for event_type in crd.event_types:
      if type_string == event_type.type:
        return event_type
  raise exceptions.EventTypeNotFound(
      'Unknown event type: {}.'.format(type_string))
