# Copyright 2015 Google Inc. All Rights Reserved.

"""Command to list named configuration."""

from googlecloudsdk.calliope import base
from googlecloudsdk.core import named_configs
from googlecloudsdk.core.console import console_io


class List(base.Command):
  """Lists available named configurations."""

  detailed_help = {
      'DESCRIPTION': """\
          {description}

          See `gcloud topic configurations` for an overview of named
          configurations.
          """,
      'EXAMPLES': """\
          To list all available configurations, run:

            $ {command}
          """,
  }

  def Run(self, args):
    configs = named_configs.ListNamedConfigs(log_warnings=True)
    return configs

  def Display(self, _, resources):
    # Custom selector to format configs as a table
    selectors = (('NAME', lambda x: x.name),
                 ('IS_ACTIVE', lambda x: x.is_active))
    console_io.PrintExtendedList(resources, selectors)
