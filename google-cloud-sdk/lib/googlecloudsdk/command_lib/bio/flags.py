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

"""Provides common arguments for the Bio command surface."""

from googlecloudsdk.calliope import arg_parsers
from googlecloudsdk.calliope import base


# Operation flags
def GetOperationNameFlag(verb):
  return base.Argument(
      'name',
      metavar='OPERATION_NAME',
      help='Name for the operation you want to {0}.'.format(verb))


# DeepVariant flags
def GetPipelineInputPairFlag():
  return base.Argument(
      '--input-pair',
      type=arg_parsers.ArgList(min_length=2, max_length=2),
      metavar='FASTQ_PATH',
      required=True,
      help='''A comma-separated pair of Google Cloud Storage paths of the
        forward and reverse strand FASTQ files used as input.''')


def GetPipelineOutputPathFlag():
  return base.Argument(
      '--output-path',
      required=True,
      help='''The Google Cloud Storage path for copying the final output files.
        For example, `gs://<user_bucket>/<sample_name>/`.''')


def GetPipelineSampleNameFlag():
  return base.Argument(
      '--sample-name', required=True, help='''The sample name.''')


def GetPipelineLoggingFlag():
  return base.Argument(
      '--logging',
      required=True,
      metavar='LOGGING_PATH',
      help="""The location in Google Cloud Storage to which the
        pipeline logs will be copied. Can be specified as a fully qualified
        directory path, in which case logs will be output with a unique id
        as the filename in that directory, or as a fully specified path,
        which must end in `.log`, in which case that path will be
        used. Stdout and stderr logs from the run are also generated and
        output as `-stdout.log` and `-stderr.log`. For example,
        `gs://<user_bucket>/<log_path>`.""")


def GetPipelineZonesFlag():
  return base.Argument(
      '--zones',
      metavar='ZONE',
      type=arg_parsers.ArgList(),
      completion_resource='compute.zones',
      help="""A list of Google Compute Engine zones which may
        be used to run the pipeline. A zone with available quota will be
        randomly selected at the time of execution. If empty, any zone may
        be selected.""")
