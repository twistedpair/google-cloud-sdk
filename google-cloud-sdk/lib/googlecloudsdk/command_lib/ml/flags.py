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
"""Provides common arguments for the ML command surface."""
import argparse
import sys

from googlecloudsdk.api_lib.storage import storage_util
from googlecloudsdk.calliope import arg_parsers
from googlecloudsdk.calliope import base
from googlecloudsdk.core import exceptions


class ArgumentError(exceptions.Error):
  pass


# Run flags
DISTRIBUTED = base.Argument(
    '--distributed',
    action='store_true',
    default=False,
    help=('Runs the provided code in distributed mode by providing cluster '
          'configurations as environment variables to subprocesses'))
PARAM_SERVERS = base.Argument(
    '--parameter-server-count',
    type=int,
    help=('Number of parameter servers with which to run. '
          'Ignored if --distributed is not specified. Default: 2'))
WORKERS = base.Argument(
    '--worker-count',
    type=int,
    help=('Number of workers with which to run. '
          'Ignored if --distributed is not specified. Default: 2'))
START_PORT = base.Argument(
    '--start-port',
    type=int,
    default=27182,
    help=('Start of the range of ports reserved by the local cluster. '
          'Ignored if --distributed is not specified'))


# TODO(user): move these into a class
CONFIG = base.Argument('--config', help='Path to yaml configuration file.')
JOB_NAME = base.Argument('job', help='Name of the job.')
MODULE_NAME = base.Argument(
    '--module-name',
    required=True,
    help='Name of the module to run')
PACKAGE_PATH = base.Argument(
    '--package-path',
    help='Path to a Python package to build')
PACKAGES = base.Argument(
    '--packages',
    nargs='+',
    default=[],
    help='Path to .tar.gz archives of Python code to be used for training')
STAGING_BUCKET = base.Argument(
    '--staging-bucket',
    help='Bucket in which to stage training archives',
    type=storage_util.BucketReference.Argument,
    required=True)
USER_ARGS = base.Argument(
    'user_args',
    nargs=argparse.REMAINDER,
    help='Additional user arguments to be fowarded to user code')
VERSION_NAME = base.Argument('version', help='Name of the model version.')
VERSION_DATA = base.Argument(
    '--origin',
    required=True,
    help='Google Cloud Storage location containing the model graph.')
POLLING_INTERVAL = base.Argument(
    '--polling-interval',
    type=arg_parsers.BoundedInt(1, sys.maxint, unlimited=True),
    required=False,
    default=60,
    help='Number of seconds to wait between efforts to fetch the latest '
    'log messages.')
ALLOW_MULTILINE_LOGS = base.Argument(
    '--allow-multiline-logs',
    action='store_true',
    help='Output multiline log messages as single records.')


def GetModelName(positional=True, required=False):
  help_text = 'Name of the model.'
  if positional:
    return base.Argument('model', help=help_text)
  else:
    return base.Argument('--model', help=help_text, required=required)
