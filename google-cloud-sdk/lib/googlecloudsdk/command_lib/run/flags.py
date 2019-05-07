# -*- coding: utf-8 -*- #
# Copyright 2018 Google Inc. All Rights Reserved.
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
"""Provides common arguments for the Run command surface."""

from __future__ import absolute_import
from __future__ import division
from __future__ import print_function
from __future__ import unicode_literals

import re

from googlecloudsdk.api_lib.run import global_methods
from googlecloudsdk.command_lib.functions.deploy import env_vars_util
from googlecloudsdk.command_lib.run import config_changes
from googlecloudsdk.command_lib.run import exceptions as serverless_exceptions
from googlecloudsdk.command_lib.run import source_ref as source_ref_util
from googlecloudsdk.command_lib.util.args import labels_util
from googlecloudsdk.command_lib.util.args import map_util
from googlecloudsdk.command_lib.util.args import repeated
from googlecloudsdk.core import exceptions
from googlecloudsdk.core import log
from googlecloudsdk.core import properties
from googlecloudsdk.core.console import console_io
from googlecloudsdk.core.util import times


_VISIBILITY_MODES = {
    'internal': 'Visible only within the cluster.',
    'external': 'Visible from outside the cluster.',
}


class ArgumentError(exceptions.Error):
  pass


def _AddSourceArg(parser):
  """Add a source resource arg."""
  parser.add_argument(
      '--source',
      # TODO(b/110538411): re-expose source arg when it's time.
      hidden=True,
      help="""\
      The app source. Defaults to the working directory. May be a GCS bucket,
      Google source code repository, or directory on the local filesystem.
      """)


def _AddImageArg(parser):
  """Add an image resource arg."""
  parser.add_argument(
      '--image',
      help='Path to the GCR container to deploy.')


def AddAllowUnauthenticatedFlag(parser):
  """Add the --allow-unauthenticated flag."""
  parser.add_argument(
      '--allow-unauthenticated',
      default=False,
      action='store_true',
      help='True to allow unauthenticated access to the service.')


def AddAsyncFlag(parser):
  """Add an async flag."""
  parser.add_argument(
      '--async', default=False, action='store_true',
      help='True to deploy asynchronously.')


def AddEndpointVisibilityEnum(parser):
  """Add the --connectivity=[external|internal] flag."""
  parser.add_argument(
      '--connectivity',
      choices=_VISIBILITY_MODES,
      help=('Defaults to \'external\'. If \'external\', the service can be '
            'invoked through the internet, in addition to through the cluster '
            'network. Only applicable to Cloud Run on Kubernetes Engine.'))


def AddServiceFlag(parser):
  """Add a service resource flag."""
  parser.add_argument(
      '--service', required=False,
      help='Limit matched revisions to the given service.')


def AddSourceRefFlags(parser):
  """Add the image and source args."""
  source_ref_group = parser.add_mutually_exclusive_group()
  _AddSourceArg(source_ref_group)
  _AddImageArg(source_ref_group)


def AddRegionArg(parser):
  """Add a region arg."""
  parser.add_argument(
      '--region', help='Region in which the resource can be found. '
      'Alternatively, set the property [run/region].')


# TODO(b/118339293): When global list endpoint ready, stop hardcoding regions.
def AddRegionArgWithDefault(parser):
  """Add a region arg which defaults to us-central1.

  This is used by commands which list global resources.

  Args:
    parser: ArgumentParser, The calliope argparse parser.
  """
  parser.add_argument(
      '--region', default='us-central1',
      help='Region in which to list the resources.')


def AddFunctionArg(parser):
  """Add a function resource arg."""
  parser.add_argument(
      '--function',
      hidden=True,
      help="""\
      Specifies that the deployed object is a function. If a value is
      provided, that value is used as the entrypoint.
      """)


def AddCloudSQLFlags(parser):
  """Add flags for setting CloudSQL stuff."""
  repeated.AddPrimitiveArgs(
      parser,
      'Service',
      'cloudsql-instances',
      'Cloud SQL instances',
      auto_group_help=False,
      additional_help="""\
      These flags modify the Cloud SQL instances this Service connects to.
      You can specify a name of a Cloud SQL instance if it's in the same
      project and region as your Cloud Run service; otherwise specify
      <project>:<region>:<instance> for the instance.""")


def AddMutexEnvVarsFlags(parser):
  """Add flags for creating updating and deleting env vars."""
  # TODO(b/119837621): Use env_vars_util.AddUpdateEnvVarsFlags when
  # `gcloud run` supports an env var file.
  key_type = env_vars_util.EnvVarKeyType
  value_type = env_vars_util.EnvVarValueType
  flag_name = 'env-vars'
  long_name = 'environment variables'

  group = parser.add_mutually_exclusive_group()
  update_remove_group = group.add_argument_group(
      help=('Only --update-{0} and --remove-{0} can be used together. If both '
            'are specified, --remove-{0} will be applied first.'
           ).format(flag_name))
  map_util.AddMapUpdateFlag(update_remove_group, flag_name, long_name,
                            key_type=key_type, value_type=value_type)
  map_util.AddMapRemoveFlag(update_remove_group, flag_name, long_name,
                            key_type=key_type)
  map_util.AddMapClearFlag(group, flag_name, long_name)
  map_util.AddMapSetFlag(group, flag_name, long_name, key_type=key_type,
                         value_type=value_type)


def AddMemoryFlag(parser):
  parser.add_argument('--memory',
                      help='Set a memory limit. Ex: 1Gi, 512Mi.')


def AddCpuFlag(parser):
  parser.add_argument('--cpu',
                      help='Set a CPU limit in Kubernetes cpu units. '
                           'Ex: .5, 500m, 2.')


def AddConcurrencyFlag(parser):
  parser.add_argument('--concurrency',
                      help='Set the number of concurrent requests allowed per '
                      'instance. A concurrency of 0 or unspecified indicates '
                      'any number of concurrent requests are allowed. To unset '
                      'this field, provide the special value `default`.')


def AddTimeoutFlag(parser):
  parser.add_argument(
      '--timeout',
      help='Set the maximum request execution time (timeout). It is specified '
      'as a duration; for example, "10m5s" is ten minutes, and five seconds. '
      'If you don\'t specify a unit, seconds is assumed. For example, "10" is '
      '10 seconds.')


def AddServiceAccountFlag(parser):
  parser.add_argument(
      '--service-account',
      help='Email address of the IAM service account associated with the '
      'revision of the service. The service account represents the identity of '
      'the running revision, and determines what permissions the revision has. '
      'If not provided, the revision will use the project\'s default service '
      'account.')


def _HasEnvChanges(args):
  """True iff any of the env var flags are set."""
  env_flags = ['update_env_vars', 'set_env_vars',
               'remove_env_vars', 'clear_env_vars']
  return any(args.IsSpecified(flag) for flag in env_flags)


def _HasCloudSQLChanges(args):
  """True iff any of the cloudsql flags are set."""
  instances_flags = ['add_cloudsql_instances', 'set_cloudsql_instances',
                     'remove_cloudsql_instances', 'clear_cloudsql_instances']
  # hasattr check is to allow the same code to work for release tracks that
  # don't have the args at all yet.
  return any(hasattr(args, flag) and args.IsSpecified(flag)
             for flag in instances_flags)


def _HasLabelChanges(args):
  """True iff any of the label flags are set."""
  label_flags = ['update_labels', 'clear_labels', 'remove_labels']
  # hasattr check is to allow the same code to work for release tracks that
  # don't have the args at all yet.
  return any(hasattr(args, flag) and args.IsSpecified(flag)
             for flag in label_flags)


def _GetEnvChanges(args):
  """Return config_changes.EnvVarChanges for given args."""
  kwargs = {}

  update = args.update_env_vars or args.set_env_vars
  if update:
    kwargs['env_vars_to_update'] = update

  remove = args.remove_env_vars
  if remove:
    kwargs['env_vars_to_remove'] = remove

  if args.set_env_vars or args.clear_env_vars:
    kwargs['clear_others'] = True

  return config_changes.EnvVarChanges(**kwargs)


def GetConfigurationChanges(args):
  """Returns a list of changes to Configuration, based on the flags set."""
  changes = []
  if _HasEnvChanges(args):
    changes.append(_GetEnvChanges(args))

  if _HasCloudSQLChanges(args):
    region = GetRegion(args)
    project = (getattr(args, 'project', None) or
               properties.VALUES.core.project.Get(required=True))
    changes.append(config_changes.CloudSQLChanges(project, region, args))

  if 'cpu' in args and args.cpu:
    changes.append(config_changes.ResourceChanges(cpu=args.cpu))
  if 'memory' in args and args.memory:
    changes.append(config_changes.ResourceChanges(memory=args.memory))
  if 'concurrency' in args and args.concurrency:
    try:
      c = int(args.concurrency)
    except ValueError:
      c = args.concurrency
      if c != 'default':
        log.warning('Specifying concurrency as Single or Multi is deprecated; '
                    'an integer is preferred.')
    changes.append(config_changes.ConcurrencyChanges(concurrency=c))
  if 'timeout' in args and args.timeout:
    try:
      # A bare number is interpreted as seconds.
      timeout_secs = int(args.timeout)
    except ValueError:
      timeout_duration = times.ParseDuration(args.timeout)
      timeout_secs = int(timeout_duration.total_seconds)
    if timeout_secs <= 0:
      raise ArgumentError(
          'The --timeout argument must be a positive time duration.')
    changes.append(config_changes.TimeoutChanges(timeout=timeout_secs))
  if 'service_account' in args and args.service_account:
    changes.append(
        config_changes.ServiceAccountChanges(
            service_account=args.service_account))
  if _HasLabelChanges(args):
    diff = labels_util.Diff.FromUpdateArgs(args)
    if diff.MayHaveUpdates():
      changes.append(config_changes.LabelChanges(diff))

  return changes


def GetFunction(function_arg):
  """Returns the function name, or None if not deploying a function."""
  return function_arg


def GetService(args):
  """Get and validate the service resource from the args."""
  service_ref = args.CONCEPTS.service.Parse()
  # Valid service names comprise only alphanumeric characters and dashes. Must
  # not begin or end with a dash, and must not contain more than 63 characters.
  # Must be lowercase.
  service_re = re.compile(r'(?=^[a-z0-9-]{1,63}$)(?!^\-.*)(?!.*\-$)')
  if service_re.match(service_ref.servicesId):
    return service_ref
  raise ArgumentError(
      'Invalid service name [{}]. Service name must use only lowercase '
      'alphanumeric characters and dashes. Cannot begin or end with a dash, '
      'and cannot be longer than 63 characters.'.format(service_ref.servicesId))


def GetSourceRef(source_arg, image_arg):
  """Return a SourceRef representing either image path or source directory."""
  if image_arg:
    return source_ref_util.SourceRef.MakeImageRef(image_arg)
  elif source_arg:
    return source_ref_util.SourceRef.MakeDirRef(source_arg)
  else:
    raise ArgumentError(
        'You must provide a container image using the --image flag.')


def GetRegion(args, prompt=False):
  """Prompt for region if not provided.

  Region is decided in the following order:
  - region argument;
  - run/region gcloud config;
  - compute/region gcloud config;
  - prompt user.

  Args:
    args: Namespace, The args namespace.
    prompt: bool, whether to attempt to prompt.

  Returns:
    A str representing region.
  """
  if getattr(args, 'region', None):
    return args.region
  if properties.VALUES.run.region.IsExplicitlySet():
    return properties.VALUES.run.region.Get()
  if properties.VALUES.compute.region.IsExplicitlySet():
    return properties.VALUES.compute.region.Get()
  if prompt and console_io.CanPrompt():
    client = global_methods.GetServerlessClientInstance()
    all_regions = global_methods.ListRegions(client)
    idx = console_io.PromptChoice(
        all_regions, message='Please specify a region:\n', cancel_option=True)
    region = all_regions[idx]
    # set the region on args, so we're not embarassed the next time we call
    # GetRegion
    args.region = region
    log.status.Print(
        'To make this the default region, run '
        '`gcloud config set run/region {}`.\n'.format(region))
    return region


def ValidateClusterArgs(args):
  """Raise an error if a cluster is provided with no region or vice versa.

  Args:
    args: Namespace, The args namespace.

  Raises:
    ConfigurationError if a cluster is specified without a location or a
    location is specified without a cluster.
  """
  cluster_name = args.cluster or properties.VALUES.run.cluster.Get()
  cluster_location = (args.cluster_location or
                      properties.VALUES.run.cluster_location.Get())
  error_msg = ('Connecting to a cluster requires a {} to be specified. '
               'Either set the {} property or use the `{}` flag.')
  if cluster_name and not cluster_location:
    raise serverless_exceptions.ConfigurationError(
        error_msg.format('cluster location', 'run/cluster_location',
                         '--cluster-location'))
  if cluster_location and not cluster_name:
    raise serverless_exceptions.ConfigurationError(
        error_msg.format('cluster name', 'run/cluster', '--cluster'))


def VerifyOnePlatformFlags(args):
  """Raise ConfigurationError if args includes GKE only arguments."""
  if getattr(args, 'connectivity', None):
    raise serverless_exceptions.ConfigurationError(
        'The `--connectivity=[internal|external]` flag '
        'is not supported on OnePlatform.')

  if getattr(args, 'cpu', None):
    raise serverless_exceptions.ConfigurationError(
        'The `--cpu flag is not supported on OnePlatform.')


def VerifyGKEFlags(args):
  """Raise ConfigurationError if args includes OnePlatform only arguments."""
  if getattr(args, 'allow_unauthenticated', None):
    raise serverless_exceptions.ConfigurationError(
        'The `--allow-unauthenticated` flag '
        'is not supported with Cloud Run on GKE.')

  if getattr(args, 'service_account', None):
    raise serverless_exceptions.ConfigurationError(
        'The `--service-account` flag '
        'is not supported with Cloud Run on GKE.')


def ValidateIsGKE(args):
  """Returns True if args properly specify GKE.

  Args:
    args: Namespace, The args namespace.  Caller must add
      resource_args.CLUSTER_PRESENTATION to concept parser first.
  """
  cluster_ref = args.CONCEPTS.cluster.Parse()
  if not cluster_ref:
    ValidateClusterArgs(args)
  return bool(cluster_ref)
