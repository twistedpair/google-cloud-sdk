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
"""Utils for manipulating Transfer resource names."""

from __future__ import absolute_import
from __future__ import division
from __future__ import unicode_literals


def _add_single_transfer_prefix(prefix, resource_string):
  return '{}/{}'.format(prefix, resource_string)


def _add_transfer_prefix(prefix, resource_string_or_list):
  if isinstance(resource_string_or_list, str):
    return _add_single_transfer_prefix(prefix, resource_string_or_list)
  elif isinstance(resource_string_or_list, list):
    return [
        _add_single_transfer_prefix(prefix, resource_string)
        for resource_string in resource_string_or_list
    ]
  raise ValueError('Argument must be string or list of strings.')


def add_job_prefix(job_name_string_or_list):
  return _add_transfer_prefix('transferJobs', job_name_string_or_list)


def add_operation_prefix(job_operation_string_or_list):
  return _add_transfer_prefix('transferOperations',
                              job_operation_string_or_list)
