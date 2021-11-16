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

"""Factory for RuntimeConfig message."""

from __future__ import absolute_import
from __future__ import division
from __future__ import unicode_literals

from apitools.base.py import encoding
from googlecloudsdk.calliope import arg_parsers


class RuntimeConfigFactory(object):
  """Factory for RuntimeConfig message.

  Factory to add RuntimeConfig message arguments to argument parser and create
  RuntimeConfig message from parsed arguments.
  """

  def __init__(self, dataproc):
    """Factory for RuntimeConfig message.

    Args:
      dataproc: Api_lib.dataproc.Dataproc instance.
    """
    self.dataproc = dataproc

  def GetMessage(self, args):
    """Builds a RuntimeConfig message.

    Build a RuntimeConfig message instance according to user settings. Returns
    None if all fields are None.

    Args:
      args: Parsed arguments.

    Returns:
      RuntimeConfig: A RuntimeConfig message instance. This function returns
      None if all fields are None.
    """
    kwargs = {}

    if args.container_image:
      kwargs['containerImage'] = args.container_image

    if args.properties:
      kwargs['properties'] = encoding.DictToAdditionalPropertyMessage(
          args.properties,
          self.dataproc.messages.RuntimeConfig.PropertiesValue,
          sort_items=True)

    if args.version:
      kwargs['version'] = args.version

    if not kwargs:
      return None

    return self.dataproc.messages.RuntimeConfig(**kwargs)


def AddArguments(parser):
  """Adds arguments related to RuntimeConfig message to the given parser."""
  parser.add_argument(
      '--container-image',
      help=('Container image to use for batch job execution. '
            'IMAGE name should follow the docker image naming format: '
            '{hostname}/{repository}:{version}.'))

  parser.add_argument(
      '--properties',
      type=arg_parsers.ArgDict(),
      metavar='PROPERTY=VALUE',
      help='Container image properties.')

  parser.add_argument(
      '--version',
      help='Batch runtime version.')
