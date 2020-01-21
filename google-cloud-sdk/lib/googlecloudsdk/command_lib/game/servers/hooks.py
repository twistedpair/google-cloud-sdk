# -*- coding: utf-8 -*- #
# Copyright 2019 Google LLC. All Rights Reserved.
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

"""Argument processors for Game Servers surface arguments."""

from __future__ import absolute_import
from __future__ import division
from __future__ import unicode_literals

import json

from apitools.base.protorpclite import messages as _messages
from apitools.base.py import encoding
from googlecloudsdk.calliope import arg_parsers
from googlecloudsdk.command_lib.game.servers import utils
from googlecloudsdk.core import exceptions
from googlecloudsdk.core import properties
from googlecloudsdk.core import yaml

import six

DEFAULT_LOCATION = 'global'

PARENT_TEMPLATE = 'projects/{}/locations/{}'
PARENT_DEPLOYMENT_TEMPLATE = 'projects/{}/locations/{}/gameServerDeployments/{}'
PARENT_REALM_TEMPLATE = 'projects/{}/locations/{}/realms/{}'

DEPLOYMENT_WILDCARD = '-'
LOCATION_WILDCARD = '-'
REALM_WILDCARD = '-'


class InvalidSpecFileError(exceptions.Error):
  """Error if a spec file is not valid JSON or YAML."""


class InvalidSchemaError(exceptions.Error):
  """Error if a schema is improperly specified."""


def FlattenedArgDict(value):
  dict_value = arg_parsers.ArgDict()(value)
  return [{'key': key, 'value': value} for key, value in dict_value.items()]


def AddDefaultLocationToListRequest(ref, args, req):
  """Python hook for yaml commands to wildcard the location in list requests."""
  del ref  # Unused
  project = properties.VALUES.core.project.Get(required=True)
  location = args.location or LOCATION_WILDCARD
  req.parent = PARENT_TEMPLATE.format(project, location)
  return req


def AddDefaultLocationAndRealmToListRequest(ref, args, req):
  """Python hook for yaml commands to wildcard the realm and location in list requests."""
  del ref
  project = properties.VALUES.core.project.Get(required=True)
  location = args.location or LOCATION_WILDCARD
  # If realm is specified but location is not, we fall back to global, which is
  # the default location for realms.
  if args.realm and not args.location:
    location = DEFAULT_LOCATION
  realm = args.realm or REALM_WILDCARD
  req.parent = PARENT_REALM_TEMPLATE.format(project, location, realm)
  return req


def AddDefaultLocationAndDeploymentToListRequest(ref, args, req):
  """Python hook for yaml commands to wildcard the deployment and location in list requests."""
  del ref
  project = properties.VALUES.core.project.Get(required=True)
  location = args.location or LOCATION_WILDCARD
  # If deployment is specified but location is not, we fall back to global
  # which is the default location for realms.
  if args.deployment and not args.location:
    location = DEFAULT_LOCATION
  deployment = args.deployment or DEPLOYMENT_WILDCARD
  req.parent = PARENT_DEPLOYMENT_TEMPLATE.format(project, location, deployment)
  return req


def ProcessConfigOverrideFile(config_override_file):
  """Reads a JSON/YAML config_override_file and returns collection of config override object."""

  try:
    overrides = json.loads(config_override_file[0])
  except ValueError as e:
    try:
      overrides = yaml.load(config_override_file[0])
    except yaml.YAMLParseError as e:
      raise InvalidSpecFileError(
          'Error parsing config_override file: [{}]'.format(e))

  messages = utils.GetMessages()
  message_class = messages.GameServerConfigOverride
  try:
    overrides_message = [encoding.DictToMessage(o, message_class)
                         for o in overrides]
  except AttributeError:
    raise InvalidSchemaError(
        'Invalid schema: unexpected game server config override(s) format.')
  except _messages.ValidationError as e:
    # Unfortunately apitools doesn't provide a way to get the path to the
    # invalid field here.
    raise InvalidSchemaError('Invalid schema: [{}]'.format(e))
  unrecognized_field_paths = _GetUnrecognizedFieldPaths(overrides_message)
  if unrecognized_field_paths:
    error_msg_lines = ['Invalid schema, the following fields are unrecognized:']
    error_msg_lines += unrecognized_field_paths
    raise InvalidSchemaError('\n'.join(error_msg_lines))

  return overrides_message


def ProcessFleetConfigsFile(fleet_configs_file):
  """Reads a JSON/YAML fleet_configs_file and returns collectiong of fleet configs object."""
  try:
    fleet_configs = json.loads(fleet_configs_file[0])
  except ValueError as e:
    try:
      fleet_configs = yaml.load(fleet_configs_file[0])
    except yaml.YAMLParseError as e:
      raise InvalidSpecFileError(
          'Error parsing fleet_configs file: [{}]'.format(e))

  messages = utils.GetMessages()
  message_class = messages.FleetConfig
  fleet_configs_message = []
  try:
    for fc in fleet_configs:
      f = encoding.DictToMessage(fc, message_class)
      spec = yaml.load(f.fleetSpec)
      spec_as_json_str = json.dumps(spec)
      f.fleetSpec = spec_as_json_str
      fleet_configs_message.append(f)
  except AttributeError:
    raise InvalidSchemaError(
        'Invalid schema: expected proper fleet configs')
  except _messages.ValidationError as e:
    # The most likely reason this is reaised is the file that is submitted is
    # following new format (json/yaml without string blob) and we will parse
    # with the new format
    for fc in fleet_configs:
      f = messages.FleetConfig()
      if 'name' in fc:
        f.name = fc['name']
      if 'fleetSpec' not in fc:
        raise InvalidSchemaError(
            'Invalid schema: expected proper fleet configs')
      spec_as_json_str = json.dumps(fc['fleetSpec'])
      f.fleetSpec = spec_as_json_str
      fleet_configs_message.append(f)
  unrecognized_field_paths = _GetUnrecognizedFieldPaths(fleet_configs_message)
  if unrecognized_field_paths:
    error_msg_lines = ['Invalid schema, the following fields are unrecognized:']
    error_msg_lines += unrecognized_field_paths
    raise InvalidSchemaError('\n'.join(error_msg_lines))

  return fleet_configs_message


def ProcessScalingConfigsFile(scaling_configs_file):
  """Reads a JSON/YAML scaling_configs_file and returns collectiong of scaling configs object."""

  try:
    scaling_configs = json.loads(scaling_configs_file[0])
  except ValueError as e:
    try:
      scaling_configs = yaml.load(scaling_configs_file[0])
    except yaml.YAMLParseError as e:
      raise InvalidSpecFileError(
          'Error parsing scaling_configs file: [{}]'.format(e))

  messages = utils.GetMessages()
  message_class = messages.ScalingConfig
  selector = messages.LabelSelector()
  scaling_configs_message = []
  try:
    for sc in scaling_configs:
      esc = encoding.DictToMessage(sc, message_class)
      if not esc.selectors:
        # Add default selector if not set
        esc.selectors = [selector]
      # Convert yaml to json
      spec = yaml.load(esc.fleetAutoscalerSpec)
      spec_as_json_str = json.dumps(spec)
      esc.fleetAutoscalerSpec = spec_as_json_str
      scaling_configs_message.append(esc)
  except AttributeError:
    raise InvalidSchemaError(
        'Invalid schema: expected proper scaling configs')
  except _messages.ValidationError as e:
    # The most likely reason this is reaised is the file that is submitted is
    # following new format (json/yaml without string blob) and we will parse
    # with the new format
    for sc in scaling_configs:
      s = messages.ScalingConfig()
      if 'selectors' in sc:
        if not isinstance(sc['selectors'], list):
          raise InvalidSchemaError('Invalid schema: selectors must be a list')
        s.selectors = []
        for lab in sc['selectors']:
          labels = []
          for (key, val) in lab['labels'].items():
            labels.append(utils.ParseClusters(None, key, val, messages))
          s.selectors.append(utils.ParseLabels(None, labels, messages))
      else:
        # Add default selector if not set
        s.selectors = [selector]
      if 'name' in sc:
        s.name = sc['name']
      if 'schedules' in sc:
        s.schedules = []
        if not isinstance(sc['schedules'], list):
          raise InvalidSchemaError('Invalid schema: schedules must be a list')
        for sh in sc['schedules']:
          schedule = messages.Schedule()
          schedule.cronJobDuration = sh['cronJobDuration']
          schedule.cronSpec = sh['cronSpec']
          s.schedules.append(schedule)
      if 'fleetAutoscalerSpec' not in sc:
        raise InvalidSchemaError(
            'Invalid schema: expected proper scaling configs')
      spec_as_json_str = json.dumps(sc['fleetAutoscalerSpec'])
      s.fleetAutoscalerSpec = spec_as_json_str
      scaling_configs_message.append(s)
  return scaling_configs_message


def _GetUnrecognizedFieldPaths(message):
  """Returns the field paths for unrecognized fields in the message."""
  errors = encoding.UnrecognizedFieldIter(message)
  unrecognized_field_paths = []
  for edges_to_message, field_names in errors:
    message_field_path = '.'.join(six.text_type(e) for e in edges_to_message)
    # Don't print the top level columns field since the user didn't specify it
    message_field_path = message_field_path.replace('columns', '', 1)
    for field_name in field_names:
      unrecognized_field_paths.append('{}.{}'.format(
          message_field_path, field_name))
  return sorted(unrecognized_field_paths)

