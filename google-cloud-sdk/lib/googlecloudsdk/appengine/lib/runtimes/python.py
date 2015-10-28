# Copyright 2015 Google Inc. All Rights Reserved.

"""Fingerprinting code for the Python runtime."""

import os
import textwrap

from googlecloudsdk.core import log
from googlecloudsdk.core.console import console_io

from googlecloudsdk.appengine.lib import fingerprinting
from googlecloudsdk.appengine.lib.images import config

PYTHON_RUNTIME_NAME = 'python'

# TODO(user): We'll move these into directories once we externalize
# fingerprinting.
PYTHON_APP_YAML = textwrap.dedent("""\
    runtime: {runtime}
    env: 2
    api_version: 1
    entrypoint: {entrypoint}
    """)
DOCKERIGNORE = textwrap.dedent("""\
    .dockerignore
    Dockerfile
    .git
    .hg
    .svn
    """)
DOCKERFILE_PREAMBLE = 'FROM gcr.io/google_appengine/python\n'
DOCKERFILE_REQUIREMENTS_TXT = textwrap.dedent("""\
    ADD requirements.txt /app/
    RUN pip install -r requirements.txt
    """)
DOCKERFILE_INSTALL_APP = 'ADD . /app/\n'


class PythonConfigurator(fingerprinting.Configurator):
  """Generates configuration for a Python application."""

  def __init__(self, path, params, got_requirements_txt, entrypoint):
    """Constructor.

    Args:
      path: (str) Root path of the source tree.
      params: (fingerprinting.Params) Parameters passed through to the
        fingerprinters.
      got_requirements_txt: (bool) True if there's a requirements.txt file.
      entrypoint: (str) Name of the entrypoint to generate.
    """

    self.root = path
    self.params = params
    self.got_requirements_txt = got_requirements_txt
    self.entrypoint = entrypoint

  def GenerateConfigs(self):
    """Generate all config files for the module."""
    # Write "Saving file" messages to the user or to log depending on whether
    # we're in "deploy."
    if self.params.deploy:
      notify = log.info
    else:
      notify = log.status.Print

    # Generate app.yaml.
    cleaner = fingerprinting.Cleaner()
    if not self.params.deploy:
      app_yaml = os.path.join(self.root, 'app.yaml')
      if not os.path.exists(app_yaml):
        notify('Saving [app.yaml] to [%s].' % self.root)
        runtime = 'custom' if self.params.custom else 'python'
        with open(app_yaml, 'w') as f:
          f.write(PYTHON_APP_YAML.format(entrypoint=self.entrypoint,
                                         runtime=runtime))
        cleaner.Add(app_yaml)

    if self.params.custom or self.params.deploy:
      dockerfile = os.path.join(self.root, config.DOCKERFILE)
      if not os.path.exists(dockerfile):
        notify('Saving [%s] to [%s].' % (config.DOCKERFILE, self.root))
        # Customize the dockerfile.
        with open(dockerfile, 'w') as out:
          out.write(DOCKERFILE_PREAMBLE)

          if self.got_requirements_txt:
            out.write(DOCKERFILE_REQUIREMENTS_TXT)

          out.write(DOCKERFILE_INSTALL_APP)

          # Generate the appropriate start command.
          if self.entrypoint:
            out.write('CMD %s\n' % self.entrypoint)

        cleaner.Add(dockerfile)

      # Generate .dockerignore TODO(user): eventually this file will just be
      # copied verbatim.
      dockerignore = os.path.join(self.root, '.dockerignore')
      if not os.path.exists(dockerignore):
        notify('Saving [.dockerignore] to [%s].' % self.root)
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
  entrypoint = None
  appinfo = params.appinfo
  if appinfo:
    # We only want to do fingerprinting for 'python', for 'python-compat' we
    # want to fall through to plain dockerfiles.
    if appinfo.GetEffectiveRuntime() != 'python':
      return None

    if appinfo.entrypoint:
      entrypoint = appinfo.entrypoint

  log.info('Checking for Python.')

  requirements_txt = os.path.join(path, 'requirements.txt')

  got_requirements_txt = os.path.isfile(requirements_txt)
  got_py_files = False

  # check for any python files.
  for _, _, files in os.walk(path):
    for filename in files:
      if filename.endswith('.py'):
        got_py_files = True

  if not got_requirements_txt and not got_py_files:
    return None

  # Query the user for the WSGI entrypoint:
  if not entrypoint:
    if console_io.IsInteractive():
      entrypoint = console_io.PromptResponse(
          'This looks like a Python app.  If so, please enter the command to '
          "run to run the app in production (enter nothing if it's not a "
          'python app): ').strip()
      if not entrypoint:
        log.info('No entrypoint specified.  Assuming this is not a python app.')
      elif appinfo:
        # We've got an entrypoint and the user had an app.yaml that didn't
        # specify it.
        # TODO(user): offer to edit the user's app.yaml.
        log.status.Print('To avoid being asked for an entrypoint in the '
                         'future, please add the entrypoint to your app.yaml:\n'
                         '  entrypoint: %s' % entrypoint)
    else:
      log.warn("This appears to be a python app.  You'll need to provide the "
               'command to run the app in production.  Please either run this '
               'interactively or create an app.yaml with "runtime: python" and '
               'an "entrypoint" field defining the full command.')
      return None

  return PythonConfigurator(path, params, got_requirements_txt,
                            entrypoint)
