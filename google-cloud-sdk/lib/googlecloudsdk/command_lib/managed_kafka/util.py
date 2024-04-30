# -*- coding: utf-8 -*- #
# Copyright 2024 Google LLC. All Rights Reserved.
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
"""A library used to support Apache Kafka for BigQuery commands."""

from apitools.base.py import encoding
from googlecloudsdk import core
from googlecloudsdk.api_lib.util import apis

# Retrieve all message type for conversions from gcloud primitives to
# apitool types.
_MESSAGE = apis.GetMessagesModule("managedkafka", "v1")


def AddUpdateMaskForSubnets(_, args, request):
  """Adds the update mask for the subnets in the request.

  Args:
    _:  resource parameter required but unused variable.
    args: list of flags.
    request:  the payload to return.

  Returns:
    The updated request with the update mask.
  """
  if not args.subnets:
    return request

  request.cluster = {"gcpConfig": {}}
  request.updateMask = "gcpConfig.accessConfig.networkConfigs"
  return MapSubnetsToNetworkConfig(_, args, request)


def MapSubnetsToNetworkConfig(_, args, request):
  """Maps the list of subnets from the flag to the API fields in the request.

  Args:
    _:  resource parameter required but unused variable.
    args: list of flags.
    request:  the payload to return.

  Returns:
    The updated request with networkConfig in the JSON format.
  """
  # Reference the existing GCP config if already created for the request.
  if not request.cluster.gcpConfig:
    request.cluster.gcpConfig = {}
  request.cluster.gcpConfig.accessConfig = {"networkConfigs": []}
  for subnet in args.subnets:
    network_config = {"subnet": subnet}
    request.cluster.gcpConfig.accessConfig.networkConfigs.append(
        encoding.DictToMessage(
            network_config, _MESSAGE.NetworkConfig
        )
    )
  return request


def ListWithBootstrapAddr(response, _):
  """Synthesizes the bootstrap address to the response for a list request.

  Args:
    response: the payload to return.
    _: list of flags.

  Returns:
    The updated clusters with the bootstrap.
  """
  return [
      SynthesizeBootstrapAddr(cluster, cluster.name) for cluster in response
  ]


def DescribeWithBootstrapAddr(response, _):
  """Synthesizes the bootstrap address to the response for a describe request.

  Args:
    response: the payload to return.
    _: list of flags.

  Returns:
    The updated cluster with the bootstrap.
  """
  return SynthesizeBootstrapAddr(response, response.name)


def SynthesizeBootstrapAddr(response, cluster):
  """Synthesizes the bootstrap address to the response.

  Args:
    response: the payload to update.
    cluster: the fully qualifed name of the cluster.

  Returns:
    The updated cluster with the bootstrap
  """
  # The fully qualified name will always be consistent. We also have to use the
  # fully qualifed name instead of the resource directly to support both
  # `describe` and `list`.
  name = cluster.split("/")[5]
  location = cluster.split("/")[3]
  project = core.properties.VALUES.core.project.Get()
  bootstrap = (
      f"bootstrap.{name}.{location}.managedkafka.{project}.cloud.goog:9092"
  )
  synthesized = core.resource.resource_projector.MakeSerializable(response)
  synthesized["bootstrapAddress"] = bootstrap
  return synthesized


def UpdateTopics(_, args, request):
  """Load the topics JSON from the argument to the request.

  Args:
    _:  resource parameter required but unused variable.
    args: list of flags.
    request:  the payload to return.

  Returns:
    The updated request with topics.
  """
  topics = core.yaml.load(args.topics_file)
  request.consumerGroup = {
      "topics": encoding.DictToMessage(
          topics, _MESSAGE.ConsumerGroup.TopicsValue
      )
  }
  request.updateMask = "topics"
  return request
