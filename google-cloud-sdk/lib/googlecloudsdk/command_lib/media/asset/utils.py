# -*- coding: utf-8 -*- #
# Copyright 2021 Google LLC. All Rights Reserved.
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
"""Create hooks for Cloud Media Asset's asset type."""

from __future__ import absolute_import
from __future__ import division
from __future__ import unicode_literals

from apitools.base.py import encoding
from googlecloudsdk.core import exceptions

import six


def ValidateMediaAssetMessage(message):
  """Validate all parsed message from file are valid."""
  errors = encoding.UnrecognizedFieldIter(message)
  unrecognized_field_paths = []
  for edges_to_message, field_names in errors:
    message_field_path = '.'.join(six.text_type(e) for e in edges_to_message)
    for field_name in field_names:
      unrecognized_field_paths.append('{}.{}'.format(message_field_path,
                                                     field_name))
  if unrecognized_field_paths:
    error_msg_lines = [
        'Invalid schema, the following fields are unrecognized:'] + \
        unrecognized_field_paths
    raise exceptions.Error('\n'.join(error_msg_lines))
