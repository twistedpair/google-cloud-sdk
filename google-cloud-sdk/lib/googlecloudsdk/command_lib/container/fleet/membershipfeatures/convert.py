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
"""Base classes for commands for MembershipFeature resource."""


from __future__ import absolute_import
from __future__ import division
from __future__ import unicode_literals

from apitools.base.py import encoding
from googlecloudsdk.calliope import base


def ToV2MembershipFeature(
    self,
    membership_path: str,
    feature_name: str,
    v1_membership_feature_spec,
):
  """Converts a v1alpha MembershipFeature to a v2alpha MembershipFeature."""
  v2_membershipfeature = self.messages_v2.MembershipFeature()
  v2_membershipfeature.name = f'{membership_path}/features/{feature_name}'
  v2_membershipfeature.spec = self.messages_v2.FeatureSpec()
  v2_membershipfeature.spec.origin = _ToV2Origin(
      self, v1_membership_feature_spec.origin
  )

  if feature_name == 'policycontroller':
    v2_membershipfeature.spec.policycontroller = _ToV2PolicyControllerSpec(
        self, v1_membership_feature_spec.policycontroller
    )
  elif feature_name == 'configmanagement':
    v2_membershipfeature.spec.configmanagement = _ToV2ConfigManagementSpec(
        self, v1_membership_feature_spec.configmanagement
    )
  else:
    raise ValueError(
        f'Unsupported membership feature: {v2_membershipfeature.name}'
    )
  return v2_membershipfeature


def _ToV2ConfigManagementSpec(
    self,
    v1_configmanagement_spec,
):
  """Converts a v1alpha ConfigManagementMembershipSpec to a v2alpha ConfigManagementSpec."""
  if v1_configmanagement_spec is None:
    return None

  v2_configmanagement_spec = self.messages_v2.ConfigManagementSpec()
  if (
      self.ReleaseTrack() is base.ReleaseTrack.ALPHA
      or self.ReleaseTrack() is base.ReleaseTrack.BETA
  ):
    v2_configmanagement_spec.binauthz = _ToV2ConfigManagementBinauthzConfig(
        self, v1_configmanagement_spec.binauthz
    )

  v2_configmanagement_spec.cluster = v1_configmanagement_spec.cluster
  v2_configmanagement_spec.configSync = _ToV2ConfigManagementConfigSync(
      self, v1_configmanagement_spec.configSync
  )
  v2_configmanagement_spec.hierarchyController = (
      _ToV2ConfigManagementHierarchyController(
          self, v1_configmanagement_spec.hierarchyController
      )
  )
  v2_configmanagement_spec.management = (
      _ToV2ConfigManagementManagementValueValuesEnum(
          self, v1_configmanagement_spec.management
      )
  )
  v2_configmanagement_spec.policyController = (
      _ToV2ConfigManagementPolicyController(
          self, v1_configmanagement_spec.policyController
      )
  )
  v2_configmanagement_spec.version = v1_configmanagement_spec.version
  return v2_configmanagement_spec


def _ToV2ConfigManagementBinauthzConfig(
    self,
    v1_binauthz_config,
):
  """Converts a v1alpha ConfigManagementBinauthzConfig to a v2alpha ConfigManagementBinauthzConfig."""
  if v1_binauthz_config is None:
    return None

  v2_binauthz_config = self.messages_v2.ConfigManagementBinauthzConfig()
  v2_binauthz_config.enabled = v1_binauthz_config.enabled
  return v2_binauthz_config


def _ToV2ConfigManagementConfigSync(
    self,
    v1_configsync,
):
  """Converts a v1alpha ConfigManagementConfigSync to a v2alpha ConfigManagementConfigSync."""
  if v1_configsync is None:
    return None

  v2_configsync = self.messages_v2.ConfigManagementConfigSync()
  v2_configsync.enabled = v1_configsync.enabled
  v2_configsync.git = _ToV2ConfigManagementGitConfig(self, v1_configsync.git)
  v2_configsync.deploymentOverrides = [
      _ToV2ConfigManagementDeploymentOverride(self, deployment_override)
      for deployment_override in v1_configsync.deploymentOverrides
  ]
  v2_configsync.metricsGcpServiceAccountEmail = (
      v1_configsync.metricsGcpServiceAccountEmail
  )
  v2_configsync.oci = _ToV2ConfigManagementOciConfig(self, v1_configsync.oci)
  v2_configsync.preventDrift = v1_configsync.preventDrift
  v2_configsync.sourceFormat = v1_configsync.sourceFormat
  v2_configsync.stopSyncing = v1_configsync.stopSyncing
  return v2_configsync


def _ToV2ConfigManagementDeploymentOverride(
    self,
    v1_deployment_override,
):
  """Converts a v1alpha ConfigManagementDeploymentOverride to a v2alpha ConfigManagementDeploymentOverride."""
  if v1_deployment_override is None:
    return None
  v2_deployment_override = self.messages_v2.ConfigManagementDeploymentOverride()
  v2_deployment_override.deploymentName = v1_deployment_override.deploymentName
  v2_deployment_override.deploymentNamespace = (
      v1_deployment_override.deploymentNamespace
  )
  v2_deployment_override.containers = [
      _ToV2ConfigManagementContainerOverride(self, container)
      for container in v1_deployment_override.containers
  ]
  return v2_deployment_override


def _ToV2ConfigManagementContainerOverride(
    self,
    v1_container,
):
  """Converts a v1alpha ConfigManagementContainerOverride to a v2alpha ConfigManagementContainerOverride."""
  if v1_container is None:
    return None
  v2_container = self.messages_v2.ConfigManagementContainerOverride()
  v2_container.containerName = v1_container.containerName
  v2_container.cpuRequest = v1_container.cpuRequest
  v2_container.memoryRequest = v1_container.memoryRequest
  v2_container.cpuLimit = v1_container.cpuLimit
  v2_container.memoryLimit = v1_container.memoryLimit
  return v2_container


def _ToV2ConfigManagementGitConfig(
    self,
    v1_git_config,
):
  """Converts a v1alpha ConfigManagementGitConfig to a v2alpha ConfigManagementGitConfig."""
  if v1_git_config is None:
    return None

  v2_git_config = self.messages_v2.ConfigManagementGitConfig()
  v2_git_config.gcpServiceAccountEmail = v1_git_config.gcpServiceAccountEmail
  v2_git_config.httpsProxy = v1_git_config.httpsProxy
  v2_git_config.policyDir = v1_git_config.policyDir
  v2_git_config.secretType = v1_git_config.secretType
  v2_git_config.syncBranch = v1_git_config.syncBranch
  v2_git_config.syncRepo = v1_git_config.syncRepo
  v2_git_config.syncRev = v1_git_config.syncRev
  v2_git_config.syncWaitSecs = v1_git_config.syncWaitSecs
  return v2_git_config


def _ToV2ConfigManagementOciConfig(
    self,
    v1_oci_config,
):
  """Converts a v1alpha ConfigManagementOciConfig to a v2alpha ConfigManagementOciConfig."""
  if v1_oci_config is None:
    return None

  v2_oci_config = self.messages_v2.ConfigManagementOciConfig()
  v2_oci_config.gcpServiceAccountEmail = v1_oci_config.gcpServiceAccountEmail
  v2_oci_config.policyDir = v1_oci_config.policyDir
  v2_oci_config.secretType = v1_oci_config.secretType
  v2_oci_config.syncRepo = v1_oci_config.syncRepo
  v2_oci_config.syncWaitSecs = v1_oci_config.syncWaitSecs
  return v2_oci_config


def _ToV2ConfigManagementHierarchyController(
    self,
    v1_hierarchy_controller,
):
  """Converts a v1alpha ConfigManagementHierarchyController to a v2alpha ConfigManagementHierarchyController."""
  if v1_hierarchy_controller is None:
    return None

  v2_hierarchy_controller = (
      self.messages_v2.ConfigManagementHierarchyControllerConfig()
  )
  v2_hierarchy_controller.enableHierarchicalResourceQuota = (
      v1_hierarchy_controller.enableHierarchicalResourceQuota
  )
  v2_hierarchy_controller.enablePodTreeLabels = (
      v1_hierarchy_controller.enablePodTreeLabels
  )
  v2_hierarchy_controller.enabled = v1_hierarchy_controller.enabled
  return v2_hierarchy_controller


def _ToV2ConfigManagementManagementValueValuesEnum(
    self,
    v1_management,
):
  """Converts a v1alpha ConfigManagementMembershipSpec.ManagementValueValuesEnum to a v2alpha ConfigManagementManagementValueValuesEnum."""
  if v1_management is None:
    return None

  if (
      v1_management
      is self.messages.ConfigManagementMembershipSpec.ManagementValueValuesEnum.MANAGEMENT_UNSPECIFIED
  ):
    return (
        self.messages_v2.ConfigManagementSpec.ManagementValueValuesEnum.MANAGEMENT_UNSPECIFIED
    )
  elif (
      v1_management
      is self.messages.ConfigManagementMembershipSpec.ManagementValueValuesEnum.MANAGEMENT_AUTOMATIC
  ):
    return (
        self.messages_v2.ConfigManagementSpec.ManagementValueValuesEnum.MANAGEMENT_AUTOMATIC
    )
  elif (
      v1_management
      is self.messages.ConfigManagementMembershipSpec.ManagementValueValuesEnum.MANAGEMENT_MANUAL
  ):
    return (
        self.messages_v2.ConfigManagementSpec.ManagementValueValuesEnum.MANAGEMENT_MANUAL
    )
  else:
    raise ValueError(f'Unsupported management value: {v1_management}')


def _ToV2ConfigManagementPolicyController(
    self,
    v1_policycontroller,
):
  """Converts a v1alpha ConfigManagementPolicyController to a v2alpha ConfigManagementPolicyController."""
  if v1_policycontroller is None:
    return None

  v2_policycontroller = self.messages_v2.ConfigManagementPolicyController()
  v2_policycontroller.auditIntervalSeconds = (
      v1_policycontroller.auditIntervalSeconds
  )
  v2_policycontroller.enabled = v1_policycontroller.enabled
  v2_policycontroller.exemptableNamespaces = (
      v1_policycontroller.exemptableNamespaces
  )
  v2_policycontroller.logDeniesEnabled = v1_policycontroller.logDeniesEnabled
  v2_policycontroller.monitoring = (
      _ToV2ConfigManagementPolicyControllerMonitoring(
          self, v1_policycontroller.monitoring
      )
  )
  v2_policycontroller.mutationEnabled = v1_policycontroller.mutationEnabled
  v2_policycontroller.referentialRulesEnabled = (
      v1_policycontroller.referentialRulesEnabled
  )
  v2_policycontroller.templateLibraryInstalled = (
      v1_policycontroller.templateLibraryInstalled
  )
  v2_policycontroller.updateTime = v1_policycontroller.updateTime
  return v2_policycontroller


def _ToV2ConfigManagementPolicyControllerMonitoring(
    self,
    v1_monitoring,
):
  """Converts a v1alpha ConfigManagementPolicyControllerMonitoring to a v2alpha ConfigManagementPolicyControllerMonitoring."""
  if v1_monitoring is None:
    return None

  v2_monitoring = self.messages_v2.ConfigManagementPolicyControllerMonitoring()
  v2_monitoring.backends = [
      _ToV2ConfigManagementPolicyControllerMonitoringBackendsValueListEntryValuesEnum(
          self, backend
      )
      for backend in v1_monitoring.backends
  ]
  return v2_monitoring


def _ToV2ConfigManagementPolicyControllerMonitoringBackendsValueListEntryValuesEnum(
    self,
    v1_monitoring_backend,
):
  """Converts a v1alpha ConfigManagementPolicyControllerMonitoring.BackendsValueListEntryValuesEnum to a v2alpha ConfigManagementPolicyControllerMonitoring.BackendsValueListEntryValuesEnum."""
  if v1_monitoring_backend is None:
    return None

  if (
      v1_monitoring_backend
      is self.messages.ConfigManagementPolicyControllerMonitoring.BackendsValueListEntryValuesEnum.MONITORING_BACKEND_UNSPECIFIED
  ):
    return (
        self.messages_v2.ConfigManagementPolicyControllerMonitoring.BackendsValueListEntryValuesEnum.MONITORING_BACKEND_UNSPECIFIED
    )
  elif (
      v1_monitoring_backend
      is self.messages.ConfigManagementPolicyControllerMonitoring.BackendsValueListEntryValuesEnum.PROMETHEUS
  ):
    return (
        self.messages_v2.ConfigManagementPolicyControllerMonitoring.BackendsValueListEntryValuesEnum.PROMETHEUS
    )
  elif (
      v1_monitoring_backend
      is self.messages.ConfigManagementPolicyControllerMonitoring.BackendsValueListEntryValuesEnum.CLOUD_MONITORING
  ):
    return (
        self.messages_v2.ConfigManagementPolicyControllerMonitoring.BackendsValueListEntryValuesEnum.CLOUD_MONITORING
    )
  else:
    raise ValueError(f'Unsupported monitoring backend: {v1_monitoring_backend}')


def _ToV2Origin(
    self,
    v1_origin,
):
  """Converts a v1alpha Origin to a v2alpha Origin."""
  if v1_origin is None:
    return None

  v2_origin = self.messages_v2.Origin()
  v2_origin.type = _ToV2OriginTypeValueValuesEnum(self, v1_origin.type)
  return v2_origin


def _ToV2OriginTypeValueValuesEnum(
    self,
    v1_origin_type,
):
  """Converts a v1alpha OriginTypeValueValuesEnum to a v2alpha OriginTypeValueValuesEnum."""
  if v1_origin_type is None:
    return None

  if (
      v1_origin_type
      is self.messages.Origin.TypeValueValuesEnum.TYPE_UNSPECIFIED
  ):
    return (
        self.messages_v2.Origin.TypeValueValuesEnum.TYPE_UNSPECIFIED
    )
  elif (
      v1_origin_type
      is self.messages.Origin.TypeValueValuesEnum.FLEET
  ):
    return (
        self.messages_v2.Origin.TypeValueValuesEnum.FLEET
    )
  elif (
      v1_origin_type
      is self.messages.Origin.TypeValueValuesEnum.FLEET_OUT_OF_SYNC
  ):
    return (
        self.messages_v2.Origin.TypeValueValuesEnum.FLEET_OUT_OF_SYNC
    )
  elif (
      v1_origin_type
      is self.messages.Origin.TypeValueValuesEnum.USER
  ):
    return (
        self.messages_v2.Origin.TypeValueValuesEnum.USER
    )
  else:
    raise ValueError(f'Unsupported origin type: {v1_origin_type}')


def _ToV2PolicyControllerSpec(
    self,
    v1_policycontroller_spec,
):
  """Converts a v1alpha PolicyControllerSpec to a v2alpha PolicyControllerSpec."""
  if v1_policycontroller_spec is None:
    return None

  v2_policycontroller_spec = self.messages_v2.PolicyControllerSpec()
  v2_policycontroller_spec.version = v1_policycontroller_spec.version
  v2_policycontroller_spec.policyControllerHubConfig = (
      _ToV2PolicyControllerHubConfig(
          self, v1_policycontroller_spec.policyControllerHubConfig
      )
  )
  return v2_policycontroller_spec


def _ToV2PolicyControllerHubConfig(
    self,
    v1_policycontroller_hub_config,
):
  """Converts a v1alpha PolicyControllerHubConfig to a v2alpha PolicyControllerHubConfig."""
  if v1_policycontroller_hub_config is None:
    return None

  v2_policycontroller_hub_config = self.messages_v2.PolicyControllerHubConfig()
  v2_policycontroller_hub_config.installSpec = _ToV2InstallSpecValueValuesEnum(
      self, v1_policycontroller_hub_config.installSpec
  )
  v2_policycontroller_hub_config.auditIntervalSeconds = (
      v1_policycontroller_hub_config.auditIntervalSeconds
  )
  v2_policycontroller_hub_config.exemptableNamespaces = (
      v1_policycontroller_hub_config.exemptableNamespaces
  )
  v2_policycontroller_hub_config.referentialRulesEnabled = (
      v1_policycontroller_hub_config.referentialRulesEnabled
  )
  v2_policycontroller_hub_config.logDeniesEnabled = (
      v1_policycontroller_hub_config.logDeniesEnabled
  )
  v2_policycontroller_hub_config.mutationEnabled = (
      v1_policycontroller_hub_config.mutationEnabled
  )
  v2_policycontroller_hub_config.monitoring = _ToV2Monitoring(
      self, v1_policycontroller_hub_config.monitoring
  )
  v2_policycontroller_hub_config.policyContent = _ToV2PolicyContentSpec(
      self, v1_policycontroller_hub_config.policyContent
  )
  v2_policycontroller_hub_config.constraintViolationLimit = (
      v1_policycontroller_hub_config.constraintViolationLimit
  )
  v2_policycontroller_hub_config.deploymentConfigs = _ToV2DeploymentConfigs(
      self, v1_policycontroller_hub_config.deploymentConfigs
  )

  return v2_policycontroller_hub_config


def _ToV2InstallSpecValueValuesEnum(
    self,
    v1_install_spec_value,
):
  """Converts a v1alpha InstallSpecValueValuesEnum to a v2alpha InstallSpecValueValuesEnum."""
  if v1_install_spec_value is None:
    return None

  if (
      v1_install_spec_value
      is self.messages.PolicyControllerHubConfig.InstallSpecValueValuesEnum.INSTALL_SPEC_UNSPECIFIED
  ):
    return (
        self.messages_v2.PolicyControllerHubConfig.InstallSpecValueValuesEnum.INSTALL_SPEC_UNSPECIFIED
    )
  elif (
      v1_install_spec_value
      is self.messages.PolicyControllerHubConfig.InstallSpecValueValuesEnum.INSTALL_SPEC_NOT_INSTALLED
  ):
    return (
        self.messages_v2.PolicyControllerHubConfig.InstallSpecValueValuesEnum.INSTALL_SPEC_NOT_INSTALLED
    )
  elif (
      v1_install_spec_value
      is self.messages.PolicyControllerHubConfig.InstallSpecValueValuesEnum.INSTALL_SPEC_ENABLED
  ):
    return (
        self.messages_v2.PolicyControllerHubConfig.InstallSpecValueValuesEnum.INSTALL_SPEC_ENABLED
    )
  elif (
      v1_install_spec_value
      is self.messages.PolicyControllerHubConfig.InstallSpecValueValuesEnum.INSTALL_SPEC_SUSPENDED
  ):
    return (
        self.messages_v2.PolicyControllerHubConfig.InstallSpecValueValuesEnum.INSTALL_SPEC_SUSPENDED
    )
  elif (
      v1_install_spec_value
      is self.messages.PolicyControllerHubConfig.InstallSpecValueValuesEnum.INSTALL_SPEC_DETACHED
  ):
    return (
        self.messages_v2.PolicyControllerHubConfig.InstallSpecValueValuesEnum.INSTALL_SPEC_DETACHED
    )
  else:
    raise ValueError(f'Unsupported install spec value: {v1_install_spec_value}')


def _ToV2Monitoring(
    self,
    v1_monitoring,
):
  """Converts a v1alpha PolicyControllerMonitoringConfig to a v2alpha PolicyControllerMonitoringConfig."""
  if v1_monitoring is None:
    return None

  v2_monitoring = self.messages_v2.PolicyControllerMonitoringConfig()
  v2_monitoring.backends = [
      _ToV2MonitoringBackend(self, backend)
      for backend in v1_monitoring.backends
  ]
  return v2_monitoring


def _ToV2MonitoringBackend(
    self,
    v1_monitoring_backend,
):
  """Converts a v1alpha MonitoringBackend to a v2alpha MonitoringBackend."""
  if v1_monitoring_backend is None:
    return None

  if (
      v1_monitoring_backend
      is self.messages.PolicyControllerMonitoringConfig.BackendsValueListEntryValuesEnum.MONITORING_BACKEND_UNSPECIFIED
  ):
    return (
        self.messages_v2.PolicyControllerMonitoringConfig.BackendsValueListEntryValuesEnum.MONITORING_BACKEND_UNSPECIFIED
    )
  elif (
      v1_monitoring_backend
      is self.messages.PolicyControllerMonitoringConfig.BackendsValueListEntryValuesEnum.PROMETHEUS
  ):
    return (
        self.messages_v2.PolicyControllerMonitoringConfig.BackendsValueListEntryValuesEnum.PROMETHEUS
    )
  elif (
      v1_monitoring_backend
      is self.messages.PolicyControllerMonitoringConfig.BackendsValueListEntryValuesEnum.CLOUD_MONITORING
  ):
    return (
        self.messages_v2.PolicyControllerMonitoringConfig.BackendsValueListEntryValuesEnum.CLOUD_MONITORING
    )
  else:
    raise ValueError(f'Unsupported monitoring backend: {v1_monitoring_backend}')


def _ToV2PolicyContentSpec(
    self,
    v1_policy_content_spec,
):
  """Converts a v1alpha PolicyControllerPolicyContentSpec to a v2alpha PolicyControllerPolicyContentSpec."""
  v2_policy_content_spec = self.messages_v2.PolicyControllerPolicyContentSpec()
  if v1_policy_content_spec is None:
    return v2_policy_content_spec

  v2_policy_content_spec.bundles = _ToV2Bundles(
      self, v1_policy_content_spec.bundles
  )
  v2_policy_content_spec.templateLibrary = _ToV2TemplateLibraryConfig(
      self, v1_policy_content_spec.templateLibrary
  )
  return v2_policy_content_spec


def _ToV2Bundles(
    self,
    v1_bundles,
):
  """Converts a v1alpha Bundles to a v2alpha Bundles."""
  if v1_bundles is None:
    return None

  v2_bundles_dict = {}
  for bundle in v1_bundles.additionalProperties:
    v2_bundles_dict[bundle.key] = _ToV2BundleInstallSpec(self, bundle.value)

  return encoding.DictToAdditionalPropertyMessage(
      v2_bundles_dict,
      self.messages_v2.PolicyControllerPolicyContentSpec.BundlesValue,
      sort_items=True,
  )


def _ToV2BundleInstallSpec(
    self,
    v1_bundle_install_spec,
):
  """Converts a v1alpha BundleInstallSpec to a v2alpha BundleInstallSpec."""
  if v1_bundle_install_spec is None:
    return None

  v2_bundle_install_spec = self.messages_v2.PolicyControllerBundleInstallSpec()
  v2_bundle_install_spec.exemptedNamespaces = (
      v1_bundle_install_spec.exemptedNamespaces
  )
  return v2_bundle_install_spec


def _ToV2TemplateLibraryConfig(
    self,
    v1_template_library_config,
):
  """Converts a v1alpha TemplateLibraryConfig to a v2alpha TemplateLibraryConfig."""
  if v1_template_library_config is None:
    return None

  v2_template_library_config = (
      self.messages_v2.PolicyControllerTemplateLibraryConfig()
  )
  v2_template_library_config.installation = _ToV2InstallationValueValuesEnum(
      self, v1_template_library_config.installation
  )
  return v2_template_library_config


def _ToV2InstallationValueValuesEnum(
    self,
    v1_installation_value,
):
  """Converts a v1alpha InstallationValueValuesEnum to a v2alpha InstallationValueValuesEnum."""
  if v1_installation_value is None:
    return None

  if (
      v1_installation_value
      is self.messages.PolicyControllerTemplateLibraryConfig.InstallationValueValuesEnum.INSTALLATION_UNSPECIFIED
  ):
    return (
        self.messages_v2.PolicyControllerTemplateLibraryConfig.InstallationValueValuesEnum.INSTALLATION_UNSPECIFIED
    )
  elif (
      v1_installation_value
      is self.messages.PolicyControllerTemplateLibraryConfig.InstallationValueValuesEnum.NOT_INSTALLED
  ):
    return (
        self.messages_v2.PolicyControllerTemplateLibraryConfig.InstallationValueValuesEnum.NOT_INSTALLED
    )
  elif (
      v1_installation_value
      is self.messages.PolicyControllerTemplateLibraryConfig.InstallationValueValuesEnum.ALL
  ):
    return (
        self.messages_v2.PolicyControllerTemplateLibraryConfig.InstallationValueValuesEnum.ALL
    )
  else:
    raise ValueError(f'Unsupported installation value: {v1_installation_value}')


def _ToV2DeploymentConfigs(
    self,
    v1_deployment_configs,
):
  """Converts a v1alpha DeploymentConfigs to a v2alpha DeploymentConfigs."""
  if v1_deployment_configs is None:
    return None

  v2_deployment_configs_dict = {}
  for deployment in v1_deployment_configs.additionalProperties:
    v2_deployment_configs_dict[deployment.key] = (
        _ToV2PolicyControllerDeploymentConfig(self, deployment.value)
    )

  return encoding.DictToAdditionalPropertyMessage(
      v2_deployment_configs_dict,
      self.messages_v2.PolicyControllerHubConfig.DeploymentConfigsValue,
      sort_items=True,
  )


def _ToV2PolicyControllerDeploymentConfig(
    self,
    v1_deployment_config,
):
  """Converts a v1alpha PolicyControllerDeploymentConfig to a v2alpha PolicyControllerDeploymentConfig."""
  if v1_deployment_config is None:
    return None

  v2_deployment_config = (
      self.messages_v2.PolicyControllerPolicyControllerDeploymentConfig()
  )
  v2_deployment_config.replicaCount = v1_deployment_config.replicaCount
  v2_deployment_config.containerResources = (
      _ToV2PolicyControllerResourceRequirements(
          self, v1_deployment_config.containerResources
      )
  )
  v2_deployment_config.podAntiAffinity = v1_deployment_config.podAntiAffinity
  v2_deployment_config.podTolerations = [
      _ToV2PolicyControllerToleration(self, pod_tolerations)
      for pod_tolerations in v1_deployment_config.podTolerations
  ]
  v2_deployment_config.podAffinity = _ToV2PodAffinity(
      self, v1_deployment_config.podAffinity
  )
  return v2_deployment_config


def _ToV2PolicyControllerResourceRequirements(
    self,
    v1_resource_requirements,
):
  """Converts a v1alpha PolicyControllerResourceRequirements to a v2alpha PolicyControllerResourceRequirements."""
  if v1_resource_requirements is None:
    return None

  v2_resource_requirements = (
      self.messages_v2.PolicyControllerResourceRequirements()
  )
  v2_resource_requirements.limits = _ToV2PolicyControllerResourceList(
      self, v1_resource_requirements.limits
  )
  v2_resource_requirements.requests = _ToV2PolicyControllerResourceList(
      self, v1_resource_requirements.requests
  )
  return v2_resource_requirements


def _ToV2PolicyControllerResourceList(
    self,
    v1_resource_list,
):
  """Converts a v1alpha PolicyControllerResourceList to a v2alpha PolicyControllerResourceList."""
  if v1_resource_list is None:
    return None

  v2_resource_list = self.messages_v2.PolicyControllerResourceList()
  v2_resource_list.cpu = v1_resource_list.cpu
  v2_resource_list.memory = v1_resource_list.memory
  return v2_resource_list


def _ToV2PodAffinity(
    self,
    v1_pod_affinity,
):
  """Converts a v1alpha PodAffinity to a v2alpha PodAffinity."""
  if v1_pod_affinity is None:
    return None

  if (
      v1_pod_affinity
      is self.messages.PolicyControllerPolicyControllerDeploymentConfig.PodAffinityValueValuesEnum.AFFINITY_UNSPECIFIED
  ):
    return (
        self.messages_v2.PolicyControllerPolicyControllerDeploymentConfig.PodAffinityValueValuesEnum.AFFINITY_UNSPECIFIED
    )
  elif (
      v1_pod_affinity
      is self.messages.PolicyControllerPolicyControllerDeploymentConfig.PodAffinityValueValuesEnum.NO_AFFINITY
  ):
    return (
        self.messages_v2.PolicyControllerPolicyControllerDeploymentConfig.PodAffinityValueValuesEnum.NO_AFFINITY
    )
  elif (
      v1_pod_affinity
      is self.messages.PolicyControllerPolicyControllerDeploymentConfig.PodAffinityValueValuesEnum.ANTI_AFFINITY
  ):
    return (
        self.messages_v2.PolicyControllerPolicyControllerDeploymentConfig.PodAffinityValueValuesEnum.ANTI_AFFINITY
    )
  else:
    raise ValueError(f'Unsupported pod affinity: {v1_pod_affinity}')


def _ToV2PolicyControllerToleration(
    self,
    v1_toleration,
):
  """Converts a v1alpha PolicyControllerToleration to a v2alpha PolicyControllerToleration."""
  if v1_toleration is None:
    return None

  v2_toleration = self.messages_v2.PolicyControllerToleration()
  v2_toleration.key = v1_toleration.key
  v2_toleration.operator = v1_toleration.operator
  v2_toleration.value = v1_toleration.value
  v2_toleration.effect = v1_toleration.effect
  return v2_toleration
