# Copyright 2013 Google Inc. All Rights Reserved.

"""Provide commands for working with backups of Cloud SQL instances."""


from googlecloudsdk.calliope import base
from googlecloudsdk.calliope import exceptions


@base.ReleaseTracks(base.ReleaseTrack.GA, base.ReleaseTrack.BETA)
class BackupRuns(base.Group):
  """Provide commands for working with backups of Cloud SQL instances.

  Provide commands for working with backups of Cloud SQL instances
  including listing and getting information about backups for a Cloud SQL
  instance.
  """

  @staticmethod
  def Args(parser):
    parser.add_argument(
        '--instance',
        '-i',
        completion_resource='sql.instances',
        help='Cloud SQL instance ID.')

  def Filter(self, tool_context, args):
    if not args.instance:
      raise exceptions.ToolException('argument --instance/-i is required')
