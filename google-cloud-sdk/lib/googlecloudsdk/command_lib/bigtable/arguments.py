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

from __future__ import absolute_import
from __future__ import unicode_literals

from googlecloudsdk.calliope import actions
from googlecloudsdk.calliope import arg_parsers
from googlecloudsdk.calliope import base
from googlecloudsdk.calliope.concepts import concepts
from googlecloudsdk.calliope.concepts import deps
from googlecloudsdk.command_lib.util import completers
from googlecloudsdk.command_lib.util.concepts import concept_parsers
from googlecloudsdk.core import properties
from googlecloudsdk.core.util import text


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

  def AddInstance(self, positional=True, required=True, multiple=False,
                  additional_help=None):
    """Add argument for instance ID to parser."""
    help_text = 'ID of the {}.'.format(text.Pluralize(2 if multiple else 1,
                                                      'instance'))
    if additional_help:
      help_text = ' '.join([help_text, additional_help])
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

  def AddInstanceDisplayName(self, required=False):
    """Add argument group for display-name to parser."""
    self.parser.add_argument(
        '--display-name',
        help='Friendly name of the instance.',
        required=required)
    # Specify old flag as removed with an error message
    self.parser.add_argument(
        '--description',
        action=actions.DeprecationAction(
            '--description',
            removed=True,
            error=('Flag {flag_name} has been removed. '
                   'Use --display-name=DISPLAY_NAME instead.')),
        help='Friendly name of the instance.',
        hidden=True)
    return self

  def AddInstanceType(self, default=None, help_text=None):
    """Add default instance type choices to parser."""
    choices = {
        'PRODUCTION':
            'Production instances have a minimum of '
            'three nodes, provide high availability, and are suitable for '
            'applications in production.',
        'DEVELOPMENT': 'Development instances are low-cost instances meant '
                       'for development and testing only. They do not '
                       'provide high availability and no service level '
                       'agreement applies.'
    }

    self.parser.add_argument(
        '--instance-type',
        default=default,
        type=lambda x: x.upper(),
        choices=choices,
        help=help_text)

    return self


def InstanceAttributeConfig():
  return concepts.ResourceParameterAttributeConfig(
      name='instance',
      help_text='The Cloud Bigtable instance for the {resource}.')


def ProjectAttributeConfig():
  return concepts.ResourceParameterAttributeConfig(
      name='project',
      help_text='The Cloud project for the {resource}.',
      # Fall back to the project configured as the gcloud default
      fallthroughs=[deps.PropertyFallthrough(properties.VALUES.core.project)])


def GetInstanceResourceSpec():
  """Return the resource specification for a Bigtable instance."""
  return concepts.ResourceSpec(
      'bigtableadmin.projects.instances',
      resource_name='instance',
      instancesId=InstanceAttributeConfig(),
      projectsId=ProjectAttributeConfig(),
      disable_auto_completers=False)


def AddInstanceResourceArg(parser, verb):
  """Add --instance resource argument to the parser."""
  concept_parsers.ConceptParser.ForResource(
      'instance',
      GetInstanceResourceSpec(),
      'The instance {}.'.format(verb),
      required=True,
      plural=False).AddToParser(parser)
