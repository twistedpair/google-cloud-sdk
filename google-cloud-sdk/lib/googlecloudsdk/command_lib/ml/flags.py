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

from googlecloudsdk.calliope import base

# TODO(user): move these into a class
CONFIG = base.Argument('--config', help='Path to yaml configuration file.')
JOB_NAME = base.Argument('job', help='Name of the job.')
MODULE_NAME = base.Argument('--module', help='Name of Python module to run.')
TRAINER_URI = base.Argument(
    '--trainer-uri',
    help='Google Cloud Storage location of the training program.',
    nargs='+')
VERSION_NAME = base.Argument('version', help='Name of the model version.')
VERSION_DATA = base.Argument(
    '--origin',
    required=True,
    help='Google Cloud Storage location containing the model graph.')


def GetModelName(positional=True, required=False):
  help_text = 'Name of the model.'
  if positional:
    return base.Argument('model', help=help_text)
  else:
    return base.Argument('--model', help=help_text, required=required)
