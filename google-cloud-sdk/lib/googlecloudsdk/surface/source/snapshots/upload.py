# Copyright 2015 Google Inc. All Rights Reserved.

"""Snapshot a project repository.

TODO(danielsb) make snapshot a group with "create", "list", etc.
"""

import json
import os
from googlecloudsdk.api_lib.source import snapshot
from googlecloudsdk.calliope import base
from googlecloudsdk.core import log


class Upload(base.Command):
  """Upload a source snapshot from given input files."""

  detailed_help = {
      'DESCRIPTION': """\
          This command uploads a snapshot of the specified source directory to
          a Google-hosted Git repository accessible with the current project's
          credentials. If the name of an existing snapshot is provided, the
          existing snapshot will be modified to include the new files.
          Otherwise a new snapshot will be created to hold the files.

          When creating a snapshot, this command can also produce a source
          context json file describing the snapshot.

          See https://cloud.google.com/tools/cloud-debugger/ for details on
          where to deploy the source context json file in order to enable
          Cloud Diagnostic tools to display the snapshotted sources.

      """
  }

  @staticmethod
  def Args(parser):
    parser.add_argument(
        'source_location', metavar='PATH',
        help="""\
            The directory or archive containing the sources to snapshot. Files
            and subdirectories contained in that directory or archive will be
            added to the snapshot. If PATH refers to a file, the file may be
            a Java source jar or a zip archive.
        """)
    parser.add_argument(
        '--snapshot-id', metavar='ID',
        completion_resource='source.snapshots',
        help="""\
            The ID of the snapshot to create or modify.
        """)
    parser.add_argument(
        '--target-path', metavar='PATH', default='',
        help="""\
            The directory tree under source-location will be uploaded under
            target-path in the snapshot's directory tree.
        """)
    parser.add_argument(
        '--context-file', metavar='json-file-name',
        help="""\
            The name of the source context json file to produce. Defaults to
            source-contexts.json in the current directory. If context-file names
            a directory, the output file will be source-contexts.json in that
            directory.
        """)

  def Run(self, args):
    """Run the snapshot upload command."""

    mgr = snapshot.SnapshotManager()
    result = mgr.UploadSnapshot(args.snapshot_id, args.source_location,
                                args.target_path)
    if args.context_file:
      if os.path.isdir(args.context_file):
        json_filename = os.path.join(args.context_file, 'source-contexts.json')
      else:
        json_filename = args.context_file
    else:
      json_filename = 'source-contexts.json'
    with open(json_filename, 'w') as source_context_file:
      json.dump(result['source_contexts'], source_context_file)
    log.Print('Created context file {0}\n'.format(json_filename))
    return result

  def Display(self, args, result):
    """This method is called to print the result of the Run() method.

    Args:
      args: The arguments that command was run with.
      result: The value returned from the Run() method.
    """
    log.Print(
        ('Created source snapshot {snapshot.id}.\n'
         'Wrote {files_written} files, {size_written} bytes.\n').
        format(**result))
