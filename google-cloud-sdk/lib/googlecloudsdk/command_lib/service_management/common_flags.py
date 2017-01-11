# Copyright 2016 Google Inc. All Rights Reserved.
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

"""Common flags for the consumers subcommand group."""

from googlecloudsdk.api_lib.service_management import services_util
from googlecloudsdk.calliope import base
from googlecloudsdk.command_lib.service_management import completion_callbacks


def operation_flag(suffix='to act on'):
  return base.Argument(
      'operation',
      help='The name of the operation {0}.'.format(suffix))


def producer_service_flag(suffix='to act on'):
  return base.Argument(
      'service',
      completion_resource=services_util.SERVICES_COLLECTION,
      list_command_callback_fn=(completion_callbacks.
                                ProducerServiceFlagCompletionCallback),
      help='The name of the service {0}.'.format(suffix))


def consumer_service_flag(suffix='to act on'):
  return base.Argument(
      'service',
      completion_resource=services_util.SERVICES_COLLECTION,
      list_command_callback_fn=(completion_callbacks.
                                ConsumerServiceFlagCompletionCallback),
      help='The name of the service {0}.'.format(suffix))


def available_service_flag(suffix='to act on'):
  # NOTE: Because listing available services often forces the tab completion
  #       code to timeout, this flag will not enable tab completion.
  return base.Argument(
      'service',
      help='The name of the service {0}.'.format(suffix))


def key_flag(suffix='to act on'):
  return base.Argument(
      '--key',
      help='The identifier of the key {0}.'.format(suffix))
