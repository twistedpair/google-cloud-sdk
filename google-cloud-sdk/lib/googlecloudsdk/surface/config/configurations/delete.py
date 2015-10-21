# Copyright 2015 Google Inc. All Rights Reserved.

"""Command to delete named configuration."""

from googlecloudsdk.calliope import base
from googlecloudsdk.core import exceptions
from googlecloudsdk.core import log
from googlecloudsdk.core import named_configs
from googlecloudsdk.core.console import console_io


class DeleteCanceledException(exceptions.Error):
  """Raise when a user aborts a deletion."""

  def __init__(self, message=None):
    super(DeleteCanceledException, self).__init__(
        message or 'Deletion aborted by user.')


class Delete(base.Command):
  """Deletes a named configuration."""

  detailed_help = {
      'DESCRIPTION': """\
          {description} You cannot delete a configuration that is active, even
          when overridden with the --configuration flag.  To delete the current
          active configuration, first `gcloud config configurations activate`
          another one.

          See `gcloud topic configurations` for an overview of named
          configurations.
          """,
      'EXAMPLES': """\
          To delete named configuration, run:

            $ {command} my_config

          To list get a list of existing configurations, run:

            $ gcloud config configurations list
          """,
  }

  @staticmethod
  def Args(parser):
    """Adds args for this command."""
    parser.add_argument(
        'configuration_name',
        help=('Configuration name to delete, '
              'can not be currently active configuration.'))

  def Run(self, args):

    # TODO(b/23621782): Move logic to a core library.
    if not args.quiet:
      if not console_io.PromptContinue(
          'The following configuration will be deleted: [{0}]'.format(
              args.configuration_name)):
        raise DeleteCanceledException

    named_configs.DeleteNamedConfig(args.configuration_name)
    log.DeletedResource(args.configuration_name)
