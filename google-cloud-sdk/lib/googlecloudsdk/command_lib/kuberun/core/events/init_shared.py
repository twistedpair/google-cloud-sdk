# -*- coding: utf-8 -*- #
# Copyright 2020 Google LLC. All Rights Reserved.
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
"""Provides shared classes for 'kuberun core events' init commands and 'events init' surface."""

from __future__ import absolute_import
from __future__ import division
from __future__ import print_function
from __future__ import unicode_literals

import collections

from googlecloudsdk.api_lib.events import iam_util
from googlecloudsdk.api_lib.kuberun.core import events_constants
from googlecloudsdk.command_lib.events import exceptions
from googlecloudsdk.command_lib.iam import iam_util as core_iam_util
from googlecloudsdk.core import log
from googlecloudsdk.core import resources
from googlecloudsdk.core.console import console_io

CONTROL_PLANE_REQUIRED_SERVICES = (
    # cloudresourcemanager isn't required for eventing itself, but is required
    # for this command to perform the IAM bindings necessary.
    'cloudresourcemanager.googleapis.com',
    'cloudscheduler.googleapis.com',
    'logging.googleapis.com',
    'pubsub.googleapis.com',
    'stackdriver.googleapis.com',
    'storage-api.googleapis.com',
    'storage-component.googleapis.com',
)

ServiceAccountConfig = collections.namedtuple('ServiceAccountConfig', [
    'arg_name', 'display_name', 'description', 'default_service_account',
    'kuberun_google_service_account', 'recommended_roles', 'secret_name'
])

CONTROL_PLANE_SERVICE_ACCOUNT_CONFIG = ServiceAccountConfig(
    arg_name='service_account',
    display_name='Cloud Run Events',
    description='Cloud Run Events on-cluster Infrastructure',
    default_service_account=events_constants
    .EVENTS_CONTROL_PLANE_SERVICE_ACCOUNT,
    kuberun_google_service_account=events_constants
    .KUBERUN_EVENTS_CONTROL_PLANE_SERVICE_ACCOUNT,
    recommended_roles=(
        # CloudSchedulerSource
        'roles/cloudscheduler.admin',
        # CloudAuditLogsSource
        'roles/logging.configWriter',
        # CloudAuditLogsSource
        'roles/logging.privateLogViewer',
        # All Sources
        'roles/pubsub.admin',
        # CloudStorageSource
        'roles/storage.admin',
    ),
    secret_name='google-cloud-key',
)

BROKER_SERVICE_ACCOUNT_CONFIG = ServiceAccountConfig(
    arg_name='broker_service_account',
    display_name='Cloud Run Events Broker',
    description='Cloud Run Events on-cluster Broker',
    default_service_account=events_constants.EVENTS_BROKER_SERVICE_ACCOUNT,
    kuberun_google_service_account=events_constants
    .KUBERUN_EVENTS_BROKER_SERVICE_ACCOUNT,
    recommended_roles=(
        'roles/pubsub.editor',
        'roles/monitoring.metricWriter',
        'roles/cloudtrace.agent',
    ),
    secret_name='google-broker-key',
)

SOURCES_SERVICE_ACCOUNT_CONFIG = ServiceAccountConfig(
    arg_name='sources_service_account',
    display_name='Cloud Run Events Sources',
    description='Cloud Run Events on-cluster Sources',
    default_service_account=events_constants.EVENTS_SOURCES_SERVICE_ACCOUNT,
    kuberun_google_service_account=events_constants
    .KUBERUN_EVENTS_SOURCES_SERVICE_ACCOUNT,
    recommended_roles=(
        'roles/pubsub.editor',
        'roles/monitoring.metricWriter',
        'roles/cloudtrace.agent',
    ),
    secret_name='google-cloud-sources-key',
)

SERVICE_ACCOUNT_CONFIGS = (
    CONTROL_PLANE_SERVICE_ACCOUNT_CONFIG,
    BROKER_SERVICE_ACCOUNT_CONFIG,
    SOURCES_SERVICE_ACCOUNT_CONFIG,
)

# is_default is False when user provides their own gsa email.
GsaEmail = collections.namedtuple('GsaEmail', ['email', 'is_default'])


def determine_cluster_eventing_type(client):
  """Determine cluster eventing type inferred by namespaces."""
  namespaces_list = client.ListNamespaces()

  if 'events-system' in namespaces_list:
    # KubeRun events installed
    return events_constants.ClusterEventingType.KUBERUN_SECRETS
  elif 'cloud-run-events' in namespaces_list:
    # CloudRun events installed
    return events_constants.ClusterEventingType.CLOUDRUN_SECRETS
  else:
    raise exceptions.EventingInitializationError('Neither CloudRun nor KubeRun '
                                                 'events installed')


def _default_gsa(sa_config, cluster_eventing_type):
  if cluster_eventing_type == events_constants.ClusterEventingType.CLOUDRUN_SECRETS:
    return sa_config.default_service_account
  elif cluster_eventing_type == events_constants.ClusterEventingType.KUBERUN_SECRETS:
    return sa_config.kuberun_google_service_account
  else:
    raise exceptions.EventingInitializationError(
        'Unexpected cluster eventing type')


def construct_service_account_email(sa_config, args, cluster_eventing_type):
  """Creates default service account email or use provided if specified.

  Args:
    sa_config: A ServiceAccountConfig.
    args: Command line arguments.
    cluster_eventing_type: An enum denoting the eventing cluster type.

  Returns:
    GsaEmail
  """
  log.status.Print('Creating service account for {}.'.format(
      sa_config.description))
  if not args.IsSpecified(sa_config.arg_name):
    default_gsa_name = _default_gsa(sa_config, cluster_eventing_type)
    sa_email = iam_util.GetOrCreateServiceAccountWithPrompt(
        default_gsa_name, sa_config.display_name, sa_config.description)
    return GsaEmail(email=sa_email, is_default=True)
  else:
    sa_email = getattr(args, sa_config.arg_name)
    return GsaEmail(email=sa_email, is_default=False)


def initialize_eventing_secrets(client, gsa_emails, cluster_eventing_type):
  """Initializes eventing cluster binding three gsa's with roles and secrets.

  Args:
    client: An api_tools client.
    gsa_emails: A Dict[ServiceAccountConfig, GsaEmail] holds the gsa email and
      if the email was user provided.
    cluster_eventing_type: An enum denoting the eventing cluster type.
  """
  for sa_config in SERVICE_ACCOUNT_CONFIGS:
    _configure_service_account_roles(sa_config, gsa_emails)
    _add_secret_to_service_account(client, sa_config, cluster_eventing_type,
                                   gsa_emails[sa_config].email)
    log.status.Print('Finished configuring service account for {}.\n'.format(
        sa_config.description))
  client.MarkClusterInitialized(cluster_eventing_type)


def _configure_service_account_roles(sa_config, gsa_emails):
  """Configures a service account with necessary iam roles for eventing."""

  log.status.Print('Configuring service account for {}.'.format(
      sa_config.description))

  # We use projectsId of '-' to handle the case where a user-provided service
  # account may belong to a different project and we need to obtain a key for
  # that service account.
  #
  # The IAM utils used below which print or bind roles are implemented to
  # specifically operate on the current project and are not impeded by this
  # projectless ref.
  service_account_ref = resources.REGISTRY.Parse(
      gsa_emails[sa_config].email,
      params={'projectsId': '-'},
      collection=core_iam_util.SERVICE_ACCOUNTS_COLLECTION)

  should_bind_roles = gsa_emails[sa_config].is_default

  iam_util.PrintOrBindMissingRolesWithPrompt(service_account_ref,
                                             sa_config.recommended_roles,
                                             should_bind_roles)


def _add_secret_to_service_account(client, sa_config, cluster_eventing_type,
                                   sa_email):
  """Adds new secret to service account.

  Args:
    client: An api_tools client.
    sa_config: A ServiceAccountConfig.
    cluster_eventing_type: An enum denoting the eventing type.
    sa_email: String of the targeted service account email.
  """
  control_plane_namespace = (
      events_constants.ControlPlaneNamespaceFromEventingType(
          cluster_eventing_type))

  secret_ref = resources.REGISTRY.Parse(
      sa_config.secret_name,
      params={'namespacesId': control_plane_namespace},
      collection='run.api.v1.namespaces.secrets',
      api_version='v1')

  service_account_ref = resources.REGISTRY.Parse(
      sa_email,
      params={'projectsId': '-'},
      collection=core_iam_util.SERVICE_ACCOUNTS_COLLECTION)

  prompt_if_can_prompt(
      'This will create a new key for the service account [{}].'.format(
          sa_email))
  _, key_ref = client.CreateOrReplaceServiceAccountSecret(
      secret_ref, service_account_ref)
  log.status.Print('Added key [{}] to cluster for [{}].'.format(
      key_ref.Name(), sa_email))


def prompt_if_can_prompt(message):
  """Prompts user with message."""
  if console_io.CanPrompt():
    console_io.PromptContinue(message=message, cancel_on_no=True)
