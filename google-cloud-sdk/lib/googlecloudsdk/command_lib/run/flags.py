# -*- coding: utf-8 -*- #
# Copyright 2018 Google LLC. All Rights Reserved.
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

import os
import re

from googlecloudsdk.api_lib.container import kubeconfig
from googlecloudsdk.api_lib.run import global_methods
from googlecloudsdk.api_lib.util import apis
from googlecloudsdk.calliope import actions
from googlecloudsdk.calliope import arg_parsers
from googlecloudsdk.command_lib.functions.deploy import env_vars_util
from googlecloudsdk.command_lib.run import config_changes
from googlecloudsdk.command_lib.run import exceptions as serverless_exceptions
from googlecloudsdk.command_lib.run import pretty_print
from googlecloudsdk.command_lib.util.args import labels_util
from googlecloudsdk.command_lib.util.args import map_util
from googlecloudsdk.command_lib.util.args import repeated
from googlecloudsdk.core import exceptions
from googlecloudsdk.core import log
from googlecloudsdk.core import properties
from googlecloudsdk.core import resources
from googlecloudsdk.core.console import console_io
from googlecloudsdk.core.util import files
from googlecloudsdk.core.util import times


_VISIBILITY_MODES = {
    'internal': 'Visible only within the cluster.',
    'external': 'Visible from outside the cluster.',
}

_PLATFORMS = {
    'managed': 'Fully managed version of Cloud Run. Use with the `--region` '
               'flag or set the [run/region] property to specify a Cloud Run '
               'region.',
    'gke': 'Cloud Run on Google Kubernetes Engine. Use with the `--cluster` '
           'and `--cluster-location` flags or set the [run/cluster] and '
           '[run/cluster_location] properties to specify a cluster in a given '
           'zone.'
}

_PLATFORM_SHORT_DESCRIPTIONS = {
    'managed': 'the managed version of Cloud Run',
    'gke': 'Cloud Run on GKE',
    'kubernetes': 'a Kubernetes cluster'
}

_DEFAULT_KUBECONFIG_PATH = '~/.kube/config'


class ArgumentError(exceptions.Error):
  pass


class KubeconfigError(exceptions.Error):
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
      help='Name of the container image to deploy (e.g. '
      '`gcr.io/cloudrun/hello:latest`).')


def AddAllowUnauthenticatedFlag(parser):
  """Add the --allow-unauthenticated flag."""
  parser.add_argument(
      '--allow-unauthenticated',
      action=arg_parsers.StoreTrueFalseAction,
      help='Whether to enable allowing unauthenticated access to the service.')


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
  _AddImageArg(parser)


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


def AddPlatformArg(parser):
  """Add a platform arg."""
  parser.add_argument(
      '--platform',
      choices=_PLATFORMS,
      action=actions.StoreProperty(properties.VALUES.run.platform),
      help='Target platform for running commands. '
      'Alternatively, set the property [run/platform]. '
      'This flag will be required in a future version of '
      'the gcloud command-line tool.')


def AddKubeconfigFlags(parser):
  parser.add_argument(
      '--kubeconfig',
      hidden=True,
      help='The absolute path to your kubectl config file. If not specified, '
      'the colon- or semicolon-delimited list of paths specified by '
      '$KUBECONFIG will be used. If $KUBECONFIG is unset, this defaults to '
      '`{}`.'.format(_DEFAULT_KUBECONFIG_PATH))
  parser.add_argument(
      '--context',
      hidden=True,
      help='The name of the context in your kubectl config file to use for '
      'connecting.')


def AddRevisionSuffixArg(parser):
  parser.add_argument(
      '--revision-suffix',
      hidden=True,
      help='Specify the suffix of the revision name. Revision names always '
      'start with the service name automatically. For example, specifying '
      '[--revision-suffix=v1] for a service named \'helloworld\', '
      'would lead to a revision named \'helloworld-v1\'.')


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


_CLOUD_SQL_API_SERVICE_TOKEN = 'sql-component.googleapis.com'
_CLOUD_SQL_ADMIN_API_SERVICE_TOKEN = 'sqladmin.googleapis.com'


def _CheckCloudSQLApiEnablement():
  if not properties.VALUES.core.should_prompt_to_enable_api.GetBool():
    return
  project = properties.VALUES.core.project.Get(required=True)
  apis.PromptToEnableApi(
      project, _CLOUD_SQL_API_SERVICE_TOKEN,
      serverless_exceptions.CloudSQLError(
          'Cloud SQL API could not be enabled.'))
  apis.PromptToEnableApi(
      project, _CLOUD_SQL_ADMIN_API_SERVICE_TOKEN,
      serverless_exceptions.CloudSQLError(
          'Cloud SQL Admin API could not be enabled.'))


def GetConfigurationChanges(args):
  """Returns a list of changes to Configuration, based on the flags set."""
  changes = []
  if _HasEnvChanges(args):
    changes.append(_GetEnvChanges(args))

  if _HasCloudSQLChanges(args):
    region = GetRegion(args)
    project = (getattr(args, 'project', None) or
               properties.VALUES.core.project.Get(required=True))
    _CheckCloudSQLApiEnablement()
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
  if 'revision_suffix' in args and args.revision_suffix:
    changes.append(config_changes.RevisionNameChanges(args.revision_suffix))
  return changes


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


def GetClusterRef(cluster):
  project = properties.VALUES.core.project.Get(required=True)
  return resources.REGISTRY.Parse(
      cluster.name,
      params={
          'projectId': project,
          'zone': cluster.zone
      },
      collection='container.projects.zones.clusters')


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


def GetEndpointVisibility(args):
  """Return bool for explicitly set connectivity or None if not set."""
  if args.connectivity == 'internal':
    return True
  if args.connectivity == 'external':
    return False
  return None


def GetAllowUnauthenticated(args, client=None, service_ref=None, prompt=False):
  """Return bool for the explicit intent to allow unauth invocations or None.

  If --[no-]allow-unauthenticated is set, return that value. If not set,
  prompt for value if desired. If prompting not necessary or doable,
  return None, indicating that no action needs to be taken.

  Args:
    args: Namespace, The args namespace
    client: from googlecloudsdk.command_lib.run import serverless_operations
      serverless_operations.ServerlessOperations object
    service_ref: service resource reference (e.g. args.CONCEPTS.service.Parse())
    prompt: bool, whether to attempt to prompt.

  Returns:
    bool indicating whether to allow/unallow unauthenticated or None if N/A
  """
  if getattr(args, 'allow_unauthenticated', None) is not None:
    return args.allow_unauthenticated

  if prompt:
    if client is None or service_ref is None:
      raise ValueError(
          'A client and service reference are required for determining if the '
          'service\'s IAM policy binding can be modified.')
    if client.CanSetIamPolicyBinding(service_ref):
      return console_io.PromptContinue(
          prompt_string=('Allow unauthenticated invocations '
                         'to [{}]'.format(service_ref.servicesId)),
          default=False)
    else:
      pretty_print.Info(
          'This service will require authentication to be invoked.')
  return None


def GetKubeconfig(args):
  """Get config from kubeconfig file.

  Get config from potentially 3 different places, falling back to the next
  option as necessary:
  1. file_path specified as argument by the user
  2. List of file paths specified in $KUBECONFIG
  3. Default config path (~/.kube/config)

  Args:
    args: Namespace, The args namespace.

  Returns:
    dict: config object

  Raises:
    KubeconfigError: if $KUBECONFIG is set but contains no valid paths
  """
  if getattr(args, 'kubeconfig', None):
    return kubeconfig.Kubeconfig.LoadFromFile(
        files.ExpandHomeDir(args.kubeconfig))
  if os.getenv('KUBECONFIG'):
    config_paths = os.getenv('KUBECONFIG').split(os.pathsep)
    config = None
    # Merge together all valid paths into single config
    for path in config_paths:
      try:
        other_config = kubeconfig.Kubeconfig.LoadFromFile(
            files.ExpandHomeDir(path))
        if not config:
          config = other_config
        else:
          config.Merge(other_config)
      except kubeconfig.Error:
        pass
    if not config:
      raise KubeconfigError('No valid file paths found in $KUBECONFIG')
    return config
  return kubeconfig.Kubeconfig.LoadFromFile(
      files.ExpandHomeDir(_DEFAULT_KUBECONFIG_PATH))


def ValidateClusterArgs(args):
  """Raise an error if a cluster is provided with no region or vice versa.

  Args:
    args: Namespace, The args namespace.

  Raises:
    ConfigurationError if a cluster is specified without a location or a
    location is specified without a cluster.
  """
  cluster_name = (
      getattr(args, 'cluster', None) or properties.VALUES.run.cluster.Get())
  cluster_location = (
      getattr(args, 'cluster_location', None) or
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


def _FlagIsExplicitlySet(args, flag):
  """Return True if --flag is explicitly passed by the user."""
  return hasattr(args, flag) and args.IsSpecified(flag)


def VerifyOnePlatformFlags(args):
  """Raise ConfigurationError if args includes GKE only arguments."""
  error_msg = ('The `{flag}` flag is not supported on the fully managed '
               'version of Cloud Run. Specify `--platform {platform}` or run '
               '`gcloud config set run/platform {platform}` to work with '
               '{platform_desc}.')

  if _FlagIsExplicitlySet(args, 'connectivity'):
    raise serverless_exceptions.ConfigurationError(
        error_msg.format(
            flag='--connectivity=[internal|external]',
            platform='gke',
            platform_desc=_PLATFORM_SHORT_DESCRIPTIONS['gke']))

  if _FlagIsExplicitlySet(args, 'cpu'):
    raise serverless_exceptions.ConfigurationError(
        error_msg.format(
            flag='--cpu',
            platform='gke',
            platform_desc=_PLATFORM_SHORT_DESCRIPTIONS['gke']))

  if _FlagIsExplicitlySet(args, 'cluster'):
    raise serverless_exceptions.ConfigurationError(
        error_msg.format(
            flag='--cluster',
            platform='gke',
            platform_desc=_PLATFORM_SHORT_DESCRIPTIONS['gke']))

  if _FlagIsExplicitlySet(args, 'cluster_location'):
    raise serverless_exceptions.ConfigurationError(
        error_msg.format(
            flag='--cluster-location',
            platform='gke',
            platform_desc=_PLATFORM_SHORT_DESCRIPTIONS['gke']))

  if _FlagIsExplicitlySet(args, 'kubeconfig'):
    raise serverless_exceptions.ConfigurationError(
        error_msg.format(
            flag='--kubeconfig',
            platform='kubernetes',
            platform_desc=_PLATFORM_SHORT_DESCRIPTIONS['kubernetes']))

  if _FlagIsExplicitlySet(args, 'context'):
    raise serverless_exceptions.ConfigurationError(
        error_msg.format(
            flag='--context',
            platform='kubernetes',
            platform_desc=_PLATFORM_SHORT_DESCRIPTIONS['kubernetes']))


def VerifyGKEFlags(args):
  """Raise ConfigurationError if args includes OnePlatform only arguments."""
  error_msg = ('The `{flag}` flag is not supported with Cloud Run on GKE. '
               'Specify `--platform {platform}` or run `gcloud config set '
               'run/platform {platform}` to work with {platform_desc}.')

  if _FlagIsExplicitlySet(args, 'allow_unauthenticated'):
    raise serverless_exceptions.ConfigurationError(
        error_msg.format(
            flag='--allow-unauthenticated',
            platform='managed',
            platform_desc=_PLATFORM_SHORT_DESCRIPTIONS['managed']))

  if _FlagIsExplicitlySet(args, 'service_account'):
    raise serverless_exceptions.ConfigurationError(
        error_msg.format(
            flag='--service-account',
            platform='managed',
            platform_desc=_PLATFORM_SHORT_DESCRIPTIONS['managed']))

  if _FlagIsExplicitlySet(args, 'region'):
    raise serverless_exceptions.ConfigurationError(
        error_msg.format(
            flag='--region',
            platform='managed',
            platform_desc=_PLATFORM_SHORT_DESCRIPTIONS['managed']))

  if _FlagIsExplicitlySet(args, 'revision_suffix'):
    raise serverless_exceptions.ConfigurationError(
        error_msg.format(
            flag='--revision-suffix',
            platform='managed',
            platform_desc=_PLATFORM_SHORT_DESCRIPTIONS['managed']))

  if _FlagIsExplicitlySet(args, 'kubeconfig'):
    raise serverless_exceptions.ConfigurationError(
        error_msg.format(
            flag='--kubeconfig',
            platform='kubernetes',
            platform_desc=_PLATFORM_SHORT_DESCRIPTIONS['kubernetes']))

  if _FlagIsExplicitlySet(args, 'context'):
    raise serverless_exceptions.ConfigurationError(
        error_msg.format(
            flag='--context',
            platform='kubernetes',
            platform_desc=_PLATFORM_SHORT_DESCRIPTIONS['kubernetes']))


def VerifyKubernetesFlags(args):
  """Raise ConfigurationError if args includes OnePlatform or GKE only arguments."""
  error_msg = ('The `{flag}` flag is not supported when connecting to a '
               'Kubenetes cluster. Specify `--platform {platform}` or run '
               '`gcloud config set run/platform {platform}` to work with '
               '{platform_desc}.')

  if _FlagIsExplicitlySet(args, 'allow_unauthenticated'):
    raise serverless_exceptions.ConfigurationError(
        error_msg.format(
            flag='--allow-unauthenticated',
            platform='managed',
            platform_desc=_PLATFORM_SHORT_DESCRIPTIONS['managed']))

  if _FlagIsExplicitlySet(args, 'service_account'):
    raise serverless_exceptions.ConfigurationError(
        error_msg.format(
            flag='--service-account',
            platform='managed',
            platform_desc=_PLATFORM_SHORT_DESCRIPTIONS['managed']))

  if _FlagIsExplicitlySet(args, 'region'):
    raise serverless_exceptions.ConfigurationError(
        error_msg.format(
            flag='--region',
            platform='managed',
            platform_desc=_PLATFORM_SHORT_DESCRIPTIONS['managed']))

  if _FlagIsExplicitlySet(args, 'revision_suffix'):
    raise serverless_exceptions.ConfigurationError(
        error_msg.format(
            flag='--revision-suffix',
            platform='managed',
            platform_desc=_PLATFORM_SHORT_DESCRIPTIONS['managed']))

  if _FlagIsExplicitlySet(args, 'cluster'):
    raise serverless_exceptions.ConfigurationError(
        error_msg.format(
            flag='--cluster',
            platform='gke',
            platform_desc=_PLATFORM_SHORT_DESCRIPTIONS['gke']))

  if _FlagIsExplicitlySet(args, 'cluster_location'):
    raise serverless_exceptions.ConfigurationError(
        error_msg.format(
            flag='--cluster-location',
            platform='gke',
            platform_desc=_PLATFORM_SHORT_DESCRIPTIONS['gke']))


def GetPlatform(args):
  """Returns the platform to run on."""
  platform = properties.VALUES.run.platform.Get()
  if platform is None:
    log.warning(
        'No target platform specified. This will be a required flag in a '
        'future version of the gcloud command-line tool. Pass the `--platform` '
        'flag or set the [run/platform] property to satisfy this warning.\n'
        'Available platforms:\n{}\n'.format('\n'.join(
            ['- {}: {}'.format(k, v) for k, v in _PLATFORMS.items()])))
    # The check below ends up calling this method so to prevent a stack overflow
    # we set the platform temporarily
    properties.VALUES.run.platform.Set('temp_skip')
    if ValidateIsGKE(args):
      platform = 'gke'
    elif getattr(args, 'kubeconfig', None):
      platform = 'kubernetes'
    else:
      platform = 'managed'
    # Set the platform so we don't warn on future calls to this method
    properties.VALUES.run.platform.Set(platform)

  if platform == 'managed':
    VerifyOnePlatformFlags(args)
  elif platform == 'gke':
    VerifyGKEFlags(args)
  elif platform == 'kubernetes':
    VerifyKubernetesFlags(args)
  elif platform != 'temp_skip':
    raise ArgumentError(
        'Invalid target platform specified: [{}].\n'
        'Available platforms:\n{}'.format(
            platform,
            '\n'.join(['- {}: {}'.format(k, v) for k, v in _PLATFORMS.items()
                      ])))
  return platform


def IsKubernetes(args):
  """Returns True if args property specify Kubernetes.

  Args:
    args: Namespace, The args namespace.
  """
  return GetPlatform(args) == 'kubernetes'


def IsGKE(args):
  """Returns True if args properly specify GKE.

  Args:
    args: Namespace, The args namespace.
  """
  return GetPlatform(args) == 'gke'


def IsManaged(args):
  """Returns True if args properly specify managed.

  Args:
    args: Namespace, The args namespace.
  """
  return GetPlatform(args) == 'managed'


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
