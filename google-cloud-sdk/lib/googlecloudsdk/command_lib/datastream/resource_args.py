# -*- coding: utf-8 -*- #
# Copyright 2020 Google LLC. All Rights Reserved.
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
"""Shared resource flags for Datastream commands."""

from __future__ import absolute_import
from __future__ import division
from __future__ import unicode_literals

from googlecloudsdk.calliope.concepts import concepts
from googlecloudsdk.command_lib.util.concepts import concept_parsers
from googlecloudsdk.command_lib.util.concepts import presentation_specs


def ConnectionProfileAttributeConfig(name='connection_profile'):
  return concepts.ResourceParameterAttributeConfig(
      name=name,
      help_text='The connection profile of the {resource}.',
      completion_request_params={'fieldMask': 'name'},
      completion_id_field='id')


def PrivateConnectionAttributeConfig(name='private_connection'):
  return concepts.ResourceParameterAttributeConfig(
      name=name,
      help_text='The private connection of the {resource}.',
      completion_request_params={'fieldMask': 'name'},
      completion_id_field='id')


def LocationAttributeConfig():
  return concepts.ResourceParameterAttributeConfig(
      name='location', help_text='The Cloud location for the {resource}.')


def GetLocationResourceSpec(resource_name='location'):
  return concepts.ResourceSpec(
      'datastream.projects.locations',
      resource_name=resource_name,
      locationsId=LocationAttributeConfig(),
      projectsId=concepts.DEFAULT_PROJECT_ATTRIBUTE_CONFIG,
      disable_auto_completers=False)


def GetConnectionProfileResourceSpec(resource_name='connection_profile'):
  return concepts.ResourceSpec(
      'datastream.projects.locations.connectionProfiles',
      resource_name=resource_name,
      connectionProfilesId=ConnectionProfileAttributeConfig(name=resource_name),
      locationsId=LocationAttributeConfig(),
      projectsId=concepts.DEFAULT_PROJECT_ATTRIBUTE_CONFIG,
      disable_auto_completers=False)


def GetPrivateConnectionResourceSpec(resource_name='private_connection'):
  return concepts.ResourceSpec(
      'datastream.projects.locations.privateConnections',
      resource_name=resource_name,
      privateConnectionsId=PrivateConnectionAttributeConfig(name=resource_name),
      locationsId=LocationAttributeConfig(),
      projectsId=concepts.DEFAULT_PROJECT_ATTRIBUTE_CONFIG,
      disable_auto_completers=False)


def AddConnectionProfileResourceArg(parser, verb, positional=True):
  """Add a resource argument for a Datastream connection profile.

  Args:
    parser: the parser for the command.
    verb: str, the verb to describe the resource, such as 'to update'.
    positional: bool, if True, means that the resource is a positional rather
      than a flag.
  """
  if positional:
    name = 'connection_profile'
  else:
    name = '--connection-profile'

  connectivity_parser = parser.add_group(mutex=True)
  connectivity_parser.add_argument(
      '--static-ip-connectivity',
      action='store_true',
      help="""use static ip connectivity""")
  connectivity_parser.add_argument(
      '--no-connectivity', action='store_true', help="""no connectivity""")
  forward_ssh_parser = connectivity_parser.add_group()
  forward_ssh_parser.add_argument(
      '--forward-ssh-hostname',
      help="""Hostname for the SSH tunnel.""",
      required=True)
  forward_ssh_parser.add_argument(
      '--forward-ssh-username',
      help="""Username for the SSH tunnel.""",
      required=True)
  forward_ssh_parser.add_argument(
      '--forward-ssh-port',
      help="""Port for the SSH tunnel, default value is 22.\
      """,
      default=22)
  password_group = forward_ssh_parser.add_group(required=True, mutex=True)
  password_group.add_argument(
      '--forward-ssh-password', help="""\
          SSH password.
          """)
  password_group.add_argument(
      '--forward-ssh-private-key', help='SSH private key..')

  resource_specs = [
      presentation_specs.ResourcePresentationSpec(
          name,
          GetConnectionProfileResourceSpec(),
          'The connection profile {}.'.format(verb),
          required=True),
      presentation_specs.ResourcePresentationSpec(
          '--private-connection-name',
          GetPrivateConnectionResourceSpec(),
          'Resource ID of the private connection.',
          flag_name_overrides={'location': ''},
          group=connectivity_parser)
  ]
  concept_parsers.ConceptParser(
      resource_specs,
      command_level_fallthroughs={
          '--private-connection-name.location': ['--location'],
      }).AddToParser(parser)


def AddConnectionProfileDiscoverResourceArg(parser):
  """Add a resource argument for a Datastream connection profile discover command.

  Args:
    parser: the parser for the command.
  """
  connection_profile_parser = parser.add_group(mutex=True, required=True)
  connection_profile_parser.add_argument(
      '--connection-profile-object-file',
      help="""Path to a YAML (or JSON) file containing the configuration
      for a connection profile object. If you pass - as the value of the
      flag the file content will be read from stdin."""
  )

  resource_specs = [
      presentation_specs.ResourcePresentationSpec(
          '--connection-profile-name',
          GetConnectionProfileResourceSpec(),
          'Resource ID of the connection profile.',
          flag_name_overrides={'location': ''},
          group=connection_profile_parser)
  ]
  concept_parsers.ConceptParser(
      resource_specs,
      command_level_fallthroughs={
          '--connection-profile-name.location': ['--location'],
      }).AddToParser(parser)


def AddPrivateConnectionResourceArg(parser, verb, positional=True):
  """Add a resource argument for a Datastream private connection.

  Args:
    parser: the parser for the command.
    verb: str, the verb to describe the resource, such as 'to update'.
    positional: bool, if True, means that the resource is a positional rather
      than a flag.
  """
  if positional:
    name = 'private_connection'
  else:
    name = '--private-connection'
  concept_parsers.ConceptParser.ForResource(
      name,
      GetPrivateConnectionResourceSpec(),
      'The private connection {}.'.format(verb),
      required=True).AddToParser(parser)
