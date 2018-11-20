# -*- coding: utf-8 -*- #
# Copyright 2017 Google Inc. All Rights Reserved.
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
"""Utilities for "gcloud scheduler" commands."""

from __future__ import absolute_import
from __future__ import division
from __future__ import unicode_literals

from googlecloudsdk.api_lib.app import region_util
from googlecloudsdk.api_lib.util import apis
from googlecloudsdk.calliope import arg_parsers
from googlecloudsdk.command_lib.tasks import app
from googlecloudsdk.core.util import http_encoding


_PUBSUB_MESSAGE_URL = 'type.googleapis.com/google.pubsub.v1.PubsubMessage'


def _GetPubsubMessages():
  return apis.GetMessagesModule('pubsub', apis.ResolveVersion('pubsub'))


def _GetSchedulerMessages():
  return apis.GetMessagesModule('cloudscheduler', 'v1beta1')


def ModifyCreateJobRequest(job_ref, args, create_job_req):
  """Change the job.name field to a relative name."""
  del args  # Unused in ModifyCreateJobRequest
  create_job_req.job.name = job_ref.RelativeName()
  return create_job_req


def ModifyCreatePubsubJobRequest(job_ref, args, create_job_req):
  """Add the pubsubMessage field to the given request.

  Because the Cloud Scheduler API has a reference to a PubSub message, but
  represents it as a bag of properties, we need to construct the object here and
  insert it into the request.

  Args:
    job_ref: Resource reference to the job to be created (unused)
    args: argparse namespace with the parsed arguments from the command line. In
        particular, we expect args.message_body and args.attributes (optional)
        to be AdditionalProperty types.
    create_job_req: CloudschedulerProjectsLocationsJobsCreateRequest, the
        request constructed from the remaining arguments.

  Returns:
    CloudschedulerProjectsLocationsJobsCreateRequest: the given request but with
        the job.pubsubTarget.pubsubMessage field populated.
  """
  ModifyCreateJobRequest(job_ref, args, create_job_req)
  create_job_req.job.pubsubTarget.data = http_encoding.Encode(
      args.message_body or args.message_body_from_file)
  if args.attributes:
    create_job_req.job.pubsubTarget.attributes = args.attributes
  return create_job_req


def ParseAttributes(attributes):
  """Parse "--attributes" flag as an argparse type.

  The flag is given as a Calliope ArgDict:

      --attributes key1=value1,key2=value2

  Args:
    attributes: str, the value of the --attributes flag.

  Returns:
    dict, a dict with 'additionalProperties' as a key, and a list of dicts
        containing key-value pairs as the value.
  """
  attributes = arg_parsers.ArgDict()(attributes)
  return {
      'additionalProperties':
          [{'key': key, 'value': value}
           for key, value in sorted(attributes.items())]
  }


_MORE_REGIONS_AVAILABLE_WARNING = """\
The regions listed here are only those in which the Cloud Scheduler API is
available. To see full list of App Engine regions available,
create an app using the following command:

    $ gcloud app create
"""


VALID_REGIONS = [
    region_util.Region('us-central', True, True),
    region_util.Region('europe-west', True, True),
    region_util.Region('asia-northeast1', True, True),
]


class AppLocationResolver(object):
  """Callable that resolves and caches the app location for the project.

  The "fallback" for arg marshalling gets used multiple times in the course of
  YAML command translation. This prevents multiple API roundtrips without making
  that class stateful.
  """

  def __init__(self):
    self.location = None

  def __call__(self):
    if self.location is None:
      self.location = app.ResolveAppLocation(valid_regions=VALID_REGIONS,
                                             product='Cloud Scheduler')
    return self.location
