# -*- coding: utf-8 -*- #
# Copyright 2018 Google LLC. All Rights Reserved.
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
"""Shared utilities for access the CloudAsset API client."""

from __future__ import absolute_import
from __future__ import division
from __future__ import unicode_literals

from apitools.base.py import encoding
from apitools.base.py import exceptions as apitools_exceptions
from apitools.base.py import list_pager

from googlecloudsdk.api_lib.util import apis
from googlecloudsdk.api_lib.util import exceptions
from googlecloudsdk.calliope import exceptions as gcloud_exceptions
from googlecloudsdk.command_lib.asset import utils as asset_utils
from googlecloudsdk.command_lib.util.apis import arg_utils
from googlecloudsdk.command_lib.util.args import repeated
from googlecloudsdk.core import exceptions as core_exceptions
from googlecloudsdk.core import log
from googlecloudsdk.core.util import times

import six

API_NAME = 'cloudasset'
DEFAULT_API_VERSION = 'v1'
V1P1BETA1_API_VERSION = 'v1p1beta1'
V1P4BETA1_API_VERSION = 'v1p4beta1'
V1P5BETA1_API_VERSION = 'v1p5beta1'
V1P7BETA1_API_VERSION = 'v1p7beta1'
_HEADERS = {
    'Content-Type': 'application/x-www-form-urlencoded',
    'X-HTTP-Method-Override': 'GET'
}
_HTTP_ERROR_FORMAT = ('HTTP request failed with status code {}. '
                      'Response content: {}')
# A dictionary that captures version differences for IAM Policy Analyzer.
_IAM_POLICY_ANALYZER_VERSION_DICT_JSON = {
    V1P4BETA1_API_VERSION: {
        'resource_selector': 'analysisQuery_resourceSelector',
        'identity_selector': 'analysisQuery_identitySelector',
        'access_selector': 'analysisQuery_accessSelector',
        'options': 'options',
    },
    DEFAULT_API_VERSION: {
        'resource_selector': 'analysisQuery_resourceSelector',
        'identity_selector': 'analysisQuery_identitySelector',
        'access_selector': 'analysisQuery_accessSelector',
        'condition_context': 'analysisQuery_conditionContext',
        'options': 'analysisQuery_options',
    },
}


class MessageDecodeError(core_exceptions.Error):
  """Error raised when a failure to decode a message occurs."""


def GetMessages(version=DEFAULT_API_VERSION):
  """Import and return the cloudasset messages module.

  Args:
    version: the API version

  Returns:
    cloudasset message module.
  """
  return apis.GetMessagesModule(API_NAME, version)


def GetClient(version=DEFAULT_API_VERSION):
  """Import and return the cloudasset client module.

  Args:
    version: the API version

  Returns:
    cloudasset API client module.
  """
  return apis.GetClientInstance(API_NAME, version)


def ContentTypeTranslation(content_type):
  """Translate content type from gcloud format to API format.

  Args:
    content_type: the gcloud format of content_type

  Returns:
    cloudasset API format of content_type.
  """
  if content_type == 'resource':
    return 'RESOURCE'
  if content_type == 'iam-policy':
    return 'IAM_POLICY'
  if content_type == 'org-policy':
    return 'ORG_POLICY'
  if content_type == 'access-policy':
    return 'ACCESS_POLICY'
  if content_type == 'os-inventory':
    return 'OS_INVENTORY'
  if content_type == 'relationship':
    return 'RELATIONSHIP'
  return 'CONTENT_TYPE_UNSPECIFIED'


def PartitionKeyTranslation(partition_key):
  if partition_key == 'read-time':
    return 'READ_TIME'
  if partition_key == 'request-time':
    return 'REQUEST_TIME'
  return 'PARTITION_KEY_UNSPECIFIED'


def MakeGetAssetsHistoryHttpRequests(args,
                                     service,
                                     api_version=DEFAULT_API_VERSION):
  """Manually make the get assets history request."""
  messages = GetMessages(api_version)

  encoding.AddCustomJsonFieldMapping(
      messages.CloudassetBatchGetAssetsHistoryRequest,
      'readTimeWindow_startTime', 'readTimeWindow.startTime')
  encoding.AddCustomJsonFieldMapping(
      messages.CloudassetBatchGetAssetsHistoryRequest, 'readTimeWindow_endTime',
      'readTimeWindow.endTime')

  content_type = arg_utils.ChoiceToEnum(
      args.content_type, messages.CloudassetBatchGetAssetsHistoryRequest
      .ContentTypeValueValuesEnum)
  parent = asset_utils.GetParentNameForGetHistory(args.organization,
                                                  args.project)
  start_time = times.FormatDateTime(args.start_time)
  end_time = None
  if args.IsSpecified('end_time'):
    end_time = times.FormatDateTime(args.end_time)

  response = service.BatchGetAssetsHistory(
      messages.CloudassetBatchGetAssetsHistoryRequest(
          assetNames=args.asset_names,
          relationshipTypes=args.relationship_types,
          contentType=content_type,
          parent=parent,
          readTimeWindow_endTime=end_time,
          readTimeWindow_startTime=start_time,
      ))

  for asset in response.assets:
    yield asset


def _RenderAnalysisforAnalyzeIamPolicy(analysis,
                                       api_version=DEFAULT_API_VERSION):
  """Renders the analysis query and results of the AnalyzeIamPolicy request."""

  for analysis_result in analysis.analysisResults:
    entry = {}

    policy = {
        'attachedResource': analysis_result.attachedResourceFullName,
        'binding': analysis_result.iamBinding,
    }
    entry['policy'] = policy

    entry['ACLs'] = []
    for acl in analysis_result.accessControlLists:
      acls = {}
      acls['identities'] = analysis_result.identityList.identities
      acls['accesses'] = acl.accesses
      acls['resources'] = acl.resources
      if api_version == DEFAULT_API_VERSION and acl.conditionEvaluation:
        acls[
            'conditionEvaluationValue'] = acl.conditionEvaluation.evaluationValue
      entry['ACLs'].append(acls)

    yield entry


def _RenderResponseforAnalyzeIamPolicy(response,
                                       analyze_service_account_impersonation,
                                       api_version=DEFAULT_API_VERSION):
  """Renders the response of the AnalyzeIamPolicy request."""

  if response.fullyExplored:
    msg = 'Your analysis request is fully explored. '
  else:
    msg = ('Your analysis request is NOT fully explored. You can use the '
           '--show-response option to see the unexplored part. ')

  has_results = False
  if response.mainAnalysis.analysisResults:
    has_results = True
  if (not has_results) and analyze_service_account_impersonation:
    for sa_impersonation_analysis in response.serviceAccountImpersonationAnalysis:
      if sa_impersonation_analysis.analysisResults:
        has_results = True
        break

  if not has_results:
    msg += 'No matching ACL is found.'
  else:
    msg += ('The ACLs matching your requests are listed per IAM policy binding'
            ', so there could be duplications.')

  for entry in _RenderAnalysisforAnalyzeIamPolicy(response.mainAnalysis,
                                                  api_version):
    yield entry

  if analyze_service_account_impersonation:
    for analysis in response.serviceAccountImpersonationAnalysis:
      title = {
          'Service Account Impersonation Analysis Query': analysis.analysisQuery
      }
      yield title
      for entry in _RenderAnalysisforAnalyzeIamPolicy(analysis, api_version):
        yield entry

  log.status.Print(msg)


def MakeAnalyzeIamPolicyHttpRequests(args,
                                     service,
                                     messages,
                                     api_version=DEFAULT_API_VERSION):
  """Manually make the analyze IAM policy request."""
  parent = asset_utils.GetParentNameForAnalyzeIamPolicy(args.organization,
                                                        args.project,
                                                        args.folder)

  full_resource_name = args.full_resource_name if args.IsSpecified(
      'full_resource_name') else None

  identity = args.identity if args.IsSpecified('identity') else None

  roles = args.roles if args.IsSpecified('roles') else []

  permissions = args.permissions if args.IsSpecified('permissions') else []

  expand_groups = args.expand_groups if args.expand_groups else None

  expand_resources = args.expand_resources if args.expand_resources else None

  expand_roles = args.expand_roles if args.expand_roles else None

  analyze_service_account_impersonation = args.analyze_service_account_impersonation if args.analyze_service_account_impersonation else None

  output_resource_edges = None
  if args.output_resource_edges:
    if not args.show_response:
      raise gcloud_exceptions.InvalidArgumentException(
          '--output-resource-edges',
          'Must be set together with --show-response to take effect.')
    output_resource_edges = args.output_resource_edges

  output_group_edges = None
  if args.output_group_edges:
    if not args.show_response:
      raise gcloud_exceptions.InvalidArgumentException(
          '--output-group-edges',
          'Must be set together with --show-response to take effect.')
    output_group_edges = args.output_group_edges

  execution_timeout = None
  if args.IsSpecified('execution_timeout'):
    execution_timeout = str(args.execution_timeout) + 's'

  if api_version == V1P4BETA1_API_VERSION:
    response = service.AnalyzeIamPolicy(
        messages.CloudassetAnalyzeIamPolicyRequest(
            analysisQuery_accessSelector_permissions=permissions,
            analysisQuery_accessSelector_roles=roles,
            analysisQuery_identitySelector_identity=identity,
            analysisQuery_resourceSelector_fullResourceName=full_resource_name,
            options_analyzeServiceAccountImpersonation=analyze_service_account_impersonation,
            options_executionTimeout=execution_timeout,
            options_expandGroups=expand_groups,
            options_expandResources=expand_resources,
            options_expandRoles=expand_roles,
            options_outputGroupEdges=output_group_edges,
            options_outputResourceEdges=output_resource_edges,
            parent=parent,
        ))
  else:
    access_time = None
    if args.IsSpecified('access_time'):
      access_time = times.FormatDateTime(args.access_time)

    response = service.AnalyzeIamPolicy(
        messages.CloudassetAnalyzeIamPolicyRequest(
            analysisQuery_accessSelector_permissions=permissions,
            analysisQuery_accessSelector_roles=roles,
            analysisQuery_identitySelector_identity=identity,
            analysisQuery_options_analyzeServiceAccountImpersonation=analyze_service_account_impersonation,
            analysisQuery_options_expandGroups=expand_groups,
            analysisQuery_options_expandResources=expand_resources,
            analysisQuery_options_expandRoles=expand_roles,
            analysisQuery_options_outputGroupEdges=output_group_edges,
            analysisQuery_options_outputResourceEdges=output_resource_edges,
            analysisQuery_resourceSelector_fullResourceName=full_resource_name,
            analysisQuery_conditionContext_accessTime=access_time,
            executionTimeout=execution_timeout,
            scope=parent,
        ))
  if not args.show_response:
    return _RenderResponseforAnalyzeIamPolicy(
        response, analyze_service_account_impersonation, api_version)
  return response


class AnalyzeIamPolicyClient(object):
  """Client for IAM policy analysis."""

  def __init__(self, api_version=DEFAULT_API_VERSION):
    self.api_version = api_version
    self.client = GetClient(api_version)

    if api_version == V1P4BETA1_API_VERSION:
      self.service = self.client.v1p4beta1
    else:
      self.service = self.client.v1

  def Analyze(self, args):
    """Calls MakeAnalyzeIamPolicy method."""
    messages = self.EncodeMessages(args)
    return MakeAnalyzeIamPolicyHttpRequests(args, self.service, messages,
                                            self.api_version)

  def EncodeMessages(self, args):
    """Adds custom encoding for MakeAnalyzeIamPolicy request."""
    messages = GetMessages(self.api_version)

    def AddCustomJsonFieldMapping(prefix, suffix):
      field = _IAM_POLICY_ANALYZER_VERSION_DICT_JSON[
          self.api_version][prefix] + suffix
      encoding.AddCustomJsonFieldMapping(
          messages.CloudassetAnalyzeIamPolicyRequest,
          field,
          field.replace('_', '.'),
      )

    AddCustomJsonFieldMapping('resource_selector', '_fullResourceName')
    AddCustomJsonFieldMapping('identity_selector', '_identity')
    AddCustomJsonFieldMapping('access_selector', '_roles')
    AddCustomJsonFieldMapping('access_selector', '_permissions')
    AddCustomJsonFieldMapping('options', '_expandGroups')
    AddCustomJsonFieldMapping('options', '_expandResources')
    AddCustomJsonFieldMapping('options', '_expandRoles')
    AddCustomJsonFieldMapping('options', '_outputResourceEdges')
    AddCustomJsonFieldMapping('options', '_outputGroupEdges')
    AddCustomJsonFieldMapping('options', '_analyzeServiceAccountImpersonation')

    if self.api_version == V1P4BETA1_API_VERSION and args.IsSpecified(
        'execution_timeout'):
      AddCustomJsonFieldMapping('options', '_executionTimeout')

    if self.api_version == DEFAULT_API_VERSION and args.IsSpecified(
        'access_time'):
      AddCustomJsonFieldMapping('condition_context', '_accessTime')

    return messages


class AssetExportClient(object):
  """Client for export asset."""

  def __init__(self, parent, client=None):
    self.parent = parent
    self.api_version = DEFAULT_API_VERSION
    self.message_module = GetMessages(self.api_version)
    self.service = client.v1 if client else GetClient(self.api_version).v1

  def Export(self, args):
    """Export assets with the asset export method."""
    content_type = ContentTypeTranslation(args.content_type)
    partition_key = PartitionKeyTranslation(args.partition_key)
    partition_key = getattr(
        self.message_module.PartitionSpec.PartitionKeyValueValuesEnum,
        partition_key)
    if args.output_path or args.output_path_prefix:
      output_config = self.message_module.OutputConfig(
          gcsDestination=self.message_module.GcsDestination(
              uri=args.output_path, uriPrefix=args.output_path_prefix))
    else:
      source_ref = args.CONCEPTS.bigquery_table.Parse()
      output_config = self.message_module.OutputConfig(
          bigqueryDestination=self.message_module.BigQueryDestination(
              dataset='projects/' + source_ref.projectId + '/datasets/' +
              source_ref.datasetId,
              table=source_ref.tableId,
              force=args.force_,
              partitionSpec=self.message_module.PartitionSpec(
                  partitionKey=partition_key),
              separateTablesPerAssetType=args.per_type_))
    snapshot_time = None
    if args.snapshot_time:
      snapshot_time = times.FormatDateTime(args.snapshot_time)
    content_type = getattr(
        self.message_module.ExportAssetsRequest.ContentTypeValueValuesEnum,
        content_type)
    export_assets_request = self.message_module.ExportAssetsRequest(
        assetTypes=args.asset_types,
        contentType=content_type,
        outputConfig=output_config,
        readTime=snapshot_time,
        relationshipTypes=args.relationship_types)
    request_message = self.message_module.CloudassetExportAssetsRequest(
        parent=self.parent, exportAssetsRequest=export_assets_request)
    try:
      operation = self.service.ExportAssets(request_message)
    except apitools_exceptions.HttpBadRequestError as bad_request:
      raise exceptions.HttpException(bad_request, error_format='{error_info}')
    except apitools_exceptions.HttpForbiddenError as permission_deny:
      raise exceptions.HttpException(
          permission_deny, error_format='{error_info}')
    return operation


class AssetFeedClient(object):
  """Client for asset feed."""

  def __init__(self, parent, api_version=DEFAULT_API_VERSION):
    self.parent = parent
    self.message_module = GetMessages(api_version)
    self.service = GetClient(api_version).feeds

  def Create(self, args):
    """Create a feed."""
    content_type = ContentTypeTranslation(args.content_type)
    content_type = getattr(self.message_module.Feed.ContentTypeValueValuesEnum,
                           content_type)
    feed_output_config = self.message_module.FeedOutputConfig(
        pubsubDestination=self.message_module.PubsubDestination(
            topic=args.pubsub_topic))
    feed_condition = self.message_module.Expr(
        expression=args.condition_expression,
        title=args.condition_title,
        description=args.condition_description)
    feed = self.message_module.Feed(
        assetNames=args.asset_names,
        assetTypes=args.asset_types,
        contentType=content_type,
        feedOutputConfig=feed_output_config,
        condition=feed_condition,
        relationshipTypes=args.relationship_types)
    create_feed_request = self.message_module.CreateFeedRequest(
        feed=feed, feedId=args.feed)
    request_message = self.message_module.CloudassetFeedsCreateRequest(
        parent=self.parent, createFeedRequest=create_feed_request)
    return self.service.Create(request_message)

  def Describe(self, args):
    """Describe a feed."""
    request_message = self.message_module.CloudassetFeedsGetRequest(
        name='{}/feeds/{}'.format(self.parent, args.feed))
    return self.service.Get(request_message)

  def Delete(self, args):
    """Delete a feed."""
    request_message = self.message_module.CloudassetFeedsDeleteRequest(
        name='{}/feeds/{}'.format(self.parent, args.feed))
    self.service.Delete(request_message)

  def List(self):
    """List feeds under a parent."""
    request_message = self.message_module.CloudassetFeedsListRequest(
        parent=self.parent)
    return self.service.List(request_message)

  def Update(self, args):
    """Update a feed."""
    update_masks = []
    content_type = ContentTypeTranslation(args.content_type)
    content_type = getattr(self.message_module.Feed.ContentTypeValueValuesEnum,
                           content_type)
    feed_name = '{}/feeds/{}'.format(self.parent, args.feed)
    if args.content_type or args.clear_content_type:
      update_masks.append('content_type')
    if args.pubsub_topic:
      update_masks.append('feed_output_config.pubsub_destination.topic')
    if args.condition_expression or args.clear_condition_expression:
      update_masks.append('condition.expression')
    if args.condition_title or args.clear_condition_title:
      update_masks.append('condition.title')
    if args.condition_description or args.clear_condition_description:
      update_masks.append('condition.description')
    asset_names, asset_types, relationship_types = self.UpdateAssetNamesTypesAndRelationships(
        args, feed_name, update_masks)
    update_mask = ','.join(update_masks)
    feed_output_config = self.message_module.FeedOutputConfig(
        pubsubDestination=self.message_module.PubsubDestination(
            topic=args.pubsub_topic))
    feed_condition = self.message_module.Expr(
        expression=args.condition_expression,
        title=args.condition_title,
        description=args.condition_description)
    feed = self.message_module.Feed(
        assetNames=asset_names,
        assetTypes=asset_types,
        contentType=content_type,
        feedOutputConfig=feed_output_config,
        condition=feed_condition,
        relationshipTypes=relationship_types)
    update_feed_request = self.message_module.UpdateFeedRequest(
        feed=feed, updateMask=update_mask)
    request_message = self.message_module.CloudassetFeedsPatchRequest(
        name=feed_name, updateFeedRequest=update_feed_request)
    return self.service.Patch(request_message)

  def UpdateAssetNamesTypesAndRelationships(self, args, feed_name,
                                            update_masks):
    """Get Updated assetNames, assetTypes and relationshipTypes."""
    feed = self.service.Get(
        self.message_module.CloudassetFeedsGetRequest(name=feed_name))
    asset_names = repeated.ParsePrimitiveArgs(args, 'asset_names',
                                              lambda: feed.assetNames)
    if asset_names is not None:
      update_masks.append('asset_names')
    else:
      asset_names = []
    asset_types = repeated.ParsePrimitiveArgs(args, 'asset_types',
                                              lambda: feed.assetTypes)
    if asset_types is not None:
      update_masks.append('asset_types')
    else:
      asset_types = []
    relationship_types = repeated.ParsePrimitiveArgs(
        args, 'relationship_types', lambda: feed.relationshipTypes)
    if relationship_types is not None:
      update_masks.append('relationship_types')
    else:
      relationship_types = []
    return asset_names, asset_types, relationship_types


class AssetSearchClient(object):
  """Client for search assets."""

  _DEFAULT_PAGE_SIZE = 20

  def __init__(self, api_version):
    self.message_module = GetMessages(api_version)
    self.api_version = api_version
    if api_version == V1P1BETA1_API_VERSION:
      self.resource_service = GetClient(api_version).resources
      self.search_all_resources_method = 'SearchAll'
      self.search_all_resources_request = self.message_module.CloudassetResourcesSearchAllRequest
      self.policy_service = GetClient(api_version).iamPolicies
      self.search_all_iam_policies_method = 'SearchAll'
      self.search_all_iam_policies_request = self.message_module.CloudassetIamPoliciesSearchAllRequest
    else:
      self.resource_service = GetClient(api_version).v1
      self.search_all_resources_method = 'SearchAllResources'
      self.search_all_resources_request = self.message_module.CloudassetSearchAllResourcesRequest
      self.policy_service = GetClient(api_version).v1
      self.search_all_iam_policies_method = 'SearchAllIamPolicies'
      self.search_all_iam_policies_request = self.message_module.CloudassetSearchAllIamPoliciesRequest

  def SearchAllResources(self, args):
    """Calls SearchAllResources method."""
    if self.api_version == V1P1BETA1_API_VERSION:
      optional_extra_args = {}
    else:
      optional_extra_args = {'readMask': args.read_mask}
    request = self.search_all_resources_request(
        scope=asset_utils.GetDefaultScopeIfEmpty(args),
        query=args.query,
        assetTypes=args.asset_types,
        orderBy=args.order_by,
        **optional_extra_args)
    return list_pager.YieldFromList(
        self.resource_service,
        request,
        method=self.search_all_resources_method,
        field='results',
        batch_size=args.page_size or self._DEFAULT_PAGE_SIZE,
        batch_size_attribute='pageSize',
        current_token_attribute='pageToken',
        next_token_attribute='nextPageToken')

  def SearchAllIamPolicies(self, args):
    """Calls SearchAllIamPolicies method."""
    if self.api_version == V1P1BETA1_API_VERSION:
      request = self.search_all_iam_policies_request(
          scope=asset_utils.GetDefaultScopeIfEmpty(args), query=args.query)
    else:
      request = self.search_all_iam_policies_request(
          scope=asset_utils.GetDefaultScopeIfEmpty(args),
          query=args.query,
          assetTypes=args.asset_types,
          orderBy=args.order_by)
    return list_pager.YieldFromList(
        self.policy_service,
        request,
        method=self.search_all_iam_policies_method,
        field='results',
        batch_size=args.page_size or self._DEFAULT_PAGE_SIZE,
        batch_size_attribute='pageSize',
        current_token_attribute='pageToken',
        next_token_attribute='nextPageToken')


class AssetListClient(object):
  """Client for list assets."""

  def __init__(self, parent, api_version=DEFAULT_API_VERSION):
    self.parent = parent
    self.message_module = GetMessages(api_version)
    self.service = GetClient(api_version).assets

  def List(self, args, do_filter=False):
    """List assets with the asset list method."""
    snapshot_time = None
    if args.snapshot_time:
      snapshot_time = times.FormatDateTime(args.snapshot_time)
    content_type = ContentTypeTranslation(args.content_type)
    list_assets_request = self.message_module.CloudassetAssetsListRequest(
        parent=self.parent,
        contentType=getattr(
            self.message_module.CloudassetAssetsListRequest
            .ContentTypeValueValuesEnum, content_type),
        assetTypes=args.asset_types,
        readTime=snapshot_time,
        relationshipTypes=args.relationship_types)
    return list_pager.YieldFromList(
        self.service,
        list_assets_request,
        field='assets',
        limit=args.limit,
        batch_size=args.page_size,
        batch_size_attribute='pageSize',
        current_token_attribute='pageToken',
        next_token_attribute='nextPageToken',
        predicate=args.filter_func if do_filter else None)


class AssetOperationClient(object):
  """Client for operations."""

  def __init__(self, api_version=DEFAULT_API_VERSION):
    self.service = GetClient(api_version).operations
    self.message = GetMessages(api_version).CloudassetOperationsGetRequest

  def Get(self, name):
    request = self.message(name=name)
    return self.service.Get(request)


class GetHistoryClient(object):
  """Client for get history assets."""

  def __init__(self, api_version=DEFAULT_API_VERSION):
    self.api_version = api_version
    self.client = GetClient(api_version)
    self.service = self.client.v1

  def GetHistory(self, args):
    return MakeGetAssetsHistoryHttpRequests(args, self.service,
                                            self.api_version)


class IamPolicyAnalysisLongrunningClient(object):
  """Client for analyze IAM policy asynchronously."""

  def __init__(self, api_version=DEFAULT_API_VERSION):
    self.message_module = GetMessages(api_version)
    if api_version == V1P4BETA1_API_VERSION:
      self.service = GetClient(api_version).v1p4beta1
    else:
      self.service = GetClient(api_version).v1

  def Analyze(self, scope, args, api_version=DEFAULT_API_VERSION):
    """Analyze IAM Policy asynchronously."""
    analysis_query = self.message_module.IamPolicyAnalysisQuery()
    if api_version == V1P4BETA1_API_VERSION:
      analysis_query.parent = scope
    else:
      analysis_query.scope = scope
    if args.IsSpecified('full_resource_name'):
      analysis_query.resourceSelector = self.message_module.ResourceSelector(
          fullResourceName=args.full_resource_name)
    if args.IsSpecified('identity'):
      analysis_query.identitySelector = self.message_module.IdentitySelector(
          identity=args.identity)
    if args.IsSpecified('roles') or args.IsSpecified('permissions'):
      analysis_query.accessSelector = self.message_module.AccessSelector()
      if args.IsSpecified('roles'):
        analysis_query.accessSelector.roles.extend(args.roles)
      if args.IsSpecified('permissions'):
        analysis_query.accessSelector.permissions.extend(args.permissions)

    output_config = None
    if api_version == V1P4BETA1_API_VERSION:
      output_config = self.message_module.IamPolicyAnalysisOutputConfig(
          gcsDestination=self.message_module.GcsDestination(
              uri=args.output_path))
    else:
      if args.gcs_output_path:
        output_config = self.message_module.IamPolicyAnalysisOutputConfig(
            gcsDestination=self.message_module.GoogleCloudAssetV1GcsDestination(
                uri=args.gcs_output_path))
      else:
        output_config = self.message_module.IamPolicyAnalysisOutputConfig(
            bigqueryDestination=self.message_module
            .GoogleCloudAssetV1BigQueryDestination(
                dataset=args.bigquery_dataset,
                tablePrefix=args.bigquery_table_prefix))
        if args.IsSpecified('bigquery_partition_key'):
          output_config.bigqueryDestination.partitionKey = getattr(
              self.message_module.GoogleCloudAssetV1BigQueryDestination
              .PartitionKeyValueValuesEnum, args.bigquery_partition_key)
        if args.IsSpecified('bigquery_write_disposition'):
          output_config.bigqueryDestination.writeDisposition = args.bigquery_write_disposition

    options = self.message_module.Options()
    if args.expand_groups:
      options.expandGroups = args.expand_groups
    if args.expand_resources:
      options.expandResources = args.expand_resources
    if args.expand_roles:
      options.expandRoles = args.expand_roles
    if args.output_resource_edges:
      options.outputResourceEdges = args.output_resource_edges
    if args.output_group_edges:
      options.outputGroupEdges = args.output_group_edges
    if args.analyze_service_account_impersonation:
      options.analyzeServiceAccountImpersonation = args.analyze_service_account_impersonation

    operation = None
    if api_version == V1P4BETA1_API_VERSION:
      request = self.message_module.ExportIamPolicyAnalysisRequest(
          analysisQuery=analysis_query,
          options=options,
          outputConfig=output_config)
      request_message = self.message_module.CloudassetExportIamPolicyAnalysisRequest(
          parent=scope, exportIamPolicyAnalysisRequest=request)
      operation = self.service.ExportIamPolicyAnalysis(request_message)
    else:
      analysis_query.options = options
      if args.IsSpecified('access_time'):
        analysis_query.conditionContext = self.message_module.ConditionContext(
            accessTime=times.FormatDateTime(args.access_time))
      request = self.message_module.AnalyzeIamPolicyLongrunningRequest(
          analysisQuery=analysis_query, outputConfig=output_config)
      request_message = self.message_module.CloudassetAnalyzeIamPolicyLongrunningRequest(
          scope=scope, analyzeIamPolicyLongrunningRequest=request)
      operation = self.service.AnalyzeIamPolicyLongrunning(request_message)

    return operation


class AnalyzeMoveClient(object):
  """Client for analyzing resource move."""

  def __init__(self, api_version=DEFAULT_API_VERSION):
    self.api_version = api_version
    self.message_module = GetMessages(api_version)
    self.service = GetClient(api_version).v1

  def AnalyzeMove(self, args):
    """Analyze resource move."""
    project = 'projects/' + args.project

    if args.IsSpecified('destination_folder'):
      destination = 'folders/' + args.destination_folder
    else:
      destination = 'organizations/' + args.destination_organization

    scope = self.message_module.CloudassetAnalyzeMoveRequest.ViewValueValuesEnum.FULL
    if args.blockers_only:
      scope = self.message_module.CloudassetAnalyzeMoveRequest.ViewValueValuesEnum.BASIC

    request_message = self.message_module.CloudassetAnalyzeMoveRequest(
        destinationParent=destination, resource=project, view=scope)

    return self.service.AnalyzeMove(request_message)


class AssetQueryClient(object):
  """Client for QueryAsset API."""

  def __init__(self, parent, api_version=DEFAULT_API_VERSION):
    self.parent = parent
    self.message_module = GetMessages(api_version)
    self.service = GetClient(api_version).v1

  def Query(self, args):
    """Make QueryAssets request."""
    timeout = None
    if args.IsSpecified('timeout'):
      timeout = six.text_type(args.timeout) + 's'
    query_assets_request = self.message_module.CloudassetQueryAssetsRequest(
        parent=self.parent,
        queryAssetsRequest=self.message_module.QueryAssetsRequest(
            jobReference=args.job_reference,
            pageSize=args.page_size,
            pageToken=args.page_token,
            statement=args.statement,
            timeout=timeout))
    return self.service.QueryAssets(query_assets_request)


class OrgPolicyAnalyzerClient(object):
  """Client for org policy analysis."""

  _DEFAULT_PAGE_SIZE = 100

  def __init__(self, api_version=DEFAULT_API_VERSION):
    self.message_module = GetMessages(api_version)
    self.service = GetClient(api_version).v1

  def AnalyzeOrgPolicyGovernedResources(self, args):
    """Calls AnalyzeOrgPolicyGovernedResources method."""
    request = self.message_module.CloudassetAnalyzeOrgPolicyGovernedResourcesRequest(
        scope=args.scope, constraint=args.constraint)
    return list_pager.YieldFromList(
        self.service,
        request,
        method='AnalyzeOrgPolicyGovernedResources',
        field='governedResources',
        limit=args.limit,
        batch_size=args.page_size or self._DEFAULT_PAGE_SIZE,
        batch_size_attribute='pageSize',
        current_token_attribute='pageToken',
        next_token_attribute='nextPageToken')

  def AnalyzeOrgPolicyGovernedContainers(self, args):
    """Calls AnalyzeOrgPolicyGovernedContainers method."""
    request = self.message_module.CloudassetAnalyzeOrgPolicyGovernedContainersRequest(
        scope=args.scope, constraint=args.constraint)
    return list_pager.YieldFromList(
        self.service,
        request,
        method='AnalyzeOrgPolicyGovernedContainers',
        field='governedContainers',
        limit=args.limit,
        batch_size=args.page_size or self._DEFAULT_PAGE_SIZE,
        batch_size_attribute='pageSize',
        current_token_attribute='pageToken',
        next_token_attribute='nextPageToken')

  def AnalyzeOrgPolicies(self, args):
    """Calls AnalyzeOrgPolicies method."""
    request = self.message_module.CloudassetAnalyzeOrgPoliciesRequest(
        scope=args.scope, constraint=args.constraint)
    return list_pager.YieldFromList(
        self.service,
        request,
        method='AnalyzeOrgPolicies',
        field='orgPolicyResults',
        limit=args.limit,
        batch_size=args.page_size or self._DEFAULT_PAGE_SIZE,
        batch_size_attribute='pageSize',
        current_token_attribute='pageToken',
        next_token_attribute='nextPageToken')
