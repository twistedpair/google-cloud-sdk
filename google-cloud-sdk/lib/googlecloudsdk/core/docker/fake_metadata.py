# Copyright 2014 Google Inc. All Rights Reserved.
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

"""Library for launching a docker container serving GCE-style metadata."""

import json
import os
import random
import string
import tempfile

from googlecloudsdk.core import config
from googlecloudsdk.core import exceptions
from googlecloudsdk.core import log
from googlecloudsdk.core.docker import constants
from googlecloudsdk.core.docker import docker


MANIFEST_FORMAT = """\
computeMetadata:
  v1: &V1
    project:
      projectId: &PROJECT-ID
        {project_id}
      # TODO(mattmoor): remove gcloud's dependency on this.
      numericProjectId: 1234
    instance:
      attributes: {attributes}
      projectId: *PROJECT-ID
      hostname: test-hostname.kir
      machineType: n1-standard-1
      maintenanceEvent: NONE
      serviceAccounts:
        # Use YAML magic to minimize redundancy
        default: *DEFAULT
        {email}: &DEFAULT
          email: {email}
          scopes: {scopes}
      zone: us-central1-a
"""


class MetadataOptions(object):
  """Options for creating and running the fake metadata service."""

  def __init__(self, account=None, credential=None, project=None,
               attributes=None, scopes=None):
    """Constructor."""
    if not attributes:
      attributes = {}
    if not scopes:
      scopes = config.CLOUDSDK_SCOPES

    self.account = account
    self.credential = credential
    self.project = project
    self.attributes = attributes
    self.scopes = scopes


class FakeMetadata(object):
  """Creates a Fake Metadata instance usable via 'with'."""

  def __init__(self, image, options, suffix=None):
    """Initialize the fake metadata instance."""
    self._image = image
    self._options = options

    if not suffix:
      suffix = ''.join(random.choice(
          string.ascii_uppercase + string.digits) for _ in range(5))
    self.suffix = suffix

  @property
  def name(self):
    """String, identifying a container. Required for linking."""
    return 'metadata-%s' % self.suffix

  @property
  def manifest_file(self):
    """String, path to the manifest file."""
    return os.path.join(
        tempfile.gettempdir(),
        'fake_metadata_{suffix}.yaml'.format(suffix=self.suffix))

  @property
  def image(self):
    """String, identifying a fake-metadata image to be run."""
    return self._image

  def __enter__(self):
    """Creates a fake metadata environment."""
    log.Print('Surfacing credentials via {metadata}...'.format(
        metadata=self.name))

    # Use JSON to inject structured data into the YAML since it
    # is an effective way to create indentation-insensitive YAML
    # NOTE: YAML 1.2 is a superset of JSON.
    with open(self.manifest_file, 'w') as f_out:
      f_out.write(MANIFEST_FORMAT.format(
          attributes=json.dumps(self._options.attributes),
          project_id=self._options.project,
          email=self._options.account,
          scopes=json.dumps(self._options.scopes)))

    # We refresh credentials in case a pull is needed.
    docker.UpdateDockerCredentials(constants.DEFAULT_REGISTRY)
    result = docker.Execute([
        'run', '-d',
        '--name', self.name,
        '-v', self.manifest_file + ':' + self.manifest_file,
        self.image,
        # Arguments to the //cloud/containers/metadata binary,
        # which is the entrypoint:
        '-manifest_file='+self.manifest_file,
        '-refresh_token='+self._options.credential.refresh_token])
    if result != 0:
      raise exceptions.Error('Unable to launch fake-metadata.')
    return self

  # pylint: disable=redefined-builtin
  def __exit__(self, type, value, traceback):
    """Cleans up a fake metadata environment."""
    log.Print('Shutting down metadata credentials')
    result = docker.Execute(['rm', '-f', self.name])
    if result != 0:
      raise exceptions.Error('Unable to tear down fake-metadata.')
    # Clean up the temporary file.
    os.remove(self.manifest_file)
