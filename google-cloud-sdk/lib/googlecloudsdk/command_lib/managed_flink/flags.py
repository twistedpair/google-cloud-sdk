# -*- coding: utf-8 -*- #
# Copyright 2024 Google LLC. All Rights Reserved.
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
"""Flags and helpers for the Managed Flink CLI."""

import argparse
from googlecloudsdk.calliope import arg_parsers
from googlecloudsdk.calliope import base
from googlecloudsdk.command_lib.util import completers
from googlecloudsdk.command_lib.util import parameter_info_lib

_AUTOTUNING_MODES = {
    'fixed': 'The number of taskmanagers is fixed.',
    'elastic': (
        'The number of taskmanagers is scaled automatically according to'
        ' workload.'
    ),
}

# Completers


class ListCommandParameterInfo(parameter_info_lib.ParameterInfoByConvention):
  """Helper class for ListCommandCompleter."""

  def GetFlag(
      self,
      parameter_name,
      parameter_value=None,
      check_properties=True,
      for_update=False,
  ):
    return super(ListCommandParameterInfo, self).GetFlag(
        parameter_name,
        parameter_value,
        check_properties=check_properties,
        for_update=for_update,
    )


class ListCommandCompleter(completers.ListCommandCompleter):
  """Helper class for DeploymentCompleter."""

  def ParameterInfo(self, parsed_args, arguments):
    return ListCommandParameterInfo(
        parsed_args,
        arguments,
        self.collection,
        updaters=COMPLETERS_BY_CONVENTION,
    )


class DeploymentCompleter(ListCommandCompleter):
  """Completer for listing deployments."""

  def __init__(self, **kwargs):
    super(DeploymentCompleter, self).__init__(
        collection='managedflink.projects.locations.deployments',
        list_command='managed-flink deployments list',
        **kwargs,
    )


COMPLETERS_BY_CONVENTION = {'deployment': (DeploymentCompleter, False)}


# Flags
def AddNetworkConfigArgs(parser):
  """Adds network config arguments."""
  parser.add_argument(
      '--network-config-vpc',
      metavar='NETWORK',
      dest='network',
      help='The network to use for the job.',
  )
  parser.add_argument(
      '--network-config-subnetwork',
      metavar='SUBNETWORK',
      dest='subnetwork',
      help='The subnetwork to use for the job.',
  )


def AddWorkloadIdentityArgument(parser):
  """Adds workload identity argument."""
  parser.add_argument(
      '--workload-identity',
      metavar='WORKLOAD_IDENTITY',
      dest='workload_identity',
      help=(
          'The workload identity to use for the job. Managed Flink'
          ' Default Workload Identity will be used if not specified.'
      ),
  )


def AddLocationArgument(parser):
  """Creates location argument."""
  base.Argument(
      '--location',
      metavar='LOCATION',
      required=True,
      dest='location',
      suggestion_aliases=['--region'],
      help='The location to run the job in.',
  ).AddToParser(parser)


def AddJobTypeArgument(parser):
  """Job type arguments."""
  base.Argument(
      '--job-type',
      metavar='JOB_TYPE',
      choices=['auto', 'jar', 'python', 'sql'],
      default='auto',
      help=(
          'The type of job to run. If "auto" will be selected based on the file'
          ' extension for the job argument.'
      ),
  ).AddToParser(parser)


def AddJobJarArgument(parser):
  """Creates the job argument."""
  base.Argument(
      'job',
      metavar='JAR|PY|SQL',
      help=(
          'The file containing the Flink job to run. Can be a jar, python, or'
          ' sql file.'
      ),
  ).AddToParser(parser)


def AddExtraJarsArgument(parser):
  """Creates the extra jars argument."""
  base.Argument(
      '--jars',
      metavar='JAR',
      type=arg_parsers.ArgList(),
      dest='extra_jars',
      help=(
          'The extra jars to pass to the job. Can be a jar, python, or'
          ' sql file.'
      ),
  ).AddToParser(parser)


def AddDryRunArgument(parser):
  """Creates dry run argument."""
  base.Argument(
      '--dry-run',
      action='store_true',
      dest='dry_run',
      default=False,
      required=False,
      help='Return command used to submit a job without invoking API.',
  ).AddToParser(parser)


# This has been temporarily disabled. Commented out to avoid confusing
# test coverage.
# def AddManagedKafkaClustersArgument(parser):
#  """Creates the managed flink argument."""
#  base.Argument(
#      '--managed-kafka-clusters',
#      metavar='MANAGED_KAFKA_CLUSTERS',
#      dest='managed_kafka_clusters',
#      type=arg_parsers.ArgList(),
#      help='Specifies managed kafka clusters to associate with this job.',
#  ).AddToParser(parser)


def AddMainClassArgument(parser):
  """Creates main class argument."""
  base.Argument(
      '--class',
      metavar='CLASS',
      dest='main_class',
      help=(
          'The main class of the Flink job. Required if the jar file manifest'
          ' does not contain a main class.'
      ),
  ).AddToParser(parser)


def AddJobArgsCollector(parser):
  """Collects extra arguments into the job_args list."""
  parser.add_argument(
      'job_args',
      nargs=argparse.REMAINDER,
      help='The job arguments to pass.',
  )


def AddNameArgument(parser):
  """Creates name argument."""
  base.Argument(
      '--name',
      metavar='NAME',
      dest='name',
      required=False,
      help='The name of the job. The Flink job name will be used if not set.',
  ).AddToParser(parser)


def AddJobIdArgument(parser):
  """Creates job id argument."""
  base.Argument(
      'job_id',
      metavar='JOBID',
      help='The id of the job.',
  ).AddToParser(parser)


def AddAsyncArgument(parser, default=False):
  """Creates async argument."""
  base.Argument(
      '--async',
      action='store_true',
      dest='async_submit',
      default=default,
      required=False,
      help='Return immediately after job submission.',
  ).AddToParser(parser)


def AddStagingLocationArgument(parser):
  """Creates staging location argument."""
  base.Argument(
      '--staging-location',
      metavar='STAGING_LOCATION',
      dest='staging_location',
      required=True,
      help=(
          'The Google Cloud Storage staging location for the job. Must start'
          ' with gs://'
      ),
  ).AddToParser(parser)


def AddDeploymentArgument(
    parser,
    help_text_to_prepend=None,
    help_text_to_overwrite=None,
    required=False,
):
  """Creates deployment argument."""

  if help_text_to_overwrite:
    help_text = help_text_to_overwrite
  else:
    help_text = """
    The Flink Deployment to use for this invocation.
    """

  if help_text_to_prepend:
    help_text = '\n\n'.join((help_text_to_prepend, help_text))

  base.Argument(
      '--deployment',
      metavar='DEPLOYMENT_NAME',
      required=required,
      dest='deployment',
      completer=DeploymentCompleter,
      help=help_text,
  ).AddToParser(parser)


def AddAutotuningModeArgument(parser, default='elastic', required=False):
  """Creates autotuning mode argument."""

  base.Argument(
      '--autotuning-mode',
      metavar='AUTOTUNING_MODE',
      choices=_AUTOTUNING_MODES,
      default=default,
      required=required,
      dest='autotuning_mode',
      help='Selects the autotuning mode for jobs.',
  ).AddToParser(parser)


def AddFixedParallelismArgs(parser):
  """Adds fixed parallelism arguments."""
  parser.add_argument(
      '--parallelism',
      type=arg_parsers.BoundedInt(lower_bound=1, upper_bound=10000),
      help='The parallelism of the job when in "fixed" autotuning mode.',
  )


def AddElasticParallelismArgs(parser):
  """Adds elastic parallelism arguments."""
  parser.add_argument(
      '--min-parallelism',
      type=arg_parsers.BoundedInt(lower_bound=1, upper_bound=10000),
      help=(
          'The minimum parallelism of the job when in "elastic" autotuning'
          ' mode. This will also be the initial parallelism of the job.'
      ),
  )
  parser.add_argument(
      '--max-parallelism',
      type=arg_parsers.BoundedInt(lower_bound=1, upper_bound=10000),
      help=(
          'The maximum parallelism of the job when in "elastic" autotuning'
          ' mode.'
      ),
  )


def AddShowOutputArgument(parser):
  """Creates show output argument."""
  base.Argument(
      '--enable-output',
      action='store_true',
      dest='show_output',
      default=False,
      required=False,
      help='Shows the output of the Flink client.',
  ).AddToParser(parser)


def AddExtraArchivesArgument(parser):
  """Creates the extra archives argument."""
  base.Argument(
      '--archives',
      metavar='ZIP',
      type=arg_parsers.ArgList(),
      dest='archives',
      help=(
          'The extra archives to pass to the job. Can be a zip file containing'
          ' resource files for the job.'
      ),
  ).AddToParser(parser)


def AddPythonVirtualEnvArgument(parser):
  """Creates main class argument."""
  base.Argument(
      '--python-venv',
      metavar='ZIP',
      dest='python_venv',
      help=(
          'The path to the zip file to manage the virtualenv for Python'
          ' dependencies. Required if the job type is python. Must start with'
          ' gs://.'
      ),
  ).AddToParser(parser)
