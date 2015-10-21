# Copyright 2014 Google Inc. All Rights Reserved.
"""Command for getting autoscalers."""

# TODO(user): Rename get command to describe to be consistent with compute.

from googlecloudsdk.calliope import exceptions as calliope_exceptions
from googlecloudsdk.core import log
from googlecloudsdk.shared.compute import autoscaler_utils as util
from googlecloudsdk.shared.compute import base_classes
from googlecloudsdk.third_party.apitools.base import py as apitools_base


def UtilizationTargetTypeForItem(item):
  if hasattr(item, 'utilizationTargetType') and item.utilizationTargetType:
    return item.utilizationTargetType
  return ''


class GetAutoscaler(base_classes.BaseCommand):
  """Get Autoscaler instances."""

  @staticmethod
  def Args(parser):
    parser.add_argument('name', help='Autoscaler name.')

  def Run(self, args):
    log.warn('Please use instead [gcloud compute instance-groups '
             'managed describe].')
    client = self.context['autoscaler-client']
    messages = self.context['autoscaler_messages_module']
    resources = self.context['autoscaler_resources']
    autoscaler_ref = resources.Parse(
        args.name, collection='autoscaler.autoscalers')
    request = messages.AutoscalerAutoscalersGetRequest()
    request.project = autoscaler_ref.project
    request.zone = autoscaler_ref.zone
    request.autoscaler = autoscaler_ref.autoscaler

    try:
      return client.autoscalers.Get(request)

    except apitools_base.exceptions.HttpError as error:
      raise calliope_exceptions.HttpException(util.GetErrorMessage(error))

  def Display(self, unused_args, result):
    self.format(result)
