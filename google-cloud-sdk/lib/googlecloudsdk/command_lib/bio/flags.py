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

from googlecloudsdk.calliope import base
from googlecloudsdk.command_lib.bio import util


# Operation flags
def GetOperationNameFlag(verb):
  return base.Argument(
      'name',
      metavar='OPERATION_NAME',
      completion_resource=util.OPERATIONS_COLLECTION,
      help='Name for the operation you want to {0}.'.format(verb))
