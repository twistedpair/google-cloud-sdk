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
import itertools
import sys

from googlecloudsdk.api_lib.storage import storage_util
from googlecloudsdk.calliope import arg_parsers
from googlecloudsdk.calliope import base
from googlecloudsdk.core import exceptions
from googlecloudsdk.core import log


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
    # TODO(b/33234717) remove nargs=+ after deprecation period
    nargs='+',
    default=[],
    type=arg_parsers.ArgList(),
    metavar='PACKAGE',
    help='Path to Python archives used for training')
USER_ARGS = base.Argument(
    'user_args',
    nargs=argparse.REMAINDER,
    help='Additional user arguments to be fowarded to user code')
VERSION_NAME = base.Argument('version', help='Name of the model version.')
VERSION_DATA = base.Argument(
    '--origin',
    required=True,
    help='Location containing the model graph.',
    detailed_help="""\
Location of ```model/``` "directory" (as output by
https://www.tensorflow.org/versions/r0.12/api_docs/python/state_ops.html#Saver).

Can be a Google Cloud Storage (`gs://`) path or local file path (no prefix). In
the latter case the files will be uploaded to Google Cloud Storage and a
`--staging-bucket` argument is required.
""")

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
TASK_NAME = base.Argument(
    '--task-name',
    required=False,
    default=None,
    help='If set, display only the logs for this particular task.')


def GetModelName(positional=True, required=False):
  help_text = 'Name of the model.'
  if positional:
    return base.Argument('model', help=help_text)
  else:
    return base.Argument('--model', help=help_text, required=required)


# TODO(b/33234717): remove after PACKAGES nargs=+ deprecation period.
def ProcessPackages(args):
  """Flatten PACKAGES flag and warn if multiple arguments were used."""
  if args.packages is not None:
    if len(args.packages) > 1:
      log.warn('Use of --packages with space separated values is '
               'deprecated and will not work in the future. Use comma '
               'instead.')
    # flatten packages into a single list
    args.packages = list(itertools.chain.from_iterable(args.packages))


def GetStagingBucket(required):
  return base.Argument(
      '--staging-bucket',
      help='Bucket in which to stage training archives',
      type=storage_util.BucketReference.Argument,
      required=required)
