# -*- coding: utf-8 -*- #
# Copyright 2019 Google Inc. All Rights Reserved.
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
"""Utilities for Cloud Data Catalog crawler commands."""

from __future__ import absolute_import
from __future__ import division
from __future__ import unicode_literals

from googlecloudsdk.api_lib.data_catalog import crawlers
from googlecloudsdk.command_lib.util.apis import arg_utils
from googlecloudsdk.core import exceptions


DATACATALOG_CRAWLER_API_VERSION = 'v1alpha3'


class InvalidCrawlScopeError(exceptions.Error):
  """Error if a crawl scope is invalid."""


class InvalidRunOptionError(exceptions.Error):
  """Error if a run option is invalid."""


def ParseScopeFlagsForCreate(ref, args, request):
  """Python hook that parses the crawl scope args into the request.

  Args:
    ref: The crawler resource reference.
    args: The parsed args namespace.
    request: The update crawler request.
  Returns:
    Request with crawl scope set appropriately.
  """
  del ref
  _ValidateScopeFlagsForCreate(args)
  client = crawlers.CrawlersClient()
  messages = client.messages
  if args.IsSpecified('buckets'):
    buckets = [messages.GoogleCloudDatacatalogV1alpha3BucketSpec(bucket=b)
               for b in args.buckets]
  else:
    buckets = None
  return _SetScopeInRequest(args.crawl_scope, buckets, request)


def _ValidateScopeFlagsForCreate(args):
  if args.IsSpecified('buckets') and args.crawl_scope != 'bucket':
    raise InvalidCrawlScopeError(
        'Argument `--buckets` is only valid for bucket-scoped crawlers. '
        'Use `--crawl-scope=bucket` to specify a bucket-scoped crawler.')
  if not args.IsSpecified('buckets') and args.crawl_scope == 'bucket':
    raise InvalidCrawlScopeError(
        'Argument `--buckets` must be provided when creating a bucket-scoped '
        'crawler.')


def _SetScopeInRequest(crawl_scope, buckets, request):
  """Returns request with the crawl scope set."""
  client = crawlers.CrawlersClient()
  messages = client.messages

  if crawl_scope == 'bucket' and buckets is not None:
    arg_utils.SetFieldInMessage(
        request,
        'googleCloudDatacatalogV1alpha3Crawler.config.bucketScope.buckets',
        buckets)
  elif crawl_scope == 'project':
    arg_utils.SetFieldInMessage(
        request,
        'googleCloudDatacatalogV1alpha3Crawler.config.projectScope',
        messages.GoogleCloudDatacatalogV1alpha3ParentProjectScope())
  elif crawl_scope == 'organization':
    arg_utils.SetFieldInMessage(
        request,
        'googleCloudDatacatalogV1alpha3Crawler.config.organizationScope',
        messages.GoogleCloudDatacatalogV1alpha3ParentOrganizationScope())

  return request


def ParseSchedulingFlagsForCreate(ref, args, request):
  _ValidateSchedulingFlags(ref, args, request)
  return _SetRunOptionInRequest(
      args.run_option, args.run_schedule, request)


def _ValidateSchedulingFlags(ref, args, request):
  del ref, request
  if args.run_option == 'scheduled' and not args.IsSpecified('run_schedule'):
    raise InvalidRunOptionError(
        'Argument `--run-schedule` must be provided if `--run-option=scheduled`'
        ' was specified.')
  if args.run_option != 'scheduled' and args.IsSpecified('run_schedule'):
    raise InvalidRunOptionError(
        'Argument `--run-schedule` can only be provided for scheduled '
        'crawlers. Use `--run-option=scheduled` to specify a scheduled '
        'crawler.')


def _SetRunOptionInRequest(run_option, run_schedule, request):
  """Returns request with the run option set."""
  client = crawlers.CrawlersClient()
  messages = client.messages

  if run_option == 'manual':
    arg_utils.SetFieldInMessage(
        request,
        'googleCloudDatacatalogV1alpha3Crawler.config.adHocRun',
        messages.GoogleCloudDatacatalogV1alpha3AdhocRun())
  elif run_option == 'scheduled':
    scheduled_run_option = arg_utils.ChoiceToEnum(
        run_schedule,
        (messages.GoogleCloudDatacatalogV1alpha3ScheduledRun
         .ScheduledRunOptionValueValuesEnum))
    arg_utils.SetFieldInMessage(
        request,
        'googleCloudDatacatalogV1alpha3Crawler.config.scheduledRun.scheduledRunOption',
        scheduled_run_option)
  return request
