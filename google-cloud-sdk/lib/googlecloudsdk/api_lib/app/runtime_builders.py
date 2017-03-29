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
CloudBuild build steps. Additionally, the runtime root stores a
`<runtime>.version` file which indicates the current default version. That is,
if `python-v1.yaml` is the current active pipeline, `python.version` will
contain `v1`.

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
    python.version python-v1.yaml
    $ cat /tmp/runtime-root
    v1
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

Or (even easier) use a 'custom' runtime:

    $ cd $MY_APP_DIR
    $ ls
    cloudbuild.yaml app.yaml
    $ rm -f Dockerfile
    $ grep 'runtime' app.yaml
    runtime: custom
    $ gcloud beta app deploy
"""
import abc
import contextlib
import os

import enum
from googlecloudsdk.api_lib.cloudbuild import cloudbuild_util
from googlecloudsdk.api_lib.cloudbuild import config as cloudbuild_config
from googlecloudsdk.api_lib.storage import storage_api
from googlecloudsdk.api_lib.storage import storage_util
from googlecloudsdk.calliope import exceptions as calliope_exceptions
from googlecloudsdk.core import exceptions
from googlecloudsdk.core import log
from googlecloudsdk.core import properties


CLOUDBUILD_FILE = 'cloudbuild.yaml'
WHITELISTED_RUNTIMES = ['aspnetcore']


class CloudBuildLoadError(exceptions.Error):
  """Error indicating an issue loading the runtime Cloud Build specification."""


class CloudBuildFileNotFound(CloudBuildLoadError):
  """Error indicating a missing Cloud Build file."""


class InvalidRuntimeBuilderPath(CloudBuildLoadError):
  """Error indicating that the runtime builder path format wasn't recognized."""

  def __init__(self, path):
    super(InvalidRuntimeBuilderPath, self).__init__(
        '[{}] is not a valid runtime builder path. '
        'Please set the app/runtime_builders_root property to a URL with '
        'either the Google Cloud Storage (`gs://`) or local file (`file://`) '
        'protocol.'.format(path))


class RuntimeBuilderStrategy(enum.Enum):
  """Enum indicating when to use runtime builders."""
  NEVER = 1
  WHITELIST = 2  # That is, turned on for a whitelisted set of runtimes
  ALWAYS = 3

  def ShouldUseRuntimeBuilders(self, runtime, needs_dockerfile):
    """Returns True if runtime should use runtime builders under this strategy.

    For the most part, this is obvious: the ALWAYS strategy returns True, the
    WHITELIST strategy returns True if the given runtime is in the list of
    WHITELISTED_RUNTIMES, and the NEVER strategy returns False.

    However, in the case of 'custom' runtimes, things get tricky: if the
    strategy *is not* NEVER, we return True only if there is no `Dockerfile` in
    the current directory (this method assumes that there is *either* a
    `Dockerfile` or a `cloudbuild.yaml` file), since one needs to get generated
    by the Cloud Build.

    Args:
      runtime: str, the runtime being built.
      needs_dockerfile: bool, whether the Dockerfile in the source directory is
        absent.

    Returns:
      bool, whether to use the runtime builders.
    Raises:
      ValueError: if an unrecognized runtime_builder_strategy is given
    """
    if self is RuntimeBuilderStrategy.WHITELIST:
      if runtime == 'custom':
        return needs_dockerfile
      return runtime in WHITELISTED_RUNTIMES
    elif self is RuntimeBuilderStrategy.ALWAYS:
      if runtime == 'custom':
        return needs_dockerfile
      return True
    elif self is RuntimeBuilderStrategy.NEVER:
      return False
    else:
      raise ValueError('Invalid runtime builder strategy [{}].'.format(self))


def _Join(*args):
  """Join parts of a Cloud Storage or local path."""
  if args[0].startswith('gs://'):
    # Cloud Storage always uses '/' as separator, regardless of local platform
    return '/'.join([arg.strip('/') for arg in args])
  else:
    return os.path.join(*args)


def _Read(path):
  """Read a file/object (local or on Cloud Storage).

  >>> with _Read('gs://builder/object.txt') as f:
  ...   assert f.read() == 'foo'
  >>> with _Read('file:///path/to/object.txt') as f:
  ...   assert f.read() == 'bar'

  Args:
    path: str, the path to the file/object to read. Must begin with 'file://' or
      'gs://'

  Returns:
    a file-like context manager.

  Raises:
    IOError: if the file is local and open()ing it raises this error.
    OSError: if the file is local and open()ing it raises this error.
    calliope_exceptions.BadFileException: if the remote file read failed.
    InvalidRuntimeBuilderPath: if the path is invalid (doesn't begin with an
        appropriate prefix.
  """
  if path.startswith('file://'):
    return open(path[len('file://'):])
  elif path.startswith('gs://'):
    storage_client = storage_api.StorageClient()
    object_ = storage_util.ObjectReference.FromUrl(path)
    return contextlib.closing(storage_client.ReadObject(object_))
  else:
    raise InvalidRuntimeBuilderPath(path)


class RuntimeBuilderVersion(object):
  __metaclass__ = abc.ABCMeta

  @abc.abstractmethod
  def LoadCloudBuild(self, params):
    """Loads the Cloud Build configuration file for this runtime version.

    Args:
      params: dict, a dictionary of values to be substituted in to the
        Cloud Build configuration template corresponding to this runtime
        version.

    Returns:
      Build message, the parsed and parameterized Cloud Build configuration
        file.

    Raises:
      CloudBuildLoadError: if the Cloud Build configuration file could not be
        loaded.
    """
    raise NotImplementedError()


class CannedBuilderVersion(RuntimeBuilderVersion):
  """A runtime/version pair representing the runtime version to use."""

  def __init__(self, runtime, version=None):
    self.runtime = runtime
    self.version = version

  def ToYamlFileName(self):
    """Returns the YAML filename corresponding to this runtime version.

    >>> CannedBuilderVersion('nodejs', 'v1').ToYamlFileName()
    'nodejs-v1.yaml'

    Returns:
      str, the name of the YAML file within the runtime root corresponding to
      this version.

    Raises:
      ValueError: if this CannedBuilderVersion doesn't have an explicit
          version.
    """
    if not self.version:
      raise ValueError('Only CannedBuilderVersions with explicit versions have '
                       'a YAML filename.')
    return '-'.join([self.runtime, self.version]) + '.yaml'

  def ToVersionFileName(self):
    """Returns name of the file containing the default version of the runtime.

    >>> CannedBuilderVersion('nodejs').ToVersionFileName()
    'nodejs.version'
    >>> CannedBuilderVersion('nodejs', 'v1').ToYamlFileName()
    'nodejs.version'

    Returns:
      str, the name of the YAML file within the runtime root corresponding to
      this version.
    """
    return self.runtime + '.version'

  def __eq__(self, other):
    return (self.runtime, self.version) == (other.runtime, other.version)

  def __ne__(self, other):
    return not self.__eq__(other)

  def _CreateCloudBuildNotFoundException(self, path):
    msg = ('Could not find Cloud Build config [{path}]. '
           'Please ensure that your app/runtime_builders_root property is set '
           'correctly and that ')
    if self.version:
      msg += ('[{version}] is a valid version of the builder for runtime '
              '[{runtime}].')
    else:
      msg += 'runtime [{runtime}] is valid.'
    return CloudBuildFileNotFound(
        msg.format(path=path, runtime=self.runtime, version=self.version))

  def LoadCloudBuild(self, params):
    """Loads the Cloud Build configuration file for this runtime version.

    Pulls the file from the app/runtime_builders_root value. Supported protocols
    are Cloud Storage ('gs://') and local filesystem ('file://').

    If this RuntimeBuilderVersion has a version, this loads the file from
    '<runtime>-<version>.yaml' in the runtime builders root. Otherwise, it
    checks '<runtime>.version' to get the default version, and loads the
    configuration for that version.

    Args:
      params: dict, a dictionary of values to be substituted in to the
        Cloud Build configuration template corresponding to this runtime
        version.

    Returns:
      Build message, the parsed and parameterized Cloud Build configuration
        file.

    Raises:
      CloudBuildLoadError: if the Cloud Build configuration file could not be
        loaded.
    """
    build_file_root = properties.VALUES.app.runtime_builders_root.Get(
        required=True)
    log.debug('Using runtime builder root [%s]', build_file_root)

    if self.version is None:
      log.debug('Fetching version for runtime [%s]...', self.runtime)
      version_file_path = _Join(build_file_root, self.ToVersionFileName())
      try:
        with _Read(version_file_path) as f:
          version = f.read().strip()
      except (IOError, OSError, calliope_exceptions.BadFileException):
        raise self._CreateCloudBuildNotFoundException(version_file_path)
      log.info('Using version [%s] for runtime [%s].', version, self.runtime)
      builder_version = CannedBuilderVersion(self.runtime, version)
      return builder_version.LoadCloudBuild(params)

    messages = cloudbuild_util.GetMessagesModule()
    build_file_name = self.ToYamlFileName()
    build_file_path = _Join(build_file_root, build_file_name)
    try:
      with _Read(build_file_path) as data:
        return cloudbuild_config.LoadCloudbuildConfigFromStream(
            data, messages=messages, params=params)
    except (IOError, OSError, calliope_exceptions.BadFileException):
      raise self._CreateCloudBuildNotFoundException(build_file_path)


class CustomBuilderVersion(RuntimeBuilderVersion):
  """A 'custom' runtime version.

  Loads its Cloud Build configuration from `cloudbuild.yaml` in the application
  source directory.
  """

  CLOUDBUILD_FILE = 'cloudbuild.yaml'

  def __init__(self, source_dir):
    self.source_dir = source_dir

  def __eq__(self, other):
    # Needed for tests
    return self.source_dir == other.source_dir

  def __ne__(self, other):
    # Needed for tests
    return not self.__eq__(other)

  def _CreateCloudBuildNotFoundException(self):
    return CloudBuildFileNotFound(
        'Could not find Cloud Build config [{}] in directory [{}].'.format(
            CLOUDBUILD_FILE, self.source_dir))

  def LoadCloudBuild(self, params):
    """Loads the Cloud Build configuration file for this runtime version.

    Pulls the file from the app/runtime_builders_root value. Supported protocols
    are Cloud Storage ('gs://') and local filesystem ('file://').

    Args:
      params: dict, a dictionary of values to be substituted in to the
        Cloud Build configuration template corresponding to this runtime
        version.

    Returns:
      Build message, the parsed and parameterized Cloud Build configuration
        file.

    Raises:
      CloudBuildLoadError: if the Cloud Build configuration file could not be
        loaded.
    """
    messages = cloudbuild_util.GetMessagesModule()
    build_file_path = os.path.join(self.source_dir, self.CLOUDBUILD_FILE)
    try:
      with open(build_file_path) as data:
        return cloudbuild_config.LoadCloudbuildConfigFromStream(
            data, messages=messages, params=params)
    except (IOError, OSError, calliope_exceptions.BadFileException):
      raise self._CreateCloudBuildNotFoundException()


def FromServiceInfo(service, source_dir):
  """Constructs a RuntimeBuilderVersion from a ServiceYamlInfo.

  If the service runtime is 'custom', then uses a CustomBuilderVersion (which
  reads from a local 'cloudbuild.yaml' file. Otherwise, uses a
  CannedBuilderVersion, which reads from the runtime_builders_root.

  Args:
    service: ServiceYamlInfo, The parsed service config.
    source_dir: str, the source containing the application directory to build.

  Returns:
    RuntimeBuilderVersion for the service.
  """
  if service.runtime == 'custom':
    return CustomBuilderVersion(source_dir)
  else:
    runtime_config = service.parsed.runtime_config
    version = runtime_config.get('runtime_version') if runtime_config else None
    return CannedBuilderVersion(service.runtime, version)
