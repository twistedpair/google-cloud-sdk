# Copyright 2015 Google Inc. All Rights Reserved.

"""The `app instances enable-debug` command."""

from googlecloudsdk.api_lib.app import appengine_client
from googlecloudsdk.api_lib.app import instances_util
from googlecloudsdk.calliope import base
from googlecloudsdk.core import log
from googlecloudsdk.core import properties
from googlecloudsdk.core.console import console_io


class EnableDebug(base.Command):
  """Enables debug mode for an instance.

  When in debug mode, SSH will be enabled on the VMs, and you can use
  `gcloud compute ssh` to login to them. They will be removed from the health
  checking pools, but they still receive requests.

  Note that any local changes to an instance will be **lost** and the instance
  restarted if debug mode is disabled on the instance.
  """

  detailed_help = {
      'DESCRIPTION': '{description}',
      'EXAMPLES': """\
          To enable debug mode for a particular instance, run:

              $ {command} service/version/nwz0

          or

              $ {command} --service=service --version=version nwz0

          To enable debug mode for an instance chosen interactively, run:

              $ {command}
          """,
  }

  @staticmethod
  def Args(parser):
    instance = parser.add_argument(
        'instance', nargs='?',
        help=('The instance to enable debug mode on.'))
    instance.detailed_help = (
        'The instance to enable debug mode on (either an instance name or a '
        'resource path (<service>/<version>/<instance>). If not specified, '
        'select instance interactively. Must uniquely specify (with other '
        'flags) exactly one instance')

    service = parser.add_argument(
        '--service', '-s',
        help='Only match instances belonging to this service.')
    service.detailed_help = (
        'If specified, only match instances belonging to the given service. '
        'This affects both interactive and non-interactive selection.')

    version = parser.add_argument(
        '--version', '-v',
        help='Only match instances belonging to this version.')
    version.detailed_help = (
        'If specified, only match instances belonging to the given version. '
        'This affects both interactive and non-interactive selection.')

  def Run(self, args):
    client = appengine_client.AppengineClient()
    # --user-output-enabled=false prevents this from printing, as well as from
    # consuming the generator from the other command
    # The command being called here uses a cli.Execute call under-the-hood, so
    # in order to avoid leaking the abstraction we defer to the implementation
    # in `instances list`.
    all_instances = list(self.cli.Execute(
        ['preview', 'app', 'instances', 'list',
         '--user-output-enabled=false',
         '--project', properties.VALUES.core.project.Get()]))
    instance = instances_util.GetMatchingInstance(
        all_instances, service=args.service, version=args.version,
        instance=args.instance)

    console_io.PromptContinue(
        'Enabling debug mode for instance [{0}].'.format(instance),
        cancel_on_no=True)
    client.SetManagedBySelf(module=instance.service, version=instance.version,
                            instance=instance.id)
    log.status.Print('Enabled debug mode for instance [{0}].'.format(instance))
