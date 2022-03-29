# -*- coding: utf-8 -*- #
# Copyright 2022 Google LLC. All Rights Reserved.
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
"""Provide Client and Message Instances to Overwatch."""
from __future__ import absolute_import
from __future__ import division
from __future__ import unicode_literals

from googlecloudsdk.api_lib.util import apis


# TODO(b/225094051) Create an SLZ client using discovery tools.
def get_overwatch_client(no_http=False):
  return apis.GetClientInstance('securedlandingzones', 'v1', no_http=no_http)


# Get the slz-overwatch resquest/response messages
def get_overwatch_message():
  client = get_overwatch_client()
  return client.MESSAGE_MODULE


# Get the service object from the client.
def get_overwatch_service():
  client = get_overwatch_client()
  return client.overwatch
