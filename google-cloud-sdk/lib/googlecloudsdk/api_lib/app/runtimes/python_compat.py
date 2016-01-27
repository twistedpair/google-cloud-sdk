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

"""Fingerprinting code for the Python runtime."""

import os
import textwrap

from googlecloudsdk.api_lib.app.ext_runtimes import fingerprinting
from googlecloudsdk.api_lib.app.images import config
from googlecloudsdk.core import log

NAME = 'Python Compat'
ALLOWED_RUNTIME_NAMES = ('python27', 'python-compat')
PYTHON_RUNTIME_NAME = 'python27'

PYTHON_APP_YAML = textwrap.dedent("""\
    runtime: {runtime}
    vm: true
    api_version: 1
    """)
DOCKERIGNORE = textwrap.dedent("""\
    .dockerignore
    Dockerfile
    .git
    .hg
    .svn
    """)
DOCKERFILE_PREAMBLE = 'FROM gcr.io/google_appengine/python-compat\n'

DOCKERFILE_INSTALL_APP = 'ADD . /app/\n'


class PythonConfigurator(fingerprinting.Configurator):
  """Generates configuration for a Python application."""

  def __init__(self, path, params):
    """Constructor.

    Args:
      path: (str) Root path of the source tree.
      params: (fingerprinting.Params) Parameters passed through to the
        fingerprinters.
    """

    self.root = path
    self.params = params

  def GenerateConfigs(self):
    """Generate all config files for the module."""
    # Write "Writing file" messages to the user or to log depending on whether
    # we're in "deploy."
    if self.params.deploy:
      notify = log.info
    else:
      notify = log.status.Print

    # Generate app.yaml.
    cleaner = fingerprinting.Cleaner()
    if not self.params.appinfo:
      app_yaml = os.path.join(self.root, 'app.yaml')
      if not os.path.exists(app_yaml):
        notify('Writing [app.yaml] to [%s].' % self.root)
        runtime = 'custom' if self.params.custom else 'python27'
        with open(app_yaml, 'w') as f:
          f.write(PYTHON_APP_YAML.format(runtime=runtime))
        cleaner.Add(app_yaml)

    if self.params.custom or self.params.deploy:
      dockerfile = os.path.join(self.root, config.DOCKERFILE)
      if not os.path.exists(dockerfile):
        notify('Writing [%s] to [%s].' % (config.DOCKERFILE, self.root))
        # Customize the dockerfile.
        with open(dockerfile, 'w') as out:
          out.write(DOCKERFILE_PREAMBLE)
          out.write(DOCKERFILE_INSTALL_APP)

        cleaner.Add(dockerfile)

      dockerignore = os.path.join(self.root, '.dockerignore')
      if not os.path.exists(dockerignore):
        notify('Writing [.dockerignore] to [%s].' % self.root)
        with open(dockerignore, 'w') as f:
          f.write(DOCKERIGNORE)
        cleaner.Add(dockerignore)

    if not cleaner.HasFiles():
      notify('All config files already exist, not generating anything.')

    return cleaner


def Fingerprint(path, params):
  """Check for a Python app.

  Args:
    path: (str) Application path.
    params: (fingerprinting.Params) Parameters passed through to the
      fingerprinters.

  Returns:
    (PythonConfigurator or None) Returns a module if the path contains a
    python app.
  """
  log.info('Checking for Python Compat.')

  # We need an appinfo and it needs to directly specify this runtime to use it.
  if (not params.appinfo or
      params.appinfo.GetEffectiveRuntime() not in ALLOWED_RUNTIME_NAMES):
    return None

  log.info('Python Compat matches ([{0}] specified in "runtime" field)'.format(
      params.appinfo.GetEffectiveRuntime()))
  return PythonConfigurator(path, params)
