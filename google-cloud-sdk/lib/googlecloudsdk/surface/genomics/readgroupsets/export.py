# Copyright 2015 Google Inc. All Rights Reserved.

"""Implementation of gcloud genomics readgroupsets export.
"""

import sys
from googlecloudsdk.api_lib import genomics as lib
from googlecloudsdk.api_lib.genomics import genomics_util
from googlecloudsdk.calliope import arg_parsers
from googlecloudsdk.calliope import base
from googlecloudsdk.calliope import exceptions
from googlecloudsdk.third_party.apitools.base import py as apitools_base


class Export(base.Command):
  """Exports a read group set to a BAM file in cloud storage.

  Exports a read group set, optionally restricted by reference name, to a BAM
  file in a provided Google Cloud Storage object. This command yields an
  asynchronous Operation resource which tracks the completion of this task. See
  https://cloud.google.com/genomics/managing-reads for more details.
  """

  @staticmethod
  def Args(parser):
    """Register flags for this command."""
    parser.add_argument(
        'read_group_set_id',
        type=str,
        help='The ID of the read group set to export.')
    parser.add_argument(
        '--export-uri',
        type=str,
        required=True,
        help=('Google Cloud Storage URI to which the BAM file '
              '(https://samtools.github.io/hts-specs/SAMv1.pdf) should be '
              'exported.'))
    parser.add_argument(
        '--reference-names',
        type=arg_parsers.ArgList(),
        default=[],
        help=('Comma separated list of reference names to be exported from the '
              'given read group set. Provide * to export unmapped reads. By '
              'default, all reads are exported.'))

  def Run(self, args):
    """This is what gets called when the user runs this command.

    Args:
      args: an argparse namespace, All the arguments that were provided to this
        command invocation.

    Returns:
      an Operation message which tracks the asynchronous export
    """
    apitools_client = self.context[lib.GENOMICS_APITOOLS_CLIENT_KEY]
    genomics_messages = self.context[lib.GENOMICS_MESSAGES_MODULE_KEY]

    try:
      return apitools_client.readgroupsets.Export(
          genomics_messages.GenomicsReadgroupsetsExportRequest(
              readGroupSetId=args.read_group_set_id,
              exportReadGroupSetRequest=
              genomics_messages.ExportReadGroupSetRequest(
                  projectId=genomics_util.GetProjectId(),
                  exportUri=args.export_uri,
                  referenceNames=args.reference_names)
          ))
    except apitools_base.HttpError as error:
      # Map our error messages (JSON API camelCased) back into flag names.
      msg = (genomics_util.GetErrorMessage(error)
             .replace('exportUri', '--export-uri')
             .replace('referenceNames', '--reference-names'))
      unused_type, unused_value, traceback = sys.exc_info()
      raise exceptions.HttpException, msg, traceback

  def Display(self, args_unused, op):
    """This method is called to print the result of the Run() method.

    Args:
      args_unused: The arguments that command was run with.
      op: The operation message returned from the Run() method.
    """

    self.format(op)
