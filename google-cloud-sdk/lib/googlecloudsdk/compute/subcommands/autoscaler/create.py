# Copyright 2014 Google Inc. All Rights Reserved.
"""Command for creating autoscalers."""


from googlecloudsdk.api_lib.compute import autoscaler_utils as util
from googlecloudsdk.api_lib.compute import base_classes
from googlecloudsdk.calliope import exceptions as calliope_exceptions
from googlecloudsdk.core import list_printer
from googlecloudsdk.core import log
from googlecloudsdk.third_party.apitools.base.py import exceptions


class CreateAutoscaler(base_classes.BaseCommand):
  """Create Autoscaler instances."""

  @staticmethod
  def Args(parser):
    parser.add_argument(
        '--async',
        action='store_true',
        help='Do not wait for the operation to complete.',)
    parser.add_argument('name', help='Autoscaler name.')
    util.AddAutoscalerArgs(parser)

  def Run(self, args):
    log.warn('Please use instead [gcloud compute instance-groups '
             'managed set-autoscaling].')
    messages = self.context['autoscaler_messages_module']
    client = self.context['autoscaler-client']
    resources = self.context['autoscaler_resources']
    autoscaler_ref = resources.Parse(
        args.name, collection='autoscaler.autoscalers')
    try:
      request = messages.AutoscalerAutoscalersInsertRequest()
      request.project = autoscaler_ref.project
      request.zone = autoscaler_ref.zone
      request.autoscaler = util.PrepareAutoscaler(args, messages, resources)
      request.autoscaler.name = autoscaler_ref.autoscaler
      result = client.autoscalers.Insert(request)

      operation_ref = resources.Create(
          'autoscaler.zoneOperations',
          operation=result.name,
          autoscaler=request.autoscaler,
      )
      if args.async:
        return client.zoneOperations.Get(operation_ref.Request())
      util.WaitForOperation(client, operation_ref,
                            'Creating Autoscaler instance')
      log.CreatedResource(autoscaler_ref)
      return client.autoscalers.Get(autoscaler_ref.Request())

    except exceptions.HttpError as error:
      raise calliope_exceptions.HttpException(util.GetErrorMessage(error))
    except ValueError as error:
      raise calliope_exceptions.HttpException(error)

  def Display(self, unused_args, result):
    list_printer.PrintResourceList('autoscaler.instances', [result])
