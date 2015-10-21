# Copyright 2013 Google Inc. All Rights Reserved.

"""Command to list properties."""

from googlecloudsdk.calliope import base
from googlecloudsdk.calliope import exceptions as c_exc
from googlecloudsdk.core import exceptions
from googlecloudsdk.core import log
from googlecloudsdk.core import named_configs
from googlecloudsdk.core import properties


class BadConfigListInvocation(exceptions.Error):
  """Exception for incorrect invocations of `config list`."""


@base.ReleaseTracks(base.ReleaseTrack.ALPHA, base.ReleaseTrack.GA)
class List(base.Command):
  """View Google Cloud SDK properties.

  List all currently available Cloud SDK properties associated with your current
  workspace or global configuration.
  """

  detailed_help = {
      'DESCRIPTION': '{description}',
      'EXAMPLES': """\
          To list the project property in the core section, run:

            $ {command} project

          To list the zone property in the compute section, run:

            $ {command} compute/zone

          To list all the properties, run:
            $ {command} --all

          Note you cannot specify both --all and a property name.
          """,
  }

  @staticmethod
  def Args(parser):
    """Adds args for this command."""
    parser.add_argument(
        '--all', action='store_true',
        help='List all set and unset properties that match the arguments.')
    property_arg = parser.add_argument(
        'property',
        metavar='SECTION/PROPERTY',
        nargs='?',
        help='The property to be listed. Note that SECTION/ is optional while '
        'referring to properties in the core section.')
    property_arg.completer = List.group_class.PropertiesCompleter

  def _GetPropertiesToDisplay(self, args):
    """List available regular properties."""

    # Don't try to look up real properties that don't exist.
    if List._PositionalRequestsMetaProperties(args):
      return {}

    section, prop = properties.ParsePropertyString(args.property)

    if prop:
      return {section: {
          prop: properties.VALUES.Section(section).Property(prop).Get()}}
    if section:
      return {section: properties.VALUES.Section(section).AllValues(
          list_unset=args.all)}
    return properties.VALUES.AllValues(list_unset=args.all)

  @staticmethod
  def _PositionalRequestsMetaProperties(args):
    return args.property in ('meta', 'meta/active_config')

  @staticmethod
  def _GetMetaPropertiesToDisplay(args):
    """List available regular property-like settings."""

    # Simplifed control flow because there's only one meta property.
    # It's not a good idea to generalize because we can't really
    # test with just a single metaproperty choice.

    meta_property_requested = List._PositionalRequestsMetaProperties(args)

    # User explicitly requested a regular property
    if args.property and not meta_property_requested:
      return {}

    active_config = named_configs.GetNameOfActiveNamedConfig()
    active_config_as_property = {'meta': {'active_config': active_config}}

    # User wants to see meta/active_config
    if List._PositionalRequestsMetaProperties(args) or args.all:
      return active_config_as_property

    # Show meta/active config iff set (i.e. non-None)
    if active_config:
      return active_config_as_property

    return {}

  @c_exc.RaiseToolExceptionInsteadOf(properties.Error)
  def Run(self, args):
    if args.all and args.property:
      raise BadConfigListInvocation('`gcloud config list` cannot take both '
                                    'a property name and the `--all` flag.')

    return dict(self._GetMetaPropertiesToDisplay(args),
                **self._GetPropertiesToDisplay(args))

  def Display(self, _, result):
    properties.DisplayProperties(log.out, result)
