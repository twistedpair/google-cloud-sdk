# Copyright 2014 Google Inc. All Rights Reserved.
"""Command for listing autoscalers."""

from googlecloudsdk.calliope import exceptions as calliope_exceptions
from googlecloudsdk.core import list_printer
from googlecloudsdk.core import log
from googlecloudsdk.core import properties
from googlecloudsdk.shared.compute import autoscaler_utils as util
from googlecloudsdk.shared.compute import base_classes
from googlecloudsdk.third_party.apitools.base import py as apitools_base
from googlecloudsdk.third_party.apitools.base.py import exceptions


class ListAutoscalers(base_classes.BaseCommand):
  """List Autoscaler instances."""

  # TODO(user): Add --limit flag.
  def Run(self, args):
    log.warn('Please use instead [gcloud compute instance-groups '
             'managed list].')
    client = self.context['autoscaler-client']
    messages = self.context['autoscaler_messages_module']
    resources = self.context['autoscaler_resources']
    try:
      request = messages.AutoscalerAutoscalersListRequest()
      request.project = properties.VALUES.core.project.Get(required=True)
      request.zone = resources.Parse(
          args.zone, collection='compute.zones').zone
      return apitools_base.YieldFromList(client.autoscalers, request)

    except exceptions.HttpError as error:
      raise calliope_exceptions.HttpException(util.GetErrorMessage(error))
    except ValueError as error:
      raise calliope_exceptions.HttpException(error)

  def Display(self, unused_args, result):
    list_printer.PrintResourceList('autoscaler.instances', result)
