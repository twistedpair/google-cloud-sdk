# Copyright 2015 Google Inc. All Rights Reserved.
"""Fingerprinting code for the Java runtime."""

import os
import textwrap

from googlecloudsdk.api_lib.app.ext_runtimes import fingerprinting
from googlecloudsdk.api_lib.app.images import config
from googlecloudsdk.core import exceptions
from googlecloudsdk.core import log

NAME ='java'
ALLOWED_RUNTIME_NAMES = ('java', 'custom')
JAVA_RUNTIME_NAME = 'java'

# TODO(ludo): We'll move these into directories once we externalize
# fingerprinting.
JAVA_APP_YAML = textwrap.dedent("""\
    runtime: {runtime}
    env: 2
    api_version: 1
    """)
DOCKERIGNORE = textwrap.dedent("""\
    .dockerignore
    Dockerfile
    .git
    .hg
    .svn
    """)
DOCKERFILE_JAVA8_PREAMBLE = 'FROM gcr.io/google_appengine/openjdk8\n'
DOCKERFILE_JETTY9_PREAMBLE = 'FROM gcr.io/google_appengine/jetty9\n'
DOCKERFILE_LEGACY_PREAMBLE = 'FROM gcr.io/google_appengine/java-compat\n'
DOCKERFILE_COMPAT_PREAMBLE = 'FROM gcr.io/google_appengine/jetty9-compat\n'
DOCKEFILE_CMD = 'CMD {0}\n'
DOCKERFILE_JAVA8_ENTRYPOINT = 'ENTRYPOINT ["java", "-jar", "/app/{0}"]\n'
DOCKERFILE_INSTALL_APP = 'ADD {0} /app/\n'
DOCKERFILE_INSTALL_WAR = 'ADD {0} $JETTY_BASE/webapps/root.war\n'


class JavaConfigError(exceptions.Error):
  """Errors in Java Application Config."""


class JavaConfigurator(fingerprinting.Configurator):
  """Generates configuration for a Java application.

     What is supported is:
      - jar file (run with Open JDK8 image)
      - war file (run with Jetty9 image)
      - Exploded war directory (with WEB-INF/):
        - if env: 2, we use the latest Jetty9 compat runtime image
        - if not, we use the current Jetty9 compat image we build.
      This will ease the transition to the new Jetty9 compat runtime for people
      migrating to env: 2. Once all are on env: 2, we will remove entirely the
      support for the legacy Jetty9 compat runtime.
  """

  def __init__(self, path, appinfo, deploy, entrypoint, server,
               artifact_to_deploy, custom):
    """Constructor.

    Args:
      path: (str) Root path of the source tree.
      appinfo: (apphosting.api.appinfo.AppInfoExternal or None) The parsed
      app.yaml file for the module if it exists.
      deploy: (bool) True if run in deployment mode.
      entrypoint: (str) Name of the entrypoint to generate.
      server: (str) Name of the server to use (jetty9 or None for now).
      artifact_to_deploy: (str) Name of the file or directory to deploy.
      custom: (bool) True if it is a custom runtime.
    """

    self.root = path
    self.appinfo = appinfo
    self.deploy = deploy
    self.custom = custom
    self.entrypoint = entrypoint
    self.server = server
    self.artifact_to_deploy = artifact_to_deploy
    # Write messages to the console or to the log depending on whether we're
    # doing a "deploy."
    if self.deploy:
      self.notify = log.info
    else:
      self.notify = log.status.Print

  def GenerateConfigs(self):
    """Generates all config files for the module.

    Returns:
      (fingerprinting.Cleaner) A cleaner populated with the generated files
    """

    cleaner = fingerprinting.Cleaner()

    if not self.appinfo:
      self._GenerateAppYaml(cleaner)
    if self.custom or self.deploy:
      self.notify('sdfsdfsdfsdfsdfsdfdsd.')
      self._GenerateDockerfile(cleaner)
      self._GenerateDockerignore(cleaner)

    if not cleaner.HasFiles():
      self.notify('All config files already exist, not generating anything.')

    return cleaner

  def _GenerateAppYaml(self, cleaner):
    """Generates an app.yaml file appropriate to this application.

    Args:
      cleaner: (fingerprinting.Cleaner) A cleaner to populate
    """
    app_yaml = os.path.join(self.root, 'app.yaml')
    if not os.path.exists(app_yaml):
      self.notify('Saving [app.yaml] to [{0}].'.format(self.root))
      runtime = 'custom' if self.custom else 'java'
      with open(app_yaml, 'w') as f:
        f.write(JAVA_APP_YAML.format(runtime=runtime))

  def _GenerateDockerfile(self, cleaner):
    """Generates a Dockerfile appropriate to this application.

    Args:
      cleaner: (fingerprinting.Cleaner) A cleaner to populate

    Raises:
      JavaConfigError: if there is an app.yaml configuration error.
    """
    env2 = self.appinfo and self.appinfo.env == '2'
    dockerfile = os.path.join(self.root, config.DOCKERFILE)
    if not os.path.exists(dockerfile):
      self.notify('Saving [%s] to [%s].' % (config.DOCKERFILE, self.root))
      # Customize the dockerfile.
      with open(dockerfile, 'w') as out:
        if self.artifact_to_deploy.endswith('.war'):
          out.write(DOCKERFILE_JETTY9_PREAMBLE)
          out.write(DOCKERFILE_INSTALL_WAR.format(self.artifact_to_deploy))
        if self.artifact_to_deploy.endswith('.jar'):
          if self.server is not None:
            raise JavaConfigError('Cannot use server %s '
                                  'for jar deployment.' % self.server)
          out.write(DOCKERFILE_JAVA8_PREAMBLE)
          out.write(DOCKERFILE_INSTALL_APP.format(self.artifact_to_deploy))
        if self.artifact_to_deploy == '.':
          if env2:
            out.write(DOCKERFILE_COMPAT_PREAMBLE)
          else:
            out.write(DOCKERFILE_LEGACY_PREAMBLE)
          out.write(DOCKERFILE_INSTALL_APP.format(self.artifact_to_deploy))

        # Generate the appropriate start command.
        if self.entrypoint:
          out.write(DOCKEFILE_CMD % self.entrypoint)
        elif self.artifact_to_deploy.endswith('.jar'):
          # for jar execution generate the command to run:
          out.write(DOCKERFILE_JAVA8_ENTRYPOINT.format(self.artifact_to_deploy))

      cleaner.Add(dockerfile)

  def _GenerateDockerignore(self, cleaner):
    """Generates a .dockerignore file appropriate to this application.

    Args:
      cleaner: (fingerprinting.Cleaner) A cleaner to populate
    """
    dockerignore = os.path.join(self.root, '.dockerignore')
    if not os.path.exists(dockerignore):
      self.notify('Saving [.dockerignore] to [{0}].'.format(self.root))
      with open(dockerignore, 'w') as f:
        f.write(DOCKERIGNORE)
      cleaner.Add(dockerignore)


def Fingerprint(path, params):
  """Check for a Java app.

  Args:
    path: (str) Application path.
    params: (fingerprinting.Params) Parameters passed through to the
      fingerprinters.

  Returns:
    (JavaConfigurator or None) Returns a module if the path contains a
    Java app.

  Raises:
    JavaConfigError: if there is an app.yaml configuration error.
  """
  entrypoint = None
  server = None
  appinfo = params.appinfo
  if appinfo and appinfo.entrypoint:
    entrypoint = appinfo.entrypoint

  log.info('Checking for Java.')
  if appinfo:
    runtime_config = appinfo.runtime_config
    if runtime_config:
      for key, value in runtime_config.iteritems():
        if key == 'server':
          if value != 'jetty9':
            raise JavaConfigError('Unknown server : %s.' % value)
          server = value
        elif key == 'jdk':
          if value != 'openjdk8':
            raise JavaConfigError('Unknown JDK : %s.' % value)
        else:
          raise JavaConfigError('Unknown runtime_config entry : %s.' % key)

  artifact_to_deploy = '?'

  # check for any Java known artifacts: a jar, a war, or an exploded Web App.
  # TODO(ludo): expand to more complex configs with multiple Jars.
  number_of_possible_artifacts = 0
  for filename in os.listdir(path):
    if filename.endswith('.war'):
      artifact_to_deploy = filename
      number_of_possible_artifacts += 1
    if filename.endswith('.jar'):
      artifact_to_deploy = filename
      number_of_possible_artifacts += 1
    if filename.endswith('WEB-INF'):
      artifact_to_deploy = '.'
      number_of_possible_artifacts += 1
  if number_of_possible_artifacts == 0:
    return None
  if number_of_possible_artifacts > 1:
    raise JavaConfigError('Too many java artifacts to deploy '
                          '(.jar, .war, or Java Web App).')

  return JavaConfigurator(path, appinfo, params.deploy, entrypoint, server,
                          artifact_to_deploy, params.custom)
