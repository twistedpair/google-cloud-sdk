# -*- coding: utf-8 -*- #
# Copyright 2019 Google LLC. All Rights Reserved.
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
"""Support library to generate Build and BuildTrigger configs."""

from __future__ import absolute_import
from __future__ import division
from __future__ import unicode_literals

from googlecloudsdk.api_lib.cloudbuild import cloudbuild_util
from googlecloudsdk.core.util import times

import six

_DEFAULT_BUILD_TAGS = [
    'gcp-cloud-build-deploy',
    'gcp-cloud-build-deploy-gcloud'
]

_GKE_DEPLOY_PROD = 'gcr.io/cloud-builders/gke-deploy:stable'

_SUGGESTED_CONFIGS_PATH = 'gs://{0}/config/{1}/suggested'
_EXPANDED_CONFIGS_PATH = 'gs://{0}/config/{1}/expanded'

# Build substitution variables
_DOCKERFILE_PATH_SUB_VAR = '_DOCKERFILE_PATH'
_APP_NAME_SUB_VAR = '_APP_NAME'
_K8S_YAML_PATH_SUB_VAR = '_K8S_YAML_PATH'
_K8S_NAMESPACE_SUB_VAR = '_K8S_NAMESPACE'
_EXPOSE_PORT_SUB_VAR = '_EXPOSE_PORT'
_GKE_CLUSTER_SUB_VAR = '_GKE_CLUSTER'
_GKE_LOCATION_SUB_VAR = '_GKE_LOCATION'
_OUTPUT_BUCKET_PATH_SUB_VAR = '_OUTPUT_BUCKET_PATH'

_SAVE_CONFIGS_SCRIPT = '''
set -e

gsutil cp -r output/suggested {0}
echo "Copied suggested base configs to {0}"
gsutil cp -r output/expanded {1}
echo "Copied expanded configs to {1}"
'''.format(
    _SUGGESTED_CONFIGS_PATH.format(
        '$' + _OUTPUT_BUCKET_PATH_SUB_VAR, '$BUILD_ID'),
    _EXPANDED_CONFIGS_PATH.format(
        '$' + _OUTPUT_BUCKET_PATH_SUB_VAR, '$BUILD_ID')
)

# Build step IDs
_BUILD_BUILD_STEP_ID = 'Build'
_PUSH_BUILD_STEP_ID = 'Push'
_PREPARE_DEPLOY_BUILD_STEP_ID = 'Prepare deploy'
_SAVE_CONFIGS_BUILD_STEP_ID = 'Save configs'
_APPLY_DEPLOY_BUILD_STEP_ID = 'Apply deploy'


def SuggestedConfigsPath(gcs_config_staging_path, build_id):
  """Gets the formatted suggested configs path.

  Args:
    gcs_config_staging_path: The path to a GCS subdirectory where the configs
      are saved to.
    build_id: The build_id of the build that creates and saves the configs.

  Returns:
    Formatted suggested configs path as a string.
  """
  return _SUGGESTED_CONFIGS_PATH.format(
      gcs_config_staging_path, build_id)


def ExpandedConfigsPath(gcs_config_staging_path, build_id):
  """Gets the formatted expanded configs path.

  Args:
    gcs_config_staging_path: The path to a GCS subdirectory where the configs
      are saved to.
    build_id: The build_id of the build that creates and saves the configs.

  Returns:
    Formatted expanded configs path as a string.
  """
  return _EXPANDED_CONFIGS_PATH.format(
      gcs_config_staging_path, build_id)


def SaveConfigsBuildStepIsSuccessful(messages, build):
  """Returns True if the step with _SAVE_CONFIGS_BUILD_STEP_ID id is successful.

  Args:
    messages: Cloud Build messages module. i.e., the return value of
      cloudbuild_util.GetMessagesModule().
    build: The build that contains the step to check.

  Returns:
    True if the step is successful, else false.
  """
  save_configs_build_step = next((
      x for x in build.steps if x.id == _SAVE_CONFIGS_BUILD_STEP_ID
  ), None)

  status = save_configs_build_step.status
  return status == messages.BuildStep.StatusValueValuesEnum.SUCCESS


def CreateBuild(
    messages, build_timeout, build_and_push, staged_source,
    image, dockerfile_path, app_name, app_version, config_path, namespace,
    expose_port, gcs_config_staging_path, cluster, location, build_tags
):
  """Creates the Cloud Build config to run.

  Args:
    messages: Cloud Build messages module. i.e., the return value of
      cloudbuild_util.GetMessagesModule().
    build_timeout: An optional maximum time a build is run before it times out.
      For example, "2h15m5s" is 2 hours, 15 minutes, and 5 seconds. If you do
      not specify a unit, seconds is assumed. If this value is None, a timeout
      is not set.
    build_and_push: If True, the created build will have Build and Push steps.
    staged_source: An optional GCS object for a staged source repository. The
      object must have bucket, name, and generation fields. If this value is
      None, the created build will not have a source.
    image: The image that will deployed and optionally built beforehand. The
      image can include a tag or digest.
    dockerfile_path: A path to the source repository's Dockerfile, relative to
    the source repository's root directory.
    app_name: An app name that is set to a substitution variable.
    app_version: An app version that is set to a substitution variable.
    config_path: An optional path to the source repository's Kubernetes configs,
      relative to the source repository's root directory that is set to a
      substitution variable. If this value is None, the substitution variable is
      set to '' to indicate its absence.
    namespace: A Kubernetes namespace of the cluster to deploy to that
      is set to a substitution variable.
    expose_port: An optional port that the deployed application listens to that
      is set to a substitution variable. If this value is None, the substitution
      variable is set to 0 to indicate its absence.
    gcs_config_staging_path: An optional path to a GCS subdirectory to copy
      application configs that is set to a substitution variable. If this value
      is None, the substitution variable is set to '' to indicate its absence.
    cluster: The name of the target cluster to deploy to.
    location: The zone/region of the target cluster to deploy to.
    build_tags: Tags to append to build tags in additional to default tags.

  Returns:
    messages.Build, the Cloud Build config.
  """

  build = messages.Build()

  if build_timeout is not None:
    try:
      # A bare number is interpreted as seconds.
      build_timeout_secs = int(build_timeout)
    except ValueError:
      build_timeout_duration = times.ParseDuration(build_timeout)
      build_timeout_secs = int(build_timeout_duration.total_seconds)
    build.timeout = six.text_type(build_timeout_secs) + 's'

  if staged_source:
    build.source = messages.Source(
        storageSource=messages.StorageSource(
            bucket=staged_source.bucket,
            object=staged_source.name,
            generation=staged_source.generation
        )
    )

  if config_path is None:
    config_path = ''

  if not expose_port:
    expose_port = '0'
  else:
    expose_port = str(expose_port)

  build.steps = []

  if build_and_push:
    build.steps.append(messages.BuildStep(
        id=_BUILD_BUILD_STEP_ID,
        name='gcr.io/cloud-builders/docker',
        args=[
            'build',
            '--network',
            'cloudbuild',
            '--no-cache',
            '-t',
            image,
            '-f',
            '${}'.format(_DOCKERFILE_PATH_SUB_VAR),
            '.'
        ]
    ))
    build.steps.append(messages.BuildStep(
        id=_PUSH_BUILD_STEP_ID,
        name='gcr.io/cloud-builders/docker',
        args=[
            'push',
            image,
        ]
    ))

  build.steps.append(messages.BuildStep(
      id=_PREPARE_DEPLOY_BUILD_STEP_ID,
      name=_GKE_DEPLOY_PROD,
      args=[
          'prepare',
          '--filename=${}'.format(_K8S_YAML_PATH_SUB_VAR),
          '--image={}'.format(image),
          '--app=${}'.format(_APP_NAME_SUB_VAR),
          '--version={}'.format(app_version),
          '--namespace=${}'.format(_K8S_NAMESPACE_SUB_VAR),
          '--output=output',
          '--annotation=gcb-build-id=$BUILD_ID',
          '--expose=${}'.format(_EXPOSE_PORT_SUB_VAR)
      ],
  ))
  build.steps.append(messages.BuildStep(
      id=_SAVE_CONFIGS_BUILD_STEP_ID,
      name='gcr.io/cloud-builders/gsutil',
      entrypoint='sh',
      args=[
          '-c',
          _SAVE_CONFIGS_SCRIPT
      ]
  ))
  build.steps.append(messages.BuildStep(
      id=_APPLY_DEPLOY_BUILD_STEP_ID,
      name=_GKE_DEPLOY_PROD,
      args=[
          'apply',
          '--filename=output/expanded',
          '--namespace=${}'.format(_K8S_NAMESPACE_SUB_VAR),
          '--cluster=${}'.format(_GKE_CLUSTER_SUB_VAR),
          '--location=${}'.format(_GKE_LOCATION_SUB_VAR),
          '--timeout=24h'  # Set this to max value allowed for a build so that
          # this step never times out. We prefer the timeout given to the build
          # to take precedence.
      ],
  ))

  build.substitutions = cloudbuild_util.EncodeSubstitutions(
      _BuildSubstitutionsDict(dockerfile_path, app_name, config_path,
                              namespace, expose_port, cluster, location,
                              gcs_config_staging_path),
      messages)

  build.tags = _DEFAULT_BUILD_TAGS[:]
  if build_tags:
    for tag in build_tags:
      build.tags.append(tag)

  build.options = messages.BuildOptions()
  build.options.substitutionOption = messages.BuildOptions.SubstitutionOptionValueValuesEnum.ALLOW_LOOSE

  return build


def _BuildSubstitutionsDict(dockerfile_path, app_name, config_path, namespace,
                            expose_port, cluster, location,
                            gcs_config_staging_path):
  """Creates a dict of substitutions for a Build or BuildTrigger to encode.

  Args:
    dockerfile_path: Value for _DOCKERFILE_PATH_SUB_VAR substitution variable.
    app_name: Value for _APP_NAME_SUB_VAR substitution variable.
    config_path: Value for _K8S_YAML_PATH_SUB_VAR substitution variable.
    namespace: Value for _K8S_NAMESPACE_SUB_VAR substitution variable.
    expose_port: Value for _EXPOSE_PORT_SUB_VAR substitution variable.
    cluster: Value for _GKE_CLUSTER_SUB_VAR substitution variable.
    location: Value for _GKE_LOCATION_SUB_VAR substitution variable.
    gcs_config_staging_path: Value for _OUTPUT_BUCKET_PATH_SUB_VAR substitution
      variable.

  Returns:
    Dict of substitutions mapped to values.
  """
  return {
      _DOCKERFILE_PATH_SUB_VAR: dockerfile_path,
      _APP_NAME_SUB_VAR: app_name,
      _K8S_YAML_PATH_SUB_VAR: config_path,
      _K8S_NAMESPACE_SUB_VAR: namespace,
      _EXPOSE_PORT_SUB_VAR: expose_port,
      _GKE_CLUSTER_SUB_VAR: cluster,
      _GKE_LOCATION_SUB_VAR: location,
      _OUTPUT_BUCKET_PATH_SUB_VAR: gcs_config_staging_path
  }
