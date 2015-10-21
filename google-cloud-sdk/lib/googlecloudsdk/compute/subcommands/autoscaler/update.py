# Copyright 2014 Google Inc. All Rights Reserved.
"""Command for updating autoscalers."""

from googlecloudsdk.calliope import exceptions as calliope_exceptions
from googlecloudsdk.core import log
from googlecloudsdk.shared.compute import autoscaler_utils as util
from googlecloudsdk.shared.compute import base_classes
from googlecloudsdk.third_party.apitools.base.py import exceptions


class UpdateAutoscaler(base_classes.BaseCommand):  # BaseAsyncMutator
  """Update Autoscaler instances."""

  @staticmethod
  def Args(parser):
    util.AddAutoscalerArgs(parser)
    parser.add_argument('name', help='Autoscaler name.')

  def Run(self, args):
    log.warn('Please use instead [gcloud compute instance-groups '
             'managed set-autoscaling].')
    client = self.context['autoscaler-client']
    messages = self.context['autoscaler_messages_module']
    resources = self.context['autoscaler_resources']
    try:
      autoscaler_ref = resources.Parse(
          args.name, collection='autoscaler.autoscalers')
      request = messages.AutoscalerAutoscalersUpdateRequest()
      request.project = autoscaler_ref.project
      request.zone = autoscaler_ref.zone
      request.autoscaler = autoscaler_ref.autoscaler
      request.autoscalerResource = util.PrepareAutoscaler(
          args, messages, resources)
      request.autoscalerResource.name = autoscaler_ref.autoscaler
      result = client.autoscalers.Update(request)
      if result.error:
        raise exceptions.Error(util.GetErrorMessage(result.error))
      operation_ref = resources.Create(
          'autoscaler.zoneOperations',
          operation=result.name,
          autoscaler=request.autoscaler,
      )
      util.WaitForOperation(client, operation_ref,
                            'Updating Autoscaler instance')
      log.status.write('Updated [{0}].\n'.format(args.name))

    except exceptions.HttpError as error:
      raise calliope_exceptions.HttpException(util.GetErrorMessage(error))
    except ValueError as error:
      raise calliope_exceptions.HttpException(error)
