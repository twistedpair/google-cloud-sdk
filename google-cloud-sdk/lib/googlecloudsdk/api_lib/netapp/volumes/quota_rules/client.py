# -*- coding: utf-8 -*- #
# Copyright 2025 Google LLC. All Rights Reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#    http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""Commands for interacting with the Cloud NetApp Files Quota Rules API resource."""

from apitools.base.py import list_pager
from googlecloudsdk.api_lib.netapp import constants
from googlecloudsdk.api_lib.netapp import util as netapp_api_util
from googlecloudsdk.api_lib.util import waiter
from googlecloudsdk.calliope import base
from googlecloudsdk.core import log
from googlecloudsdk.core import resources


class QuotaRulesClient(object):
  """Wrapper for working with Quota Rules in the Cloud NetApp Files API Client.
  """

  def __init__(self, release_track=base.ReleaseTrack.BETA):
    self.release_track = release_track
    if self.release_track == base.ReleaseTrack.BETA:
      self._adapter = BetaQuotaRulesAdapter()
    elif self.release_track == base.ReleaseTrack.GA:
      self._adapter = QuotaRulesAdapter()
    else:
      raise ValueError('[{}] is not a valid API version.'.format(
          netapp_api_util.VERSION_MAP[release_track]))

  @property
  def client(self):
    return self._adapter.client

  @property
  def messages(self):
    return self._adapter.messages

  def WaitForOperation(self, operation_ref):
    """Waits on the long-running operation until the done field is True.

    Args:
      operation_ref: the operation reference.

    Raises:
      waiter.OperationError: if the operation contains an error.

    Returns:
      the 'response' field of the Operation.
    """
    return waiter.WaitFor(
        waiter.CloudOperationPollerNoResources(
            self.client.projects_locations_operations), operation_ref,
        'Waiting for [{0}] to finish'.format(operation_ref.Name()))

  def CreateQuotaRule(self, quota_rule_ref, volume_ref, async_, config):
    """Create a Cloud NetApp Volume Quota Rule."""
    request = (
        self.messages.NetappProjectsLocationsVolumesQuotaRulesCreateRequest(
            parent=volume_ref,
            quotaRuleId=quota_rule_ref.Name(),
            quotaRule=config,
        )
    )
    create_op = self.client.projects_locations_volumes_quotaRules.Create(
        request
    )
    if async_:
      return create_op
    operation_ref = resources.REGISTRY.ParseRelativeName(
        create_op.name, collection=constants.OPERATIONS_COLLECTION
    )
    return self.WaitForOperation(operation_ref)

  def ParseQuotaRuleConfig(
      self,
      name=None,
      quota_rule_type=None,
      target=None,
      disk_limit_mib=None,
      description=None,
      labels=None,
  ):
    """Parses the command line arguments for Create Quota Rule into a config."""
    quota_rule = self.messages.QuotaRule()
    quota_rule.name = name
    quota_rule.type = quota_rule_type
    quota_rule.target = target
    quota_rule.diskLimitMib = disk_limit_mib
    quota_rule.description = description
    quota_rule.labels = labels
    return quota_rule

  def ListQuotaRules(self, volume_ref, limit=None):
    """List Cloud NetApp Volume Quota Rules.

    Args:
      volume_ref: The parent Volume to list Cloud Netapp Volume QuotaRules.
      limit: The number of Cloud Netapp Volume QuotaRules to limit the results
        to. This limit is passed to the server and the server does the limiting.

    Returns:
      Generator that yields the Cloud Netapp Volume QuotaRules.
    """
    request = self.messages.NetappProjectsLocationsVolumesQuotaRulesListRequest(
        parent=volume_ref
    )
    # Check for unreachable locations.
    response = self.client.projects_locations_volumes_quotaRules.List(request)
    for location in response.unreachable:
      log.warning('Location {} may be unreachable.'.format(location))
    return list_pager.YieldFromList(
        self.client.projects_locations_volumes_quotaRules,
        request,
        field=constants.QUOTA_RULE_RESOURCE,
        limit=limit,
        batch_size_attribute='pageSize',
    )

  def GetQuotaRule(self, quota_rule_ref):
    """Get a Cloud NetApp Volume Quota Rule."""
    request = self.messages.NetappProjectsLocationsVolumesQuotaRulesGetRequest(
        name=quota_rule_ref.RelativeName()
    )
    return self.client.projects_locations_volumes_quotaRules.Get(request)

  def DeleteQuotaRule(self, quota_rule_ref, async_):
    """Delete a Cloud NetApp Volume Quota Rule."""
    request = (
        self.messages.NetappProjectsLocationsVolumesQuotaRulesDeleteRequest(
            name=quota_rule_ref.RelativeName()
        )
    )
    delete_op = self.client.projects_locations_volumes_quotaRules.Delete(
        request
    )
    if async_:
      return delete_op
    operation_ref = resources.REGISTRY.ParseRelativeName(
        delete_op.name, collection=constants.OPERATIONS_COLLECTION
    )
    return self.WaitForOperation(operation_ref)

  def ParseUpdatedQuotaRuleConfig(
      self,
      quota_rule_config,
      disk_limit_mib=None,
      description=None,
      labels=None,
  ):
    """Parses updates into a quota rule config.

    Args:
      quota_rule_config: The quota rule config to update.
      disk_limit_mib: int, a new disk limit, if any.
      description: str, a new description, if any.
      labels: LabelsValue message, the new labels value, if any.

    Returns:
      The quota rule message.
    """
    if disk_limit_mib is not None:
      quota_rule_config.diskLimitMib = disk_limit_mib
    if description is not None:
      quota_rule_config.description = description
    if labels is not None:
      quota_rule_config.labels = labels
    return quota_rule_config

  def UpdateQuotaRule(self, quota_rule_ref, quota_rule, update_mask, async_):
    """Updates a Cloud NetApp Volume Quota Rule.

    Args:
      quota_rule_ref: the reference to the Quota Rule.
      quota_rule: Quota rule config, the updated quota rule.
      update_mask: str, a comma-separated list of updated fields.
      async_: bool, if False, wait for the operation to complete.

    Returns:
      an Operation or Volume message.
    """
    request = (
        self.messages.NetappProjectsLocationsVolumesQuotaRulesPatchRequest(
            name=quota_rule_ref.RelativeName(),
            updateMask=update_mask,
            quotaRule=quota_rule,
        )
    )
    update_op = self.client.projects_locations_volumes_quotaRules.Patch(request)
    if async_:
      return update_op
    operation_ref = resources.REGISTRY.ParseRelativeName(
        update_op.name, collection=constants.OPERATIONS_COLLECTION)
    return self.WaitForOperation(operation_ref)


class QuotaRulesAdapter(object):
  """Adapter for the Cloud NetApp Files API Quota Rule resource."""

  def __init__(self):
    self.release_track = base.ReleaseTrack.GA
    self.client = netapp_api_util.GetClientInstance(
        release_track=self.release_track
    )
    self.messages = netapp_api_util.GetMessagesModule(
        release_track=self.release_track
    )


class BetaQuotaRulesAdapter(QuotaRulesAdapter):
  """Adapter for the Beta Cloud NetApp Files API Quota Rule resource."""

  def __init__(self):
    super(BetaQuotaRulesAdapter, self).__init__()
    self.release_track = base.ReleaseTrack.BETA
    self.client = netapp_api_util.GetClientInstance(
        release_track=self.release_track
    )
    self.messages = netapp_api_util.GetMessagesModule(
        release_track=self.release_track
    )

