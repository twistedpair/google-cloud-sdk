# Copyright 2015 Google Inc. All Rights Reserved.

"""'functions list' command."""

import sys

from googlecloudsdk.calliope import arg_parsers
from googlecloudsdk.calliope import base
from googlecloudsdk.calliope import exceptions as base_exceptions
from googlecloudsdk.core import list_printer
from googlecloudsdk.core import properties
from googlecloudsdk.third_party.apitools.base import py as apitools_base

from googlecloudsdk.functions.lib import util


class List(base.Command):
  """Lists all the functions in a given region."""

  @staticmethod
  def Args(parser):
    """Register flags for this command."""
    parser.add_argument(
        '--limit', default=None,
        help='If greater than zero, the maximum number of results.',
        type=arg_parsers.BoundedInt(1, sys.maxint))

  def Run(self, args):
    """This is what gets called when the user runs this command.

    Args:
      args: an argparse namespace. All the arguments that were provided to this
        command invocation.

    Yields:
      Objects representing user functions.
    """
    client = self.context['functions_client']
    list_generator = apitools_base.YieldFromList(
        service=client.projects_regions_functions,
        request=self.BuildRequest(args),
        limit=args.limit, field='functions',
        batch_size_attribute='pageSize')
    # Decorators (e.g. util.CatchHTTPErrorRaiseHTTPException) don't work
    # for generators. We have to catch the exception above the iteration loop,
    # but inside the function.
    try:
      for item in list_generator:
        yield item
    except apitools_base.HttpError as error:
      msg = util.GetHttpErrorMessage(error)
      unused_type, unused_value, traceback = sys.exc_info()
      raise base_exceptions.HttpException, msg, traceback

  def BuildRequest(self, args):
    """This method creates a ListRequest message to be send to GCF.

    Args:
      args: an argparse namespace. All the arguments that were provided to this
        command invocation.

    Returns:
      A ListRequest message.
    """
    messages = self.context['functions_messages']
    project = properties.VALUES.core.project.Get(required=True)
    location = 'projects/{0}/regions/{1}'.format(
        project, args.region)
    return messages.CloudfunctionsProjectsRegionsFunctionsListRequest(
        location=location)

  def Display(self, unused_args, result):
    """This method is called to print the result of the Run() method.

    Args:
      unused_args: The arguments that command was run with.
      result: The value returned from the Run() method.
    """
    list_printer.PrintResourceList('functions.projects.regions.functions',
                                   result)
