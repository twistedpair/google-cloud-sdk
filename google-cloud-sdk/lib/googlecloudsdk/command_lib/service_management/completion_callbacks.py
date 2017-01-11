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

"""Callback functions for tab completion."""

from googlecloudsdk.core import exceptions


def _ServiceFlagCompletionCallback(list_type, project):
  """Callback function for service tab-completion.

  Args:
    list_type: str, should be one of 'produced', 'enabled', or 'available'
    project: str, the name of the project for which to retrieve candidates

  Returns:
    The list of arguments that the gcloud infrastructure will use to retrieve
    candidate services.
  """
  # Sanity check the type of list_type argument
  if not isinstance(list_type, basestring):
    raise exceptions.InternalError(
        'Could not read list type in service flag completion callback.')

  # Sanity check the list_type contents
  if list_type not in ['produced', 'enabled']:
    raise exceptions.InternalError(
        'Invalid list type in service flag completion callback.')

  result = ['service-management', 'list', '--%s' % list_type,
            '--format=value(serviceConfig.name)']
  if project:
    result.extend(['--project', project])

  return result


def ProducerServiceFlagCompletionCallback(parsed_args):
  return _ServiceFlagCompletionCallback('produced',
                                        getattr(parsed_args, 'project', None))


def ConsumerServiceFlagCompletionCallback(parsed_args):
  return _ServiceFlagCompletionCallback('enabled',
                                        getattr(parsed_args, 'project', None))
