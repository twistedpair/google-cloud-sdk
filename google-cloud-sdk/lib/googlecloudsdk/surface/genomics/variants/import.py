# Copyright 2015 Google Inc. All Rights Reserved.
"""Implementation of gcloud genomics variants import.
"""
from googlecloudsdk.calliope import arg_parsers
from googlecloudsdk.calliope import base
from googlecloudsdk.shared import genomics as lib
from googlecloudsdk.shared.genomics import genomics_util


class Import(base.Command):
  """Imports variants into Google Genomics.

  Import variants from VCF or MasterVar files that are in Google Cloud Storage.
  """

  @staticmethod
  def Args(parser):
    """Register flags for this command."""
    parser.add_argument('--variantset-id',
                        type=str,
                        required=True,
                        help='The ID of the destination variant set.')
    parser.add_argument('--source-uris',
                        type=arg_parsers.ArgList(min_length=1),
                        required=True,
                        help=('A comma-delimited list of URI patterns '
                              'referencing existing VCF or MasterVar files in '
                              'Google Cloud Storage.'))
    parser.add_argument('--file-format',
                        choices=['COMPLETE_GENOMICS', 'VCF'],
                        default='VCF',
                        help=('The format of the variant data being imported. '
                              'If unspecified, defaults to VCF.'))
    parser.add_argument('--normalize-reference-names',
                        type=bool,
                        default=False,
                        help=('Convert reference names to the canonical '
                              'representation. hg19 haplotypes (those '
                              'reference names containing "_hap") are not '
                              'modified in any way. All other reference names '
                              'are modified according to the following rules: '
                              'The reference name is capitalized. '
                              'The "chr" prefix is dropped for all autosomes '
                              'and sex chromsomes. For example "chr17" '
                              'becomes "17" and "chrX" becomes "X". All '
                              'mitochondrial chromosomes ("chrM", "chrMT", '
                              'etc) become "MT".'))

  @genomics_util.ReraiseHttpException
  def Run(self, args):
    """This is what gets called when the user runs this command.

    Args:
      args: an argparse namespace, All the arguments that were provided to this
        command invocation.

    Returns:
      an ImportVariantsResponse message
    """
    apitools_client = self.context[lib.GENOMICS_APITOOLS_CLIENT_KEY]
    genomics_messages = self.context[lib.GENOMICS_MESSAGES_MODULE_KEY]

    format_enum = genomics_messages.ImportVariantsRequest.FormatValueValuesEnum
    file_format = format_enum.FORMAT_VCF
    if args.file_format == 'COMPLETE_GENOMICS':
      file_format = format_enum.FORMAT_COMPLETE_GENOMICS

    request = genomics_messages.ImportVariantsRequest(
        variantSetId=args.variantset_id,
        sourceUris=args.source_uris,
        format=file_format,
        normalizeReferenceNames=args.normalize_reference_names)
    return apitools_client.variants.Import(request)

  def Display(self, args_unused, resp):
    """This method is called to print the result of the Run() method.

    Args:
      args_unused: The arguments that command was run with.
      resp: The ImportVariantsResponse message returned from the Run() method.
    """
    self.format(resp)
