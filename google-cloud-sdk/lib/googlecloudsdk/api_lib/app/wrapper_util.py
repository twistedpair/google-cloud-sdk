# Copyright 2015 Google Inc. All Rights Reserved.
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

"""Utilities for the dev_appserver.py wrapper script.

Functions for parsing app.yaml files and installing the required components.
"""
import os

from googlecloudsdk.core import log
import yaml

_RUNTIME_COMPONENTS = {
    'java': 'app-engine-java',
    'php55': 'app-engine-php',
    'go': 'app-engine-go',
}


_WARNING_RUNTIMES = {
    'php': ('The Cloud SDK no longer ships runtimes for PHP 5.4.  Please set '
            'your runtime to be "php55".')
}

_YAML_FILE_EXTENSIONS = ('.yaml', '.yml')


class MultipleAppYamlError(Exception):
  """An application configuration has more than one valid app yaml files."""


def GetRuntimes(args):
  """Gets a list of unique runtimes that the user is about to run.

  Args:
    args: A list of arguments (typically sys.argv).

  Returns:
    A set of runtime strings.

  Raises:
    MultipleAppYamlError: The supplied application configuration has duplicate
      app yamls.
  """
  runtimes = set()
  for arg in args:
    # Check all the arguments to see if they're application yaml files or
    # directories that include yaml files.
    yaml_candidate = None
    if (os.path.isfile(arg) and
        os.path.splitext(arg)[1] in _YAML_FILE_EXTENSIONS):
      yaml_candidate = arg
    elif os.path.isdir(arg):
      for extension in _YAML_FILE_EXTENSIONS:
        fullname = os.path.join(arg, 'app' + extension)
        if os.path.isfile(fullname):
          if yaml_candidate:
            raise MultipleAppYamlError(
                'Directory "{0}" contains conflicting files {1}'.format(
                    arg, ' and '.join(yaml_candidate)))

          yaml_candidate = fullname

    if yaml_candidate:
      with open(yaml_candidate) as f:
        try:
          info = yaml.safe_load(f)
          # safe_load can return arbitrary objects, we need a dict.
          if not isinstance(info, dict):
            continue
          # Grab the runtime from the yaml, if it exists.
          if 'runtime' in info:
            runtime = info.get('runtime')
            if type(runtime) == str:
              runtimes.add(runtime)
              if runtime in _WARNING_RUNTIMES:
                log.warn(_WARNING_RUNTIMES[runtime])
        except yaml.YAMLError:
          continue
    elif os.path.isfile(os.path.join(arg, 'WEB-INF', 'appengine-web.xml')):
      # For unstanged Java App Engine apps, which may not have any yaml files.
      runtimes.add('java')
  return runtimes


def GetComponents(runtimes):
  """Gets a list of required components.

  Args:
    runtimes: A list containing the required runtime ids.
  Returns:
    A list of components that must be present.
  """
  # Always install python.
  components = ['app-engine-python']
  for requested_runtime in runtimes:
    for component_runtime, component in _RUNTIME_COMPONENTS.iteritems():
      if component_runtime in requested_runtime:
        components.append(component)
  return components
