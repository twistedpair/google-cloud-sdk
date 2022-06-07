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

import collections
from apitools.base.py import encoding
from googlecloudsdk.calliope import arg_parsers


class RuntimeConfigFactory(object):
  """Factory for RuntimeConfig message.

  Factory to add RuntimeConfig message arguments to argument parser and create
  RuntimeConfig message from parsed arguments.
  """

  def __init__(self, dataproc, use_config_property=False):
    """Factory for RuntimeConfig message.

    Args:
      dataproc: Api_lib.dataproc.Dataproc instance.
      use_config_property: Use --property instead of --properties
    """
    self.dataproc = dataproc
    self.use_config_property = use_config_property

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

    flat_property = collections.OrderedDict()
    if self.use_config_property:
      if args.property:
        for entry in args.property:
          for k, v in entry.items():
            flat_property[k] = v
    elif args.properties:
      flat_property = args.properties
    if flat_property:
      kwargs['properties'] = encoding.DictToAdditionalPropertyMessage(
          flat_property,
          self.dataproc.messages.RuntimeConfig.PropertiesValue,
          sort_items=True)

    if args.version:
      kwargs['version'] = args.version

    if not kwargs:
      return None

    return self.dataproc.messages.RuntimeConfig(**kwargs)


def AddArguments(parser, use_config_property=False):
  """Adds arguments related to RuntimeConfig message to the given parser."""
  parser.add_argument(
      '--container-image',
      help=('Optional custom container image to use for the batch/session '
            'runtime environment. If not specified, a default container image '
            'will be used. The value should follow the container image naming '
            'format: {registry}/{repository}/{name}:{tag}, for example, '
            'gcr.io/my-project/my-image:1.2.3'))
  if use_config_property:
    parser.add_argument(
        '--property',
        type=arg_parsers.ArgDict(),
        action='append',
        metavar='PROPERTY=VALUE',
        help='Specifies configuration properties.')
  else:
    parser.add_argument(
        '--properties',
        type=arg_parsers.ArgDict(),
        metavar='PROPERTY=VALUE',
        help="""\
        Specifies configuration properties for the workload. See
        [Dataproc Serverless for Spark documentation](https://cloud.google.com/dataproc-serverless/docs/concepts/properties)
        for the list of supported properties.""")

  parser.add_argument(
      '--version',
      help=('Optional runtime version.  If not specified, a default '
            'version will be used.'))
