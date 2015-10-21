# Copyright 2015 Google Inc. All Rights Reserved.

"""Docker image and docker container classes.

In Docker terminology image is a read-only layer that never changes.
Container is created once you start a process in Docker from an Image. Container
consists of read-write layer, plus information about the parent Image, plus
some additional information like its unique ID, networking configuration,
and resource limits.
For more information refer to http://docs.docker.io/.

Mapping to Docker CLI:
Image is a result of "docker build path/to/Dockerfile" command.
ImageOptions allows to pass parameters to these commands.

Versions 1.9 and 1.10 of docker remote API are supported.
"""

import os
import socket
import ssl
import sys


from docker import docker
from googlecloudsdk.core import exceptions
from googlecloudsdk.core import log
from googlecloudsdk.core.util import platforms
import requests
from requests.packages import urllib3
from googlecloudsdk.appengine.lib.images import config


# This suppresses a urllib3 warning. More info can be found here:
# https://urllib3.readthedocs.org/en/latest/security.html
urllib3.disable_warnings()


DEFAULT_LINUX_DOCKER_HOST = '/var/run/docker.sock'
DOCKER_CONNECTION_ERROR = 'Couldn\'t connect to the Docker daemon.'
DOCKER_CONNECTION_ERROR_LOCAL = (
    'If you would like to perform the docker build locally, please check '
    'whether the environment variables DOCKER_HOST, DOCKER_CERT_PATH and '
    'DOCKER_TLS_VERIFY are set correctly.\n'
    'With boot2docker, you can set them up by running:\n'
    '  boot2docker shellinit\n'
    'and executing the commands that boot2docker shows.')


class DockerDaemonConnectionError(exceptions.Error):
  """Raised if the docker client can't connect to the Docker daemon."""


def KwargsFromEnv(host, cert_path, tls_verify):
  """Helper to build docker.Client constructor kwargs from the environment."""
  log.debug('Detected docker environment variables: DOCKER_HOST=%s, '
            'DOCKER_CERT_PATH=%s, DOCKER_TLS_VERIFY=%s', host, cert_path,
            tls_verify)
  params = {}

  if host:
    params['base_url'] = (host.replace('tcp://', 'https://') if tls_verify
                          else host)
  elif sys.platform.startswith('linux'):
    # if this is a linux user, the default value of DOCKER_HOST should be the
    # unix socket.

    # first check if the socket is valid to give a better feedback to the user.
    if os.path.exists(DEFAULT_LINUX_DOCKER_HOST):
      sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
      try:
        sock.connect(DEFAULT_LINUX_DOCKER_HOST)
        params['base_url'] = 'unix://' + DEFAULT_LINUX_DOCKER_HOST
      except socket.error:
        log.warning('Found a stale /var/run/docker.sock, '
                    'did you forget to start your Docker daemon?')
      finally:
        sock.close()

  if tls_verify and cert_path:
    # assert_hostname=False is needed for boot2docker to work with our custom
    # registry.
    params['tls'] = docker.tls.TLSConfig(
        client_cert=(os.path.join(cert_path, 'cert.pem'),
                     os.path.join(cert_path, 'key.pem')),
        ca_cert=os.path.join(cert_path, 'ca.pem'),
        verify=True,
        ssl_version=ssl.PROTOCOL_TLSv1,
        assert_hostname=False)
  return params


def NewDockerClientNoCheck(**kwargs):
  """Factory method for building a docker.Client from environment variables.

  Args:
    **kwargs: Any kwargs will be passed to the docker.Client constructor and
      override any determined from the environment.

  Returns:
    A docker.Client instance.

  Raises:
    DockerDaemonConnectionError: If the Docker daemon isn't responding.
  """
  kwargs['version'] = config.DOCKER_PY_VERSION
  kwargs['timeout'] = config.DOCKER_D_REQUEST_TIMEOUT

  if 'base_url' not in kwargs:
    raise DockerDaemonConnectionError(DOCKER_CONNECTION_ERROR)
  return docker.Client(**kwargs)


def NewDockerClient(local=False, **kwargs):
  """Factory method for building a docker.Client from environment variables.

  Args:
    local: bool, whether this is a local docker build
    **kwargs: Any kwargs will be passed to the docker.Client constructor and
      override any determined from the environment.

  Returns:
    A docker.Client instance.

  Raises:
    DockerDaemonConnectionError: If the Docker daemon isn't responding.
  """
  client = NewDockerClientNoCheck(**kwargs)
  try:
    client.ping()
  except requests.exceptions.SSLError as e:
    # Will be surfaced as error in the thrown exception
    log.debug('Failed to connect to Docker daemon due to an SSL problem: %s', e)
    msg = ''
    # There is a common problem with TLS and docker-py on OS X Python
    # installations, especially the one in Homebrew.
    if platforms.Platform.Current() == platforms.OperatingSystem.MACOSX:
      msg += ('\n\nThis may be due to the issue described at the following '
              'URL, especially if you\'re using a Python installation from '
              'Homebrew: '
              'https://github.com/docker/docker-py/issues/465\n\n'
              'One possible workaround is to set the environment variable '
              'CLOUDSDK_PYTHON to another Python executable (that is, not the '
              'one from Homebrew).')
      try:
        # This is a part of requests[security], which is a set of optional
        # dependencies for the requests library. If installed, it can work
        # around the SSL issue.
        # pylint: disable=g-import-not-at-top
        import ndg  # pylint: disable=import-error,unused-variable
        # pylint: enable=g-import-not-at-top
      except ImportError:
        msg += ('\n\nYou do not appear to have requests[security] installed. '
                'Consider installing this package (which bundles security '
                'libraries that may fix this problem) to the current Python '
                'installation as another possible workaround:\n'
                '  pip install requests[security]\n'
                'If you do this, you must set the environment variable '
                'CLOUDSDK_PYTHON_SITEPACKAGES before running the Cloud SDK '
                'again:\n'
                '  export CLOUDSDK_PYTHON_SITEPACKAGES=1')
    raise DockerDaemonConnectionError(
        'Couldn\'t connect to the Docker daemon due to an SSL problem.' + msg)
  except requests.exceptions.ConnectionError, e:
    # Will be surfaced as error in the thrown exception
    log.debug('Failed to connect to Docker Daemon due to: %s', e)
    msg = DOCKER_CONNECTION_ERROR
    if local:
      msg += '\n' + DOCKER_CONNECTION_ERROR_LOCAL
    raise DockerDaemonConnectionError(msg)
  return client
