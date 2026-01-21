# -*- coding: utf-8 -*- #
# Copyright 2024 Google LLC. All Rights Reserved.
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
"""Common logic between commands on Config Management surface."""

from googlecloudsdk.command_lib.container.fleet.config_management import utils
from googlecloudsdk.command_lib.container.fleet.features import base
from googlecloudsdk.command_lib.container.fleet.policycontroller import constants
from googlecloudsdk.core import exceptions
from googlecloudsdk.core import yaml

# TODO(b/298461043): Move error message instructions into
# https://cloud.google.com/anthos-config-management/docs/reference/gcloud-apply-fields.
MAP_NODE_EXCEPTION_FORMAT = ('{} must be a YAML mapping node.'
                             ' This field should either contain indented'
                             ' key, value pairs or have the empty map {{}} as'
                             ' its value.'
                             ' See --help flag output for links to examples.')

LIST_EXCEPTION_FORMAT = (
    '{} must be a YAML list.'
    ' This field should contain indented'
    ' list elements.'
    ' See --help flag output for links to examples.'
)


class Common(base.FeatureCommand):
  """Common operations between commands on Config Management surface.
  """

  def parse_config_management(self, config_file_path):
    """Parse a Config Management membership spec from config_file_path.

    Args:
      config_file_path: Path to file with syntax following the --config flag of
        the apply command.
    Returns:
      config_management: Populated ConfigManagementMembershipSpec message.
    Raises: Any errors during parsing. May not check semantic meaning of
      field values.
    """
    # TODO(b/298461043): Investigate whether it is worth our time to move the
    # apply-spec syntax into proto so that we get automatic parsing.
    try:
      config = yaml.load_path(config_file_path)
    except yaml.Error as e:
      raise exceptions.Error(
          'Invalid config yaml file {}'.format(config_file_path), e
      )
    _validate_meta(config)
    # TODO(b/298461043): Align on parsing and error messages across ACM
    # sub-components.
    # TODO(b/298461043): Scan for illegal fields by reading from
    # utils.APPLY_SPEC_VERSION_1. Access specific fields via constant variables
    # in utils.
    return self.messages.ConfigManagementMembershipSpec(
        configSync=self._parse_config_sync(config),
        policyController=self._parse_policy_controller(config),
        hierarchyController=self._parse_hierarchy_controller_config(config),
        management=self._parse_upgrades(config),
        cluster=config.get('spec', {}).get('cluster', ''),
        version=config['spec'].get(utils.VERSION),
    )

  def _parse_config_sync(self, configmanagement):
    """Load ConfigSync configuration with the parsed configmanagement yaml.

    Args:
      configmanagement: dict, The data loaded from the config-management.yaml
        given by user.

    Returns:
      config_sync: The ConfigSync configuration holds configmanagement.spec.git
      or configmanagement.spec.oci being used in MembershipConfigs
    Raises: gcloud core Error, if the configSync field on configmanagement has
      invalid syntax. Note that this function does not check semantic meaning of
      field values, other than for .spec.configSync.sourceType.
    """

    if (
        'spec' not in configmanagement
        or utils.CONFIG_SYNC not in configmanagement['spec']
    ):
      return None
    if not isinstance(configmanagement['spec'][utils.CONFIG_SYNC], dict):
      raise exceptions.Error(
          MAP_NODE_EXCEPTION_FORMAT.format('.spec.'+utils.CONFIG_SYNC)
      )
    spec_source = configmanagement['spec'][utils.CONFIG_SYNC]
    illegal_fields = _find_unknown_fields(spec_source,
                                          yaml.load(utils.APPLY_SPEC_VERSION_1)
                                          ['spec'][utils.CONFIG_SYNC])
    if illegal_fields:
      raise exceptions.Error('Please remove illegal field(s) {}'.format(
          ', '.join(['.spec.{}.{}'.format(utils.CONFIG_SYNC, f)
                     for f in illegal_fields])
      ))

    config_sync = self.messages.ConfigManagementConfigSync()
    if utils.DEPLOYMENT_OVERRIDES in spec_source:
      setattr(
          config_sync,
          utils.DEPLOYMENT_OVERRIDES,
          self._parse_deployment_overrides(
              spec_source[utils.DEPLOYMENT_OVERRIDES]
          ),
      )
    # missing `enabled: true` will enable configSync
    config_sync.enabled = True
    if 'enabled' in spec_source:
      config_sync.enabled = spec_source['enabled']
    # Default to use sourceType 'git' if not specified
    source_type = spec_source.get('sourceType', 'git')
    if source_type == 'git':
      config_sync.git = self._parse_git_config(spec_source)
    elif source_type == 'oci':
      config_sync.oci = self._parse_oci_config(spec_source)
    else:
      raise exceptions.Error((
          '.spec.{}.sourceType has illegal value {}.'
          ' Please replace with `git` or `oci`'.format(
              utils.CONFIG_SYNC, source_type
          )
      ))
    if 'sourceFormat' in spec_source:
      config_sync.sourceFormat = spec_source['sourceFormat']
    if 'stopSyncing' in spec_source:
      config_sync.stopSyncing = spec_source['stopSyncing']
    if 'preventDrift' in spec_source:
      config_sync.preventDrift = spec_source['preventDrift']
    if 'metricsGcpServiceAccountEmail' in spec_source:
      config_sync.metricsGcpServiceAccountEmail = spec_source[
          'metricsGcpServiceAccountEmail'
      ]
    return config_sync

  def _parse_deployment_overrides(self, spec_deployment_overrides):
    """Load DeploymentOverrides with the parsed config-management.yaml."""
    if not isinstance(spec_deployment_overrides, list):
      raise exceptions.Error(
          LIST_EXCEPTION_FORMAT.format(
              '.spec.configSync.' + utils.DEPLOYMENT_OVERRIDES
          )
      )
    deployment_overrides = []
    for deployment_override in spec_deployment_overrides:
      illegal_fields = _find_unknown_fields(
          deployment_override,
          {
              'name',
              'namespace',
              utils.CONTAINER_OVERRIDES,
          },
      )
      if illegal_fields:
        raise exceptions.Error(
            'Please remove illegal field(s) {}'.format(
                ', '.join([
                    '.spec.configSync.deploymentOverrides.' + f
                    for f in illegal_fields
                ])
            )
        )
      deployment_overrides.append(
          self.messages.ConfigManagementDeploymentOverride(
              deploymentName=deployment_override.get('name', ''),
              deploymentNamespace=deployment_override.get(
                  'namespace', ''
              ),
              containers=self._parse_containers(
                  deployment_override.get(utils.CONTAINER_OVERRIDES, [])
              ),
          )
      )
    return deployment_overrides

  def _parse_containers(self, spec_containers):
    """Load Containers with the parsed config-management.yaml."""
    if not isinstance(spec_containers, list):
      raise exceptions.Error(
          LIST_EXCEPTION_FORMAT.format(
              '.spec.configSync.'
              + utils.DEPLOYMENT_OVERRIDES
              + '.'
              + utils.CONTAINER_OVERRIDES
          )
      )
    containers = []
    for container in spec_containers:
      illegal_fields = _find_unknown_fields(
          container,
          {
              'name',
              'cpuRequest',
              'memoryRequest',
              'cpuLimit',
              'memoryLimit',
          },
      )
      if illegal_fields:
        raise exceptions.Error(
            'Please remove illegal field(s) {}'.format(
                ', '.join([
                    '.spec.configSync.deploymentOverrides.containers.' + f
                    for f in illegal_fields
                ])
            )
        )
      containers.append(
          self.messages.ConfigManagementContainerOverride(
              containerName=container.get('name', ''),
              cpuRequest=container.get('cpuRequest', ''),
              memoryRequest=container.get('memoryRequest', ''),
              cpuLimit=container.get('cpuLimit', ''),
              memoryLimit=container.get('memoryLimit', ''),
          )
      )
    return containers

  def _parse_git_config(self, spec_source):
    """Load GitConfig with the parsed config_sync yaml.

    Args:
      spec_source: The config_sync dict loaded from the config-management.yaml
        given by user.

    Returns:
      git_config: The GitConfig configuration being used in MembershipConfigs
    """

    git_config = self.messages.ConfigManagementGitConfig()
    if 'syncWait' in spec_source:
      git_config.syncWaitSecs = spec_source['syncWait']
    for field in [
        'policyDir',
        'secretType',
        'syncBranch',
        'syncRepo',
        'syncRev',
        'httpsProxy',
        'gcpServiceAccountEmail',
    ]:
      if field in spec_source:
        setattr(git_config, field, spec_source[field])
    return git_config

  def _parse_oci_config(self, spec_source):
    """Load OciConfig with the parsed config_sync yaml.

    Args:
      spec_source: The config_sync dict loaded from the config-management.yaml
        given by user.

    Returns:
      oci_config: The OciConfig being used in MembershipConfigs
    """

    oci_config = self.messages.ConfigManagementOciConfig()
    if 'syncWait' in spec_source:
      oci_config.syncWaitSecs = spec_source['syncWait']
    for field in [
        'policyDir',
        'secretType',
        'syncRepo',
        'gcpServiceAccountEmail',
    ]:
      if field in spec_source:
        setattr(oci_config, field, spec_source[field])
    return oci_config

  def _parse_policy_controller(self, configmanagement):
    """Load PolicyController with the parsed config-management.yaml.

    Args:
      configmanagement: dict, The data loaded from the config-management.yaml
        given by user.

    Returns:
      policy_controller: The Policy Controller configuration for
      MembershipConfigs, filled in the data parsed from
      configmanagement.spec.policyController
    Raises:
      gcloud core Error, if Policy Controller has invalid syntax. Note that
      this function does not check semantic meaning of field values other than
      monitoring backends.
    """

    if (
        'spec' not in configmanagement
        or 'policyController' not in configmanagement['spec']
    ):
      return None

    if not isinstance(configmanagement['spec']['policyController'], dict):
      raise exceptions.Error(
          MAP_NODE_EXCEPTION_FORMAT.format('.spec.policyController')
      )
    spec_policy_controller = configmanagement['spec']['policyController']
    # Required field
    if 'enabled' not in spec_policy_controller:
      raise exceptions.Error(
          'Missing required field .spec.policyController.enabled'
      )
    enabled = spec_policy_controller['enabled']
    if not isinstance(enabled, bool):
      raise exceptions.Error(
          'policyController.enabled should be `true` or `false`'
      )

    policy_controller = self.messages.ConfigManagementPolicyController()
    # When the policyController is set to be enabled, policy_controller will
    # be filled with the valid fields set in spec_policy_controller, which
    # were mapped from the config-management.yaml
    illegal_fields = _find_unknown_fields(spec_policy_controller, {
        'enabled',
        'templateLibraryInstalled',
        'auditIntervalSeconds',
        'referentialRulesEnabled',
        'exemptableNamespaces',
        'logDeniesEnabled',
        'mutationEnabled',
        'monitoring',
    })
    if illegal_fields:
      raise exceptions.Error('Please remove illegal field(s) {}'.format(
          ', '.join(['.spec.policyController.'+f for f in illegal_fields])
      ))
    for field in spec_policy_controller:
      if field == 'monitoring':
        monitoring = self._build_monitoring_msg(spec_policy_controller[field])
        setattr(policy_controller, field, monitoring)
      else:
        setattr(policy_controller, field, spec_policy_controller[field])

    return policy_controller

  def _build_monitoring_msg(self, spec_monitoring):
    """Build PolicyControllerMonitoring message from the parsed spec.

    Args:
      spec_monitoring: dict, The monitoring data loaded from the
        config-management.yaml given by user.

    Returns:
      monitoring: The Policy Controller Monitoring configuration for
      MembershipConfigs, filled in the data parsed from
      configmanagement.spec.policyController.monitoring
    Raises: gcloud core Error, if spec_monitoring is invalid, including its
      backend values.
    """
    if not isinstance(spec_monitoring, dict):
      raise exceptions.Error(
          MAP_NODE_EXCEPTION_FORMAT.format('.spec.policyController.monitoring')
      )
    backends = spec_monitoring.get('backends', [])
    if not backends:
      return None

    # n.b. Policy Controller is the source of truth for supported backends.
    converter = constants.monitoring_backend_converter(self.messages)

    def convert(backend):
      result = converter.get(backend.lower())
      if not result:
        raise exceptions.Error(
            'policyController.monitoring.backend {} is not recognized'.format(
                backend
            )
        )
      return result
    try:
      monitoring_backends = [convert(backend) for backend in backends]
    except (TypeError, AttributeError):
      raise exceptions.Error(
          ('.spec.policyController.monitoring.backend must be a sequence of'
           ' strings. See --help flag output for details')
      )
    return self.messages.ConfigManagementPolicyControllerMonitoring(
        backends=monitoring_backends
    )

  def _parse_hierarchy_controller_config(self, configmanagement):
    """Load HierarchyController with the parsed config-management.yaml.

    Args:
      configmanagement: dict, The data loaded from the config-management.yaml
        given by user.

    Returns:
      hierarchy_controller: The Hierarchy Controller configuration for
      MembershipConfigs, filled in the data parsed from
      configmanagement.spec.hierarchyController
    Raises: gcloud core Error, if Hierarchy Controller has invalid syntax. Note
      that this function does not check semantic meaning of field values.
    """

    if (
        'spec' not in configmanagement
        or 'hierarchyController' not in configmanagement['spec']
    ):
      return None

    if not isinstance(configmanagement['spec']['hierarchyController'], dict):
      raise exceptions.Error(
          MAP_NODE_EXCEPTION_FORMAT.format('.spec.hierarchyController')
      )
    spec = configmanagement['spec']['hierarchyController']
    # Required field
    if 'enabled' not in spec:
      raise exceptions.Error(
          'Missing required field .spec.hierarchyController.enabled'
      )
    if not isinstance(spec['enabled'], bool):
      raise exceptions.Error(
          'hierarchyController.enabled should be `true` or `false`'
      )

    config_proto = self.messages.ConfigManagementHierarchyControllerConfig()
    # When the hierarchyController is set to be enabled, hierarchy_controller
    # will be filled with the valid fields set in spec, which
    # were mapped from the config-management.yaml
    illegal_fields = _find_unknown_fields(spec, {
        'enabled',
        'enablePodTreeLabels',
        'enableHierarchicalResourceQuota',
    })
    if illegal_fields:
      raise exceptions.Error('Please remove illegal field(s) {}'.format(
          ', '.join(['.spec.hierarchyController.'+f for f in illegal_fields])
      ))
    for field in spec:
      setattr(config_proto, field, spec[field])

    return config_proto

  def _parse_upgrades(self, configmanagement) -> str:
    """Parse configmanagement `.spec.upgrades` into management  enum.

    Args:
      configmanagement: dict of file contents for --config flag on apply command
        that represents Config Management membership spec.
    Returns:
      v1main ConfigManagementMembershipSpec management value.
    Raises: gcloud core Error for invalid value.
    """
    upgrades = configmanagement.get('spec', {}).get(utils.UPGRADES, '')
    legal_fields = [
        utils.UPGRADES_AUTO,
        utils.UPGRADES_MANUAL,
        utils.UPGRADES_EMPTY,
    ]
    valid_values = ' '.join(f"'{field}'" for field in legal_fields)
    if upgrades not in legal_fields:
      raise exceptions.Error(
          'The valid values of field .spec.{} are: {}'.format(
              utils.UPGRADES, valid_values
          )
      )
    spec_api = self.messages.ConfigManagementMembershipSpec
    if upgrades == utils.UPGRADES_AUTO:
      return spec_api.ManagementValueValuesEnum.MANAGEMENT_AUTOMATIC
    else:
      return spec_api.ManagementValueValuesEnum.MANAGEMENT_MANUAL


def _validate_meta(configmanagement):
  """Validate the parsed configmanagement yaml.

  Args:
    configmanagement: Data type loaded from yaml.
  Raises: gcloud core Error, if the top-level fields have invalid syntax.
  """
  if not isinstance(configmanagement, dict):
    raise exceptions.Error('Invalid ConfigManagement template.')
  illegal_root_fields = _find_unknown_fields(configmanagement, {
      'applySpecVersion',
      'spec',
  })
  if illegal_root_fields:
    raise exceptions.Error('Please remove illegal field(s) {}'.format(
        ', '.join(['.'+f for f in illegal_root_fields])
    ))
  if 'applySpecVersion' not in configmanagement:
    raise exceptions.Error('Missing required field .applySpecVersion')
  if configmanagement['applySpecVersion'] != 1:
    raise exceptions.Error(
        'Only "applySpecVersion: 1" is supported.'
    )
  if 'spec' not in configmanagement:
    raise exceptions.Error('Missing required field .spec')
  if not isinstance(configmanagement['spec'], dict):
    raise exceptions.Error(MAP_NODE_EXCEPTION_FORMAT.format('.spec'))
  illegal_spec_fields = _find_unknown_fields(configmanagement['spec'], {
      utils.CONFIG_SYNC,
      utils.POLICY_CONTROLLER,
      utils.HNC,
      utils.CLUSTER,
      utils.UPGRADES,
      utils.VERSION,
  })
  if illegal_spec_fields:
    raise exceptions.Error('Please remove illegal field(s) {}'.format(
        ', '.join(['.spec.'+f for f in illegal_spec_fields])
    ))


def _find_unknown_fields(source, known_fields):
  """Returns the list of string elements in source not in known_fields.

  Args:
    source: The source iterable to check.
    known_fields: The collection of known fields.
  """
  illegal_fields = []
  for field in source:
    if field not in known_fields:
      illegal_fields.append(field)
  return illegal_fields
