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
"""Fleet API type helpers.

Because the Fleet API is split into multiple API tracks, this file provides
helpers to make it easier to work with the different tracks. TypeAlias is not
used because it is only supported in Python 3.10+. These type aliases are
intended to be used in type hints when the specific track is not known.
"""

from typing import Generator, Union
from googlecloudsdk.generated_clients.apis.gkehub.v1 import gkehub_v1_client as ga_client
from googlecloudsdk.generated_clients.apis.gkehub.v1 import gkehub_v1_messages as ga_messages
from googlecloudsdk.generated_clients.apis.gkehub.v1alpha import gkehub_v1alpha_client as alpha_client
from googlecloudsdk.generated_clients.apis.gkehub.v1alpha import gkehub_v1alpha_messages as alpha_messages
from googlecloudsdk.generated_clients.apis.gkehub.v1beta import gkehub_v1beta_client as beta_client
from googlecloudsdk.generated_clients.apis.gkehub.v1beta import gkehub_v1beta_messages as beta_messages


BinaryAuthorizationConfig = Union[
    alpha_messages.BinaryAuthorizationConfig,
    beta_messages.BinaryAuthorizationConfig,
    ga_messages.BinaryAuthorizationConfig,
]

BinaryAuthorizationConfigEvaluationModeValueValuesEnum = Union[
    alpha_messages.BinaryAuthorizationConfig.EvaluationModeValueValuesEnum,
    beta_messages.BinaryAuthorizationConfig.EvaluationModeValueValuesEnum,
    ga_messages.BinaryAuthorizationConfig.EvaluationModeValueValuesEnum,
]

CompliancePostureConfig = Union[
    alpha_messages.CompliancePostureConfig,
    beta_messages.CompliancePostureConfig,
    ga_messages.CompliancePostureConfig,
]

DefaultClusterConfig = Union[
    alpha_messages.DefaultClusterConfig,
    beta_messages.DefaultClusterConfig,
    ga_messages.DefaultClusterConfig,
]

Fleet = Union[alpha_messages.Fleet, beta_messages.Fleet, ga_messages.Fleet]

GkehubProjectsLocationsFleetsCreateRequest = Union[
    alpha_messages.GkehubProjectsLocationsFleetsCreateRequest,
    beta_messages.GkehubProjectsLocationsFleetsCreateRequest,
    ga_messages.GkehubProjectsLocationsFleetsCreateRequest,
]

GkehubProjectsLocationsFleetsDeleteRequest = Union[
    alpha_messages.GkehubProjectsLocationsFleetsDeleteRequest,
    beta_messages.GkehubProjectsLocationsFleetsDeleteRequest,
    ga_messages.GkehubProjectsLocationsFleetsDeleteRequest,
]

GkehubProjectsLocationsFleetsPatchRequest = Union[
    alpha_messages.GkehubProjectsLocationsFleetsPatchRequest,
    beta_messages.GkehubProjectsLocationsFleetsPatchRequest,
    ga_messages.GkehubProjectsLocationsFleetsPatchRequest,
]

GkehubProjectsLocationsOperationsListRequest = Union[
    alpha_messages.GkehubProjectsLocationsOperationsListRequest,
    beta_messages.GkehubProjectsLocationsOperationsListRequest,
    ga_messages.GkehubProjectsLocationsOperationsListRequest,
]

GkehubProjectsLocationsOperationsGetRequest = Union[
    alpha_messages.GkehubProjectsLocationsOperationsGetRequest,
    beta_messages.GkehubProjectsLocationsOperationsGetRequest,
    ga_messages.GkehubProjectsLocationsOperationsGetRequest,
]

GkehubProjectsLocationsRolloutsCreateRequest = Union[
    alpha_messages.GkehubProjectsLocationsRolloutsCreateRequest,
    # Rollouts are not yet available in beta or GA.
    # beta_messages.GkehubProjectsLocationsRolloutsCreateRequest,
    # ga_messages.GkehubProjectsLocationsRolloutsCreateRequest,
]

GkehubProjectsLocationsRolloutsDeleteRequest = Union[
    alpha_messages.GkehubProjectsLocationsRolloutsDeleteRequest,
    # Rollouts are not yet available in beta or GA.
    # beta_messages.GkehubProjectsLocationsRolloutsDeleteRequest,
    # ga_messages.GkehubProjectsLocationsRolloutsDeleteRequest,
]

GkehubProjectsLocationsRolloutsGetRequest = Union[
    alpha_messages.GkehubProjectsLocationsRolloutsGetRequest,
    # Rollouts are not yet available in beta or GA.
    # beta_messages.GkehubProjectsLocationsRolloutsGetRequest,
    # ga_messages.GkehubProjectsLocationsRolloutsGetRequest,
]

GkehubProjectsLocationsRolloutsListRequest = Union[
    alpha_messages.GkehubProjectsLocationsRolloutsListRequest,
    # Rollouts are not yet available in beta or GA.
    # beta_messages.GkehubProjectsLocationsRolloutsListRequest,
    # ga_messages.GkehubProjectsLocationsRolloutsListRequest,
]

GkehubProjectsLocationsRolloutsPauseRequest = Union[
    alpha_messages.GkehubProjectsLocationsRolloutsPauseRequest,
    # Rollouts are not yet available in beta or GA.
    # beta_messages.GkehubProjectsLocationsRolloutsPauseRequest,
    # ga_messages.GkehubProjectsLocationsRolloutsPauseRequest,
]

GkehubProjectsLocationsRolloutsResumeRequest = Union[
    alpha_messages.GkehubProjectsLocationsRolloutsResumeRequest,
    # Rollouts are not yet available in beta or GA.
    # beta_messages.GkehubProjectsLocationsRolloutsResumeRequest,
    # ga_messages.GkehubProjectsLocationsRolloutsResumeRequest,
]

Operation = Union[
    alpha_messages.Operation, beta_messages.Operation, ga_messages.Operation
]

PolicyBinding = Union[
    alpha_messages.PolicyBinding,
    beta_messages.PolicyBinding,
    ga_messages.PolicyBinding,
]

Rollout = Union[
    alpha_messages.Rollout,
    # Rollouts are not yet available in beta or GA.
    # beta_messages.Rollout,
    # ga_messages.Rollout,
]

RolloutGenerator = Generator[Rollout, None, None]

SecurityPostureConfig = Union[
    alpha_messages.SecurityPostureConfig,
    beta_messages.SecurityPostureConfig,
    ga_messages.SecurityPostureConfig,
]

SecurityPostureConfigModeValueValuesEnum = Union[
    alpha_messages.SecurityPostureConfig.ModeValueValuesEnum,
    beta_messages.SecurityPostureConfig.ModeValueValuesEnum,
    ga_messages.SecurityPostureConfig.ModeValueValuesEnum,
]

SecurityPostureConfigVulnerabilityModeValueValuesEnum = Union[
    alpha_messages.SecurityPostureConfig.VulnerabilityModeValueValuesEnum,
    beta_messages.SecurityPostureConfig.VulnerabilityModeValueValuesEnum,
    ga_messages.SecurityPostureConfig.VulnerabilityModeValueValuesEnum,
]

TrackClient = Union[
    alpha_client.GkehubV1alpha, beta_client.GkehubV1beta, ga_client.GkehubV1
]
