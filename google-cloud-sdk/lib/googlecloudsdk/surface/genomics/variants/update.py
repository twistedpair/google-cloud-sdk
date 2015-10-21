# Copyright 2015 Google Inc. All Rights Reserved.
"""Implementation of gcloud genomics variants update.
"""
from googlecloudsdk.calliope import arg_parsers
from googlecloudsdk.calliope import base
from googlecloudsdk.shared import genomics as lib
from googlecloudsdk.shared.genomics import genomics_util


class Update(base.Command):
  """Updates variant names."""

  @staticmethod
  def Args(parser):
    """Register flags for this command."""
    parser.add_argument('id',
                        type=int,
                        help='The ID of the variant to be updated.')
    names = parser.add_argument(
        '--names',
        type=arg_parsers.ArgList(min_length=1),
        required=True,
        help='Comma-delimited list of new variant names.')
    names.detailed_help = 'The new variant names replace existing names.'

  @genomics_util.ReraiseHttpException
  def Run(self, args):
    """This is what gets called when the user runs this command.

    Args:
      args: an argparse namespace, All the arguments that were provided to this
        command invocation.

    Returns:
      a Variant message
    """
    apitools_client = self.context[lib.GENOMICS_APITOOLS_CLIENT_KEY]
    genomics_messages = self.context[lib.GENOMICS_MESSAGES_MODULE_KEY]

    variant = genomics_messages.Variant(names=args.names,)
    request = genomics_messages.GenomicsVariantsPatchRequest(
        updateMask='names',
        variant=variant,
        variantId=str(args.id),)

    return apitools_client.variants.Patch(request)

  def Display(self, args_unused, variant):
    """This method is called to print the result of the Run() method.

    Args:
      args_unused: The arguments that command was run with.
      variant: The Variant message returned from the Run() method.
    """
    self.format(variant)
