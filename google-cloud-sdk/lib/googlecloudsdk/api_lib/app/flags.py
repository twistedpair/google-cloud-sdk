# Copyright 2014 Google Inc. All Rights Reserved.
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

"""This module holds common flags used by the gcloud app commands."""
import argparse

from googlecloudsdk.calliope import base

SERVER_FLAG = base.Argument(
    '--server',
    help='The App Engine server to connect to.  You will not typically need to '
    'change this value.')

VERSION_FLAG = base.Argument(
    '--version',
    required=True,
    help='The version of the app that you want to operate on.')

# TODO(user): Add module globbing.
MODULES_ARG = base.Argument(
    'modules',
    nargs='+',
    help='One or more module names to perform this action on.  To select the '
    'default module for your app, use "default".')

MODULES_OPTIONAL_ARG = base.Argument(
    'modules',
    nargs='*',
    help='An optional list of module names to perform this action on.  To '
    'select the default module for your app, use "default".  If no modules are '
    'given all modules are used.')

IGNORE_CERTS_FLAG = base.Argument(
    '--ignore-bad-certs',
    action='store_true',
    default=False,
    help=argparse.SUPPRESS)
