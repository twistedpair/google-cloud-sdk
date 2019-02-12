# *- coding: utf-8 -*- #
# Copyright 2019 Google Inc. All Rights Reserved.
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
"""Utils for GKE Hub memberships commands."""
import os
import subprocess

from googlecloudsdk.api_lib.container import kubeconfig as kconfig
from googlecloudsdk.api_lib.container import util as c_util
from googlecloudsdk.api_lib.util import apis as core_apis
from googlecloudsdk.calliope import exceptions as calliope_exceptions
from googlecloudsdk.core import log
from googlecloudsdk.core import properties

SAVE_MANIFEST_MSG = """\
Manifest saved to {0}, \
Please apply the manifest to your cluster with `kubectl apply -f {1}` and run \
`gcloud alpha container cluster-registrations create` with `--agent-deployed` flag.
You must have `cluster-admin` privilege in order to deploy the manifest. \
This file contains sensitive data,
please treat it with the same discretion of your service account key file."""

SAVE_MANIFEST_FILE = """{0}_{1}_connect_agent_manifest.yaml"""

KUBECTL_TIMEOUT = '20s'


def SetParentCollection(ref, args, request):
  """Set parent collection to global for created resources.

  Args:
    ref: reference to the membership object.
    args: command line arguments.
    request: API request to be issued
  Returns:
    modified request
  """
  del ref, args
  request.parent = request.parent + '/locations/global'
  return request


def PopulateMembership(ref, args, request):
  """Populate membership object with metadata read from the cluster.

  Args:
    ref: reference to the membership object.
    args: command line arguments.
    request: API request to be issued
  Returns:
    modified request
  """
  kubeconfig, context = GetKubeconfigAndContext(args)

  cmd = [
      'get', 'namespace', 'kube-system', '-o', 'jsonpath=\'{.metadata.uid}\''
  ]

  membership = GetMembership(ref)

  # Warn if kubectl is not installed and ask user to manually fill in
  # resource_id field.
  if not c_util.CheckKubectlInstalled():
    raise c_util.Error('kubectl not installed')

  out, err, returncode = RunKubectl(kubeconfig, context, cmd, '')
  if returncode != 0:
    raise c_util.Error('Failed to get the UID of cluster: {0}'.format(err))

  membership.name = out
  membership.endpoint = core_apis.GetMessagesModule(
      'gkehub', 'v1beta1').MembershipEndpoint(
          resourceId=out)
  request.membershipId = membership.name
  request.membership = membership
  args.membershipsId = membership.name

  return request


def GetMembership(ref):
  messages = core_apis.GetMessagesModule('gkehub', 'v1beta1')
  return messages.Membership(description=ref.membershipsId)


def DeployConnectAgent(response, args):
  """Python hook to deploy connect agent.

  Args:
    response: response to be returned.
    args: arguments of the command.
  Returns:
    modified response
  """
  if args.agent_deployed:
    return response

  # project = properties.VALUES.core.project.GetOrFail()
  # Exit if kubectl is not installed.
  if not c_util.CheckKubectlInstalled():
    log.warning('kubectl not installed, could not install the connect agent. ')
    return

  # TODO(b/123907152): implement the manifest after Docker image is ready.

  return response


def GetKubeconfigAndContext(args):
  """Get kubeconfig and context of the cluster from arguments.

  Args:
    args: command line arguments
  Returns:
    the kubeconfig and context name
  """
  kubeconfig = args.kubeconfig_file or os.environ.get('KUBECONFIG')
  if not kubeconfig:
    raise calliope_exceptions.MinimumArgumentException(
        ['--from-kubeconfig'],
        'Please specify kubeconfig or set $KUBECONFIG environment variable')
  kc = kconfig.Kubeconfig.LoadFromFile(kubeconfig)

  context_name = args.context
  if not context_name:
    context_name = kc.current_context

  if not kc.contexts[context_name]:
    raise c_util.Error('context {0} does not exist in kubeconfig {1}'.format(
        context_name, kubeconfig))

  return kubeconfig, context_name


def RunKubectl(kubeconfig, context, args, manifest):
  """Run kubectl command towards the cluster specified.

  Args:
    kubeconfig: filepath of the kubeconfig
    context: context within the kubeconfig, default to current-context
    args: command line arguments
    manifest: manifest to be injected through stdin
  Returns:
    stdout, stderr, return code
  """
  cmd = [
      c_util.CheckKubectlInstalled(), '--context', context, '--kubeconfig',
      kubeconfig, '--request-timeout', KUBECTL_TIMEOUT
  ]
  cmd.extend(args)

  p = subprocess.Popen(
      cmd,
      stdin=subprocess.PIPE,
      stdout=subprocess.PIPE,
      stderr=subprocess.PIPE)
  out, err = p.communicate(manifest)
  return out, err, p.returncode


def PrepareMembershipDeletion(response, args):
  TryDeleteNamespace(args)
  return response


def TryDeleteNamespace(args):
  """Delete the namespace in the cluster that contains the connect agent.

  Args:
    args: an argparse namespace. All arguments that were provided to this
      command invocation.
  """
  # The namespace is created by
  # //cloud/kubernetes/hub/enrollment/connect_agent.go
  namespace = 'gke-connect-{0}'.format(
      properties.VALUES.core.project.GetOrFail())
  cleanup_msg = 'please delete namespace {0} manually in your cluster.'.format(
      namespace)
  # Warn if kubectl is not installed.
  if not c_util.CheckKubectlInstalled():
    log.warning('kubectl not installed. {0}'.format(cleanup_msg))
    return
  try:
    kubeconfig, context = GetKubeconfigAndContext(args)
  except calliope_exceptions.MinimumArgumentException:
    log.warning(
        'No Kubeconfig specified and $KUBECONFIG is not set. {0}'.format(
            cleanup_msg))
    return

  cmd = ['delete', 'namespaces', namespace]

  out, err, returncode = RunKubectl(kubeconfig, context, cmd, '')
  log.status.Print(out)
  if returncode != 0:
    log.warning('Failed to delete namespace {0}. {1}'.format(err, cleanup_msg))
