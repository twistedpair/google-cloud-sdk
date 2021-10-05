# -*- coding: utf-8 -*- #
# Copyright 2021 Google LLC. All Rights Reserved.
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
"""Utilities for generating kubeconfig entries."""

from __future__ import absolute_import
from __future__ import division
from __future__ import unicode_literals

import base64

from googlecloudsdk.api_lib.container import kubeconfig as kubeconfig_util
from googlecloudsdk.core import exceptions
from googlecloudsdk.core import log
from googlecloudsdk.core.util import semver


COMMAND_DESCRIPTION = """
Fetch credentials for a running cluster on {kind}.

This command updates a kubeconfig file with appropriate credentials and
endpoint information to point kubectl at a specific cluster on {kind}.

By default, credentials are written to ``HOME/.kube/config''.
You can provide an alternate path by setting the ``KUBECONFIG'' environment
variable. If ``KUBECONFIG'' contains multiple paths, the first one is used.

This command enables switching to a specific cluster, when working
with multiple clusters. It can also be used to access a previously created
cluster from a new workstation.

By default, the command will configure kubectl to automatically refresh its
credentials using the same identity as the gcloud command-line tool.
If you are running kubectl as part of an application, it is recommended to use
[application default credentials](https://cloud.google.com/docs/authentication/production).
To configure a kubeconfig file to use application default credentials, set
the ``container/use_application_default_credentials''
[Cloud SDK property](https://cloud.google.com/sdk/docs/properties) to ``true''
before running the command.

See [](https://cloud.google.com/kubernetes-engine/docs/kubectl) for
kubectl documentation.
"""

COMMAND_EXAMPLE = """
To get credentials of a cluster named ``my-cluster'' managed in location ``us-west1'',
run:

$ {command} my-cluster --location=us-west1
"""


class UnsupportedClusterVersion(exceptions.Error):
  """Class for errors by unsupported cluster versions."""


class MissingClusterField(exceptions.Error):
  """Class for errors by missing cluster fields."""


def GenerateContext(kind, project_id, location, cluster_id):
  """Generates a kubeconfig context for an Anthos Multi-cloud cluster.

  Args:
    kind: str, kind of the cluster e.g. aws, azure.
    project_id: str, project ID accociated with the cluster.
    location: str, Google location of the cluster.
    cluster_id: str, ID of the cluster.

  Returns:
    The context for the kubeconfig entry.
  """
  template = 'gke_{kind}_{project_id}_{location}_{cluster_id}'
  return template.format(
      kind=kind,
      project_id=project_id,
      location=location,
      cluster_id=cluster_id)


def GenerateAuthProviderCmdArgs(track, kind, cluster_id, location):
  """Generates command arguments for kubeconfig's authorization provider.

  Args:
    track: str, command track to use.
    kind: str, kind of the cluster e.g. aws, azure.
    cluster_id: str, ID of the cluster.
    location: str, Google location of the cluster.

  Returns:
    The command arguments for kubeconfig's authorization provider.
  """
  template = ('{track} container {kind} clusters print-access-token '
              '{cluster_id} --location={location}')
  return template.format(
      track=track, kind=kind, cluster_id=cluster_id, location=location)


def GenerateKubeconfig(cluster, context, cmd_path, cmd_args):
  """Generates a kubeconfig entry for an Anthos Multi-cloud cluster.

  Args:
    cluster: object, Anthos Multi-cloud cluster.
    context: str, context for the kubeconfig entry.
    cmd_path: str, authentication provider command path.
    cmd_args: str, authentication provider command arguments.

  Raises:
      Error: don't have the permission to open kubeconfig file.
  """
  kubeconfig = kubeconfig_util.Kubeconfig.Default()
  # Use the same key for context, cluster, and user.
  kubeconfig.contexts[context] = kubeconfig_util.Context(
      context, context, context)

  user_kwargs = {
      'auth_provider': 'gcp',
      'auth_provider_cmd_path': cmd_path,
      'auth_provider_cmd_args': cmd_args,
      'auth_provider_expiry_key': '{.expirationTime}',
      'auth_provider_token_key': '{.accessToken}'
  }
  kubeconfig.users[context] = kubeconfig_util.User(context, **user_kwargs)

  cluster_kwargs = {}
  if cluster.clusterCaCertificate is None:
    log.warning('Cluster is missing certificate authority data.')
  else:
    cluster_kwargs['ca_data'] = _GetCaData(cluster.clusterCaCertificate)

  kubeconfig.clusters[context] = kubeconfig_util.Cluster(
      context, 'https://{}'.format(cluster.endpoint), **cluster_kwargs)
  kubeconfig.SetCurrentContext(context)
  kubeconfig.SaveToFile()
  log.status.Print(
      'A new kubeconfig entry "{}" has been generated and set as the '
      'current context.'.format(context))


def ValidateClusterVersion(cluster):
  """Validates the cluster version.

  Args:
    cluster: object, Anthos Multi-cloud cluster.

  Raises:
      UnsupportedClusterVersion: cluster version is not supported.
      MissingClusterField: expected cluster field is missing.
  """
  if cluster.controlPlane is None or cluster.controlPlane.version is None:
    raise MissingClusterField('Cluster is missing cluster version.')
  else:
    version = semver.SemVer(cluster.controlPlane.version)
    if version < semver.SemVer('1.20.0'):
      raise UnsupportedClusterVersion(
          'The command get-credentials is supported in cluster version 1.20 '
          'and newer. For older versions, use get-kubeconfig.')


def _GetCaData(pem):
  # Field certificate-authority-data in kubeconfig
  # expects a base64 encoded string of a PEM.
  return base64.b64encode(pem.encode('utf-8')).decode('utf-8')
