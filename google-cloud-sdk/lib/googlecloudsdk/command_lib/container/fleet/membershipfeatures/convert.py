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
from googlecloudsdk.generated_clients.apis.gkehub.v1alpha import gkehub_v1alpha_messages as message_v1
from googlecloudsdk.generated_clients.apis.gkehub.v2alpha import gkehub_v2alpha_messages as message_v2


def ToV2MembershipFeature(
    membership_path: str,
    feature_name: str,
    v1_membership_feature_spec: message_v1.MembershipFeatureSpec,
) -> message_v2.MembershipFeature:
  """Converts a v1alpha MembershipFeature to a v2alpha MembershipFeature."""
  v2_membershipfeature = message_v2.MembershipFeature()
  v2_membershipfeature.name = f'{membership_path}/features/{feature_name}'
  v2_membershipfeature.spec = message_v2.FeatureSpec()

  if feature_name == 'policycontroller':
    v2_membershipfeature.spec.policycontroller = _ToV2PolicyControllerSpec(
        v1_membership_feature_spec.policycontroller
    )
  else:
    raise ValueError(
        f'Unsupported membership feature: {v2_membershipfeature.name}'
    )
  return v2_membershipfeature


def _ToV2PolicyControllerSpec(
    v1_policycontroller_spec: message_v1.PolicyControllerMembershipSpec,
) -> message_v2.PolicyControllerSpec:
  """Converts a v1alpha PolicyControllerSpec to a v2alpha PolicyControllerSpec."""
  if v1_policycontroller_spec is None:
    return None

  v2_policycontroller_spec = message_v2.PolicyControllerSpec()
  v2_policycontroller_spec.version = v1_policycontroller_spec.version
  v2_policycontroller_spec.policyControllerHubConfig = (
      _ToV2PolicyControllerHubConfig(
          v1_policycontroller_spec.policyControllerHubConfig
      )
  )
  return v2_policycontroller_spec


def _ToV2PolicyControllerHubConfig(
    v1_policycontroller_hub_config: message_v1.PolicyControllerHubConfig,
) -> message_v2.PolicyControllerHubConfig:
  """Converts a v1alpha PolicyControllerHubConfig to a v2alpha PolicyControllerHubConfig."""
  if v1_policycontroller_hub_config is None:
    return None

  v2_policycontroller_hub_config = message_v2.PolicyControllerHubConfig()
  v2_policycontroller_hub_config.installSpec = _ToV2InstallSpecValueValuesEnum(
      v1_policycontroller_hub_config.installSpec
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
      v1_policycontroller_hub_config.monitoring
  )
  v2_policycontroller_hub_config.policyContent = _ToV2PolicyContentSpec(
      v1_policycontroller_hub_config.policyContent
  )
  v2_policycontroller_hub_config.constraintViolationLimit = (
      v1_policycontroller_hub_config.constraintViolationLimit
  )
  v2_policycontroller_hub_config.deploymentConfigs = _ToV2DeploymentConfigs(
      v1_policycontroller_hub_config.deploymentConfigs
  )

  return v2_policycontroller_hub_config


def _ToV2InstallSpecValueValuesEnum(
    v1_install_spec_value: message_v1.PolicyControllerHubConfig.InstallSpecValueValuesEnum,
) -> message_v2.PolicyControllerHubConfig.InstallSpecValueValuesEnum:
  """Converts a v1alpha InstallSpecValueValuesEnum to a v2alpha InstallSpecValueValuesEnum."""
  if (
      v1_install_spec_value
      is message_v1.PolicyControllerHubConfig.InstallSpecValueValuesEnum.INSTALL_SPEC_UNSPECIFIED
  ):
    return (
        message_v2.PolicyControllerHubConfig.InstallSpecValueValuesEnum.INSTALL_SPEC_UNSPECIFIED
    )
  elif (
      v1_install_spec_value
      is message_v1.PolicyControllerHubConfig.InstallSpecValueValuesEnum.INSTALL_SPEC_NOT_INSTALLED
  ):
    return (
        message_v2.PolicyControllerHubConfig.InstallSpecValueValuesEnum.INSTALL_SPEC_NOT_INSTALLED
    )
  elif (
      v1_install_spec_value
      is message_v1.PolicyControllerHubConfig.InstallSpecValueValuesEnum.INSTALL_SPEC_ENABLED
  ):
    return (
        message_v2.PolicyControllerHubConfig.InstallSpecValueValuesEnum.INSTALL_SPEC_ENABLED
    )
  elif (
      v1_install_spec_value
      is message_v1.PolicyControllerHubConfig.InstallSpecValueValuesEnum.INSTALL_SPEC_SUSPENDED
  ):
    return (
        message_v2.PolicyControllerHubConfig.InstallSpecValueValuesEnum.INSTALL_SPEC_SUSPENDED
    )
  elif (
      v1_install_spec_value
      is message_v1.PolicyControllerHubConfig.InstallSpecValueValuesEnum.INSTALL_SPEC_DETACHED
  ):
    return (
        message_v2.PolicyControllerHubConfig.InstallSpecValueValuesEnum.INSTALL_SPEC_DETACHED
    )
  else:
    raise ValueError(f'Unsupported install spec value: {v1_install_spec_value}')


def _ToV2Monitoring(
    v1_monitoring: message_v1.PolicyControllerMonitoringConfig,
) -> message_v2.PolicyControllerMonitoringConfig:
  """Converts a v1alpha PolicyControllerMonitoringConfig to a v2alpha PolicyControllerMonitoringConfig."""
  if v1_monitoring is None:
    return None

  v2_monitoring = message_v2.PolicyControllerMonitoringConfig()
  v2_monitoring.backends = [
      _ToV2MonitoringBackend(backend) for backend in v1_monitoring.backends
  ]
  return v2_monitoring


def _ToV2MonitoringBackend(
    v1_monitoring_backend: message_v1.PolicyControllerMonitoringConfig.BackendsValueListEntryValuesEnum,
) -> (
    message_v2.PolicyControllerMonitoringConfig.BackendsValueListEntryValuesEnum
):
  """Converts a v1alpha MonitoringBackend to a v2alpha MonitoringBackend."""
  if (
      v1_monitoring_backend
      is message_v1.PolicyControllerMonitoringConfig.BackendsValueListEntryValuesEnum.MONITORING_BACKEND_UNSPECIFIED
  ):
    return (
        message_v2.PolicyControllerMonitoringConfig.BackendsValueListEntryValuesEnum.MONITORING_BACKEND_UNSPECIFIED
    )
  elif (
      v1_monitoring_backend
      is message_v1.PolicyControllerMonitoringConfig.BackendsValueListEntryValuesEnum.PROMETHEUS
  ):
    return (
        message_v2.PolicyControllerMonitoringConfig.BackendsValueListEntryValuesEnum.PROMETHEUS
    )
  elif (
      v1_monitoring_backend
      is message_v1.PolicyControllerMonitoringConfig.BackendsValueListEntryValuesEnum.CLOUD_MONITORING
  ):
    return (
        message_v2.PolicyControllerMonitoringConfig.BackendsValueListEntryValuesEnum.CLOUD_MONITORING
    )
  else:
    raise ValueError(f'Unsupported monitoring backend: {v1_monitoring_backend}')


def _ToV2PolicyContentSpec(
    v1_policy_content_spec: message_v1.PolicyControllerPolicyContentSpec,
) -> message_v2.PolicyControllerPolicyContentSpec:
  """Converts a v1alpha PolicyControllerPolicyContentSpec to a v2alpha PolicyControllerPolicyContentSpec."""
  v2_policy_content_spec = message_v2.PolicyControllerPolicyContentSpec()
  if v1_policy_content_spec is None:
    return v2_policy_content_spec

  v2_policy_content_spec.bundles = _ToV2Bundles(v1_policy_content_spec.bundles)
  v2_policy_content_spec.templateLibrary = _ToV2TemplateLibraryConfig(
      v1_policy_content_spec.templateLibrary
  )
  return v2_policy_content_spec


def _ToV2Bundles(
    v1_bundles: message_v1.PolicyControllerPolicyContentSpec.BundlesValue,
) -> message_v2.PolicyControllerPolicyContentSpec.BundlesValue:
  """Converts a v1alpha Bundles to a v2alpha Bundles."""
  if v1_bundles is None:
    return None

  v2_bundles_dict = {}
  for bundle in v1_bundles.additionalProperties:
    v2_bundles_dict[bundle.key] = _ToV2BundleInstallSpec(bundle.value)

  return encoding.DictToAdditionalPropertyMessage(
      v2_bundles_dict,
      message_v2.PolicyControllerPolicyContentSpec.BundlesValue,
      sort_items=True,
  )


def _ToV2BundleInstallSpec(
    v1_bundle_install_spec: message_v1.PolicyControllerBundleInstallSpec,
) -> message_v2.PolicyControllerBundleInstallSpec:
  """Converts a v1alpha BundleInstallSpec to a v2alpha BundleInstallSpec."""
  if v1_bundle_install_spec is None:
    return None

  v2_bundle_install_spec = message_v2.PolicyControllerBundleInstallSpec()
  v2_bundle_install_spec.exemptedNamespaces = (
      v1_bundle_install_spec.exemptedNamespaces
  )
  return v2_bundle_install_spec


def _ToV2TemplateLibraryConfig(
    v1_template_library_config: message_v1.PolicyControllerTemplateLibraryConfig,
) -> message_v2.PolicyControllerTemplateLibraryConfig:
  """Converts a v1alpha TemplateLibraryConfig to a v2alpha TemplateLibraryConfig."""
  if v1_template_library_config is None:
    return None

  v2_template_library_config = (
      message_v2.PolicyControllerTemplateLibraryConfig()
  )
  v2_template_library_config.installation = _ToV2InstallationValueValuesEnum(
      v1_template_library_config.installation
  )
  return v2_template_library_config


def _ToV2InstallationValueValuesEnum(
    v1_installation_value: message_v1.PolicyControllerTemplateLibraryConfig.InstallationValueValuesEnum,
) -> (
    message_v2.PolicyControllerTemplateLibraryConfig.InstallationValueValuesEnum
):
  """Converts a v1alpha InstallationValueValuesEnum to a v2alpha InstallationValueValuesEnum."""
  if (
      v1_installation_value
      is message_v1.PolicyControllerTemplateLibraryConfig.InstallationValueValuesEnum.INSTALLATION_UNSPECIFIED
  ):
    return (
        message_v2.PolicyControllerTemplateLibraryConfig.InstallationValueValuesEnum.INSTALLATION_UNSPECIFIED
    )
  elif (
      v1_installation_value
      is message_v1.PolicyControllerTemplateLibraryConfig.InstallationValueValuesEnum.NOT_INSTALLED
  ):
    return (
        message_v2.PolicyControllerTemplateLibraryConfig.InstallationValueValuesEnum.NOT_INSTALLED
    )
  elif (
      v1_installation_value
      is message_v1.PolicyControllerTemplateLibraryConfig.InstallationValueValuesEnum.ALL
  ):
    return (
        message_v2.PolicyControllerTemplateLibraryConfig.InstallationValueValuesEnum.ALL
    )
  else:
    raise ValueError(f'Unsupported installation value: {v1_installation_value}')


def _ToV2DeploymentConfigs(
    v1_deployment_configs: message_v1.PolicyControllerHubConfig.DeploymentConfigsValue,
) -> message_v2.PolicyControllerHubConfig.DeploymentConfigsValue:
  """Converts a v1alpha DeploymentConfigs to a v2alpha DeploymentConfigs."""
  if v1_deployment_configs is None:
    return None

  v2_deployment_configs_dict = {}
  for deployment in v1_deployment_configs.additionalProperties:
    v2_deployment_configs_dict[deployment.key] = (
        _ToV2PolicyControllerDeploymentConfig(deployment.value)
    )

  return encoding.DictToAdditionalPropertyMessage(
      v2_deployment_configs_dict,
      message_v2.PolicyControllerHubConfig.DeploymentConfigsValue,
      sort_items=True,
  )


def _ToV2PolicyControllerDeploymentConfig(
    v1_deployment_config: message_v1.PolicyControllerPolicyControllerDeploymentConfig,
) -> message_v2.PolicyControllerPolicyControllerDeploymentConfig:
  """Converts a v1alpha PolicyControllerDeploymentConfig to a v2alpha PolicyControllerDeploymentConfig."""
  if v1_deployment_config is None:
    return None

  v2_deployment_config = (
      message_v2.PolicyControllerPolicyControllerDeploymentConfig()
  )
  v2_deployment_config.replicaCount = v1_deployment_config.replicaCount
  v2_deployment_config.containerResources = (
      _ToV2PolicyControllerResourceRequirements(
          v1_deployment_config.containerResources
      )
  )
  v2_deployment_config.podAntiAffinity = v1_deployment_config.podAntiAffinity
  v2_deployment_config.podTolerations = [
      _ToV2PolicyControllerToleration(pod_tolerations)
      for pod_tolerations in v1_deployment_config.podTolerations
  ]
  v2_deployment_config.podAffinity = _ToV2PodAffinity(
      v1_deployment_config.podAffinity
  )
  return v2_deployment_config


def _ToV2PolicyControllerResourceRequirements(
    v1_resource_requirements: message_v1.PolicyControllerResourceRequirements,
) -> message_v2.PolicyControllerResourceRequirements:
  """Converts a v1alpha PolicyControllerResourceRequirements to a v2alpha PolicyControllerResourceRequirements."""
  if v1_resource_requirements is None:
    return None

  v2_resource_requirements = message_v2.PolicyControllerResourceRequirements()
  v2_resource_requirements.limits = _ToV2PolicyControllerResourceList(
      v1_resource_requirements.limits
  )
  v2_resource_requirements.requests = _ToV2PolicyControllerResourceList(
      v1_resource_requirements.requests
  )
  return v2_resource_requirements


def _ToV2PolicyControllerResourceList(
    v1_resource_list: message_v1.PolicyControllerResourceList,
) -> message_v2.PolicyControllerResourceList:
  """Converts a v1alpha PolicyControllerResourceList to a v2alpha PolicyControllerResourceList."""
  if v1_resource_list is None:
    return None

  v2_resource_list = message_v2.PolicyControllerResourceList()
  v2_resource_list.cpu = v1_resource_list.cpu
  v2_resource_list.memory = v1_resource_list.memory
  return v2_resource_list


def _ToV2PodAffinity(
    v1_pod_affinity: message_v1.PolicyControllerPolicyControllerDeploymentConfig.PodAffinityValueValuesEnum,
) -> (
    message_v2.PolicyControllerPolicyControllerDeploymentConfig.PodAffinityValueValuesEnum
):
  """Converts a v1alpha PodAffinity to a v2alpha PodAffinity."""
  if (
      v1_pod_affinity
      is message_v1.PolicyControllerPolicyControllerDeploymentConfig.PodAffinityValueValuesEnum.AFFINITY_UNSPECIFIED
  ):
    return (
        message_v2.PolicyControllerPolicyControllerDeploymentConfig.PodAffinityValueValuesEnum.AFFINITY_UNSPECIFIED
    )
  elif (
      v1_pod_affinity
      is message_v1.PolicyControllerPolicyControllerDeploymentConfig.PodAffinityValueValuesEnum.NO_AFFINITY
  ):
    return (
        message_v2.PolicyControllerPolicyControllerDeploymentConfig.PodAffinityValueValuesEnum.NO_AFFINITY
    )
  elif (
      v1_pod_affinity
      is message_v1.PolicyControllerPolicyControllerDeploymentConfig.PodAffinityValueValuesEnum.ANTI_AFFINITY
  ):
    return (
        message_v2.PolicyControllerPolicyControllerDeploymentConfig.PodAffinityValueValuesEnum.ANTI_AFFINITY
    )
  else:
    raise ValueError(f'Unsupported pod affinity: {v1_pod_affinity}')


def _ToV2PolicyControllerToleration(
    v1_toleration: message_v1.PolicyControllerToleration,
) -> message_v2.PolicyControllerToleration:
  """Converts a v1alpha PolicyControllerToleration to a v2alpha PolicyControllerToleration."""
  if v1_toleration is None:
    return None

  v2_toleration = message_v2.PolicyControllerToleration()
  v2_toleration.key = v1_toleration.key
  v2_toleration.operator = v1_toleration.operator
  v2_toleration.value = v1_toleration.value
  v2_toleration.effect = v1_toleration.effect
  return v2_toleration
