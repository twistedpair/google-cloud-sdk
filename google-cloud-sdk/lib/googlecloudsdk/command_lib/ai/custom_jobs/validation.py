# -*- coding: utf-8 -*- #
# Copyright 2021 Google LLC. All Rights Reserved.
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
"""Validations of the arguments of custom-jobs command group."""

from __future__ import absolute_import
from __future__ import division
from __future__ import unicode_literals

import os

from googlecloudsdk.api_lib.ai import util as api_util
from googlecloudsdk.calliope import exceptions
from googlecloudsdk.command_lib.ai import constants
from googlecloudsdk.command_lib.ai.custom_jobs import custom_jobs_util
from googlecloudsdk.command_lib.ai.custom_jobs import local_util
from googlecloudsdk.command_lib.ai.docker import utils as docker_utils
from googlecloudsdk.core import log
from googlecloudsdk.core.util import files


def ValidateCreateArgs(args, job_spec_from_config, version):
  """Validate the argument values specified in `create` command."""
  # TODO(b/186082396): Add more validations for other args.
  if args.worker_pool_spec:
    if version != constants.GA_VERSION:
      args.worker_pool_spec = _NormalizeDeprecatedPythonImageUriInSpec(
          args.worker_pool_spec)
    _ValidateWorkerPoolSpecArgs(args.worker_pool_spec, version)
  else:
    _ValidateWorkerPoolSpecsFromConfig(job_spec_from_config)


def _ValidateWorkerPoolSpecArgs(worker_pool_specs, version):
  """Validate the argument values specified via `--worker-pool-spec` flags."""
  if custom_jobs_util.IsLocalPackagingRequired(worker_pool_specs):
    # We don't support local packaging for distributed training yet.
    if len(worker_pool_specs) > 1:
      raise exceptions.InvalidArgumentException(
          '--worker-pool-spec',
          'Local package is not supported for multiple worker pools.')

  for spec in worker_pool_specs:
    if spec:
      if version == constants.GA_VERSION:
        _ValidateSingleWorkerPoolSpecArgsGa(spec)
      else:
        _ValidateSingleWorkerPoolSpecArgsBetaAlpha(spec)


def _NormalizeDeprecatedPythonImageUriInSpec(specs):
  """Update the values of `--worker-pool-spec` flags if `python-image-uri` is specified."""

  updated = []
  for spec in specs:
    if spec and 'python-image-uri' in spec:
      # TODO(b/185461224): remove `python-image-uri`
      if 'executor-image-uri' not in spec:
        log.warning('Field `python-image-uri` in flag `--worker-pool-spec` will'
                    ' be deprecated. Please use `executor-image-uri` instead.')
        spec['executor-image-uri'] = spec['python-image-uri']
      else:
        log.warning('Field `python-image-uri` in flag `--worker-pool-spec` is '
                    'replaced by `executor-image-uri`. It is unnecessary to '
                    'specify both.')
    updated.append(spec)
  return updated


def _ValidateSingleWorkerPoolSpecArgsGa(spec):
  """Validate a single `--worker-pool-spec` flag value."""
  if 'machine-type' not in spec:
    raise exceptions.InvalidArgumentException(
        '--worker-pool-spec',
        'Key [machine-type] required in dict arg but not provided.')

  has_executor_image = 'executor-image-uri' in spec
  has_container_image = 'container-image-uri' in spec
  has_python_module = 'python-module' in spec

  if (has_executor_image + has_container_image) != 1:
    raise exceptions.InvalidArgumentException(
        '--worker-pool-spec',
        ('Exactly one of keys [executor-image-uri, container-image-uri] '
         'is required.'))

  if has_container_image and has_python_module:
    raise exceptions.InvalidArgumentException(
        '--worker-pool-spec',
        ('Key [python-module] is not allowed together with key '
         '[container-image-uri].'))

  if has_executor_image and not has_python_module:
    raise exceptions.InvalidArgumentException(
        '--worker-pool-spec', 'Key [python-module] is required.')


def _ValidateSingleWorkerPoolSpecArgsBetaAlpha(spec):
  """Validate a single `--worker-pool-spec` flag value in alpha or beta version."""
  if 'machine-type' not in spec:
    raise exceptions.InvalidArgumentException(
        '--worker-pool-spec',
        'Key [machine-type] required in dict arg but not provided.')

  if 'accelerator-count' in spec and 'accelerator-type' not in spec:
    raise exceptions.InvalidArgumentException(
        '--worker-pool-spec',
        'Key [accelerator-type] required as [accelerator-count] is specified.')

  accelerator_type = spec.get('accelerator-type', None)
  if accelerator_type:
    type_enum = api_util.GetMessage(
        'MachineSpec', constants.BETA_VERSION).AcceleratorTypeValueValuesEnum
    valid_types = [
        type for type in type_enum.names() if type.startswith('NVIDIA')
    ]
    if accelerator_type not in valid_types:
      raise exceptions.InvalidArgumentException(
          '--worker-pool-spec',
          ('Found invalid value of [accelerator-type]: {actual}. '
           'Available values are [{expected}].').format(
               actual=accelerator_type,
               expected=', '.join(v for v in sorted(valid_types))))

  has_executor_image = 'executor-image-uri' in spec
  has_container_image = 'container-image-uri' in spec

  if has_executor_image == has_container_image:
    raise exceptions.InvalidArgumentException(
        '--worker-pool-spec',
        ('Exactly one of keys [executor-image-uri, container-image-uri] '
         'is required.'))

  if has_container_image:
    disallowed_keys = set(['python-module', 'script',
                           'local-package-path']).intersection(spec.keys())
    if disallowed_keys:
      raise exceptions.InvalidArgumentException(
          '--worker-pool-spec',
          'Keys [{}] are not allowed together with key [container-image-uri]'
          .format(', '.join(disallowed_keys)))

  if has_executor_image:
    if ('python-module' in spec) == ('script' in spec):
      raise exceptions.InvalidArgumentException(
          '--worker-pool-spec',
          'Exactly one of keys [python-module, script] is required.')
    if ('script' in spec) and ('local-package-path' not in spec):
      raise exceptions.InvalidArgumentException(
          '--worker-pool-spec',
          ('Missing required key [local-package-path], '
           'key [script] is only allowed together with it.'))


def _ValidateWorkerPoolSpecsFromConfig(job_spec):
  """Validate WorkerPoolSpec message instances imported from the config file."""
  # TODO(b/186082396): adds more validations for other fields.
  for spec in job_spec.workerPoolSpecs:
    use_python_package = spec.pythonPackageSpec and (
        spec.pythonPackageSpec.executorImageUri or
        spec.pythonPackageSpec.pythonModule)
    use_container = spec.containerSpec and spec.containerSpec.imageUri

    if (use_container and use_python_package) or (not use_container and
                                                  not use_python_package):
      raise exceptions.InvalidArgumentException(
          '--config',
          ('Exactly one of fields [pythonPackageSpec, containerSpec] '
           'is required for a [workerPoolSpecs] in the YAML config file.'))


def _ImageBuildArgSpecified(args):
  """Returns names of all the flags specified only for image building."""
  image_build_args = []
  if args.script:
    image_build_args.append('script')
  if args.python_module:
    image_build_args.append('python-module')
  if args.requirements:
    image_build_args.append('requirements')
  if args.extra_packages:
    image_build_args.append('extra-packages')
  if args.extra_dirs:
    image_build_args.append('extra-dirs')
  if args.output_image_uri:
    image_build_args.append('output-image-uri')

  return image_build_args


def _ValidBuildArgsOfLocalRun(args):
  """Validates the arguments related to image building and normalize them."""
  build_args_specified = _ImageBuildArgSpecified(args)
  if not build_args_specified:
    return

  if not args.script and not args.python_module:
    raise exceptions.MinimumArgumentException(
        ['--script', '--python-module'],
        'They are required to build a training container image. '
        'Otherwise, please remove flags [{}] to directly run the `base-image`.'
        .format(', '.join(sorted(build_args_specified))))

  # Validate main script's existence:
  if args.script:
    arg_name = '--script'
  else:
    args.script = local_util.ModuleToPath(args.python_module)
    arg_name = '--python-module'

  script_path = os.path.normpath(os.path.join(args.work_dir, args.script))
  if not os.path.exists(script_path) or not os.path.isfile(script_path):
    raise exceptions.InvalidArgumentException(
        arg_name,
        r"File '{}' is not found under the working directory: '{}'.".format(
            args.script, args.work_dir))

  # Validate extra custom packages specified:
  for package in (args.extra_packages or []):
    package_path = os.path.normpath(os.path.join(args.work_dir, package))
    if not os.path.exists(package_path) or not os.path.isfile(package_path):
      raise exceptions.InvalidArgumentException(
          '--extra-packages',
          r"Package file '{}' is not found under the working directory: '{}'."
          .format(package, args.work_dir))

  # Validate extra directories specified:
  for directory in (args.extra_dirs or []):
    dir_path = os.path.normpath(os.path.join(args.work_dir, directory))
    if not os.path.exists(dir_path) or not os.path.isdir(dir_path):
      raise exceptions.InvalidArgumentException(
          '--extra-dirs',
          r"Directory '{}' is not found under the working directory: '{}'."
          .format(directory, args.work_dir))

  # Validate output image uri is in valid format
  if args.output_image_uri:
    output_image = args.output_image_uri
    try:
      docker_utils.ValidateRepositoryAndTag(output_image)
    except ValueError as e:
      raise exceptions.InvalidArgumentException(
          '--output-image-uri',
          r"'{}' is not a valid container image uri: {}".format(
              output_image, e))
  else:
    args.output_image_uri = docker_utils.GenerateImageName(
        base_name=args.script)


def ValidateLocalRunArgs(args):
  """Validates the arguments specified in `local-run` command and normalize them."""
  if args.work_dir:
    work_dir = os.path.abspath(files.ExpandHomeDir(args.work_dir))
    if not os.path.exists(work_dir) or not os.path.isdir(work_dir):
      raise exceptions.InvalidArgumentException(
          '--work-dir', r"Directory '{}' is not found.".format(work_dir))
  else:
    work_dir = files.GetCWD()
  args.work_dir = work_dir

  _ValidBuildArgsOfLocalRun(args)

  return args
