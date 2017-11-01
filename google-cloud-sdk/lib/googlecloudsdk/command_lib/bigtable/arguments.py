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
"""Module for wrangling bigtable command arguments."""

from googlecloudsdk.calliope import arg_parsers
from googlecloudsdk.calliope import base
from googlecloudsdk.command_lib.util import completers


class ClusterCompleter(completers.ListCommandCompleter):

  def __init__(self, **kwargs):
    super(ClusterCompleter, self).__init__(
        collection='bigtableadmin.projects.instances.clusters',
        list_command='beta bigtable clusters list --uri',
        **kwargs)


class InstanceCompleter(completers.ListCommandCompleter):

  def __init__(self, **kwargs):
    super(InstanceCompleter, self).__init__(
        collection='bigtableadmin.projects.instances',
        list_command='beta bigtable instances list --uri',
        **kwargs)


class ArgAdder(object):
  """A class for adding Bigtable command-line arguments."""

  def __init__(self, parser):
    self.parser = parser

  def AddAsync(self):
    self.parser.add_argument(
        '--async',
        help='Return immediately, without waiting for operation to complete.',
        action='store_true')
    return self

  def AddCluster(self, positional=True):
    """Add cluster argument."""

    help_text = 'ID of the cluster.'
    if positional:
      self.parser.add_argument(
          'cluster',
          completer=ClusterCompleter,
          help=help_text)
    else:
      self.parser.add_argument(
          '--cluster',
          completer=ClusterCompleter,
          help=help_text,
          required=True)
    return self

  def AddClusterNodes(self, in_instance=False):
    self.parser.add_argument(
        '--cluster-num-nodes' if in_instance else '--num-nodes',
        help='Number of nodes to serve.',
        required=not in_instance,
        type=int)
    return self

  def AddClusterStorage(self, in_instance=False):
    storage_argument = base.ChoiceArgument(
        '--cluster-storage-type' if in_instance else '--storage',
        choices=['hdd', 'ssd'],
        default='ssd',
        help_str='Storage class for the cluster.'
    )
    storage_argument.AddToParser(self.parser)
    return self

  def AddClusterZone(self, in_instance=False):
    self.parser.add_argument(
        '--cluster-zone' if in_instance else '--zone',
        help='ID of the zone where the cluster is located. Supported zones '
        'are listed at https://cloud.google.com/bigtable/docs/locations.',
        required=True)
    return self

  def AddInstance(self, positional=True, required=True, multiple=False):
    """Add argument for instance ID to parser."""
    help_text = 'ID of the instance.'
    name = 'instance' if positional else '--instance'
    args = {
        'completer': InstanceCompleter,
        'help': help_text
    }
    if multiple:
      if positional:
        args['nargs'] = '+'
      else:
        name = '--instances'
        args['type'] = arg_parsers.ArgList()
        args['metavar'] = 'INSTANCE'
    if not positional:
      args['required'] = required

    self.parser.add_argument(name, **args)
    return self

  def AddInstanceDescription(self, required=False):
    self.parser.add_argument(
        '--description',
        help='Friendly name of the instance.',
        required=required)
    return self

  def AddInstanceType(self, additional_choices=None, default=None,
                      help_text=None):
    """Add default instance type choices to parser."""
    choices = {
        'PRODUCTION':
            'Production instances have a minimum of '
            'three nodes, provide high availability, and are suitable for '
            'applications in production.'
    }

    if additional_choices:
      choices.update(additional_choices)

    self.parser.add_argument(
        '--instance-type',
        default=default,
        type=str.upper,
        choices=choices,
        help=help_text)

    return self
