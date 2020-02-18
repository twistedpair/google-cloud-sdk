# -*- coding: utf-8 -*- #
# Copyright 2017 Google LLC. All Rights Reserved.
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

from __future__ import absolute_import
from __future__ import division
from __future__ import unicode_literals

from googlecloudsdk.api_lib.services import services_util
from googlecloudsdk.calliope import base
from googlecloudsdk.calliope.concepts import concepts
from googlecloudsdk.command_lib.util import completers
from googlecloudsdk.command_lib.util.concepts import concept_parsers
from googlecloudsdk.command_lib.util.concepts import presentation_specs

_SERVICES_LEGACY_LIST_COMMAND = ('services list --format=disable '
                                 '--flatten=serviceName')
_SERVICES_LIST_COMMAND = ('beta services list --format=disable '
                          '--flatten=config.name')


class ConsumerServiceCompleter(completers.ListCommandCompleter):

  def __init__(self, **kwargs):
    super(ConsumerServiceCompleter, self).__init__(
        collection=services_util.SERVICES_COLLECTION,
        list_command=_SERVICES_LIST_COMMAND,
        flags=['enabled'],
        **kwargs)


class ConsumerServiceLegacyCompleter(completers.ListCommandCompleter):

  def __init__(self, **kwargs):
    super(ConsumerServiceLegacyCompleter, self).__init__(
        collection=services_util.SERVICES_COLLECTION,
        list_command=_SERVICES_LEGACY_LIST_COMMAND,
        flags=['enabled'],
        **kwargs)


def operation_flag(suffix='to act on'):
  return base.Argument(
      'operation', help='The name of the operation {0}.'.format(suffix))


def consumer_service_flag(suffix='to act on', flag_name='service'):
  return base.Argument(
      flag_name,
      nargs='*',
      completer=ConsumerServiceCompleter,
      help='The name of the service(s) {0}.'.format(suffix))


def single_consumer_service_flag(suffix='to act on', flag_name='service'):
  return base.Argument(
      flag_name,
      completer=ConsumerServiceCompleter,
      help='The name of the service {0}.'.format(suffix))


def available_service_flag(suffix='to act on', flag_name='service'):
  # NOTE: Because listing available services often forces the tab completion
  #       code to timeout, this flag will not enable tab completion.
  return base.Argument(
      flag_name,
      nargs='*',
      help='The name of the service(s) {0}.'.format(suffix))


def _create_key_resource_arg(help_txt):
  return presentation_specs.ResourcePresentationSpec(
      'key', _get_key_resource_spec(), help_txt, required=True)


def _get_key_resource_spec():
  """Return the resource specification for a key."""
  return concepts.ResourceSpec(
      'apikeys.projects.keys',
      resource_name='key',
      keysId=_key_attribute_config(),
      projectsId=concepts.DEFAULT_PROJECT_ATTRIBUTE_CONFIG)


def _key_attribute_config():
  return concepts.ResourceParameterAttributeConfig(
      name='key', help_text='Id of the key')


def key_flag(parser, suffix='to act on'):
  return concept_parsers.ConceptParser([
      _create_key_resource_arg(
          help_txt='The name of the key {0}.'.format(suffix))
  ]).AddToParser(parser)
