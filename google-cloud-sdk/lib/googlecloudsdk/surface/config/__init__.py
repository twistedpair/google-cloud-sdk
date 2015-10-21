# Copyright 2013 Google Inc. All Rights Reserved.

"""config command group."""

from googlecloudsdk.calliope import base
from googlecloudsdk.calliope import exceptions as c_exc
from googlecloudsdk.core import config
from googlecloudsdk.core import properties


class Config(base.Group):
  """View and edit Google Cloud SDK properties."""

  INSTALLATION_FLAG = base.Argument(
      '--installation',
      required=False,
      action='store_true',
      help='Update the property in the gcloud installation.',
      detailed_help="""\
          Typically properties are updated only in the currently active
          configuration, but when `--installation` is given the property is
          updated for the entire gcloud installation."""
      )

  DEPRECATED_SCOPE_FLAG = base.Argument(
      '--scope',
      required=False,
      choices=properties.Scope.AllScopeNames(),
      help='Deprecated. the configuration location in which to update the '
      'property. ({scopes})'.format(
          scopes=', '.join(properties.Scope.AllScopeNames())),
      detailed_help="""\
          Deprecated.  Gcloud will be removing support for the workspaces and
          the global user configuration.  See `gcloud help topic
          configurations` for more information.  Use the `--installation` flag
          to set installation-wide properties.

          The scope flag determines which configuration file is modified by
          this operation.  The files are read (and take precedence) in the
          following order:

          {scope_help}""".format(scope_help=properties.Scope.GetHelpString())
  )

  @staticmethod
  def RequestedScope(args):
    # This hackiness will go away when we rip out args.scope everywhere
    install = 'installation' if getattr(args, 'installation', False) else None
    scope_arg = getattr(args, 'scope', None)

    return properties.Scope.FromId(scope_arg or install)

  @staticmethod
  def PropertiesCompleter(prefix, parsed_args, **unused_kwargs):
    """Properties commmand completion helper."""
    all_sections = properties.VALUES.AllSections()
    options = []

    if '/' in prefix:
      # Section has been specified, only return properties under that section.
      parts = prefix.split('/', 1)
      section = parts[0]
      prefix = parts[1]
      if section in all_sections:
        section_str = section + '/'
        props = properties.VALUES.Section(section).AllProperties()
        options.extend([section_str + p for p in props if p.startswith(prefix)])
    else:
      # No section.  Return matching sections and properties in the default
      # group.
      options.extend([s + '/' for s in all_sections if s.startswith(prefix)])
      section = properties.VALUES.default_section.name
      props = properties.VALUES.Section(section).AllProperties()
      options.extend([p for p in props if p.startswith(prefix)])

    return options
