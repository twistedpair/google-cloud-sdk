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

from gae_ext_runtime import ext_runtime

from googlecloudsdk.api_lib.app.images import config
from googlecloudsdk.core import log

NAME = 'Python Compat'
ALLOWED_RUNTIME_NAMES = ('python27', 'python-compat')
PYTHON_RUNTIME_NAME = 'python27'

# TODO(mmuller): this generated app.yaml doesn't work because the compat
# runtimes need a "handlers" section.  Query the user for this information.
PYTHON_APP_YAML = textwrap.dedent("""\
    runtime: {runtime}
    vm: true
    api_version: 1
    threadsafe: false
    # You must add a handlers section here.  Example:
    # handlers:
    # - url: .*
    #   script: main.app
    """)
APP_YAML_WARNING = ('app.yaml has been generated, but needs to be provided a '
                    '"handlers" section.')
DOCKERIGNORE = textwrap.dedent("""\
    .dockerignore
    Dockerfile
    .git
    .hg
    .svn
    """)
COMPAT_DOCKERFILE_PREAMBLE = (
    'FROM gcr.io/google_appengine/python-compat-multicore\n')
PYTHON27_DOCKERFILE_PREAMBLE = 'FROM gcr.io/google_appengine/python-compat\n'

DOCKERFILE_INSTALL_APP = 'ADD . /app/\n'

# TODO(mmuller): Do the check for requirements.txt in the source inspection
# and don't generate the pip install if it doesn't exist.
DOCKERFILE_INSTALL_REQUIREMENTS_TXT = (
    'RUN if [ -s requirements.txt ]; then pip install -r requirements.txt; '
    'fi\n')


class PythonConfigurator(ext_runtime.Configurator):
  """Generates configuration for a Python application."""

  def __init__(self, path, params, runtime):
    """Constructor.

    Args:
      path: (str) Root path of the source tree.
      params: (ext_runtime.Params) Parameters passed through to the
        fingerprinters.
      runtime: (str) The runtime name.
    """

    self.root = path
    self.params = params
    self.runtime = runtime

  def GenerateConfigs(self):
    """Generate all config files for the module."""
    # Write "Writing file" messages to the user or to log depending on whether
    # we're in "deploy."
    if self.params.deploy:
      notify = log.info
    else:
      notify = log.status.Print

    if self.runtime == 'python-compat':
      dockerfile_preamble = COMPAT_DOCKERFILE_PREAMBLE
    else:
      dockerfile_preamble = PYTHON27_DOCKERFILE_PREAMBLE

    # Generate app.yaml.  Note: this is not a recommended use-case,
    # python-compat users likely have an existing app.yaml.  But users can
    # still get here with the --runtime flag.
    cleaner = ext_runtime.Cleaner()
    if not self.params.appinfo:
      app_yaml = os.path.join(self.root, 'app.yaml')
      if not os.path.exists(app_yaml):
        notify('Writing [app.yaml] to [%s].' % self.root)
        runtime = 'custom' if self.params.custom else self.runtime
        with open(app_yaml, 'w') as f:
          f.write(PYTHON_APP_YAML.format(runtime=runtime))
        cleaner.Add(app_yaml)
        log.warn(APP_YAML_WARNING)

    if self.params.custom or self.params.deploy:
      dockerfile = os.path.join(self.root, config.DOCKERFILE)
      if not os.path.exists(dockerfile):
        notify('Writing [%s] to [%s].' % (config.DOCKERFILE, self.root))
        # Customize the dockerfile.
        with open(dockerfile, 'w') as out:
          out.write(dockerfile_preamble)
          out.write(DOCKERFILE_INSTALL_APP)
          if self.runtime == 'python-compat':
            out.write(DOCKERFILE_INSTALL_REQUIREMENTS_TXT)

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
    params: (ext_runtime.Params) Parameters passed through to the
      fingerprinters.

  Returns:
    (PythonConfigurator or None) Returns a module if the path contains a
    python app.
  """
  log.info('Checking for Python Compat.')

  # The only way we select these runtimes is if either the user has specified
  # it or a matching runtime is specified in the app.yaml.
  if (not params.runtime and
      (not params.appinfo or
       params.appinfo.GetEffectiveRuntime() not in ALLOWED_RUNTIME_NAMES)):
    return None

  if params.appinfo:
    runtime = params.appinfo.GetEffectiveRuntime()
  else:
    runtime = params.runtime

  log.info('Python Compat matches ([{0}] specified in "runtime" field)'.format(
      runtime))
  return PythonConfigurator(path, params, runtime)
