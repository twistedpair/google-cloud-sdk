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
"""Provides common arguments for the Run command surface."""

from __future__ import absolute_import
from __future__ import division
from __future__ import print_function
from __future__ import unicode_literals

from googlecloudsdk.calliope import arg_parsers


def AddFileArg(parser):
  parser.add_argument(
      'FILE',
      type=arg_parsers.YAMLFileContents(),
      help='The absolute path to the YAML file with an application '
      'definition to update or deploy.')


def AddTypeArg(parser):
  """Add an integration type arg."""
  parser.add_argument(
      '--type',
      required=True,
      help='Type of the integration.')


def AddNameArg(parser):
  """Add an integration name arg."""
  parser.add_argument(
      '--name',
      help='Name of the integration.')


def AddServiceArg(parser):
  """Add a service arg."""
  parser.add_argument(
      '--service',
      help='Name of the Cloud Run service to attach the integration to.')


def AddParametersArg(parser):
  """Add a parameters arg."""
  parser.add_argument(
      '--parameters',
      type=arg_parsers.ArgDict(),
      action=arg_parsers.UpdateAction,
      default={},
      metavar='PARAMETER=VALUE',
      help='Comma-separated list of parameter names and values. '
      'Names must be one of the parameters shown when describing the '
      'integration type. Only simple values can be specified with this flag.')


def _ValidateParameters(integration_type, parameters):
  """Validates given params conform to what's expected from the integration."""
  # TODO(b/205648394): Validate parameters
  del integration_type
  del parameters
  pass


def GetAndValidateParameters(args, integration_type):
  """Validates all parameters and returns a dict of values."""
  # Check the passed parameters for unknown keys or missing required keys
  parameters = {}
  if args.IsSpecified('parameters'):
    parameters.update(args.parameters)

  _ValidateParameters(integration_type, parameters)

  return parameters
