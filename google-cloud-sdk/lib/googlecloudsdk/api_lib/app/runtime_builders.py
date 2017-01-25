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
r"""Library code to support App Engine Flex runtime builders.

The App Engine Flex platform runs a user's application that has been packaged
into a docker image. At the lowest level, the user provides us with a source
directory complete with Dockerfile, which we build into an image and deploy.
To make development easier, Google provides blessed language runtimes that the
user can extend in their Dockerfile to get a working base image for their
application. To further make development easier, we do not require users to
author their own Dockerfiles for "canonical" applications for each of the
Silver Languages.

In order for this to be possible, preprocessing must be done prior to the
Docker build to inspect the user's source code and automatically generate a
Dockerfile.

Flex runtime builders are a per-runtime pipeline that covers the full journey
from source directory to docker image. They are stored as templated .yaml files
representing CloudBuild Build messages. These .yaml files contain a series of
CloudBuild build steps.

Such a builder will look something like this (note that <angle_brackets> denote
values to be filled in by the builder author, and $DOLLAR_SIGNS denote a
literal part of the template to be substituted at runtime):

    steps:
    - name: 'gcr.io/google_appengine/python-builder:<version>'
    - name: 'gcr.io/cloud-builders/docker:<docker_image_version>'
      args: ['build', '-t', '$_OUTPUT_IMAGE', '.']
    images: ['$_OUTPUT_IMAGE']

To test this out in the context of a real deployment, do something like the
following (ls/grep steps just for illustrating where files are):

    $ ls /tmp/runtime-root
    python.yaml
    $ gcloud config set app/use_runtime_builders true
    $ gcloud config set app/runtime_builders_root file:///tmp/runtime-root
    $ cd $MY_APP_DIR
    $ grep 'runtime' app.yaml
    runtime: python
    $ grep 'env' app.yaml
    env: flex
    $ gcloud beta app deploy

A (possibly) easier way of achieving the same thing if you don't have a
runtime_builders_root set up for development yet:

   $ cd $MY_APP_DIR
   $ export _OUTPUT_IMAGE=gcr.io/$PROJECT/appengine/dummy
   $ gcloud container builds submit \
       --config=<(envsubst < /path/to/cloudbuild.yaml) .
   $ gcloud app deploy --image-url=$_OUTPUT_IMAGE
"""
import os

from googlecloudsdk.api_lib.cloudbuild import cloudbuild_util
from googlecloudsdk.api_lib.cloudbuild import config as cloudbuild_config
from googlecloudsdk.api_lib.storage import storage_api
from googlecloudsdk.api_lib.storage import storage_util
from googlecloudsdk.calliope import exceptions as calliope_exceptions
from googlecloudsdk.core import exceptions
from googlecloudsdk.core import properties
from googlecloudsdk.core.util import files as file_utils


class CloudBuildLoadError(exceptions.Error):
  """Error indicating an issue loading the `cloudbuild.yaml` for the runtime."""


class CloudBuildFileNotFound(CloudBuildLoadError):
  """Error indicating a missing Cloud Build file in a local path."""

  def __init__(self, name, root, builder_version):
    msg = ('Could not find file [{name}] in directory [{root}]. '
           'Please ensure that your app/runtime_builders_root property is set '
           'correctly and that ')
    if builder_version.version:
      msg += ('[{version}] is a valid version of the builder for runtime '
              '[{runtime}].')
    else:
      msg += 'runtime [{runtime}] is valid.'

    super(CloudBuildFileNotFound, self).__init__(
        msg.format(name=name, root=root, runtime=builder_version.runtime,
                   version=builder_version.version))


class CloudBuildObjectNotFound(CloudBuildLoadError):
  """Error indicating a missing object in a Cloud Storage path."""

  def __init__(self, name, bucket, builder_version):
    msg = ('Could not find object [{name}] in bucket [{bucket}]. '
           'Please ensure that your app/runtime_builders_root property is set '
           'correctly and that ')
    if builder_version.version:
      msg += ('[{version}] is a valid version of the builder for runtime '
              '[{runtime}].')
    else:
      msg += 'runtime [{runtime}] is valid.'

    super(CloudBuildObjectNotFound, self).__init__(
        msg.format(name=name, bucket=bucket, runtime=builder_version.runtime,
                   version=builder_version.version))


class InvalidRuntimeBuilderPath(CloudBuildLoadError):
  """Error indicating that the runtime builder path format wasn't recognized."""

  def __init__(self, path):
    super(InvalidRuntimeBuilderPath, self).__init__(
        '[{}] is not a valid runtime builder path. '
        'Please set the app/runtime_builders_root property to a URL with '
        'either the Google Cloud Storage (`gs://`) or local file (`file://`) '
        'protocol.'.format(path))


class RuntimeBuilderVersion(object):
  """A runtime/version pair representing the runtime version to use."""

  def __init__(self, runtime, version=None):
    self.runtime = runtime
    self.version = version

  def ToYamlFileName(self):
    """Returns the YAML filename corresponding to this runtime version.

    >>> RuntimeBuilderVersion('nodejs').ToYamlFileName()
    'nodejs.yaml'
    >>> RuntimeBuilderVersion('nodejs', 'v1').ToYamlFileName()
    'nodejs-v1.yaml'

    Returns:
      str, the name of the YAML file within the runtime root corresponding to
      this version.
    """
    return '-'.join(filter(None, [self.runtime, self.version])) + '.yaml'

  @classmethod
  def FromServiceInfo(cls, service):
    """Constructs a RuntimeBuilderVersion from a ServiceYamlInfo.

    Args:
      service: ServiceYamlInfo, The parsed service config.

    Returns:
      RuntimeBuilderVersion for the service.
    """
    return cls(service.runtime)

  def __eq__(self, other):
    return (self.runtime, self.version) == (other.runtime, other.version)

  def __ne__(self, other):
    return not self.__eq__(other)

  def LoadCloudBuild(self, params):
    """Loads the cloudbuild.yaml configuration file for this runtime version.

    Pulls the file from the app/runtime_builders_root value. Supported protocols
    are Cloud Storage ('gs://') and local filesystem ('file://').

    Args:
      params: dict, a dictionary of values to be substituted in to the
        cloudbuild.yaml template corresponding to this runtime version.

    Returns:
      Build message, the parsed and parameterized cloudbuild.yaml file.

    Raises:
      CloudBuildLoadError: if the cloudbuild.yaml file could not be loaded.
    """
    build_file_root = properties.VALUES.app.runtime_builders_root.Get(
        required=True)
    build_file_name = self.ToYamlFileName()
    messages = cloudbuild_util.GetMessagesModule()

    if build_file_root.startswith('file://'):
      build_file_path = os.path.join(build_file_root[len('file://'):],
                                     build_file_name)
      try:
        return cloudbuild_config.LoadCloudbuildConfig(
            build_file_path, messages=messages, params=params)
      except cloudbuild_config.NotFoundException:
        raise CloudBuildFileNotFound(build_file_name, build_file_root, self)
    elif build_file_root.startswith('gs://'):
      # Cloud Storage always uses '/' as separator, regardless of local platform
      if not build_file_root.endswith('/'):
        build_file_root += '/'
      object_ = storage_util.ObjectReference.FromUrl(build_file_root +
                                                     build_file_name)
      storage_client = storage_api.StorageClient()
      # TODO(b/34169164): keep this in-memory.
      with file_utils.TemporaryDirectory() as temp_dir:
        build_file_path = os.path.join(temp_dir, 'cloudbuild.yaml')
        try:
          storage_client.CopyFileFromGCS(object_.bucket_ref, object_.name,
                                         build_file_path)
        except calliope_exceptions.BadFileException:
          raise CloudBuildObjectNotFound(object_.name,
                                         object_.bucket_ref.ToBucketUrl(), self)
        return cloudbuild_config.LoadCloudbuildConfig(
            build_file_path, messages=messages, params=params)
    else:
      raise InvalidRuntimeBuilderPath(build_file_root)
