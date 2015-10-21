# Copyright 2013 Google Inc. All Rights Reserved.

"""Command to unset properties."""

from googlecloudsdk.calliope import base
from googlecloudsdk.calliope import exceptions as c_exc
from googlecloudsdk.core import log
from googlecloudsdk.core import properties


def CommonArgs(cmd_class, parser):
  """Adds args for this command."""
  property_arg = parser.add_argument(
      'property',
      metavar='SECTION/PROPERTY',
      help='The property to be unset. Note that SECTION/ is optional while '
      'referring to properties in the core section.')
  property_arg.completer = cmd_class.group_class.PropertiesCompleter


def RunUnset(cmd, args):
  """Unsets a property."""
  prop = properties.FromString(args.property)
  if not prop:
    raise c_exc.InvalidArgumentException(
        'property', 'Must be in the form: [SECTION/]PROPERTY')
  properties.PersistProperty(prop, None, scope=cmd.group.RequestedScope(args))


DETAILED_HELP = {
    'DESCRIPTION': '{description}',
    'EXAMPLES': """\
        To unset the project property in the core section, run:

          $ {command} project

        To unset the zone property in the compute section, run:

          $ {command} compute/zone
        """,
}


class Unset(base.Command):
  """Erase Google Cloud SDK properties.

  Unset a property to be as if it were never defined in the first place. You
  may optionally use the --scope flag to specify a configuration file to update.
  """

  detailed_help = DETAILED_HELP

  @staticmethod
  def Args(parser):
    """Adds args for this command."""
    scope_args = parser.add_mutually_exclusive_group()
    Unset.group_class.DEPRECATED_SCOPE_FLAG.AddToParser(scope_args)
    Unset.group_class.INSTALLATION_FLAG.AddToParser(scope_args)

    CommonArgs(Unset, parser)

  @c_exc.RaiseToolExceptionInsteadOf(properties.Error)
  def Run(self, args):
    """Runs this command."""
    if args.scope:
      log.err.Print('The `--scope` flag is deprecated.  Please run `gcloud '
                    'help topic configurations` and `gcloud help config '
                    'unset` for more information.')

    RunUnset(self, args)
