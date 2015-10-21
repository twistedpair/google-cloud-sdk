# Copyright 2014 Google Inc. All Rights Reserved.

"""The gen_repo_info_file command."""

from googlecloudsdk.calliope import base

from googlecloudsdk.shared.source import generate_source_context


@base.Hidden
class GenRepoInfoFile(base.Command):
  """Determines repository information and generates a file representation.

  The generated file is an opaque blob representing which source revision the
  application was built at, and which Google-hosted repository this revision
  will be pushed to.
  """

  detailed_help = {
      'EXAMPLES': """\
          To generate a repository information file for your app,
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
    parser.add_argument(
        '--output-file',
        default='source-context.json',
        help='The path to the output file containing the source context.')

  def Run(self, args):
    generate_source_context.GenerateSourceContext(
        args.source_directory, args.output_file)
