# Copyright 2015 Google Inc. All Rights Reserved.

"""Fingerprinting code for the node.js runtime.

WARNING WARNING WARNING: this file will shortly be removed.  Don't make any
changes here.  See ./ext_runtimes/runtime_defs/nodejs instead.
"""

import atexit
import json
import os
import textwrap

from googlecloudsdk.api_lib.app.ext_runtimes import fingerprinting
from googlecloudsdk.api_lib.app.images import config
from googlecloudsdk.api_lib.app.images import util
from googlecloudsdk.core import log

NAME ='Node.js'
ALLOWED_RUNTIME_NAMES = ['nodejs', 'custom']
NODEJS_RUNTIME_NAME = 'nodejs'

# TODO(mmuller): move these into the node_app directory.
NODEJS_APP_YAML = textwrap.dedent("""\
    runtime: {runtime}
    vm: true
    api_version: 1
    """)
DOCKERIGNORE = textwrap.dedent("""\
    # Copyright 2015 Google Inc. All Rights Reserved.
    #
    # Licensed under the Apache License, Version 2.0 (the "License");
    # you may not use this file except in compliance with the License.
    # You may obtain a copy of the License at
    #
    #     http://www.apache.org/licenses/LICENSE-2.0
    #
    # Unless required by applicable law or agreed to in writing, software
    # distributed under the License is distributed on an "AS IS" BASIS,
    # WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
    # See the License for the specific language governing permissions and
    # limitations under the License.

    node_modules
    .dockerignore
    Dockerfile
    npm-debug.log
    .git
    .hg
    .svn
    """)

# The template for the docker command that is injected into the Dockerfile
# when the user specifies a node version in their "engines" section.
# It first invokes node to check to see if the version already installed in
# the base image satisfies the spec in engines.node.  If not, it obtains the
# list of current versions from nodejs.org and invokes node again to locate
# the latest matching version.  Finally, the script installs the matching
# version.
#
# This gets expanded out into a multiline dockerfile command with
# backslash-newlines separating the lines.  For example:
#
#     RUN npm install https://... && \
#       (node -e 'var semver = require("semver"); \
#                 if (!semver.satisfies(process.version, "%(version_spec)s")) \
#                   process.exit(1);' || \
#     ... etc
INSTALL_NODE_TEMPLATE = ' \\\n'.join(textwrap.dedent("""\
    # Check to see if the the version included in the base runtime satisfies
    # %(version_spec)s, if not then do an npm install of the latest available
    # version that satisfies it.
    RUN npm install \
        https://storage.googleapis.com/gae_node_packages/semver.tar.gz &&
      (node -e 'var semver = require("semver");
                if (!semver.satisfies(process.version, "%(version_spec)s"))
                  process.exit(1);' ||
       (version=$(curl -L \
https://storage.googleapis.com/gae_node_packages/node_versions |
                  node -e '
                    var semver = require("semver");
                    var http = require("http");
                    var spec = process.argv[1];
                    var latest = "";
                    var versions = "";
                    var selected_version;

                    function verifyBinary(version) {
                      var options = {
                        "host": "storage.googleapis.com",
                        "method": "HEAD",
                        "path": "/gae_node_packages/node-" + version +
                                "-linux-x64.tar.gz"
                      };
                      var req = http.request(options, function (res) {
                        if (res.statusCode == 404) {
                          console.error("Binaries for Node satisfying version " +
                                        version + " are not available.");
                          process.exit(1);
                        }
                      });
                      req.end();
                    }
                    function satisfies(version) {
                      if (semver.satisfies(version, spec)) {
                        process.stdout.write(version);
                        verifyBinary(version);
                        return true;
                      }
                    }
                    process.stdin.on("data", function(data) {
                      versions += data;
                    });
                    process.stdin.on("end", function() {
                      versions =
                          versions.split("\\n").sort().reverse();
                      if (!versions.some(satisfies)) {
                        console.error("No version of Node found satisfying: " +
                                      spec);
                        process.exit(1);
                      }
                    });'
                    "%(version_spec)s") &&
                    rm -rf /nodejs/* &&
                    (curl \
https://storage.googleapis.com/gae_node_packages/node-$version-linux-x64.tar.gz |
                     tar xzf - -C /nodejs --strip-components=1
                     )
        )
       )
""").splitlines()) +'\n'


class NodeJSConfigurator(fingerprinting.Configurator):
  """Generates configuration for a node.js class."""

  def __init__(self, path, params, got_package_json, got_npm_start,
               nodejs_version):
    """Constructor.

    Args:
      path: (str) Root path of the source tree.
      params: (fingerprinting.Params) Parameters passed through to the
        fingerprinters.
      got_package_json: (bool) If true, the runtime contains a package.json
        file and we should do an npm install while building the docker image.
      got_npm_start: (bool) If true, the runtime contains a "start" script in
        the package.json and we should do "npm start" to start the package.
        If false, we assume there is a server.js file and we do "node
        server.js" instead.
      nodejs_version: (str or None) Required version of node.js (extracted
        from the engines.node field of package.json)
    """

    self.root = path
    self.got_package_json = got_package_json
    self.got_npm_start = got_npm_start
    self.params = params
    self.nodejs_version = nodejs_version

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
    if not self.params.appinfo:
      app_yaml = os.path.join(self.root, 'app.yaml')
      if not os.path.exists(app_yaml):
        notify('Saving [app.yaml] to [%s].' % self.root)
        runtime = 'custom' if self.params.custom else 'nodejs'
        with open(app_yaml, 'w') as f:
          f.write(NODEJS_APP_YAML.format(runtime=runtime))

    if self.params.custom or self.params.deploy:
      dockerfile = os.path.join(self.root, config.DOCKERFILE)
      if not os.path.exists(dockerfile):
        notify('Saving [%s] to [%s].' % (config.DOCKERFILE, self.root))
        util.FindOrCopyDockerfile(NODEJS_RUNTIME_NAME, self.root,
                                  cleanup=self.params.deploy)
        cleaner.Add(dockerfile)
        # Customize the dockerfile.
        os.chmod(dockerfile, os.stat(dockerfile).st_mode | 0200)
        with open(dockerfile, 'a') as out:
          if self.nodejs_version:
            # Let node check to see if it satisfies the version constraint and
            # try to install the correct version if not.
            out.write(INSTALL_NODE_TEMPLATE %
                      {'version_spec': self.nodejs_version})

          out.write('COPY . /app/\n')

          # Generate npm install if there is a package.json.
          if self.got_package_json:
            out.write(textwrap.dedent("""\
                # You have to specify "--unsafe-perm" with npm install
                # when running as root.  Failing to do this can cause
                # install to appear to succeed even if a preinstall
                # script fails, and may have other adverse consequences
                # as well.
                # This command will also cat the npm-debug.log file after the
                # build, if it exists.
                RUN npm install --unsafe-perm || \\
                  ((if [ -f npm-debug.log ]; then \\
                      cat npm-debug.log; \\
                    fi) && false)
                """))

          # Generate the appropriate start command.
          if self.got_npm_start:
            out.write('CMD npm start\n')
          else:
            out.write('CMD node server.js\n')

      # Generate .dockerignore TODO(mmuller): eventually this file will just be
      # copied verbatim.
      dockerignore = os.path.join(self.root, '.dockerignore')
      if not os.path.exists(dockerignore):
        notify('Saving [.dockerignore] to [%s].' % self.root)
        cleaner.Add(dockerignore)
        with open(dockerignore, 'w') as f:
          f.write(DOCKERIGNORE)

        if self.params.deploy:
          atexit.register(util.Clean, dockerignore)

    if not cleaner.HasFiles():
      notify('All config files already exist, not generating anything.')

    return cleaner


def Fingerprint(path, params):
  """Check for a Node.js app.

  Args:
    path: (str) Application path.
    params: (fingerprinting.Params) Parameters passed through to the
      fingerprinters.

  Returns:
    (NodeJSConfigurator or None) Returns a module if the path contains a
    node.js app.
  """
  log.info('Checking for Node.js.')
  package_json = os.path.join(path, 'package.json')

  if not os.path.isfile(package_json):
    log.debug('node.js checker: No package.json file.')
    got_package_json = False
    got_npm_start = False
    node_version = None
  else:
    got_package_json = True

    # Try to read the package.json file.
    try:
      with open(package_json) as f:
        contents = json.load(f)
    except (IOError, ValueError) as ex:
      # If we have an invalid or unreadable package.json file, there's
      # something funny going on here so fail recognition.
      log.debug('node.js checker: error accesssing package.json: %r' % ex)
      return None

    # See if we've got a scripts.start field.
    got_npm_start = bool(contents.get('scripts', {}).get('start'))

    # See if a version of node is specified.
    try:
      node_version = contents.get('engines', {}).get('node', None)
      log.info('node version is %s', node_version)
    except AttributeError:
      # Most likely "engines" wasn't a dictionary.
      log.warn('node.js checker: ignoring invalid "engines" field in '
               'package.json')
      node_version = None

    if node_version is None:
      log.warn('No node version specified.  Please add your node version, '
               'see https://docs.npmjs.com/files/package.json#engines')

  if got_npm_start or os.path.exists(os.path.join(path, 'server.js')):
    return NodeJSConfigurator(path, params, got_package_json, got_npm_start,
                              node_version)
  else:
    log.debug('nodejs. checker: No npm start and no server.js')
    return None
