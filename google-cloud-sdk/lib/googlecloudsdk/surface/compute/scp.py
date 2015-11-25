# Copyright 2014 Google Inc. All Rights Reserved.

"""Implements the command for copying files from and to virtual machines."""
import getpass
import logging

from googlecloudsdk.api_lib.compute import ssh_utils
from googlecloudsdk.calliope import actions
from googlecloudsdk.calliope import base
from googlecloudsdk.calliope import exceptions
from googlecloudsdk.core import properties
from googlecloudsdk.third_party.py27 import py27_collections as collections


RemoteFile = collections.namedtuple(
    'RemoteFile', ['user', 'instance_name', 'file_path'])
LocalFile = collections.namedtuple(
    'LocalFile', ['file_path'])


@base.ReleaseTracks(base.ReleaseTrack.ALPHA, base.ReleaseTrack.BETA)
class Scp(ssh_utils.BaseSSHCLICommand):
  """Copy files to and from Google Compute Engine virtual machines."""

  @staticmethod
  def Args(parser):
    ssh_utils.BaseSSHCLICommand.Args(parser)

    parser.add_argument(
        '--port',
        help='The port to connect to.')

    parser.add_argument(
        '--recurse',
        action='store_true',
        help='Upload directories recursively.')

    parser.add_argument(
        '--compress',
        action='store_true',
        help='Enable compression.')

    parser.add_argument(
        '--scp-flag',
        action='append',
        help='Extra flag to be sent to scp. This flag may be repeated.')

    parser.add_argument(
        'sources',
        help='Specifies the files to copy.',
        metavar='[[USER@]INSTANCE:]SRC',
        nargs='+')

    parser.add_argument(
        'destination',
        help='Specifies a destination for the source files.',
        metavar='[[USER@]INSTANCE:]DEST')

    # TODO(b/21515936): Use utils.AddZoneFlag when copy_files supports URIs
    zone = parser.add_argument(
        '--zone',
        help='The zone of the instance to copy files to/from.',
        action=actions.StoreProperty(properties.VALUES.compute.zone))
    zone.detailed_help = (
        'The zone of the instance to copy files to/from. If omitted, '
        'you will be prompted to select a zone.')

  def Run(self, args):
    super(Scp, self).Run(args)

    file_specs = []

    # Parses the positional arguments.
    for arg in args.sources + [args.destination]:
      # If the argument begins with "./" or "/", then we are dealing
      # with a local file that can potentially contain colons, so we
      # avoid splitting on colons. The case of remote files containing
      # colons is handled below by splitting only on the first colon.
      if arg.startswith('./') or arg.startswith('/'):
        file_specs.append(LocalFile(arg))
        continue

      host_file_parts = arg.split(':', 1)
      if len(host_file_parts) == 1:
        file_specs.append(LocalFile(host_file_parts[0]))
      else:
        user_host, file_path = host_file_parts
        user_host_parts = user_host.split('@', 1)
        if len(user_host_parts) == 1:
          user = getpass.getuser()
          instance = user_host_parts[0]
        else:
          user, instance = user_host_parts

        file_specs.append(RemoteFile(user, instance, file_path))

    logging.debug('Normalized arguments: %s', file_specs)

    # Validates the positional arguments.
    # TODO(b/21515495): Look into relaxing these conditions.
    sources = file_specs[:-1]
    destination = file_specs[-1]
    if isinstance(destination, LocalFile):
      for source in sources:
        if isinstance(source, LocalFile):
          raise exceptions.ToolException(
              'All sources must be remote files when the destination '
              'is local.')

    else:  # RemoteFile
      for source in sources:
        if isinstance(source, RemoteFile):
          raise exceptions.ToolException(
              'All sources must be local files when the destination '
              'is remote.')

    instances = set()
    for file_spec in file_specs:
      if isinstance(file_spec, RemoteFile):
        instances.add(file_spec.instance_name)

    if len(instances) > 1:
      raise exceptions.ToolException(
          'Copies must involve exactly one virtual machine instance; '
          'your invocation refers to [{0}] instances: [{1}].'.format(
              len(instances), ', '.join(sorted(instances))))

    instance_ref = self.CreateZonalReference(instances.pop(), args.zone)
    external_ip_address = self.GetInstanceExternalIpAddress(instance_ref)

    # Builds the scp command.
    scp_args = [self.scp_executable]
    if not args.plain:
      scp_args.extend(self.GetDefaultFlags())

    # apply args
    if args.quiet:
      scp_args.append('-q')
    if args.port:
      scp_args.extend(['-P', args.port])
    if args.recurse:
      scp_args.append('-r')
    if args.compress:
      scp_args.append('-C')
    if args.scp_flag:
      scp_args.extend(args.scp_flag)

    for file_spec in file_specs:
      if isinstance(file_spec, LocalFile):
        scp_args.append(file_spec.file_path)

      else:
        scp_args.append('{0}:{1}'.format(
            ssh_utils.UserHost(file_spec.user, external_ip_address),
            file_spec.file_path))

    self.ActuallyRun(args, scp_args, user, external_ip_address)

Scp.detailed_help = {
    'brief': 'Copy files to and from Google Compute Engine virtual machines '
             'via scp',
    'DESCRIPTION': """\
        *{command}* copies files between a virtual machine instance
        and your local machine using the scp command.

        To denote a remote file, prefix the file name with the virtual
        machine instance name (e.g., _example-instance_:~/_FILE_). To
        denote a local file, do not add a prefix to the file name
        (e.g., ~/_FILE_). For example, to copy a remote directory
        to your local host, run:

          $ {command} example-instance:~/REMOTE-DIR ~/LOCAL-DIR --zone us-central1-a

        In the above example, ``~/REMOTE-DIR'' from ``example-instance'' is
        copied into the ~/_LOCAL-DIR_ directory.

        Conversely, files from your local computer can be copied to a
        virtual machine:

          $ {command} ~/LOCAL-FILE-1 ~/LOCAL-FILE-2 example-instance:~/REMOTE-DIR --zone us-central1-a

        If a file contains a colon (``:''), you must specify it by
        either using an absolute path or a path that begins with
        ``./''.

        Under the covers, *scp(1)* or pscp (on Windows) is used to facilitate the transfer.

        When the destination is local, all sources must be the same
        virtual machine instance. When the destination is remote, all
        source must be local.
        """,
}
