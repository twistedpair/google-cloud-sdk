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

"""This module holds common flags used by the gcloud app commands."""
import argparse

from googlecloudsdk.api_lib.app import logs_util
from googlecloudsdk.api_lib.storage import storage_util
from googlecloudsdk.calliope import arg_parsers
from googlecloudsdk.calliope import base
from googlecloudsdk.command_lib.app import exceptions
from googlecloudsdk.core import log
from googlecloudsdk.core.docker import constants
from googlecloudsdk.core.docker import docker
from googlecloudsdk.third_party.appengine.api import appinfo

SERVER_FLAG = base.Argument(
    '--server',
    help=argparse.SUPPRESS)

IGNORE_CERTS_FLAG = base.Argument(
    '--ignore-bad-certs',
    action='store_true',
    default=False,
    help=argparse.SUPPRESS)

SERVICE = base.Argument(
    '--service', '-s',
    help='Limit to specific service.',
    required=False)

VERSION = base.Argument(
    '--version', '-v',
    help='Limit to specific version.',
    required=False)

LEVEL = base.Argument(
    '--level',
    help='Filter entries with severity equal to or higher than a given level.',
    required=False,
    default='any',
    choices=logs_util.LOG_LEVELS)

LOGS = base.Argument(
    '--logs',
    help=('Filter entries from a particular set of logs. Must be a '
          'comma-separated list of log names (request_log, stdout, stderr, '
          'etc).'),
    required=False,
    default=logs_util.DEFAULT_LOGS,
    metavar='APP_LOG',
    type=arg_parsers.ArgList(min_length=1))


def ValidateDockerBuildFlag(unused_value):
  raise argparse.ArgumentTypeError("""\
The --docker-build flag no longer exists.

Docker images are now built remotely using Google Container Builder. To run a
Docker build on your own host, you can run:
  docker build -t gcr.io/<project>/<service.version> .
  gcloud docker push gcr.io/<project>/<service.version>
  gcloud app deploy --image-url=gcr.io/<project>/<service.version>
If you don't already have a Dockerfile, you must run:
  gcloud beta app gen-config
first to get one.
  """)


DOCKER_BUILD_FLAG = base.Argument(
    '--docker-build',
    help=argparse.SUPPRESS,
    type=ValidateDockerBuildFlag)


LOG_SEVERITIES = ['debug', 'info', 'warning', 'error', 'critical']


def GetCodeBucket(app, project):
  """Gets a bucket reference for a Cloud Build.

  Args:
    app: App resource for this project
    project: str, The name of the current project.

  Returns:
    storage_util.BucketReference, The bucket to use.
  """
  # Attempt to retrieve the default appspot bucket, if one can be created.
  log.debug('No bucket specified, retrieving default bucket.')
  if not app.codeBucket:
    raise exceptions.DefaultBucketAccessError(project)
  return storage_util.BucketReference.FromBucketUrl(app.codeBucket)


VERSION_TYPE = arg_parsers.RegexpValidator(
    appinfo.MODULE_VERSION_ID_RE_STRING,
    'May only contain lowercase letters, digits, and hyphens. '
    'Must begin and end with a letter or digit. Must not exceed 63 characters.')


def ValidateImageUrl(image_url, services):
  """Check the user-provided image URL.

  Ensures that:
  - it is consistent with the services being deployed (there must be exactly
    one)
  - it is an image in a supported Docker registry

  Args:
    image_url: str, the URL of the image to deploy provided by the user
    services: list, the services to deploy

  Raises:
    MultiDeployError: if image_url is provided and more than one service is
      being deployed
    docker.UnsupportedRegistryError: if image_url is provided and does not point
      to one of the supported registries
  """
  # Validate the image url if provided, and ensure there is a single service
  # being deployed.
  if image_url is None:
    return
  if len(services) != 1:
    raise exceptions.MultiDeployError()
  for registry in constants.ALL_SUPPORTED_REGISTRIES:
    if image_url.startswith(registry):
      return
  raise docker.UnsupportedRegistryError(image_url)
