
# Copyright 2013 Google Inc. All Rights Reserved.
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

"""Utility methods to upload source to GCS and call Argo Cloud Build service."""

import gzip
import os
import shutil
import tempfile

from docker import docker
from googlecloudsdk.api_lib.app import cloud_storage
from googlecloudsdk.api_lib.app.api import operations
from googlecloudsdk.core import exceptions
from googlecloudsdk.core import log
from googlecloudsdk.core.console import console_io
from googlecloudsdk.third_party.apis.cloudbuild import v1 as cloudbuild_v1

CLOUDBUILD_BUILDER = 'gcr.io/cloud-builders/dockerizer'
CLOUDBUILD_SUCCESS = 'SUCCESS'
CLOUDBUILD_LOGS_URI_TEMPLATE = (
    'https://console.developers.google.com/logs?project={project_id}'
    '&service=cloudbuild.googleapis.com&key1={build_id}')

# Paths that shouldn't be ignored client-side.
# Behavioral parity with github.com/docker/docker-py.
BLACKLISTED_DOCKERIGNORE_PATHS = ['Dockerfile', '.dockerignore']


class BuildFailedError(exceptions.Error):
  """Raised when a Google Cloud Builder build fails."""


# This class is a workaround for the fact that the last line of
# docker.utils.tar does "fileobj.seek(0)" and gzip fails to seek in write mode,
# throwing "IOError: Negative seek in write mode".
class _GzipFileIgnoreSeek(gzip.GzipFile):
  """Wrapper around GzipFile that ignores seek requests."""

  def seek(self, offset, whence=0):
    return self.offset


def UploadSource(source_dir, target_object):
  """Upload a gzipped tarball of the source directory to GCS.

  Note: To provide parity with docker's behavior, we must respect .dockerignore.

  Args:
    source_dir: the directory to be archived.
    target_object: the GCS location where the tarball will be stored.
  """
  dockerignore = os.path.join(source_dir, '.dockerignore')
  exclude = None
  if os.path.exists(dockerignore):
    with open(dockerignore) as f:
      # Read the exclusions, filtering out blank lines.
      exclude = set(filter(bool, f.read().splitlines()))
      # Remove paths that shouldn't be excluded on the client.
      exclude -= set(BLACKLISTED_DOCKERIGNORE_PATHS)
  # We can't use tempfile.NamedTemporaryFile here because ... Windows.
  # See https://bugs.python.org/issue14243. There are small cleanup races
  # during process termination that will leave artifacts on the filesystem.
  # eg, CTRL-C on windows leaves both the directory and the file. Unavoidable.
  # On Posix, `kill -9` has similar behavior, but CTRL-C allows cleanup.
  try:
    temp_dir = tempfile.mkdtemp()
    f = open(os.path.join(temp_dir, 'src.tgz'), 'w+b')
    # We are able to leverage the source archiving code from docker-py;
    # however, there are two wrinkles:
    # 1) The 3P code doesn't support gzip (it's expecting a local unix socket).
    #    So we create a GzipFile object and let the 3P code write into that.
    # 2) The .seek(0) call at the end of the 3P code causes GzipFile to throw an
    #    exception. So we use GzipFileIgnoreSeek as a workaround.
    with _GzipFileIgnoreSeek(mode='wb', fileobj=f) as gz:
      docker.utils.tar(source_dir, exclude, fileobj=gz)
    f.close()
    cloud_storage.Copy(f.name, target_object)
  finally:
    shutil.rmtree(temp_dir)


def ExecuteCloudBuild(project, source_uri, output_image, cloudbuild_client):
  """Execute a call to Argo CloudBuild service and wait for it to finish.

  Args:
    project: the cloud project ID.
    source_uri: GCS object containing source to build;
                eg, gs://my-bucket/v1/foo/some.version.stuff.
    output_image: GCR location for the output docker image;
                  eg, gcr.io/test-argo/hardcoded-output-tag.
    cloudbuild_client: client to the Argo Cloud Build service.

  Raises:
    BuildFailedError: when the build fails.
  """
  (source_bucket, source_object) = cloud_storage.ParseGcsUri(source_uri)
  # TODO(user): Consider building multiple output images in a single call
  # to Argo Cloud Builder.
  build_op = cloudbuild_client.projects_builds.Create(
      cloudbuild_v1.CloudbuildProjectsBuildsCreateRequest(
          projectId=project,
          build=cloudbuild_v1.Build(
              source=cloudbuild_v1.Source(
                  storageSource=cloudbuild_v1.StorageSource(
                      bucket=source_bucket,
                      object=source_object,
                  ),
              ),
              steps=[cloudbuild_v1.BuildStep(
                  name=CLOUDBUILD_BUILDER,
                  args=[output_image]
              )],
              images=[output_image],
          ),
      )
  )
  # Build ops are named "operation/build/{project_id}/{build_id}".
  build_id = build_op.name.split('/')[-1]
  log.status.Print(
      'Started cloud build [{build_id}].'.format(build_id=build_id))
  logs_uri = CLOUDBUILD_LOGS_URI_TEMPLATE.format(project_id=project,
                                                 build_id=build_id)
  # TODO(user): wait for job to be scheduled before printing logs uri.
  # Alternatively, it would be nice if we wrote a single line to the logs prior
  # to returning from the Create call.
  log.status.Print('Logs at: ' + logs_uri)
  message = 'Waiting for cloud build [{build_id}]'.format(build_id=build_id)
  with console_io.ProgressTracker(message):
    op = operations.WaitForOperation(cloudbuild_client.operations, build_op)
  final_status = _GetStatusFromOp(op)
  if final_status != CLOUDBUILD_SUCCESS:
    raise BuildFailedError('Cloud build failed with status '
                           + final_status + '. Check logs at ' + logs_uri)


def _GetStatusFromOp(op):
  """Get the Cloud Build Status from an Operation object.

  The op.response field is supposed to have a copy of the build object; however,
  the wire JSON from the server doesn't get deserialized into an actual build
  object. Instead, it is stored as a generic ResponseValue object, so we have
  to root around a bit.

  Args:
    op: the Operation object from a CloudBuild build request.

  Returns:
    string status, likely "SUCCESS" or "ERROR".
  """
  for prop in op.response.additionalProperties:
    if prop.key == 'status':
      return prop.value.string_value
  return 'UNKNOWN'



