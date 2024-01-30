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
"""Helpers for exceptions raised by Audit Manager."""

from googlecloudsdk.calliope import exceptions

ERROR_REASON_NO_ORGANISATION_FOUND = 'ERROR_CODE_NO_ORGANISATION_FOUND_FOR_RESOURCE'
ERROR_REASON_NOT_ENROLLED = 'ERROR_CODE_RESOURCE_NOT_ENROLLED'


def ExtractErrorDetails(e):
  api_error = exceptions.HttpException(e)
  details = api_error.payload.details
  details = [x for x in details if 'reason' in x]

  if not details:
    return None

  return details[0]
