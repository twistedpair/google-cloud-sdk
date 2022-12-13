# -*- coding: utf-8 -*- #
# Copyright 2022 Google LLC. All Rights Reserved.
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
"""Library for configuring cloud-based development."""
from __future__ import absolute_import
from __future__ import division
from __future__ import print_function
from __future__ import unicode_literals

import os

from googlecloudsdk.api_lib.util import apis
from googlecloudsdk.api_lib.util import messages as messages_util
from googlecloudsdk.command_lib.code import builders
from googlecloudsdk.command_lib.code import common
from googlecloudsdk.command_lib.code import dataobject
from googlecloudsdk.command_lib.code import yaml_helper
from googlecloudsdk.command_lib.run import exceptions
from googlecloudsdk.command_lib.run import flags as run_flags
from googlecloudsdk.core import properties
from googlecloudsdk.core import yaml
from googlecloudsdk.core.util import files

RUN_MESSAGES_MODULE = apis.GetMessagesModule('run', 'v1')

_DEFAULT_BUILDPACK_BUILDER = 'gcr.io/buildpacks/builder'


def _IsGcpBaseBuilder(bldr):
  """Return true if the builder is the GCP base builder.

  Args:
    bldr: Name of the builder.

  Returns:
    True if the builder is the GCP base builder.
  """
  return bldr == _DEFAULT_BUILDPACK_BUILDER


def _BuilderFromArg(builder_arg):
  is_gcp_base_builder = _IsGcpBaseBuilder(builder_arg)
  return builders.BuildpackBuilder(
      builder=builder_arg,
      trust=is_gcp_base_builder,
      devmode=False)


class Settings(dataobject.DataObject):
  """Settings for a Cloud dev deployment."""
  NAMES = [
      'image', 'project', 'region', 'builder', 'service_name', 'service',
      'context'
  ]

  @classmethod
  def Defaults(cls):
    dir_name = os.path.basename(files.GetCWD())
    # Service names may not include space, _ and upper case characters.
    service_name = dir_name.replace('_', '-').replace(' ', '-').lower()
    service = RUN_MESSAGES_MODULE.Service(
        apiVersion='serving.knative.dev/v1', kind='Service')
    image = service_name
    dockerfile_arg_default = 'Dockerfile'
    bldr = builders.DockerfileBuilder(dockerfile=dockerfile_arg_default)
    return cls(
        service_name=service_name,
        service=service,
        image=image,
        builder=bldr,
        context=os.path.abspath(files.GetCWD()))

  def WithServiceYaml(self, yaml_path):
    """Use a pre-written service yaml for deployment."""
    # TODO(b/256683239): this is partially
    # copied from surface/run/services/replace.py and
    # should be moved somewhere common to avoid duplication

    service_dict = yaml.load_path(yaml_path)
    # Clear the status to make migration from k8s deployments easier.
    # Since a Deployment status will have several fields that Cloud Run doesn't
    # support, trying to convert it to a message as-is will fail even though
    # status is ignored by the server.
    if 'status' in service_dict:
      del service_dict['status']

    # For cases where YAML contains the project number as metadata.namespace,
    # preemptively convert them to a string to avoid validation failures.
    metadata = yaml_helper.GetOrCreate(service_dict, ['metadata'])
    namespace = metadata.get('namespace', None)
    if namespace is not None and not isinstance(namespace, str):
      service_dict['metadata']['namespace'] = str(namespace)

    try:
      service = messages_util.DictToMessageWithErrorCheck(
          service_dict, RUN_MESSAGES_MODULE.Service)
    except messages_util.ScalarTypeMismatchError as e:
      exceptions.MaybeRaiseCustomFieldMismatch(
          e,
          help_text='Please make sure that the YAML file matches the Knative '
          'service definition spec in https://kubernetes.io/docs/'
          'reference/kubernetes-api/services-resources/service-v1/'
          '#Service.')
    if self.project:
      service.metadata.namespace = str(self.project)
    replacements = {'service': service}
    # assume first image is the one we're replacing.
    replacements['image'] = service.spec.template.spec.containers[0].image
    if service.metadata.name:
      replacements['service_name'] = service.metadata.name
    return self.replace(**replacements)

  def WithArgs(self, args):
    """Update parameters based on arguments."""
    project = properties.VALUES.core.project.Get()
    region = run_flags.GetRegion(args, prompt=False)
    replacements = {'project': project, 'region': region}

    if args.IsKnownAndSpecified('builder'):
      replacements['builder'] = _BuilderFromArg(args.builder)
    elif args.IsKnownAndSpecified('dockerfile'):
      replacements['builder'] = builders.DockerfileBuilder(
          dockerfile=args.dockerfile)
    return self.replace(**replacements)

  def Build(self):
    metadata = self.service.metadata or RUN_MESSAGES_MODULE.ObjectMeta()
    metadata.name = self.service_name
    self.service.metadata = metadata
    replacements = {'service': self.service}
    return self.replace(**replacements)


def AssembleSettings(args):
  settings = Settings.Defaults()
  context_dir = getattr(args, 'source', None) or os.path.curdir
  service_config = getattr(args, 'service_config', None)
  yaml_file = common.ChooseExistingServiceYaml(context_dir, service_config)
  if yaml_file:
    settings = settings.WithServiceYaml(yaml_file)
  settings = settings.WithArgs(args)
  return settings.Build()
