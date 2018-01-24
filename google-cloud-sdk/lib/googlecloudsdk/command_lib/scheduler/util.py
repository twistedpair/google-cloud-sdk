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
import base64

from apitools.base.py import extra_types

from googlecloudsdk.api_lib.app import region_util
from googlecloudsdk.api_lib.util import apis
from googlecloudsdk.calliope import arg_parsers
from googlecloudsdk.command_lib.tasks import app


_PUBSUB_MESSAGE_URL = 'type.googleapis.com/google.pubsub.v1.PubsubMessage'


def _GetPubsubMessages():
  return apis.GetMessagesModule('pubsub', apis.ResolveVersion('pubsub'))


def _GetSchedulerMessages():
  return apis.GetMessagesModule('cloudscheduler', 'v1alpha1')


def ModifyCreatePubsubJobRequest(location_ref, args, create_job_req):
  """Add the pubsubMessage field to the given request.

  Because the Cloud Scheduler API has a reference to a PubSub message, but
  represents it as a bag of properties, we need to construct the object here and
  insert it into the request.

  Args:
    location_ref: Resource reference to the Location where the job will be
        created (unused)
    args: argparse namespace with the parsed arguments from the command line. In
        particular, we expect args.message_body and args.attributes (optional)
        to be AdditionalProperty types.
    create_job_req: CloudschedulerProjectsLocationsJobsCreateRequest, the
        request constructed from the remaining arguments.

  Returns:
    CloudschedulerProjectsLocationsJobsCreateRequest: the given request but with
        the job.pubsubTarget.pubsubMessage field populated.
  """
  # Unused in ModifyCreatePubsubJobRequest; API will assign a name
  del location_ref
  pubsub_message_type = create_job_req.job.pubsubTarget.PubsubMessageValue
  props = [
      pubsub_message_type.AdditionalProperty(
          key='@type',
          value=extra_types.JsonValue(string_value=_PUBSUB_MESSAGE_URL)),
      args.message_body
  ]
  if args.attributes:
    props.append(args.attributes)
  create_job_req.job.pubsubTarget.pubsubMessage = pubsub_message_type(
      additionalProperties=props)
  return create_job_req


def ParseMessageBody(message_body):
  """Parse "--message-body" flag as an argparse type.

  The flag is given as a string:

      --message-body 'some data'

  Args:
    message_body: str, the value of the --message-body flag.

  Returns:
    AdditionalProperty, a cloudscheduler additional property object with
        'data' as a key, and a JSON object (with a base64-encoded string value)
        as the value.
  """
  pubsub_messages = _GetPubsubMessages()
  scheduler_messages = _GetSchedulerMessages()

  # First, put into a PubsubMessage to make sure we've got the general format
  # right.
  pubsub_message = pubsub_messages.PubsubMessage(data=message_body)

  pubsub_message_type = scheduler_messages.PubsubTarget.PubsubMessageValue
  encoded_data = base64.urlsafe_b64encode(pubsub_message.data)
  return pubsub_message_type.AdditionalProperty(
      key='data',
      value=extra_types.JsonValue(string_value=encoded_data))


def ParseAttributes(attributes):
  """Parse "--attributes" flag as an argparse type.

  The flag is given as a Calliope ArgDict:

      --attributes key1=value1,key2=value2

  Args:
    attributes: str, the value of the --attributes flag.

  Returns:
    AdditionalProperty, a cloudscheduler additional property object with
        'attributes' as a key, and a JSON object (with string values) as the
        value.
  """
  attributes = arg_parsers.ArgDict()(attributes)
  pubsub_messages = _GetPubsubMessages()
  scheduler_messages = _GetSchedulerMessages()

  # First, put into a PubsubMessage to make sure we've got the general format
  # right.
  pubsub_props = []
  attributes_class = pubsub_messages.PubsubMessage.AttributesValue
  for key, value in sorted(attributes.items()):  # sort for unit tests
    pubsub_props.append(attributes_class.AdditionalProperty(key=key,
                                                            value=value))
  pubsub_message = pubsub_messages.PubsubMessage(
      attributes=attributes_class(additionalProperties=pubsub_props))

  attribute_props = []
  for prop in pubsub_message.attributes.additionalProperties:
    attribute_props.append(
        extra_types.JsonObject.Property(
            key=prop.key,
            value=extra_types.JsonValue(string_value=prop.value)
        )
    )
  attributes_value = extra_types.JsonObject(properties=attribute_props)
  pubsub_message_type = scheduler_messages.PubsubTarget.PubsubMessageValue
  return pubsub_message_type.AdditionalProperty(
      key='attributes',
      value=extra_types.JsonValue(object_value=attributes_value))


def HeaderType(string):
  """Returns ArgDict type for headers."""
  header, value = string.split(':')
  value = value.lstrip()
  return {header: value}


def HeaderProcessor(value):
  """Convert dict into HeadersValue."""
  scheduler_messages = _GetSchedulerMessages()
  props = []
  for key, value in sorted(value.items()):
    props.append(
        scheduler_messages.AppEngineHttpTarget.HeadersValue.AdditionalProperty(
            key=key,
            value=value))
  return scheduler_messages.AppEngineHttpTarget.HeadersValue(
      additionalProperties=props)


_MORE_REGIONS_AVAILABLE_WARNING = """\
The regions listed here are only those in which the Cloud Scheduler API is
available. To see full list of App Engine regions available,
create an app using the following command:

    $ gcloud app create
"""


VALID_REGIONS = [
    region_util.Region('us-central1', True, True),
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
