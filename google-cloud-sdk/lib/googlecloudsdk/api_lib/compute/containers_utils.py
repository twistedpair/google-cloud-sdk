# Copyright 2016 Google Inc. All Rights Reserved.
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
"""Functions for creating GCE container (Docker) deployments."""
import json
import re
import shlex

from googlecloudsdk.api_lib.compute import file_utils
from googlecloudsdk.api_lib.compute import metadata_utils
from googlecloudsdk.calliope import exceptions
from googlecloudsdk.core import exceptions as core_exceptions
from googlecloudsdk.core.util import times

USER_INIT_TEMPLATE = """#cloud-config
runcmd:
- ['/usr/bin/kubelet',
   '--allow-privileged=%s',
   '--manifest-url=http://metadata.google.internal/computeMetadata/v1/instance/attributes/google-container-manifest',
   '--manifest-url-header=Metadata-Flavor:Google',
   '--config=/etc/kubernetes/manifests']
"""

USER_DATA_KEY = 'user-data'

CONTAINER_MANIFEST_KEY = 'google-container-manifest'

GKE_DOCKER = 'gci-ensure-gke-docker'

ALLOWED_PROTOCOLS = ['TCP', 'UDP']

# Pin this version of gcloud to COS image major release version
COS_MAJOR_RELEASE = 'cos-stable-55'

COS_PROJECT = 'cos-cloud'


def _GetUserInit(allow_privileged):
  """Gets user-init metadata value for COS image."""
  allow_privileged_val = 'true' if allow_privileged else 'false'
  return USER_INIT_TEMPLATE % (allow_privileged_val)


def _GetContainerManifest(
    name, container_manifest, docker_image, port_mappings, run_command,
    run_as_privileged):
  """Loads container manifest from file or creates a new one."""
  if container_manifest:
    return file_utils.ReadFile(container_manifest, 'container manifest')
  else:
    return CreateContainerManifest(name, docker_image, port_mappings,
                                   run_command, run_as_privileged)


class InvalidMetadataKeyException(exceptions.ToolException):
  """InvalidMetadataKeyException is for not allowed metadata keys."""

  def __init__(self, metadata_key):
    super(InvalidMetadataKeyException, self).__init__(
        'Metadata key "{0}" is not allowed when running contenerized VM.'
        .format(metadata_key))


def CreateContainerManifest(
    name, docker_image, port_mappings, run_command, run_as_privileged):
  """Create container deployment manifest."""
  container = {
      'name': name,
      'image': docker_image,
      'imagePullPolicy': 'Always'
  }
  config = {
      'apiVersion': 'v1',
      'kind': 'Pod',
      'metadata': {'name': name},
      'spec': {'containers': [container]}
  }
  if port_mappings:
    container['ports'] = _ValidateAndParsePortMapping(port_mappings)
  if run_command:
    try:
      container['command'] = shlex.split(run_command)
    except ValueError as e:
      raise exceptions.InvalidArgumentException('--run-command', str(e))
  if run_as_privileged:
    container['securityContext'] = {'privileged': True}
  return json.dumps(config, indent=2, sort_keys=True)


def ValidateUserMetadata(metadata):
  """Validates if user-specified metadata.

  Checks if it contains values which may conflict with container deployment.
  Args:
    metadata: user-specified VM metadata.

  Raises:
    InvalidMetadataKeyException: if there is conflict with user-provided
    metadata
  """
  for entry in metadata.items:
    if entry.key in [USER_DATA_KEY, CONTAINER_MANIFEST_KEY, GKE_DOCKER]:
      raise InvalidMetadataKeyException(entry.key)


def CreateMetadataMessage(
    messages, run_as_privileged, container_manifest, docker_image,
    port_mappings, run_command, user_metadata, name):
  """Create metadata message with parameters for running Docker."""
  user_init = _GetUserInit(run_as_privileged)
  container_manifest = _GetContainerManifest(
      name=name,
      container_manifest=container_manifest,
      docker_image=docker_image,
      port_mappings=port_mappings,
      run_command=run_command,
      run_as_privileged=run_as_privileged)
  docker_metadata = {}
  docker_metadata[GKE_DOCKER] = 'true'
  docker_metadata[USER_DATA_KEY] = user_init
  docker_metadata[CONTAINER_MANIFEST_KEY] = container_manifest
  return metadata_utils.ConstructMetadataMessage(
      messages,
      metadata=docker_metadata,
      existing_metadata=user_metadata)


def CreateTagsMessage(messages, tags):
  """Create tags message with parameters for container VM or VM templates."""
  return messages.Tags(items=(tags if tags else ['container-vm']))


class NoCosImageException(core_exceptions.Error):
  """Raised when COS image could not be found."""

  def __init__(self):
    super(NoCosImageException, self).__init__(
        'Could not find COS (Cloud OS) for release family \'{0}\''
        .format(COS_MAJOR_RELEASE))


def ExpandCosImageFlag(compute_client):
  """Select a COS image to run Docker."""
  compute = compute_client.apitools_client
  images = compute_client.MakeRequests([(
      compute.images,
      'List',
      compute_client.messages.ComputeImagesListRequest(project=COS_PROJECT)
  )])
  return _SelectNewestCosImage(images)


def _SelectNewestCosImage(images):
  """Selects newest COS image from the list."""
  cos_images = sorted([image for image in images
                       if image.name.startswith(COS_MAJOR_RELEASE)],
                      key=lambda x: times.ParseDateTime(x.creationTimestamp))
  if not cos_images:
    raise NoCosImageException()
  return cos_images[-1].selfLink


def _ValidateAndParsePortMapping(port_mappings):
  """Parses and validates port mapping."""
  ports_config = []
  for port_mapping in port_mappings:
    mapping_match = re.match(r'^(\d+):(\d+):(\S+)$', port_mapping)
    if not mapping_match:
      raise exceptions.InvalidArgumentException(
          '--port-mappings',
          'Port mappings should follow PORT:TARGET_PORT:PROTOCOL format.')
    port, target_port, protocol = mapping_match.groups()
    if protocol not in ALLOWED_PROTOCOLS:
      raise exceptions.InvalidArgumentException(
          '--port-mappings',
          'Protocol should be one of [{0}]'.format(
              ', '.join(ALLOWED_PROTOCOLS)))
    ports_config.append({
        'containerPort': int(target_port),
        'hostPort': int(port),
        'protocol': protocol})
  return ports_config
