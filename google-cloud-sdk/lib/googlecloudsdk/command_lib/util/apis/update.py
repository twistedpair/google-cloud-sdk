# -*- coding: utf-8 -*- #
# Copyright 2018 Google Inc. All Rights Reserved.
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
"""Utilities for handling YAML schemas for gcloud update commands."""

from __future__ import absolute_import
from __future__ import division
from __future__ import unicode_literals

from googlecloudsdk.core import exceptions

# TODO(b/111069150): Add a single test for this file.


class NoFieldsSpecifiedError(exceptions.Error):
  """Raises when no arguments specified for update commands."""


def GetMaskString(args, spec):
  """Gets the fieldMask that is required for update api calls.

  Args:
    args: The argparse parser.
    spec: The CommandData class.

  Returns:
    A String, represents a mask specifying which fields in the resource should
    be updated.

  Raises:
    NoFieldsSpecifiedError: this error would happen when no args are specified.
  """
  params_in_spec = spec.arguments.params
  specified_args_list = set(args.GetSpecifiedArgs().keys())
  if not specified_args_list:
    raise NoFieldsSpecifiedError(
        'Must specify at least one valid parameter to update.')

  field_list = []
  for param in params_in_spec:
    if ('--' + param.arg_name in specified_args_list or
        param.arg_name in specified_args_list):
      # Field name would be the string after the last dot.
      # Example: instance.displayName -> displayName
      api_field_name = param.api_field.split('.')[-1]
      field_list.append(api_field_name)
  field_list.sort()  # Sort the list for better testing purpose.
  return ','.join(field_list)
