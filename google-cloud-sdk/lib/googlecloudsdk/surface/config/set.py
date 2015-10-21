# Copyright 2013 Google Inc. All Rights Reserved.

"""Command to set properties."""

from googlecloudsdk.calliope import base
from googlecloudsdk.calliope import exceptions as c_exc
from googlecloudsdk.core import log
from googlecloudsdk.core import named_configs
from googlecloudsdk.core import properties


@c_exc.RaiseToolExceptionInsteadOf(properties.Error)
def RunSet(cmd, args):
  """Runs a config set command."""
  requested_scope = cmd.group.RequestedScope(args)

  if not requested_scope:
    named_configs.TryEnsureWriteableNamedConfig()

  prop = properties.FromString(args.property)
  if not prop:
    raise c_exc.InvalidArgumentException(
        'property', 'Must be in the form: [SECTION/]PROPERTY')
  properties.PersistProperty(prop, args.value, scope=requested_scope)


def CommonArgs(cmd_class, parser):
  """Adds args for this command."""
  property_arg = parser.add_argument(
      'property',
      metavar='SECTION/PROPERTY',
      help='The property to be set. Note that SECTION/ is optional while '
      'referring to properties in the core section.')
  property_arg.completer = cmd_class.group_class.PropertiesCompleter
  parser.add_argument(
      'value',
      completion_resource='cloudresourcemanager.projects',
      list_command_path='beta.projects',
      help='The value to be set.')

DETAILED_HELP = {
    'DESCRIPTION': '{description}',
    'EXAMPLES': """\
        To set the project property in the core section, run:

          $ {command} project myProject

        To set the zone property in the compute section, run:

          $ {command} compute/zone zone3
        """,
}


class Set(base.Command):
  """Edit Google Cloud SDK properties.

  Set the value for an option, so that Cloud SDK tools can use them as
  configuration.
  """

  detailed_help = DETAILED_HELP

  @staticmethod
  def Args(parser):
    """Adds args for this command."""
    scope_args = parser.add_mutually_exclusive_group()
    Set.group_class.DEPRECATED_SCOPE_FLAG.AddToParser(scope_args)
    Set.group_class.INSTALLATION_FLAG.AddToParser(scope_args)

    CommonArgs(Set, parser)

  def Run(self, args):
    if args.scope:
      log.err.Print('The `--scope` flag is deprecated.  Please run `gcloud '
                    'help topic configurations` and `gcloud help config set` '
                    'for more information.')

    RunSet(self, args)
