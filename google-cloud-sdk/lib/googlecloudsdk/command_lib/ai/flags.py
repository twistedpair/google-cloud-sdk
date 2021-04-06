# -*- coding: utf-8 -*- #
# Copyright 2020 Google LLC. All Rights Reserved.
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
"""Flags defination for gcloud aiplatform."""

from __future__ import absolute_import
from __future__ import division
from __future__ import unicode_literals

import argparse
import sys
import textwrap

from googlecloudsdk.api_lib.util import apis

from googlecloudsdk.calliope import actions
from googlecloudsdk.calliope import arg_parsers
from googlecloudsdk.calliope import base
from googlecloudsdk.calliope.concepts import concepts
from googlecloudsdk.calliope.concepts import deps
from googlecloudsdk.command_lib.ai import constants
from googlecloudsdk.command_lib.ai import errors
from googlecloudsdk.command_lib.ai import region_util
from googlecloudsdk.command_lib.iam import iam_util as core_iam_util
from googlecloudsdk.command_lib.kms import resource_args as kms_resource_args
from googlecloudsdk.command_lib.util.apis import arg_utils
from googlecloudsdk.command_lib.util.concepts import concept_parsers
from googlecloudsdk.core import properties

CUSTOM_JOB_NAME = base.Argument('name', help=('Custom job\'s name to query.'))
CUSTOM_JOB_DISPLAY_NAME = base.Argument(
    '--display-name',
    required=True,
    help=('Display name of the custom job to create.'))
AIPLATFORM_REGION = base.Argument(
    '--region',
    help=(
        'Region of the AI Platform service to use. If not specified, the value '
        'of the `ai/region` config property is used. If that property '
        'is not configured, then you will be prompted to select a region. When '
        'you specify this flag, its value is stored in the `ai/region` '
        'config property.'),
    action=actions.StoreProperty(properties.VALUES.ai.region))
PYTHON_PACKGE_URIS = base.Argument(
    '--python-package-uris',
    metavar='PYTHON_PACKAGE_URIS',
    type=arg_parsers.ArgList(),
    help='The common python package uris that will be used by python image. '
    'e.g. --python-package-uri=path1,path2'
    'If customizing the python package is needed, please use config instead.')

CUSTOM_JOB_CONFIG = base.Argument(
    '--config',
    help="""
Path to the job configuration file. This file should be a YAML document containing a CustomJobSpec.
If an option is specified both in the configuration file **and** via command line arguments, the command line arguments
override the configuration file. Note that keys with underscore are invalid.

Example(YAML):

  workerPoolSpecs:
    machineSpec:
      machineType: n1-highmem-2
    replicaCount: 1
    containerSpec:
      imageUri: gcr.io/ucaip-test/ucaip-training-test
      args:
      - port=8500
      command:
      - start""")

WORKER_POOL_SPEC = base.Argument(
    '--worker-pool-spec',
    action='append',
    type=arg_parsers.ArgDict(
        spec={
            'replica-count': int,
            'machine-type': str,
            'container-image-uri': str,
            'python-image-uri': str,
            'python-module': str,
        },
        required_keys=['machine-type']),
    metavar='WORKER_POOL_SPEC',
    help="""
Define the worker pool configuration used by the custom job. You can specify multiple
worker pool specs in order to create a custom job with multiple worker pools.

The spec can contain the following fields, which are listed with corresponding
fields in the WorkerPoolSpec API message:

*machine-type*::: (Required): machineSpec.machineType
*replica-count*::: replicaCount
*container-image-uri*::: containerSpec.imageUri
*python-image-uri*::: pythonPackageSpec.executorImageUri
*python-module*::: pythonPackageSpec.pythonModule

For example:
`--worker-pool-spec=replica-count=1,machine-type=n1-highmem-2,container-image-uri=gcr.io/ucaip-test/ucaip-training-test`
""")

HPTUNING_JOB_DISPLAY_NAME = base.Argument(
    '--display-name',
    required=True,
    help=('Display name of the hyperparameter tuning job to create.'))

HPTUNING_MAX_TRIAL_COUNT = base.Argument(
    '--max-trial-count',
    type=int,
    default=1,
    help=('Desired total number of trials. The default value is 1.'))

HPTUNING_PARALLEL_TRIAL_COUNT = base.Argument(
    '--parallel-trial-count',
    type=int,
    default=1,
    help=(
        'Desired number of Trials to run in parallel. The default value is 1.'))

HPTUNING_JOB_CONFIG = base.Argument(
    '--config',
    required=True,
    help="""
Path to the job configuration file. This file should be a YAML document containing a HyperparameterTuningSpec.
If an option is specified both in the configuration file **and** via command line arguments, the command line arguments
override the configuration file.

Example(YAML):

  displayName: TestHpTuningJob
  maxTrialCount: 1
  parallelTrialCount: 1
  studySpec:
    metrics:
    - metricId: x
      goal: MINIMIZE
    parameters:
    - parameterId: z
      integerValueSpec:
        minValue: 1
        maxValue: 100
    algorithm: RANDOM_SEARCH
  trialJobSpec:
    workerPoolSpecs:
    - machineSpec:
        machineType: n1-standard-4
      replicaCount: 1
      containerSpec:
        imageUri: gcr.io/ucaip-test/ucaip-training-test
""")

_POLLING_INTERVAL_FLAG = base.Argument(
    '--polling-interval',
    type=arg_parsers.BoundedInt(1, sys.maxsize, unlimited=True),
    default=60,
    help=('Number of seconds to wait between efforts to fetch the latest '
          'log messages.'))

_ALLOW_MULTILINE_LOGS = base.Argument(
    '--allow-multiline-logs',
    action='store_true',
    default=False,
    help='Output multiline log messages as single records.')

_TASK_NAME = base.Argument(
    '--task-name',
    required=False,
    default=None,
    help='If set, display only the logs for this particular task.')

_CUSTOM_JOB_COMMAND = base.Argument(
    '--command',
    type=arg_parsers.ArgList(),
    metavar='COMMAND',
    action=arg_parsers.UpdateAction,
    help="""\
Command to be invoked when containers are started.
It overrides the entrypoint instruction in Dockerfile when provided.
""")
_CUSTOM_JOB_ARGS = base.Argument(
    '--args',
    metavar='ARG',
    type=arg_parsers.ArgList(),
    action=arg_parsers.UpdateAction,
    help="""\
Comma-separated arguments passed to containers or python tasks.
""")

_NETWORK = base.Argument(
    '--network',
    help=textwrap.dedent("""\
      Full name of the Google Compute Engine network to which the Job
      is peered with. Private services access must already have been configured.
      If unspecified, the Job is not peered with any network.
      """))

_TRAINING_SERVICE_ACCOUNT = base.Argument(
    '--service-account',
    type=core_iam_util.GetIamAccountFormatValidator(),
    required=False,
    help=textwrap.dedent("""\
      The email address of a service account to use when running the
      training appplication. You must have the `iam.serviceAccounts.actAs`
      permission for the specified service account.
      """))


def AddCreateCustomJobFlags(parser):
  """Adds flags related to create a custom job."""
  AddRegionResourceArg(parser, 'to create a custom job')
  CUSTOM_JOB_DISPLAY_NAME.AddToParser(parser)
  PYTHON_PACKGE_URIS.AddToParser(parser)
  _CUSTOM_JOB_ARGS.AddToParser(parser)
  _CUSTOM_JOB_COMMAND.AddToParser(parser)
  _TRAINING_SERVICE_ACCOUNT.AddToParser(parser)
  _NETWORK.AddToParser(parser)
  AddKmsKeyResourceArg(parser, 'custom job')
  worker_pool_spec_group = base.ArgumentGroup(
      help='Worker pool specification.', required=True)
  worker_pool_spec_group.AddArgument(CUSTOM_JOB_CONFIG)
  worker_pool_spec_group.AddArgument(WORKER_POOL_SPEC)
  worker_pool_spec_group.AddToParser(parser)


def AddStreamLogsFlags(parser):
  _POLLING_INTERVAL_FLAG.AddToParser(parser)
  _TASK_NAME.AddToParser(parser)
  _ALLOW_MULTILINE_LOGS.AddToParser(parser)


def GetModelIdArg(required=True):
  return base.Argument(
      '--model', help='Id of the uploaded model.', required=required)


def GetDeployedModelId(required=True):
  return base.Argument(
      '--deployed-model-id',
      help='Id of the deployed model.',
      required=required)


def GetIndexIdArg(required=True, helper_text='ID of the index.'):
  return base.Argument('--index', help=helper_text, required=required)


def GetDeployedIndexId(required=True):
  return base.Argument(
      '--deployed-index-id',
      help='Id of the deployed index.',
      required=required)


def GetDisplayNameArg(noun, required=True):
  return base.Argument(
      '--display-name',
      required=required,
      help='Display name of the {noun}.'.format(noun=noun))


def GetDescriptionArg(noun):
  return base.Argument(
      '--description',
      required=False,
      default=None,
      help='Description of the {noun}.'.format(noun=noun))


def AddPredictInstanceArg(parser, required=True):
  """Add arguments for different types of predict instances."""
  base.Argument(
      '--json-request',
      required=required,
      help="""\
      Path to a local file containing the body of a JSON request.

      An example of a JSON request:

          {
            "instances": [
              {"x": [1, 2], "y": [3, 4]},
              {"x": [-1, -2], "y": [-3, -4]}
            ]
          }

      This flag accepts "-" for stdin.
      """).AddToParser(parser)


def GetTrafficSplitArg():
  """Add arguments for traffic split."""
  return base.Argument(
      '--traffic-split',
      metavar='DEPLOYED_MODEL_ID=VALUE',
      type=arg_parsers.ArgDict(value_type=int),
      action=arg_parsers.UpdateAction,
      help=('List of paris of deployed model id and value to set as traffic '
            'split.'))


def AddTrafficSplitGroupArgs(parser):
  """Add arguments for traffic split."""
  group = parser.add_mutually_exclusive_group(required=False)
  group.add_argument(
      '--traffic-split',
      metavar='DEPLOYED_MODEL_ID=VALUE',
      type=arg_parsers.ArgDict(value_type=int),
      action=arg_parsers.UpdateAction,
      help=('List of paris of deployed model id and value to set as traffic '
            'split.'))

  group.add_argument(
      '--clear-traffic-split',
      action='store_true',
      help=('Clears the traffic split map. If the map is empty, the endpoint '
            'is to not accept any traffic at the moment.'))


def AddPredictionResourcesArgs(parser, version):
  """Add arguments for prediction resources."""
  base.Argument(
      '--min-replica-count',
      type=arg_parsers.BoundedInt(1, sys.maxsize, unlimited=True),
      help=("""\
Minimum number of machine replicas the deployed model will be always deployed
on. If specified, the value must be equal to or larger than 1.

If not specified and the uploaded models use dedicated resources, the default
value is 1.
""")).AddToParser(parser)

  base.Argument(
      '--max-replica-count',
      type=int,
      help=('Maximum number of machine replicas the deployed model will be '
            'always deployed on.')).AddToParser(parser)

  base.Argument(
      '--machine-type',
      help="""\
The machine resources to be used for each node of this deployment.
For available machine types, see
https://cloud.google.com/ai-platform-unified/docs/predictions/machine-types.
""").AddToParser(parser)

  base.Argument(
      '--accelerator',
      type=arg_parsers.ArgDict(
          spec={
              'type': str,
              'count': int,
          }, required_keys=['type']),
      help="""\
Manage the accelerator config for GPU serving. When deploying a model with
Compute Engine Machine Types, a GPU accelerator may also
be selected.

*type*::: The type of the accelerator. Choices are {}.

*count*::: The number of accelerators to attach to each machine running the job.
 This is usually 1. If not specified, the default value is 1.

For example:
`--accelerator=type=nvidia-tesla-k80,count=1`""".format(', '.join([
    "'{}'".format(c) for c in GetAcceleratorTypeMapper(version).choices
  ]))).AddToParser(parser)


def GetAutoscalingMetricSpecsArg():
  """Add arguments for autoscaling metric specs."""
  return base.Argument(
      '--autoscaling-metric-specs',
      metavar='METRIC-NAME=TARGET',
      type=arg_parsers.ArgDict(key_type=str, value_type=int),
      action=arg_parsers.UpdateAction,
      help="""\
Metric specifications that overrides a resource utilization metric's target
value. At most one entry is allowed per metric.

*METRIC-NAME*::: Resource metric name. Choices are {}.

*TARGET*::: Target resource utilization in percentage (1% - 100%) for the
given metric. If the value is set to 60, the target resource utilization is 60%.

For example:
`--autoscaling-metric-specs=cpu-usage=70`
""".format(', '.join([
    "'{}'".format(c)
    for c in sorted(constants.OP_AUTOSCALING_METRIC_NAME_MAPPER.keys())]
                     )))


def AddAutomaticResourcesArgs(parser, resource_type):
  """Add arguments for automatic deployment resources."""
  base.Argument(
      '--min-replica-count',
      type=arg_parsers.BoundedInt(1, sys.maxsize, unlimited=True),
      help=("""\
Minimum number of machine replicas the {} will be always deployed
on. If specified, the value must be equal to or larger than 1.
""".format(resource_type))).AddToParser(parser)

  base.Argument(
      '--max-replica-count',
      type=int,
      help=('Maximum number of machine replicas the {} will be '
            'always deployed on.'.format(resource_type))).AddToParser(parser)


def GetEnableAccessLoggingArg():
  return base.Argument(
      '--enable-access-logging',
      action='store_true',
      default=False,
      required=False,
      help="""\
If true, online prediction access logs are sent to Cloud Logging.

These logs are standard server access logs, containing information like
timestamp and latency for each prediction request.
""")


def GetEnableContainerLoggingArg():
  return base.Argument(
      '--enable-container-logging',
      action='store_true',
      default=False,
      required=False,
      help="""\
If true, the container of the deployed model instances will send `stderr` and
`stdout` streams to Cloud Logging.

Currently, only supported for custom-trained Models and AutoML Tabular Models.
""")


def GetDisableContainerLoggingArg():
  return base.Argument(
      '--disable-container-logging',
      action='store_true',
      default=False,
      required=False,
      help="""\
For custom-trained Models and AutoML Tabular Models, the container of the
deployed model instances will send `stderr` and `stdout` streams to
Cloud Logging by default. Please note that the logs incur cost,
which are subject to [Cloud Logging
pricing](https://cloud.google.com/stackdriver/pricing).

User can disable container logging by setting this flag to true.
""")


def GetServiceAccountArg():
  return base.Argument(
      '--service-account',
      required=False,
      help="""\
Service account that the deployed model's container runs as. Specify the
email address of the service account. If this service account is not
specified, the container runs as a service account that doesn't have access
to the resource project.
""")


def RegionAttributeConfig(prompt_func=region_util.PromptForRegion):
  return concepts.ResourceParameterAttributeConfig(
      name='region',
      help_text='Cloud region for the {resource}.',
      fallthroughs=[
          deps.PropertyFallthrough(properties.VALUES.ai.region),
          deps.Fallthrough(function=prompt_func, hint='region')
      ])


def GetRegionResourceSpec(prompt_func=region_util.PromptForRegion):
  return concepts.ResourceSpec(
      'aiplatform.projects.locations',
      resource_name='region',
      locationsId=RegionAttributeConfig(prompt_func=prompt_func),
      projectsId=concepts.DEFAULT_PROJECT_ATTRIBUTE_CONFIG)


def GetModelResourceSpec(
    resource_name='model', prompt_func=region_util.PromptForRegion):
  return concepts.ResourceSpec(
      'aiplatform.projects.locations.models',
      resource_name=resource_name,
      projectsId=concepts.DEFAULT_PROJECT_ATTRIBUTE_CONFIG,
      locationsId=RegionAttributeConfig(prompt_func=prompt_func),
      disable_auto_completers=False)


def AddRegionResourceArg(parser, verb, prompt_func=region_util.PromptForRegion):
  """Add a resource argument for a cloud AI Platform region.

  NOTE: Must be used only if it's the only resource arg in the command.

  Args:
    parser: the parser for the command.
    verb: str, the verb to describe the resource, such as 'to update'.
    prompt_func: function, the function to prompt for region from list of
      available regions which returns a string for the region selected.
      Default is region_util.PromptForRegion which contains three regions,
      'us-central1', 'europe-west4', and 'asia-east1'.
  """
  concept_parsers.ConceptParser.ForResource(
      '--region',
      GetRegionResourceSpec(prompt_func=prompt_func),
      'Cloud region {}.'.format(verb),
      required=True).AddToParser(parser)


def GetDefaultOperationResourceSpec():
  return concepts.ResourceSpec(
      constants.DEFAULT_OPERATION_COLLECTION,
      resource_name='operation',
      projectsId=concepts.DEFAULT_PROJECT_ATTRIBUTE_CONFIG,
      locationsId=RegionAttributeConfig(),
      disable_auto_completers=False)


def AddOperationResourceArg(parser):
  """Add a resource argument for a cloud AI Platform operation."""
  resource_name = 'operation'
  concept_parsers.ConceptParser.ForResource(
      resource_name,
      GetDefaultOperationResourceSpec(),
      'The ID of the operation.',
      required=True).AddToParser(parser)


def AddModelResourceArg(parser, verb, prompt_func=region_util.PromptForRegion):
  """Add a resource argument for a cloud AI Platform model.

  NOTE: Must be used only if it's the only resource arg in the command.

  Args:
    parser: the parser for the command.
    verb: str, the verb to describe the resource, such as 'to update'.
    prompt_func: function, the function to prompt for region from list of
      available regions which returns a string for the region selected.
      Default is region_util.PromptForRegion which contains three regions,
      'us-central1', 'europe-west4', and 'asia-east1'.
  """
  name = 'model'
  concept_parsers.ConceptParser.ForResource(
      name, GetModelResourceSpec(prompt_func=prompt_func),
      'Model {}.'.format(verb), required=True).AddToParser(parser)


def AddUploadModelFlags(parser, prompt_func=region_util.PromptForRegion):
  """Adds flags for UploadModel.

  Args:
    parser: the parser for the command.
    prompt_func: function, the function to prompt for region from list of
      available regions which returns a string for the region selected.
      Default is region_util.PromptForRegion which contains three regions,
      'us-central1', 'europe-west4', and 'asia-east1'.
  """
  AddRegionResourceArg(parser, 'to upload model', prompt_func=prompt_func)
  base.Argument(
      '--display-name', required=True,
      help=('Display name of the model.')).AddToParser(parser)
  base.Argument(
      '--description', required=False,
      help=('Description of the model.')).AddToParser(parser)
  base.Argument(
      '--container-image-uri',
      required=True,
      help=("""\
URI of the Model serving container file in the Container Registry
(e.g. gcr.io/myproject/server:latest).
""")).AddToParser(parser)
  base.Argument(
      '--artifact-uri',
      help=("""\
Path to the directory containing the Model artifact and any of its
supporting files.
""")).AddToParser(parser)
  parser.add_argument(
      '--container-env-vars',
      metavar='KEY=VALUE',
      type=arg_parsers.ArgDict(),
      action=arg_parsers.UpdateAction,
      help='List of key-value pairs to set as environment variables.')
  parser.add_argument(
      '--container-command',
      type=arg_parsers.ArgList(),
      metavar='COMMAND',
      action=arg_parsers.UpdateAction,
      help="""\
Entrypoint for the container image. If not specified, the container
image's default entrypoint is run.
""")
  parser.add_argument(
      '--container-args',
      metavar='ARG',
      type=arg_parsers.ArgList(),
      action=arg_parsers.UpdateAction,
      help="""\
Comma-separated arguments passed to the command run by the container
image. If not specified and no `--command` is provided, the container
image's default command is used.
""")
  parser.add_argument(
      '--container-ports',
      metavar='PORT',
      type=arg_parsers.ArgList(element_type=arg_parsers.BoundedInt(1, 65535)),
      action=arg_parsers.UpdateAction,
      help="""\
Container ports to receive requests at. Must be a number between 1 and 65535,
inclusive.
""")
  parser.add_argument(
      '--container-predict-route',
      help='HTTP path to send prediction requests to inside the container.')
  parser.add_argument(
      '--container-health-route',
      help='HTTP path to send health checks to inside the container.')


def AddUploadModelBetaFlags(parser):
  """Adds additional flags for v1beta1 UploadModel."""

  # For Explanation.
  parser.add_argument(
      '--explanation-method',
      help='Method used for explanation. Accepted values are `integrated-gradients`, `xrai` and `sampled-shapley`.'
  )
  parser.add_argument(
      '--explanation-metadata-file',
      help='Path to a local JSON file that contains the metadata describing the Model\'s input and output for explanation.'
  )
  parser.add_argument(
      '--explanation-step-count',
      type=int,
      help='Number of steps to approximate the path integral for explanation.')
  parser.add_argument(
      '--explanation-path-count',
      type=int,
      help='Number of feature permutations to consider when approximating the Shapley values for explanation.'
  )
  parser.add_argument(
      '--smooth-grad-noisy-sample-count',
      type=int,
      help='Number of gradient samples used for approximation at explanation. Only applicable to explanation method `integrated-gradients` or `xrai`.'
  )
  parser.add_argument(
      '--smooth-grad-noise-sigma',
      type=float,
      help='Single float value used to add noise to all the features for explanation. Only applicable to explanation method `integrated-gradients` or `xrai`.'
  )
  parser.add_argument(
      '--smooth-grad-noise-sigma-by-feature',
      metavar='KEY=VALUE',
      type=arg_parsers.ArgDict(),
      action=arg_parsers.UpdateAction,
      help='Noise sigma by features for explanation. Noise sigma represents the standard deviation of the gaussian kernel that will be used to add noise to interpolated inputs prior to computing gradients. Only applicable to explanation method `integrated-gradients` or `xrai`.'
  )


def GetMetadataFilePathArg(noun, required=False):
  return base.Argument(
      '--metadata-file',
      required=required,
      help='Path to a local JSON file that contains the additional metadata information about the {noun}.'
      .format(noun=noun))


def GetMetadataSchemaUriArg(noun):
  return base.Argument(
      '--metadata-schema-uri',
      required=False,
      help='Points to a YAML file stored on Google Cloud Storage describing additional information about {noun}.'
      .format(noun=noun))


def AddIndexResourceArg(parser, verb):
  """Add a resource argument for a cloud AI Platform index.

  NOTE: Must be used only if it's the only resource arg in the command.

  Args:
    parser: the parser for the command.
    verb: str, the verb to describe the resource, such as 'to update'.
  """
  concept_parsers.ConceptParser.ForResource(
      'index', GetIndexResourceSpec(), 'Index {}.'.format(verb),
      required=True).AddToParser(parser)


def GetIndexResourceSpec(resource_name='index'):
  return concepts.ResourceSpec(
      constants.INDEXES_COLLECTION,
      resource_name=resource_name,
      projectsId=concepts.DEFAULT_PROJECT_ATTRIBUTE_CONFIG,
      locationsId=RegionAttributeConfig(),
      disable_auto_completers=False)


def GetEndpointId():
  return base.Argument('name', help='The endpoint\'s id.')


def GetEndpointResourceSpec(
    resource_name='endpoint', prompt_func=region_util.PromptForRegion):
  return concepts.ResourceSpec(
      constants.ENDPOINTS_COLLECTION,
      resource_name=resource_name,
      projectsId=concepts.DEFAULT_PROJECT_ATTRIBUTE_CONFIG,
      locationsId=RegionAttributeConfig(prompt_func=prompt_func),
      disable_auto_completers=False)


def AddEndpointResourceArg(
    parser, verb, prompt_func=region_util.PromptForRegion):
  """Add a resource argument for a Cloud AI Platform endpoint.

  NOTE: Must be used only if it's the only resource arg in the command.

  Args:
    parser: the parser for the command.
    verb: str, the verb to describe the resource, such as 'to update'.
    prompt_func: function, the function to prompt for region from list of
      available regions. Default is region_util.PromptForRegion which contains
      three regions, 'us-central1', 'europe-west4', and 'asia-east1'.
  """
  concept_parsers.ConceptParser.ForResource(
      'endpoint',
      GetEndpointResourceSpec(prompt_func=prompt_func),
      'The endpoint {}.'.format(verb),
      required=True).AddToParser(parser)


def AddIndexEndpointResourceArg(parser, verb):
  """Add a resource argument for a cloud AI Platform index endpoint.

  NOTE: Must be used only if it's the only resource arg in the command.

  Args:
    parser: the parser for the command.
    verb: str, the verb to describe the resource, such as 'to update'.
  """
  concept_parsers.ConceptParser.ForResource(
      'index_endpoint',
      GetIndexEndpointResourceSpec(),
      'The index endpoint {}.'.format(verb),
      required=True).AddToParser(parser)


def GetIndexEndpointResourceSpec(resource_name='index_endpoint'):
  return concepts.ResourceSpec(
      constants.INDEX_ENDPOINTS_COLLECTION,
      resource_name=resource_name,
      projectsId=concepts.DEFAULT_PROJECT_ATTRIBUTE_CONFIG,
      locationsId=RegionAttributeConfig(),
      disable_auto_completers=False)


# TODO(b/357812579): Consider switch to use resource arg.
def GetNetworkArg(required=True):
  """Add arguments for VPC network."""
  return base.Argument(
      '--network',
      required=required,
      help="""
      The Google Compute Engine network name to which the IndexEndpoint should be peered.
      """)


def TensorboardRunAttributeConfig():
  return concepts.ResourceParameterAttributeConfig(
      name='tensorboard-run-id',
      help_text='ID of the tensorboard run for the {resource}.')


def TensorboardExperimentAttributeConfig():
  return concepts.ResourceParameterAttributeConfig(
      name='tensorboard-experiment-id',
      help_text='ID of the tensorboard experiment for the {resource}.')


def TensorboardAttributeConfig():
  return concepts.ResourceParameterAttributeConfig(
      name='tensorboard-id',
      help_text='ID of the tensorboard for the {resource}.')


def GetTensorboardTimeSeriesResourceSpec(
    resource_name='tensorboard_time_series'):
  return concepts.ResourceSpec(
      constants.TENSORBOARD_TIME_SERIES_COLLECTION,
      resource_name=resource_name,
      tensorboardsId=TensorboardAttributeConfig(),
      experimentsId=TensorboardExperimentAttributeConfig(),
      runsId=TensorboardRunAttributeConfig(),
      projectsId=concepts.DEFAULT_PROJECT_ATTRIBUTE_CONFIG,
      locationsId=RegionAttributeConfig(),
      disable_auto_completers=False)


def GetTensorboardRunResourceSpec(
    resource_name='tensorboard_run'):
  return concepts.ResourceSpec(
      constants.TENSORBOARD_RUNS_COLLECTION,
      resource_name=resource_name,
      tensorboardsId=TensorboardAttributeConfig(),
      experimentsId=TensorboardExperimentAttributeConfig(),
      projectsId=concepts.DEFAULT_PROJECT_ATTRIBUTE_CONFIG,
      locationsId=RegionAttributeConfig(),
      disable_auto_completers=False)


def GetTensorboardExperimentResourceSpec(
    resource_name='tensorboard_experiment'):
  return concepts.ResourceSpec(
      constants.TENSORBOARD_EXPERIMENTS_COLLECTION,
      resource_name=resource_name,
      tensorboardsId=TensorboardAttributeConfig(),
      projectsId=concepts.DEFAULT_PROJECT_ATTRIBUTE_CONFIG,
      locationsId=RegionAttributeConfig(),
      disable_auto_completers=False)


def GetTensorboardResourceSpec(resource_name='tensorboard'):
  return concepts.ResourceSpec(
      constants.TENSORBOARDS_COLLECTION,
      resource_name=resource_name,
      projectsId=concepts.DEFAULT_PROJECT_ATTRIBUTE_CONFIG,
      locationsId=RegionAttributeConfig(),
      disable_auto_completers=False)


def AddTensorboardTimeSeriesResourceArg(parser, verb):
  """Add a resource argument for a Cloud AI Platform Tensorboard time series.

  NOTE: Must be used only if it's the only resource arg in the command.

  Args:
    parser: the parser for the command.
    verb: str, the verb to describe the resource, such as 'to update'.
  """
  concept_parsers.ConceptParser.ForResource(
      'tensorboard_time_series',
      GetTensorboardTimeSeriesResourceSpec(),
      'The Tensorboard time series {}.'.format(verb),
      required=True).AddToParser(parser)


def AddTensorboardRunResourceArg(parser, verb):
  """Add a resource argument for a Cloud AI Platform Tensorboard run.

  NOTE: Must be used only if it's the only resource arg in the command.

  Args:
    parser: the parser for the command.
    verb: str, the verb to describe the resource, such as 'to update'.
  """
  concept_parsers.ConceptParser.ForResource(
      'tensorboard_run',
      GetTensorboardRunResourceSpec(),
      'The Tensorboard run {}.'.format(verb),
      required=True).AddToParser(parser)


def AddTensorboardExperimentResourceArg(parser, verb):
  """Add a resource argument for a Cloud AI Platform Tensorboard experiment.

  NOTE: Must be used only if it's the only resource arg in the command.

  Args:
    parser: the parser for the command.
    verb: str, the verb to describe the resource, such as 'to update'.
  """
  concept_parsers.ConceptParser.ForResource(
      'tensorboard_experiment',
      GetTensorboardExperimentResourceSpec(),
      'The Tensorboard experiment {}.'.format(verb),
      required=True).AddToParser(parser)


def AddTensorboardResourceArg(parser, verb):
  """Add a resource argument for a Cloud AI Platform Tensorboard.

  NOTE: Must be used only if it's the only resource arg in the command.

  Args:
    parser: the parser for the command.
    verb: str, the verb to describe the resource, such as 'to update'.
  """
  concept_parsers.ConceptParser.ForResource(
      'tensorboard',
      GetTensorboardResourceSpec(),
      'The tensorboard {}.'.format(verb),
      required=True).AddToParser(parser)


def GetTensorboardExperimentIdArg(required=True):
  return base.Argument(
      '--tensorboard-experiment-id',
      help='Id of the Tensorboard experiment.',
      required=required)


def GetTensorboardRunIdArg(required=True):
  return base.Argument(
      '--tensorboard-run-id',
      help='ID of the Tensorboard run.',
      required=required)


def GetPluginNameArg(noun):
  return base.Argument(
      '--plugin-name',
      required=False,
      default=None,
      help='Plugin name of the {noun}.'.format(noun=noun))


def GetPluginDataArg(noun):
  return base.Argument(
      '--plugin-data',
      required=False,
      default=None,
      help='Plugin data of the {noun}.'.format(noun=noun))


def AddTensorboardTimeSeriesMaxDataPointsArg():
  return base.Argument(
      '--max-data-points',
      type=int,
      help='Max data points to read from the Tensorboard time series')


def AddFilterArg(noun):
  return base.Argument(
      '--filter',
      default=None,
      help='Filter for the {noun}.'.format(noun=noun))


def ParseAcceleratorFlag(accelerator, version):
  """Validates and returns a accelerator config message object."""
  if accelerator is None:
    return None
  types = list(c for c in GetAcceleratorTypeMapper(version).choices)
  raw_type = accelerator.get('type', None)
  if raw_type not in types:
    raise errors.ArgumentError("""\
The type of the accelerator can only be one of the following: {}.
""".format(', '.join(["'{}'".format(c) for c in types])))
  accelerator_count = accelerator.get('count', 1)
  if accelerator_count <= 0:
    raise errors.ArgumentError("""\
The count of the accelerator must be greater than 0.
""")
  if version == constants.ALPHA_VERSION:
    accelerator_msg = (
        apis
        .GetMessagesModule(constants.AI_PLATFORM_API_NAME,
                           constants.AI_PLATFORM_API_VERSION[version])
        .GoogleCloudAiplatformV1alpha1MachineSpec)
  elif version == constants.BETA_VERSION:
    accelerator_msg = (
        apis
        .GetMessagesModule(constants.AI_PLATFORM_API_NAME,
                           constants.AI_PLATFORM_API_VERSION[version])
        .GoogleCloudAiplatformV1beta1MachineSpec)
  else:
    accelerator_msg = (
        apis
        .GetMessagesModule(constants.AI_PLATFORM_API_NAME,
                           constants.AI_PLATFORM_API_VERSION[version])
        .GoogleCloudAiplatformV1MachineSpec)
  accelerator_type = arg_utils.ChoiceToEnum(
      raw_type, accelerator_msg.AcceleratorTypeValueValuesEnum)
  return accelerator_msg(
      acceleratorCount=accelerator_count, acceleratorType=accelerator_type)


def GetAcceleratorTypeMapper(version):
  """Get a mapper for accelerator type to enum value."""
  if version == constants.ALPHA_VERSION:
    return arg_utils.ChoiceEnumMapper(
        'generic-accelerator',
        apis
        .GetMessagesModule(constants.AI_PLATFORM_API_NAME,
                           constants.AI_PLATFORM_API_VERSION[version])
        .GoogleCloudAiplatformV1alpha1MachineSpec
        .AcceleratorTypeValueValuesEnum,
        help_str='The available types of accelerators.',
        include_filter=lambda x: x.startswith('NVIDIA'),
        required=False)
  elif version == constants.BETA_VERSION:
    return arg_utils.ChoiceEnumMapper(
        'generic-accelerator',
        apis
        .GetMessagesModule(constants.AI_PLATFORM_API_NAME,
                           constants.AI_PLATFORM_API_VERSION[version])
        .GoogleCloudAiplatformV1beta1MachineSpec
        .AcceleratorTypeValueValuesEnum,
        help_str='The available types of accelerators.',
        include_filter=lambda x: x.startswith('NVIDIA'),
        required=False)
  return arg_utils.ChoiceEnumMapper(
      'generic-accelerator',
      apis
      .GetMessagesModule(constants.AI_PLATFORM_API_NAME,
                         constants.AI_PLATFORM_API_VERSION[version])
      .GoogleCloudAiplatformV1MachineSpec
      .AcceleratorTypeValueValuesEnum,
      help_str='The available types of accelerators.',
      include_filter=lambda x: x.startswith('NVIDIA'),
      required=False)


def AddCreateHpTuningJobFlags(parser, algorithm_enum):
  """Add arguments for creating hp tuning job."""
  AddRegionResourceArg(parser, 'to upload model')
  HPTUNING_JOB_DISPLAY_NAME.AddToParser(parser)
  HPTUNING_JOB_CONFIG.AddToParser(parser)
  HPTUNING_MAX_TRIAL_COUNT.AddToParser(parser)
  HPTUNING_PARALLEL_TRIAL_COUNT.AddToParser(parser)
  _TRAINING_SERVICE_ACCOUNT.AddToParser(parser)
  _NETWORK.AddToParser(parser)
  AddKmsKeyResourceArg(parser, 'hyperparameter tuning job')

  arg_utils.ChoiceEnumMapper(
      '--algorithm',
      algorithm_enum,
      help_str='Search algorithm specified for the given study. '
  ).choice_arg.AddToParser(parser)


def GetCustomJobResourceSpec(resource_name='custom_job'):
  return concepts.ResourceSpec(
      constants.CUSTOM_JOB_COLLECTION,
      resource_name=resource_name,
      projectsId=concepts.DEFAULT_PROJECT_ATTRIBUTE_CONFIG,
      locationsId=RegionAttributeConfig(),
      disable_auto_completers=False)


def AddCustomJobResourceArg(parser, verb):
  """Add a resource argument for a Cloud AI Platform custom job.

  NOTE: Must be used only if it's the only resource arg in the command.

  Args:
    parser: the parser for the command.
    verb: str, the verb to describe the resource, such as 'to update'.
  """
  concept_parsers.ConceptParser.ForResource(
      'custom_job',
      GetCustomJobResourceSpec(),
      'The custom job {}.'.format(verb),
      required=True).AddToParser(parser)


def GetHptuningJobResourceSpec(resource_name='hptuning_job'):
  return concepts.ResourceSpec(
      constants.HPTUNING_JOB_COLLECTION,
      resource_name=resource_name,
      projectsId=concepts.DEFAULT_PROJECT_ATTRIBUTE_CONFIG,
      locationsId=RegionAttributeConfig(),
      disable_auto_completers=False)


def AddHptuningJobResourceArg(parser, verb):
  """Add a resource argument for a Cloud AI Platform hyperparameter tuning  job.

  NOTE: Must be used only if it's the only resource arg in the command.

  Args:
    parser: the parser for the command.
    verb: str, the verb to describe the resource, such as 'to update'.
  """
  concept_parsers.ConceptParser.ForResource(
      'hptuning_job',
      GetHptuningJobResourceSpec(),
      'The hyperparameter tuning job {}.'.format(verb),
      required=True).AddToParser(parser)


def AddKmsKeyResourceArg(parser, resource):
  """Add the --kms-key resource arg to the given parser."""
  permission_info = ("The 'AI Platform Service Agent' service account must hold"
                     " permission 'Cloud KMS CryptoKey Encrypter/Decrypter'")
  kms_resource_args.AddKmsKeyResourceArg(
      parser, resource, permission_info=permission_info)


def AddLocalRunCustomJobFlags(parser):
  """Add local-run related flags to the parser."""

  # Flags for entry point of the training application
  application_group = parser.add_mutually_exclusive_group(required=True)
  application_group.add_argument(
      '--python-module',
      metavar='PYTHON_MODULE',
      help=textwrap.dedent("""
      Name of the python module to execute, in 'trainer.train' or 'train'
      format. Its path should be relative to the `work_dir`.
      """))
  application_group.add_argument(
      '--script',
      metavar='SCRIPT',
      help=textwrap.dedent("""
      The relative path of the file to execute. Accepets a Python file,
      IPYNB file, or arbitrary bash script. This path should be relative to the
      `work_dir`.
      """))

  # Flags for working directory.
  parser.add_argument(
      '--work-dir',
      metavar='WORK_DIR',
      help=textwrap.dedent("""
      Path of the working directory where the python-module or script exists.
      If not specified, it use the directory where you run the this command.

      Only the contents of this directory will be accessible to the built
      container image.
      """))

  # Flags for extra directory
  parser.add_argument(
      '--extra-dirs',
      metavar='EXTRA_DIR',
      type=arg_parsers.ArgList(),
      help=textwrap.dedent("""
      Extra directories under the working directory to include, besides the one
      that contains the main executable.

      By default, only the parent directory of the main script or python module
      is copied to the container.
      For example, if the module is "training.task" or the script is
      "training/task.py", the whole "training" directory, including its
      sub-directories, will always be copied to the container. You may specify
      this flag to also copy other directories if necessary.

      Note: if no parent is specified in 'python_module' or 'scirpt', the whole
      working directory is copied, then you don't need to specify this flag.
      """))

  # Flags for base container image
  parser.add_argument(
      '--base-image',
      metavar='BASE_IMAGE',
      required=True,
      help=textwrap.dedent("""
      URI or ID of the container image in either the Container Registry or local
      that will run the application.
      See https://cloud.google.com/ai-platform-unified/docs/training/pre-built-containers
      for available pre-built container images provided by AI Platform for training.
      """))

  # Flags for extra requirements.
  parser.add_argument(
      '--requirements',
      metavar='REQUIREMENTS',
      type=arg_parsers.ArgList(),
      help=textwrap.dedent("""
      Python dependencies from PyPI to be used when running the application.
      If this is not specified, and there is no "setup.py" or "requirements.txt"
      in the working directory, your application will only have access to what
      exists in the base image with on other dependencies.

      Example:
      'tensorflow-cpu, pandas==1.2.0, matplotlib>=3.0.2'
      """))

  # Flags for extra dependency .
  parser.add_argument(
      '--extra-packages',
      metavar='PACKAGE',
      type=arg_parsers.ArgList(),
      help=textwrap.dedent("""
      Local paths to Python archives used as training dependencies in the image
      container.
      These can be absolute or relative paths. However, they have to be under
      the work_dir; Otherwise, this tool will not be able to acces it.

      Example:
      'dep1.tar.gz, ./downloads/dep2.whl'
      """))

  # Flags for the output image
  parser.add_argument(
      '--output-image-uri',
      metavar='OUTPUT_IMAGE',
      help=textwrap.dedent("""
      Uri of the custom container image to be built with the your application
      packed in.
      """))

  # Flaga for GPU support
  parser.add_argument(
      '--gpu', action='store_true', default=False, help='Enable to use GPU.')

  # Flags for docker run
  parser.add_argument(
      '--docker-run-options',
      metavar='DOCKER_RUN_OPTIONS',
      type=arg_parsers.ArgList(),
      help=textwrap.dedent("""
      Custom Docker run options to pass to image during execution.
      For example, '--no-healthcheck, -a stdin'.

      See https://docs.docker.com/engine/reference/commandline/run/#options for
      more details.
      """))

  # User custom flags.
  parser.add_argument(
      'args',
      nargs=argparse.REMAINDER,
      default=[],
      help="""Additional user arguments to be forwarded to your application.""",
      example=('$ {command} --script=my_run.sh --base-image=gcr.io/my/image '
               '-- --my-arg bar --enable_foo'))
