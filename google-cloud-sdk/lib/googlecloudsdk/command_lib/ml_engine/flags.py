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
"""Provides common arguments for the ML Engine command surface."""
import argparse
import functools
import itertools
import sys

from googlecloudsdk.api_lib.storage import storage_util
from googlecloudsdk.calliope import actions
from googlecloudsdk.calliope import arg_parsers
from googlecloudsdk.calliope import base
from googlecloudsdk.command_lib.iam import completers as iam_completers
from googlecloudsdk.command_lib.ml_engine import models_util
from googlecloudsdk.core import exceptions
from googlecloudsdk.core import log
from googlecloudsdk.core import properties


class ArgumentError(exceptions.Error):
  pass


class MlEngineIamRolesCompleter(iam_completers.IamRolesCompleter):

  def __init__(self, **kwargs):
    super(MlEngineIamRolesCompleter, self).__init__(
        resource_collection=models_util.MODELS_COLLECTION,
        resource_dest='model',
        **kwargs)


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
    help="""\
Start of the range of ports reserved by the local cluster. This command will use
a contiguous block of ports equal to parameter-server-count + worker-count + 1.

If --distributed is not specified, this flag is ignored.
""")


OPERATION_NAME = base.Argument('operation', help='Name of the operation.')


CONFIG = base.Argument(
    '--config',
    help="""\
Path to the job configuration file. The file should be a YAML document (JSON
also accepted) containing a Job resource as defined in the API (all fields are
optional): https://cloud.google.com/ml/reference/rest/v1/projects.jobs

If an option is specified both in the configuration file *and* via command line
arguments, the command line arguments override the configuration file.
""")
JOB_NAME = base.Argument('job', help='Name of the job.')
MODULE_NAME = base.Argument(
    '--module-name',
    required=True,
    help='Name of the module to run')
PACKAGE_PATH = base.Argument(
    '--package-path',
    help="""\
Path to a Python package to build. This should point to a directory containing
the Python source for the job. It will be built using setuptools (which must be
installed) using its *parent* directory as context. If the parent directory
contains a `setup.py` file, the build will use that; otherwise, it will use a
simple built-in one.
""")
PACKAGES = base.Argument(
    '--packages',
    default=[],
    type=arg_parsers.ArgList(),
    metavar='PACKAGE',
    help="""\
Path to Python archives used for training. These can be local paths
(absolute or relative), in which case they will be uploaded to the Cloud
Storage bucket given by `--staging-bucket`, or Cloud Storage URLs
(`gs://bucket-name/path/to/package.tar.gz`).
""")


def GetJobDirFlag(upload_help=True, allow_local=False):
  """Get base.Argument() for `--job-dir`.

  If allow_local is provided, this Argument gives a str when parsed; otherwise,
  it gives a (possibly empty) ObjectReference.

  Args:
    upload_help: bool, whether to include help text related to object upload.
      Only useful in remote situations (`jobs submit training`).
    allow_local: bool, whether to allow local directories (only useful in local
      situations, like `local train`) or restrict input to directories in Cloud
      Storage.

  Returns:
    base.Argument() for the corresponding `--job-dir` flag.
  """
  help_ = """\
A {dir_type} in which to store training outputs and other data
needed for training.

This path will be passed to your TensorFlow program as `--job_dir` command-line
arg. The benefit of specifying this field is that Cloud ML Engine will validate
the path for use in training.
""".format(dir_type=('Google Cloud Storage path' +
                     (' or local_directory' if allow_local else '')))
  if upload_help:
    help_ += """\

If packages must be uploaded and `--staging-bucket` is not provided, this path
will be used instead.
"""

  if allow_local:
    type_ = str
  else:
    type_ = functools.partial(storage_util.ObjectReference.FromArgument,
                              allow_empty_object=True)
  return base.Argument('--job-dir', type=type_, help=help_)


def GetUserArgs(local=False):
  if local:
    help_text = """\
Additional user arguments to be forwarded to user code. Any relative paths will
be relative to the *parent* directory of `--package-path`.
"""
  else:
    help_text = 'Additional user arguments to be forwarded to user code'
  return base.Argument(
      'user_args',
      nargs=argparse.REMAINDER,
      help=help_text)


VERSION_NAME = base.Argument('version', help='Name of the model version.')
_SCALE_TIER_CHOICES = {
    'BASIC': ('A single worker instance. This tier is suitable for learning '
              'how to use Cloud ML Engine, and for experimenting with new '
              'models using small datasets.'),
    'STANDARD_1': 'Many workers and a few parameter servers.',
    'PREMIUM_1': 'A large number of workers with many parameter servers.',
    'BASIC_GPU': 'A single worker instance with a GPU.',
    'CUSTOM': """\
The CUSTOM tier is not a set tier, but rather enables you to use your own
cluster specification. When you use this tier, set values to configure your
processing cluster according to these guidelines (using the --config flag):

* You _must_ set `TrainingInput.masterType` to specify the type of machine to
  use for your master node. This is the only required setting.
* You _may_ set `TrainingInput.workerCount` to specify the number of workers to
  use. If you specify one or more workers, you _must_ also set
  `TrainingInput.workerType` to specify the type of machine to use for your
  worker nodes.
* You _may_ set `TrainingInput.parameterServerCount` to specify the number of
  parameter servers to use. If you specify one or more parameter servers, you
  _must_ also set `TrainingInput.parameterServerType` to specify the type of
  machine to use for your parameter servers.  Note that all of your workers must
  use the same machine type, which can be different from your parameter server
  type and master type. Your parameter servers must likewise use the same
  machine type, which can be different from your worker type and master type.\
"""}
SCALE_TIER = base.Argument(
    '--scale-tier',
    help=('Specifies the machine types, the number of replicas for workers and '
          'parameter servers.'),
    choices=_SCALE_TIER_CHOICES,
    default=None)
RUNTIME_VERSION = base.Argument(
    '--runtime-version',
    help=('The Google Cloud ML Engine runtime version for this job. '
          'Defaults to the latest stable version. See '
          'https://cloud.google.com/ml/docs/concepts/runtime-version-list for '
          'a list of accepted versions.'))

POLLING_INTERVAL = base.Argument(
    '--polling-interval',
    type=arg_parsers.BoundedInt(1, sys.maxint, unlimited=True),
    required=False,
    default=60,
    action=actions.StoreProperty(properties.VALUES.ml_engine.polling_interval),
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


STAGING_BUCKET = base.Argument(
    '--staging-bucket',
    type=storage_util.BucketReference.FromArgument,
    help="""\
        Bucket in which to stage training archives.

        Required only if a file upload is necessary (that is, other flags
        include local paths) and no other flags implicitly specify an upload
        path.
        """)
