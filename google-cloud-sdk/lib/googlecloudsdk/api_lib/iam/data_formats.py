# Copyright 2015 Google Inc. All Rights Reserved.
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
"""Custom implementation of COLLECTION_COLUMNS, since we can't use resources."""

from googlecloudsdk.api_lib.iam import utils


def Select(column, transform=None):

  def SelectColFunc(obj):
    value = getattr(obj, column)
    if transform:
      value = transform(value)
    return value

  return SelectColFunc


SERVICE_ACCOUNT_COLUMNS = (('NAME', Select('displayName')),
                           ('EMAIL', Select('email')),
                           ('DESCRIPTION', Select('description')),)

SERVICE_ACCOUNT_KEY_COLUMNS = (
    ('KEY_ID', Select('name', utils.GetKeyIdFromResourceName)),
    ('CREATED_AT', Select('validAfterTime')),
    ('EXPIRES_AT', Select('validBeforeTime')),)
