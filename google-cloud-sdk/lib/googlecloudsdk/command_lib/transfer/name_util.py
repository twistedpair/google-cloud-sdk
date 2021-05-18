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


_JOBS_PREFIX = 'transferJobs/'
_OPERATIONS_PREFIX = 'transferOperations/'


def _add_single_transfer_prefix(prefix, resource_string):
  if resource_string.startswith(prefix):
    return resource_string
  return prefix + resource_string


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
  return _add_transfer_prefix(_JOBS_PREFIX, job_name_string_or_list)


def add_operation_prefix(job_operation_string_or_list):
  return _add_transfer_prefix(_OPERATIONS_PREFIX, job_operation_string_or_list)


def remove_job_prefix(operation_string):
  if operation_string.startswith(_JOBS_PREFIX):
    return operation_string[len(_JOBS_PREFIX):]
  return operation_string


def remove_operation_prefix(operation_string):
  if operation_string.startswith(_OPERATIONS_PREFIX):
    return operation_string[len(_OPERATIONS_PREFIX):]
  return operation_string
