# Copyright 2015 Google Inc. All Rights Reserved.

"""Module to provision a remote docker instance on GCE."""

import os
import sys
import tempfile
import threading
import time

from googlecloudsdk.api_lib.app import containers
from googlecloudsdk.api_lib.app import metric_names
from googlecloudsdk.calliope import exceptions
from googlecloudsdk.core import log
from googlecloudsdk.core import metrics
from googlecloudsdk.core import properties
from googlecloudsdk.core.util import files

_RETRIES = 20
_RETRY_TIME = 1
_REMOTE_CERT_FORMAT = '{name}:/clientcert/*'
_FIREWALL_RULE_NAME = 'allow-gae-builder'
_FIREWALL_RULE_ALLOW = 'tcp:2376'
_INSTANCE_TAG = 'gae-builder'


def Provision(cli, name, zone):
  """Provisions a GCE VM to act as a remote Docker host.

  This is the main entrypoint of this module. This function configures a
  network, creates a VM, copies certificates and sets up environment variables.

  Args:
    cli: calliope.cli.CLI, The CLI object representing this command line tool.
    name: The name of the GCE instance.
    zone: The zone to place the instance in.
  Returns:
    A _Vm instance.
  Raises:
    ToolException: If there is an error provisioning the instance.
  """
  log.status.Print('Provisioning remote build service.')
  if _ShouldConfigureNetwork(cli):
    log.info('Adding firewall rule [{name}] for remote '
             'builds.'.format(name=name))
    _ConfigureNetwork(cli)
  else:
    log.info('Network already configured.')

  log.info('Creating remote build VM [{name}]'.format(name=name))
  vm = _CreateVm(cli, name, zone)
  log.status.Print('Copying certificates for secure access. You may be '
                   'prompted to create an SSH keypair.')
  vm.CopyCerts()
  return vm


def _ShouldConfigureNetwork(cli):
  """Determines whether or not the project's network needs to be configured.

  Args:
    cli: calliope.cli.CLI, The CLI object representing this command line tool.
  Returns:
    A bool indicating whether or not to configure the network.
  """
  rules = cli.Execute(['compute', 'firewall-rules', 'list',
                       '--no-user-output-enabled'])
  return not any(r for r in rules if r['name'] == _FIREWALL_RULE_NAME)


def _ConfigureNetwork(cli):
  """Configures the project's network.

  Args:
    cli: calliope.cli.CLI, The CLI object representing this command line tool.
  """
  cli.Execute(
      ['compute', 'firewall-rules', 'create', _FIREWALL_RULE_NAME,
       '--allow={allow}'.format(allow=_FIREWALL_RULE_ALLOW),
       '--target-tags={tag}'.format(tag=_INSTANCE_TAG)])


def _CreateVm(cli, name, zone):
  """Creates a VM.

  Args:
    cli: calliope.cli.CLI, The CLI object representing this command line tool.
    name: The name of the VM.
    zone: The zone to create the VM in.
  Returns:
    A VM instance.
  """
  output = cli.Execute(
      ['compute', 'instances', 'create', name,
       '--image', properties.VALUES.app.hosted_build_image.Get(),
       '--tags', _INSTANCE_TAG,
       '--machine-type',
       properties.VALUES.app.hosted_build_machine_type.Get(),
       '--boot-disk-size',
       properties.VALUES.app.hosted_build_boot_disk_size.Get(),
       '--zone', zone,
       '--no-restart-on-failure',
       '--no-user-output-enabled'])
  # Exhaust the generator.
  vm_info = list(output)
  return _Vm(cli, vm_info[0])


class _Vm(object):
  """Represents a GCE VM configured to act as a remote docker host.

  This class contains methods to retrieve certificates and set the correct
  environment variables so a docker.Client instance can connect to a Docker
  daemon running on the VM.

  This class should not be instantiated directly. It should be created by
  calling _CreateVm.
  """

  def __init__(self, cli, vm_info):
    self._cli = cli
    self._teardown_thread = None
    # We have to do relpath here because SCP doesn't handle "c:\" paths
    # correctly on Windows.
    self.cert_dir = os.path.relpath(tempfile.mkdtemp(dir=os.getcwd()))
    self._ip = vm_info['networkInterfaces'][0]['accessConfigs'][0]['natIP']
    self._name = vm_info['name']
    self._zone = vm_info['zone']

  @property
  def host(self):
    return 'tcp://{ip}:2376'.format(ip=self._ip)

  def CopyCerts(self):
    """Copies certificates from the VM for secure access.

    This can fail if the function is called before the VM is ready for SSH, or
    before the certificates are generated, so some retries are needed.

    Raises:
      exceptions.ToolException: If the certificates cannot be copied after all
        the retries.
    """
    for i in range(_RETRIES):
      try:
        self._cli.Execute(
            ['compute', 'copy-files', '--zone', self._zone,
             '--verbosity', 'none', '--no-user-output-enabled', '--quiet',
             _REMOTE_CERT_FORMAT.format(name=self._name), self.cert_dir])
        break
      except (SystemExit, exceptions.ToolException):
        log.debug(
            'Error copying certificates. Retry {retry} of {retries}.'.format(
                retry=i, retries=_RETRIES))
        time.sleep(_RETRY_TIME)
        continue
    else:
      raise exceptions.ToolException('Unable to copy certificates.')

  def StartTeardown(self):
    """Starts tearing down the remote build vm in a separate process."""
    log.info('Tearing down remote build vm.')
    self._teardown_thread = threading.Thread(target=self._Teardown)
    self._teardown_thread.start()

  def _Teardown(self):
    """Does the actual teardown. Deletes the tmpdir and the VM."""
    try:
      # It looks like the --verbosity parameter is not threadsafe, and this
      # runs in parallel. Any verbosity options we pass to this command can
      # override the rest of the command and mask errors. See b/22725326 for
      # more context.
      self._cli.Execute(
          ['compute', 'instances', 'delete', self._name,
           '--zone', self._zone, '-q'])
    except (SystemExit, exceptions.ToolException) as e:
      log.error('There was an error tearing down the remote build VM. Please '
                'check that the VM was deleted.')
      log.file_only_logger.error(
          'Teardown error: %s', e, exc_info=sys.exc_info())
    files.RmTree(self.cert_dir)


class DockerHost(object):
  """A context manager for provisioning and connecting to a Docker daemon."""

  def __init__(self, cli, version, remote):
    """Initializes a DockerHost.

    Args:
      cli: calliope.cli.CLI, The CLI object representing this command line tool.
      version: The app version being deployed.
      remote: Whether the Docker host should be remote (On GCE).
    """
    self._remote = remote
    self._name = 'gae-builder-vm-{version}'.format(version=version)
    self._zone = properties.VALUES.app.hosted_build_zone.Get()
    self._cli = cli
    self._vm = None

  def __enter__(self):
    """Sets up a docker host, if necessary.

    Returns:
      A docker.Client instance.
    """
    if self._remote:
      self._vm = Provision(self._cli, self._name, self._zone)
      kwargs = containers.KwargsFromEnv(self._vm.host, self._vm.cert_dir, True)
    else:
      kwargs = containers.KwargsFromEnv(os.environ.get('DOCKER_HOST'),
                                        os.environ.get('DOCKER_CERT_PATH'),
                                        os.environ.get('DOCKER_TLS_VERIFY'))
    metrics.CustomTimedEvent(metric_names.DOCKER_PROVISION)
    return containers.NewDockerClient(local=(not self._remote), **kwargs)

  def __exit__(self, unused_type, unused_value, unused_traceback):
    """Starts an async teardown of the docker host, if necessary."""
    if self._remote:
      self._vm.StartTeardown()
      metrics.CustomTimedEvent(metric_names.DOCKER_TEAR_DOWN)
