# Copyright 2014 Google Inc. All Rights Reserved.

"""The gen_repo_info_file command."""

import json
import os

from googlecloudsdk.api_lib.source import generate_source_context
from googlecloudsdk.calliope import base
from googlecloudsdk.core import log
from googlecloudsdk.core.util import files

OLD_SOURCE_CONTEXT_FILENAME = 'source-context.json'
SOURCE_CONTEXTS_FILENAME = 'source-contexts.json'


@base.Hidden
class GenRepoInfoFile(base.Command):
  """Determines repository information and generates a file representation.

  The generated file is an opaque blob representing which source revision the
  application was built at, and which Google-hosted repository this revision
  will be pushed to.
  """

  detailed_help = {
      'DESCRIPTION': """\
          This command generates two files, {old_name} and
          {contexts_filename}, containing information on the source revision
          and remote repository associated with the given source directory.

          {contexts_filename} contains information on all remote repositories
          associated with the directory, while {old_name} contains
          information only on one repository. It will refer to the associated
          Cloud Repository if there is one, or the remote Git repository if
          there is no Cloud Repository.

          {old_name} is deprecated in favor of {contexts_filename}.
          It is generated solely for compatibility with existing tools during
          the transition.
          """.format(old_name=OLD_SOURCE_CONTEXT_FILENAME,
                     contexts_filename=SOURCE_CONTEXTS_FILENAME),
      'EXAMPLES': """\
          To generate repository information files for your app,
          from your source directory run:

            $ {command}
          """,
  }

  @staticmethod
  def Args(parser):
    parser.add_argument(
        '--source-directory',
        default='.',
        help='The path to directory containing the source code for the build.')
    # TODO((b/25215149) Remove this option.
    parser.add_argument(
        '--output-file',
        help=(
            '(Deprecated; use --output-directory instead.) '
            'Specifies the full name of the output file to contain a single '
            'source context.  The file name must be "{old_name}" in '
            'order to work with cloud diagnostic tools.').format(
                old_name=OLD_SOURCE_CONTEXT_FILENAME))
    parser.add_argument(
        '--output-directory',
        default='',
        help=(
            'The directory in which to create the source context files. '
            'Defaults to the current directory, or the directory containing '
            '--output-file if that option is provided with a file name that '
            'includes a directory path.'))

  def Run(self, args):
    contexts = generate_source_context.CalculateExtendedSourceContexts(
        args.source_directory)

    # First create the old-style source-context.json file
    if args.output_file:
      log.warn(
          'The --output-file option is deprecated and will soon be removed.')
      output_directory = os.path.dirname(args.output_file)
      output_file = args.output_file
    else:
      output_directory = ''
      output_file = OLD_SOURCE_CONTEXT_FILENAME

    if not output_directory:
      if args.output_directory:
        output_directory = args.output_directory
        output_file = os.path.join(output_directory, output_file)
      else:
        output_directory = '.'

    best_context = generate_source_context.BestSourceContext(
        contexts, args.source_directory)
    files.MakeDir(output_directory)
    with open(output_file, 'w') as f:
      json.dump(best_context, f, indent=2, sort_keys=True)

    # Create the new source-contexts.json file.
    if args.output_directory and args.output_directory != output_directory:
      output_directory = args.output_directory
      files.MakeDir(output_directory)
    with open(
        os.path.join(output_directory, SOURCE_CONTEXTS_FILENAME), 'w') as f:
      json.dump(contexts, f, indent=2, sort_keys=True)
